"""Fully offline tests; providers are replaced with deterministic fixtures."""
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app import auto_research as ar, research, cache
from app.schemas import SocialPost

client = TestClient(app)
FILINGS = [dict(accession='0001234567-26-000001', ticker='EXMP', company_name='ExampleCorp',
                form='10-Q', period_end='2026-06-30', filed_at='2026-07-23')]
TEXT = ('ExampleCorp reported revenue of $24.5 billion for the quarter ended June 30, 2026. '
        'Adjusted EPS reached $2.15 and operating profit increased compared with last year. '
        'Management also highlighted risks around data center construction and rising investment.')


def prepare(monkeypatch):
    monkeypatch.setattr(research, '_filings_for_ticker', lambda ticker: ('ExampleCorp', FILINGS))
    monkeypatch.setattr(research, 'import_filing', lambda ticker, accession: {
        'text': TEXT, 'company_name': 'ExampleCorp', 'ticker': ticker,
        'fiscal_period': 'Quarter ending 2026-06-30', 'filed_at': '2026-07-23',
        'source_url': 'https://www.sec.gov/Archives/edgar/data/1234567/file.htm',
        'form': '10-Q'})
    monkeypatch.setattr(ar, 'discover_gdelt', lambda company, around, max_articles: [
        dict(url='https://example.com/earnings', title='ExampleCorp earnings in focus', outlet='example.com')])
    monkeypatch.setattr(ar, 'bluesky_posts', lambda company, ticker, around: [
        SocialPost(platform='Bluesky', author='analyst.example', url='https://bsky.app/profile/analyst.example/post/abc123',
                   text='ExampleCorp earnings reflect rapidly growing revenue.', created_at='2026-07-23T12:00:00Z', likes=6)])
    monkeypatch.setattr(ar, 'x_posts', lambda company, ticker, around: [])
    from app.analysis.metrics import extract_metrics
    monkeypatch.setattr(ar.xbrl, 'extract_companyfacts',
                        lambda filing, period: (extract_metrics(TEXT, period), ['SEC structured facts test fixture']))
    monkeypatch.setattr(cache, 'store', lambda result: None)


def test_one_ticker_auto_analysis_and_source_attribution(monkeypatch):
    prepare(monkeypatch)
    from app import analysis
    from app.ingest import ArticleError
    monkeypatch.setattr('app.analysis.service.fetch_article', lambda url: (_ for _ in ()).throw(ArticleError('blocked')))
    response = client.post('/api/v1/research/auto', json={'ticker': 'EXMP'})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['ticker'] == 'EXMP'
    assert result['data_origin'] == 'sec_filing'
    assert result['source_document_type'] == '10-Q'
    assert result['announcement_date'] is None  # filing date never silently substituted
    assert result['sources'][0]['extraction_status'] == 'metadata_only'
    assert result['sources'][0]['summary'] == []
    assert result['social_posts'][0]['platform'] == 'Bluesky'
    assert any(x['name'] == 'Revenue' for x in result['metrics'])


def test_auto_respects_period_end(monkeypatch):
    prepare(monkeypatch)
    result = client.post('/api/v1/research/auto', json={'ticker': 'EXMP', 'period_end': '2025-03-31'})
    assert result.status_code == 422
    assert 'period' in result.json()['detail'].lower()


def test_gdelt_domain_diversity_and_https_only(monkeypatch):
    def fake_json(url, params):
        return {'articles': [
            {'url': 'https://source-a.com/1', 'title': 'ExampleCorp quarterly earnings overview', 'seendate': '20261110000000'},
            {'url': 'https://source-a.com/2', 'title': 'ExampleCorp quarterly results again'},
            {'url': 'http://local.invalid/3', 'title': 'Unsafe non-https source'},
            {'url': 'https://source-b.com/4', 'title': 'ExampleCorp quarterly results at source B'},
        ]}
    monkeypatch.setattr(ar, '_fixed_json', fake_json)
    items = ar.discover_gdelt('ExampleCorp', None, 8)
    assert len(items) == 2
    assert items[0]['first_seen'].startswith('2026-11-10')
    assert items[1]['outlet'] == 'source-b.com'


def test_bluesky_posts_link_and_date_filter(monkeypatch):
    monkeypatch.setattr(ar, '_fixed_json', lambda url, params: {'posts': [
        {'uri': 'at://did:plc:abcdef/app.bsky.feed.post/3abc',
         'record': {'text': 'ExampleCorp earnings outlook is better than expected this quarter.', 'createdAt':'2026-07-24T12:00:00Z'},
         'author': {'handle':'finance.bsky.social'}, 'likeCount': 14},
        {'uri': 'at://did:plc:abcdef/app.bsky.feed.post/3abd',
         'record': {'text': 'ExampleCorp earnings in a completely different year are unrelated.', 'createdAt':'2025-02-24T12:00:00Z'},
         'author': {'handle':'other.bsky.social'}, 'likeCount': 3},
    ]})
    posts = ar.bluesky_posts('ExampleCorp', 'EXMP', date(2026, 7, 23))
    assert len(posts) == 1
    assert posts[0].url == 'https://bsky.app/profile/finance.bsky.social/post/3abc'


def test_schema_limits_and_no_untrusted_host():
    assert client.post('/api/v1/research/auto', json={'ticker': 'BAD TICKER'}).status_code == 422
    from pytest import raises
    with raises(ValueError):
        ar._fixed_json('https://127.0.0.1/secrets', {})
