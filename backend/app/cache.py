"""Small local SQLite store for result metadata and structured output.

Opt-out: FINPULSE_DISABLE_CACHE=1. Never store API keys. Cached evidence is
retained locally, so don't analyze confidential text on shared machines.
"""
import os
from pathlib import Path
import sqlite3
from app.schemas import AnalyzeResponse


def db_path() -> Path:
    return Path(os.getenv('FINPULSE_DB_PATH', str(Path(__file__).resolve().parents[1] / '.local' / 'finpulse.sqlite3')))


def store(result: AnalyzeResponse) -> None:
    if os.getenv('FINPULSE_DISABLE_CACHE') == '1':
        return
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=3) as db:
        db.execute('CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, company TEXT NOT NULL, ticker TEXT NOT NULL, payload TEXT NOT NULL)')
        db.execute('INSERT OR REPLACE INTO analyses VALUES (?, ?, ?, ?, ?)',
                   (result.analysis_id, result.analyzed_at.isoformat(), result.company_name,
                    result.ticker, result.model_dump_json()))


def load(analysis_id: str) -> AnalyzeResponse | None:
    if os.getenv('FINPULSE_DISABLE_CACHE') == '1':
        return None
    path = db_path()
    if not path.exists():
        return None
    with sqlite3.connect(path, timeout=3) as db:
        row = db.execute('SELECT payload FROM analyses WHERE id=?', (analysis_id,)).fetchone()
    return AnalyzeResponse.model_validate_json(row[0]) if row else None
