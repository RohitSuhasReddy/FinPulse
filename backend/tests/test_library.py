"""Manual earnings-report library and multi-quarter comparison regression tests."""
from fastapi.testclient import TestClient
from app.main import app
from app import cache

client = TestClient(app)
TEXT = ('ExampleCorp revenue was $24.5 billion for the quarter ended June 30, 2026. '
        'Operating income increased and adjusted EPS reached $2.15. '
        'Management expects investment in new systems to continue over the next year.')


def request(ticker='EXMP', period='Q2 2026'):
    return dict(company_name='ExampleCorp', ticker=ticker, fiscal_period=period,
                earnings_text=TEXT, news_sources=[])


def test_library_persists_compares_and_deletes(tmp_path, monkeypatch):
    monkeypatch.setenv('FINPULSE_DB_PATH', str(tmp_path / 'library.sqlite3'))
    monkeypatch.delenv('FINPULSE_DISABLE_CACHE', raising=False)
    a = client.post('/api/v1/analyze', json=request()).json()
    b = client.post('/api/v1/analyze', json=request('EXMP', 'Q1 2026')).json()
    c = client.post('/api/v1/analyze', json=request('EXMP', 'Q3 2026')).json()
    listing = client.get('/api/v1/analyses').json()
    assert len(listing) == 3
    assert {r['analysis_id'] for r in listing} == {a['analysis_id'], b['analysis_id'], c['analysis_id']}
    assert 'earnings_text' not in str(listing)
    assert len(client.get('/api/v1/analyses?ticker=EXMP').json()) == 3
    assert client.get('/api/v1/analyses/' + a['analysis_id']).json()['fiscal_period'] == 'Q2 2026'
    comparison = client.post('/api/v1/compare/multi',
                             json={'analysis_ids': [a['analysis_id'], c['analysis_id'], b['analysis_id']]}).json()
    assert [r['fiscal_period'] for r in comparison['periods']] == ['Q1 2026', 'Q2 2026', 'Q3 2026']
    assert comparison['ticker'] == 'EXMP'
    revenue = next(metric for metric in comparison['metrics'] if metric['name'] == 'Revenue')
    assert revenue['values'] == [24_500_000_000] * 3
    assert revenue['available_periods'] == 3
    assert revenue['change_percent'] == 0
    assert all(revenue['evidence'])
    assert client.delete('/api/v1/analyses/' + a['analysis_id']).status_code == 204
    assert client.get('/api/v1/analyses/' + a['analysis_id']).status_code == 404
    assert len(client.get('/api/v1/analyses').json()) == 2


def test_multi_comparison_validates_ticker_and_unique_period(tmp_path, monkeypatch):
    monkeypatch.setenv('FINPULSE_DB_PATH', str(tmp_path / 'validate.sqlite3'))
    monkeypatch.delenv('FINPULSE_DISABLE_CACHE', raising=False)
    a = client.post('/api/v1/analyze', json=request()).json()['analysis_id']
    b = client.post('/api/v1/analyze', json=request('DIFF','Q1 2026')).json()['analysis_id']
    c = client.post('/api/v1/analyze', json=request('EXMP','Q2 2026')).json()['analysis_id']
    assert client.post('/api/v1/compare/multi', json={'analysis_ids':[a,b]}).status_code == 422
    assert client.post('/api/v1/compare/multi', json={'analysis_ids':[a,c]}).status_code == 422
    assert client.post('/api/v1/compare/multi', json={'analysis_ids':[a,a]}).status_code == 422


def test_optout_does_not_create_database(tmp_path, monkeypatch):
    path = tmp_path / 'disabled.sqlite3'
    monkeypatch.setenv('FINPULSE_DB_PATH', str(path))
    monkeypatch.setenv('FINPULSE_DISABLE_CACHE', '1')
    client.post('/api/v1/analyze', json=request())
    assert client.get('/api/v1/analyses').json() == []
    assert not path.exists()


def test_supplied_headline_is_never_summarized_as_article():
    from app.analysis.service import analyze
    from app.schemas import AnalyzeRequest
    news = {'title':'ExampleCorp reports growth in earnings', 'outlet':'News One',
            'url':'https://publisher.example/news', 'headline_only':True}
    result = analyze(AnalyzeRequest(**{**request(), 'news_sources':[news]}))
    assert result.sources[0].extraction_status == 'metadata_only'
    assert result.sources[0].input_origin == 'headline_only'
    assert result.sources[0].summary == []
    assert result.sources[0].sentiment_label is None
    assert not any(item.news_evidence for item in result.comparison)


def test_auto_research_routes_removed():
    assert client.get('/api/v1/news/discover?company=ExampleCorp').status_code == 404
    assert client.get('/api/v1/filings/EXMP').status_code == 404
    assert client.post('/api/v1/research/auto', json={'ticker':'EXMP'}).status_code == 404
