"""FinPulse API — source-linked, text-first and local-first."""
from datetime import date
from typing import Literal
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import AnalyzeRequest, AnalyzeResponse, ArticleRequest, ArticleResponse, StockContextResponse
from app.analysis.service import analyze
from app.ingest import fetch_article, ArticleError
from app.stock import get_stock
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
