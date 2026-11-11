"""The optional Gemini market lens cannot interrupt or fabricate earnings analysis."""
from datetime import date
from app.analysis.service import analyze
from app.schemas import AnalyzeRequest, StockContextResponse, StockPoint
from app import insights

TEXT = ('ExampleCorp reported quarterly revenue of $24.5 billion. '
        'Operating margin improved to 18.4%. '
        'Management discussed investments and future risks in the business. ')


def report(earnings_date='2026-10-16'):
    return analyze(AnalyzeRequest(
        company_name='ExampleCorp', ticker='EXMP', fiscal_period='FY2026 Q3',
        earnings_text=TEXT, announcement_date=earnings_date, market_timing='unknown',
    ))


def test_market_interpretation_without_key_keeps_numeric_observations(tmp_path, monkeypatch):
    monkeypatch.setenv('FINPULSE_DB_PATH', str(tmp_path / 'market.sqlite3'))
    monkeypatch.delenv('FINPULSE_DISABLE_CACHE', raising=False)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    points = [
        StockPoint(date=date(2026, 10, 9), close=100, volume=100),
        StockPoint(date=date(2026, 10, 15), close=105, volume=200),
        StockPoint(date=date(2026, 10, 19), close=110, volume=180),
        StockPoint(date=date(2026, 10, 20), close=115, volume=170),
    ]
    monkeypatch.setattr(insights, 'get_stock', lambda ticker, day, timing: StockContextResponse(
        ticker=ticker, points=points, earnings_date=day, market_timing=timing,
        currency='USD', price_basis='Unadjusted daily close'))
    result = insights.interpret(report())
    assert result['status'] == 'not_configured'
    assert result['interpretation'] is None
    assert result['before']['change_percent'] == 5.0
    assert result['after']['change_percent'] == 4.55
    assert len(result['stock']['points']) == 4


def test_missing_date_does_not_fetch_market_prices(monkeypatch):
    monkeypatch.setattr(insights, 'get_stock', lambda *args: (_ for _ in ()).throw(RuntimeError('must not fetch')))
    result = insights.interpret(report(None))
    assert result['status'] == 'missing_date'
    assert result['stock'] is None


def test_no_outbound_calls_for_headline_only_sources(monkeypatch):
    from app.analysis import service
    # The service has no publisher download function in the manual-only workflow.
    assert not hasattr(service, 'fetch_article')
    analyzed = analyze(AnalyzeRequest(company_name='ExampleCorp', ticker='EXMP',
        fiscal_period='FY2026 Q3', earnings_text=TEXT,
        news_sources=[{'title':'ExampleCorp results and margins explored',
                       'outlet':'A publisher','url':'https://example.com/earnings',
                       'headline_only':True}]))
    assert analyzed.sources[0].summary == []
    assert analyzed.sources[0].extraction_status == 'metadata_only'
