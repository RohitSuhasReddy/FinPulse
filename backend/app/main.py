"""FinPulse API — source-linked, text-first and local-first."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field
from app import research, auto_research
from app.auto_research import AutoResearchInput
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import AnalyzeRequest, AnalyzeResponse, ArticleRequest, ArticleResponse, StockContextResponse
from app.analysis.service import analyze
from app.ingest import fetch_article, ArticleError
from app.stock import get_stock, get_recent_stock
from app import cache

app = FastAPI(title='FinPulse API', version='1.0.0',
              description='Evidence-linked earnings and multi-source news intelligence')
app.add_middleware(CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])


@app.get('/api/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'service': 'finpulse-api', 'version': '1.0.0'}


@app.post('/api/v1/analyze', response_model=AnalyzeResponse)
def analyze_earnings(payload: AnalyzeRequest) -> AnalyzeResponse:
    result = analyze(payload)
    try:
        cache.store(result)
    except OSError:
        result.warnings.append('Local cache could not be written; analysis was returned without persistence.')
    return result


@app.get('/api/v1/analyses/{analysis_id}', response_model=AnalyzeResponse)
def saved_analysis(analysis_id: str) -> AnalyzeResponse:
    if len(analysis_id) != 16 or any(c not in '0123456789abcdef' for c in analysis_id):
        raise HTTPException(404, 'Analysis not found')
    try:
        result = cache.load(analysis_id)
    except OSError:
        result = None
    if result is None:
        raise HTTPException(404, 'Analysis not found')
    return result


@app.post('/api/v1/articles/extract', response_model=ArticleResponse)
def extract_article(body: ArticleRequest) -> ArticleResponse:
    try:
        return fetch_article(str(body.url))
    except ArticleError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post('/api/v1/pdf/extract')
async def extract_pdf(file: UploadFile = File(...)) -> dict[str, str | int]:
    if file.content_type not in ('application/pdf', 'application/octet-stream'):
        raise HTTPException(415, 'Upload a PDF file')
    data = await file.read(8_000_001)
    if len(data) > 8_000_000:
        raise HTTPException(413, 'PDF must be 8 MB or smaller')
    try:
        import fitz
        with fitz.open(stream=data, filetype='pdf') as document:
            if document.page_count > 80:
                raise HTTPException(413, 'PDF must have 80 pages or fewer')
            text = '\n'.join(page.get_text('text') for page in document)[:350_000].strip()
            pages = document.page_count
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, 'PDF could not be read. Paste extracted text instead.') from exc
    if len(text) < 80:
        raise HTTPException(422, 'PDF has insufficient extractable text. Paste clean text instead.')
    return {'text': text, 'pages': pages}


@app.get('/api/v1/stocks/{ticker}', response_model=StockContextResponse)
def stock_context(ticker: str, announcement_date: date,
                  market_timing: Literal['before_open', 'after_close', 'unknown'] = Query('unknown')) -> StockContextResponse:
    try:
        return get_stock(ticker, announcement_date, market_timing)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

# Saved research library (local SQLite, no login or cloud sync).
@app.get('/api/v1/analyses')
def list_analyses(ticker: str | None = None, limit: int = Query(100, ge=1, le=200)) -> list[dict]:
    try:
        return cache.list_reports(ticker=ticker, limit=limit)
    except OSError as exc:
        raise HTTPException(503, 'Saved report library is temporarily unavailable') from exc


@app.delete('/api/v1/analyses/{analysis_id}', status_code=204)
def delete_analysis(analysis_id: str):
    if len(analysis_id) != 16 or any(c not in '0123456789abcdef' for c in analysis_id):
        raise HTTPException(404, 'Analysis not found')
    try:
        deleted = cache.delete(analysis_id)
    except OSError as exc:
        raise HTTPException(503, 'Could not access saved report library') from exc
    if not deleted:
        raise HTTPException(404, 'Analysis not found')


@app.get('/api/v1/compare')
def compare_saved(left: str, right: str) -> dict:
    if any(len(x) != 16 or any(c not in '0123456789abcdef' for c in x) for x in (left, right)):
        raise HTTPException(422, 'Invalid analysis IDs')
    try:
        a, b = cache.load(left), cache.load(right)
    except OSError as exc:
        raise HTTPException(503, 'Could not load saved reports') from exc
    if not a or not b:
        raise HTTPException(404, 'Both saved reports must exist in this local library')
    return cache.compare_reports(a, b)


@app.get('/api/v1/news/discover')
def discover_coverage(company: str = Query(min_length=2, max_length=120),
                      ticker: str = Query('', max_length=12),
                      date: date | None = None) -> dict:
    try:
        return research.discover_news(company, ticker, date)
    except research.ResearchError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get('/api/v1/filings/{ticker}')
def sec_filings(ticker: str) -> dict:
    try:
        return research.filings(ticker)
    except research.ResearchError as exc:
        status = 503 if 'FINPULSE_SEC_USER_AGENT' in str(exc) or 'unavailable' in str(exc) else 422
        raise HTTPException(status, str(exc)) from exc


class FilingSelection(BaseModel):
    ticker: str = Field(min_length=1, max_length=12, pattern=r'^[A-Za-z0-9.\-]+$')
    accession: str = Field(pattern=r'^\d{10}-\d{2}-\d{6}$')


@app.post('/api/v1/filings/import')
def import_sec_filing(selection: FilingSelection) -> dict:
    try:
        return research.import_filing(selection.ticker, selection.accession)
    except research.ResearchError as exc:
        status = 503 if 'FINPULSE_SEC_USER_AGENT' in str(exc) or 'unavailable' in str(exc) else 422
        raise HTTPException(status, str(exc)) from exc


@app.post('/api/v1/research/auto', response_model=AnalyzeResponse)
def analyze_automatically(payload: AutoResearchInput) -> AnalyzeResponse:
    """A ticker-first, one-shot research request. Each provider can fail independently."""
    try:
        return auto_research.auto_research(payload)
    except research.ResearchError as exc:
        status = 503 if ('FINPULSE_SEC_USER_AGENT' in str(exc) or 'unavailable' in str(exc)) else 422
        raise HTTPException(status, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(503, 'Automated research unavailable. Check data source connectivity or try a manual PDF.') from exc


@app.get('/api/v1/stocks/{ticker}/recent', response_model=StockContextResponse)
def stock_recent_context(ticker: str) -> StockContextResponse:
    try:
        return get_recent_stock(ticker)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
