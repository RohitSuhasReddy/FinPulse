"""Fast, local-only regression tests for the new report library and integrations."""
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app import cache, research
import pytest

client = TestClient(app)
TEXT = ('ExampleCorp revenue was $24.5 billion for the quarter ended June 30, 2026. '
        'Operating income increased and adjusted EPS reached $2.15. '
        'Management expects investment in new systems to continue over the next year.')


def request(ticker='EXMP', period='Q2 2026'):
    return dict(company_name='ExampleCorp', ticker=ticker, fiscal_period=period,
                earnings_text=TEXT, news_sources=[])


def test_library_persists_and_lists(tmp_path, monkeypatch):
    monkeypatch.setenv('FINPULSE_DB_PATH', str(tmp_path / 'library.sqlite3'))
    monkeypatch.delenv('FINPULSE_DISABLE_CACHE', raising=False)
    a = client.post('/api/v1/analyze', json=request()).json()
    b = client.post('/api/v1/analyze', json=request('EXMP', 'Q1 2026')).json()
    listing = client.get('/api/v1/analyses').json()
    assert len(listing) == 2
    assert {r['analysis_id'] for r in listing} == {a['analysis_id'], b['analysis_id']}
    assert 'earnings_text' not in str(listing)
    assert len(client.get('/api/v1/analyses?ticker=EXMP').json()) == 2
    assert client.get('/api/v1/analyses/' + a['analysis_id']).json()['fiscal_period'] == 'Q2 2026'
    compare = client.get('/api/v1/compare', params={'left': a['analysis_id'], 'right': b['analysis_id']}).json()
    assert compare['left']['ticker'] == 'EXMP'
    assert any(m['name'] == 'Revenue' for m in compare['metrics'])
    assert client.delete('/api/v1/analyses/' + a['analysis_id']).status_code == 204
    assert client.get('/api/v1/analyses/' + a['analysis_id']).status_code == 404
    assert len(client.get('/api/v1/analyses').json()) == 1


def test_optout_does_not_create_database(tmp_path, monkeypatch):
    path = tmp_path / 'disabled.sqlite3'
    monkeypatch.setenv('FINPULSE_DB_PATH', str(path))
    monkeypatch.setenv('FINPULSE_DISABLE_CACHE', '1')
    client.post('/api/v1/analyze', json=request())
    assert client.get('/api/v1/analyses').json() == []
    assert not path.exists()


def test_discovered_headline_never_fabricates_evidence(monkeypatch):
    from app.analysis.service import analyze
    from app.schemas import AnalyzeRequest
    news = {'title': 'ExampleCorp reports growth in earnings', 'outlet': 'News One',
            'url': 'https://news.google.com/rss/articles/example123', 'headline_only': True}
    result = analyze(AnalyzeRequest(**{**request(), 'news_sources': [news]}))
    assert len(result.sources) == 1
    source = result.sources[0]
    assert source.extraction_status == 'metadata_only'
    assert source.summary == []
    assert source.themes == []
    assert source.sentiment_label is None
    assert source.input_origin == 'headline_only'
    assert not any(c.news_evidence for c in result.comparison)


def test_google_news_feed_discovery(monkeypatch):
    rss = b'''<rss><channel><item><title>ExampleCorp earnings - News Outlet</title>
    <link>https://news.google.com/rss/articles/sample</link>
    <source>News Outlet</source><pubDate>Mon, 09 Nov 2026 10:00:00 GMT</pubDate>
    </item></channel></rss>'''
    monkeypatch.setattr(research, '_get', lambda *args, **kwargs: rss)
    res = client.get('/api/v1/news/discover?company=ExampleCorp&date=2026-11-09')
    assert res.status_code == 200
    assert res.json()['items'][0]['body_available'] is False
    assert res.json()['items'][0]['outlet'] == 'News Outlet'


def test_sec_requires_contact_identity(monkeypatch):
    monkeypatch.delenv('FINPULSE_SEC_USER_AGENT', raising=False)
    res = client.get('/api/v1/filings/GOOGL')
    assert res.status_code == 503
    assert 'FINPULSE_SEC_USER_AGENT' in res.json()['detail']


def test_sec_import_uses_document_from_verified_listing(monkeypatch):
    monkeypatch.setattr(research, '_filings_for_ticker', lambda ticker: ('ExampleCorp', [dict(
        accession='0001234567-26-000001', ticker='EXMP', company_name='ExampleCorp',
        form='10-Q', period_end='2026-06-30', filed_at='2026-07-22', cik=1234567,
        document='sample.htm')]))
    monkeypatch.setattr(research, '_get', lambda *args, **kwargs: b'<html><body><h1>10-Q</h1><p>Revenue of $24.5 billion and earnings per share of $2.15 in this reporting period. The company reported positive operating income performance throughout the quarter.</p></body></html>')
    resp = client.post('/api/v1/filings/import', json={'ticker':'EXMP','accession':'0001234567-26-000001'})
    assert resp.status_code == 200
    assert '$24.5 billion' in resp.json()['text']
    assert resp.json()['form'] == '10-Q'
    wrong = client.post('/api/v1/filings/import', json={'ticker':'EXMP','accession':'0001234567-26-000002'})
    assert wrong.status_code == 422
