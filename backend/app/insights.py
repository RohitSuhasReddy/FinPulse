"""Optional, isolated Gemini commentary on *observed* pre/post earnings price data.

Core earnings analysis never depends on a Gemini key or stock-data connectivity.
"""
import json
import os
import sqlite3
from datetime import timedelta
from app.schemas import AnalyzeResponse
from app.stock import get_stock
from app import cache


def _period(points, start, end):
    data = [p for p in points if start <= p.date <= end]
    if not data:
        return None
    first, last = data[0], data[-1]
    return {
        "start": first.date.isoformat(), "end": last.date.isoformat(),
        "start_close": first.close, "end_close": last.close,
        "trading_sessions": len(data),
        "change_percent": round((last.close / first.close - 1) * 100, 2)
        if first.close and len(data) >= 2 else None,
    }


def _cached(analysis_id: str):
    if os.getenv('FINPULSE_DISABLE_CACHE') == '1' or not cache.db_path().exists():
        return None
    with cache._connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS market_interpretations '
                   '(analysis_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        row = db.execute('SELECT payload FROM market_interpretations WHERE analysis_id=?',
                         (analysis_id,)).fetchone()
    return json.loads(row['payload']) if row else None


def _save(analysis_id: str, content: dict):
    if os.getenv('FINPULSE_DISABLE_CACHE') == '1':
        return
    with cache._connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS market_interpretations '
                   '(analysis_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        db.execute('INSERT OR REPLACE INTO market_interpretations VALUES (?, ?)',
                   (analysis_id, json.dumps(content)))


def interpret(report: AnalyzeResponse) -> dict:
    if report.announcement_date is None:
        return {"status": "missing_date", "interpretation": None, "stock": None,
                "before": None, "after": None,
                "notice": "Add the earnings announcement date to compare the surrounding weeks."}
    stock = get_stock(report.ticker, report.announcement_date, report.market_timing)
    day = report.announcement_date
    before = _period(stock.points, day - timedelta(days=7), day - timedelta(days=1))
    after = _period(stock.points, day + timedelta(days=1), day + timedelta(days=7))
    result = {
        "status": "unavailable", "interpretation": None, "stock": stock.model_dump(mode="json"),
        "before": before, "after": after,
        "notice": "The two calendar-week windows contain historical trading sessions, not forecasts. "
                  "Price changes do not establish why a stock moved.",
    }
    # Stock chart and dated observations are useful even without the LLM.
    saved = _cached(report.analysis_id)
    if saved:
        result["status"] = "ready"
        result["interpretation"] = saved.get("interpretation")
        result["model"] = saved.get("model")
        return result
    if not before or not after or before["change_percent"] is None or after["change_percent"] is None:
        result["notice"] += " Insufficient trading sessions for both windows."
        return result
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        result["status"] = "not_configured"
        result["notice"] += " Gemini commentary is optional; set GEMINI_API_KEY on the backend to enable."
        return result
    model = os.getenv("FINPULSE_GEMINI_MODEL", "gemini-3.5-flash").strip()
    evidence = {
        "ticker": report.ticker, "period": report.fiscal_period,
        "announcement_date": day.isoformat(), "announcement_timing": report.market_timing,
        "price_basis": stock.price_basis, "currency": stock.currency,
        "before_week": before, "after_week": after,
        "reported_metrics": [
            {"metric": m.name, "value": m.normalized_value, "unit": m.unit,
             "currency": m.currency, "period": m.reporting_period, "basis": m.metric_variant,
             "source_excerpt": m.evidence.text[:320]}
            for m in report.metrics if m.extraction_status == "extracted"
        ][:12],
        "report_excerpts": [h.text for h in report.summary[:6]],
    }
    instruction = (
        "You are writing a factual market-observation note. Use ONLY the supplied JSON. "
        "Write 110-160 words with two labeled paragraphs: 'Observed move' and 'Possible context'. "
        "Give numerical changes with their windows, acknowledge sample sizes and any missing "
        "announcement timing. Mention report claims as possible context, NEVER as a proven cause. "
        "You have no external news, sector benchmark or analyst expectations. Do NOT invent them. "
        "Do not forecast price direction, assign probability percentages, give buy/sell advice, "
        "or claim that post-report price movement proves earnings caused it. "
        "If evidence is too weak, explicitly say so."
    )
    try:
        import httpx
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json={"systemInstruction": {"parts": [{"text": instruction}]},
                  "contents": [{"role": "user", "parts": [{"text": json.dumps(evidence)}]}],
                  "generationConfig": {"temperature": 0.2, "maxOutputTokens": 450}},
            timeout=18,
        )
        response.raise_for_status()
        generated = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if not generated:
            raise ValueError("Empty model response")
        result.update({"status": "ready", "interpretation": generated, "model": model})
        try:
            _save(report.analysis_id, {"interpretation": generated, "model": model})
        except (OSError, sqlite3.Error):
            result["notice"] += " The commentary could not be saved locally."
    except (ValueError, KeyError, IndexError, OSError, Exception):
        # Gemini has no authority to interrupt report analysis or stock chart rendering.
        result["status"] = "unavailable"
        result["notice"] += " Optional Gemini interpretation is temporarily unavailable."
    return result
