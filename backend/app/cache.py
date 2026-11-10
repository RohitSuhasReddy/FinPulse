"""Local SQLite report library. Stores evidence-linked results, not uploaded PDFs.

Reports persist across backend restarts. Set FINPULSE_DISABLE_CACHE=1 to opt out.
"""
import os
from pathlib import Path
import sqlite3
from app.schemas import AnalyzeResponse


def db_path() -> Path:
    return Path(os.getenv('FINPULSE_DB_PATH', str(Path(__file__).resolve().parents[1] / '.local' / 'finpulse.sqlite3')))


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute('''CREATE TABLE IF NOT EXISTS analyses (
        id TEXT PRIMARY KEY, created_at TEXT NOT NULL, company TEXT NOT NULL,
        ticker TEXT NOT NULL, payload TEXT NOT NULL)''')
    db.execute('CREATE INDEX IF NOT EXISTS idx_analyses_ticker_date ON analyses(ticker, created_at DESC)')
    return db


def store(result: AnalyzeResponse) -> None:
    if os.getenv('FINPULSE_DISABLE_CACHE') == '1':
        return
    with _connect() as db:
        db.execute('''INSERT OR REPLACE INTO analyses(id, created_at, company, ticker, payload)
                      VALUES (?, ?, ?, ?, ?)''',
                   (result.analysis_id, result.analyzed_at.isoformat(),
                    result.company_name, result.ticker.upper(), result.model_dump_json()))


def load(analysis_id: str) -> AnalyzeResponse | None:
    if os.getenv('FINPULSE_DISABLE_CACHE') == '1' or not db_path().exists():
        return None
    with _connect() as db:
        row = db.execute('SELECT payload FROM analyses WHERE id=?', (analysis_id,)).fetchone()
    return AnalyzeResponse.model_validate_json(row['payload']) if row else None


def list_reports(ticker: str | None = None, limit: int = 100) -> list[dict]:
    """Metadata only: no source passages in the listing response."""
    if os.getenv('FINPULSE_DISABLE_CACHE') == '1' or not db_path().exists():
        return []
    with _connect() as db:
        if ticker:
            rows = db.execute('SELECT id, created_at, company, ticker, payload FROM analyses '
                              'WHERE ticker=? ORDER BY created_at DESC LIMIT ?',
                              (ticker.upper(), limit)).fetchall()
        else:
            rows = db.execute('SELECT id, created_at, company, ticker, payload FROM analyses '
                              'ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()
    from json import loads
    return [{'analysis_id': row['id'], 'company_name': row['company'], 'ticker': row['ticker'],
             'analyzed_at': row['created_at'],
             'fiscal_period': data.get('fiscal_period'),
             'announcement_date': data.get('announcement_date'),
             'extraction_version': data.get('extraction_version', 1),
             'metric_count': len(data.get('metrics', [])),
             'news_count': len(data.get('sources', []))}
            for row in rows for data in [loads(row['payload'])]]


def delete(analysis_id: str) -> bool:
    if os.getenv('FINPULSE_DISABLE_CACHE') == '1' or not db_path().exists():
        return False
    with _connect() as db:
        deleted = db.execute('DELETE FROM analyses WHERE id=?', (analysis_id,)).rowcount
    return deleted > 0


def compare_reports(left: AnalyzeResponse, right: AnalyzeResponse) -> dict:
    """Side-by-side exact-unit metric matches; not a recommendation engine."""
    def key(m):
        return (m.name.lower(), m.unit, m.currency, m.metric_variant)

    left_map = {key(m): m for m in left.metrics if m.normalized_value is not None
                and m.extraction_status == 'extracted'} if left.extraction_version >= 2 else {}
    right_map = {key(m): m for m in right.metrics if m.normalized_value is not None
                 and m.extraction_status == 'extracted'} if right.extraction_version >= 2 else {}
    common = sorted(left_map.keys() & right_map.keys())
    rows = []
    for k in common:
        a, b = left_map[k], right_map[k]
        rows.append({'name': a.name, 'unit': a.unit, 'currency': a.currency,
                     'metric_variant': a.metric_variant,
                     'left_value': a.normalized_value,
                     'right_value': b.normalized_value,
                     'left_evidence': a.evidence.model_dump(),
                     'right_evidence': b.evidence.model_dump()})
    notes = ['Comparisons use extracted values, not verified company filings. Check cited passages.']
    if left.ticker != right.ticker:
        notes.append('Different companies: numbers are side by side, not a like-for-like performance ranking.')
    if left.fiscal_period == right.fiscal_period and left.ticker == right.ticker:
        notes.append('Both reports have the same stated fiscal period. Check whether these are duplicate analyses.')
    if left.extraction_version < 2 or right.extraction_version < 2:
        notes.append('One or both analyses used the old financial extractor. Re-run those reports before comparing numeric values.')
    if not rows:
        notes.append('No extracted metrics share the same name, unit, currency and reported/adjusted basis.')
    return {'left': {'analysis_id': left.analysis_id, 'ticker': left.ticker, 'company_name': left.company_name,
                     'fiscal_period': left.fiscal_period},
            'right': {'analysis_id': right.analysis_id, 'ticker': right.ticker, 'company_name': right.company_name,
                      'fiscal_period': right.fiscal_period},
            'metrics': rows, 'notes': notes}
