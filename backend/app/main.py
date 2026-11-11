"""FinPulse API — source-linked, text-first and local-first."""
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from typing import Literal
from pydantic import BaseModel, Field
from app import insights
from app.multi_compare import compare_many
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import AnalyzeRequest, AnalyzeResponse, StockContextResponse
from app.analysis.service import analyze
from app.stock import get_stock
from app import cache

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

app = FastAPI(title='FinPulse API', version='1.0.0',
              description='Manual earnings-document intelligence and evidence-linked reports')
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


@app.post('/api/v1/pdf/extract')
async def extract_pdf(file: UploadFile = File(...)) -> dict[str, str | int]:
    if file.content_type not in ('application/pdf', 'application/octet-stream'):
        raise HTTPException(415, 'Upload a PDF file')
    data = await file.read(16_000_001)
    if len(data) > 16_000_000:
        raise HTTPException(413, 'PDF must be 16 MB or smaller')
    try:
        import fitz
        with fitz.open(stream=data, filetype='pdf') as document:
            if document.page_count > 150:
                raise HTTPException(413, 'PDF must have 150 pages or fewer')
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


class MultiComparisonSelection(BaseModel):
    analysis_ids: list[str] = Field(min_length=2)


@app.post('/api/v1/compare/multi')
def compare_selected(selection: MultiComparisonSelection) -> dict:
    if len(set(selection.analysis_ids)) != len(selection.analysis_ids):
        raise HTTPException(422, 'Do not select the same saved report twice')
    if any(len(x) != 16 or any(c not in '0123456789abcdef' for c in x) for x in selection.analysis_ids):
        raise HTTPException(422, 'Invalid analysis IDs')
    try:
        reports = [cache.load(report_id) for report_id in selection.analysis_ids]
    except OSError as exc:
        raise HTTPException(503, 'Saved reports could not be loaded') from exc
    if any(r is None for r in reports):
        raise HTTPException(404, 'One or more selected reports are missing')
    try:
        return compare_many(reports)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get('/api/v1/market/interpret/{analysis_id}')
def market_interpretation(analysis_id: str) -> dict:
    if len(analysis_id) != 16 or any(c not in '0123456789abcdef' for c in analysis_id):
        raise HTTPException(404, 'Analysis not found')
    report = cache.load(analysis_id)
    if report is None:
        raise HTTPException(404, 'Analysis not found')
    return insights.interpret(report)
