from datetime import date
import io
import json
from unittest.mock import patch
import fitz
from fastapi.testclient import TestClient
from app.main import app
from app.analysis.sentiment import classify, rules_sentiment
from app.schemas import StockPoint, AnalyzeRequest
from app.stock import session_context
from app import cache

client = TestClient(app)
SAMPLE = ('ExampleCorp reported revenue of $2.6 billion this quarter. '
          'Adjusted EPS was $1.15 and operating margin was 19.2%. '
          'Management noted strong cloud demand and ongoing supply chain risk. ')


def body():
    return {'company_name': 'ExampleCorp', 'ticker': 'TEST', 'fiscal_period': 'FY2026 Q1',
            'earnings_text': SAMPLE, 'announcement_date': '2026-10-16',
            'news_sources': [{'outlet': 'Sample News', 'title': 'Quarter summary',
                              'text': 'Revenue growth remained strong while investors assessed higher costs and cloud demand. Management noted lingering supply risks and said its outlook was resilient.'}]}


def test_external_links_are_metadata_only():
    data = body()
    data['news_sources'].append({
        'title': 'ExampleCorp quarterly results and outlook',
        'outlet': 'Independent Publisher',
        'url': 'https://publisher.example/earnings',
        'headline_only': True})
    result = client.post('/api/v1/analyze', json=data)
    assert result.status_code == 200
    articles = result.json()['sources']
    assert len(articles) == 2
    assert articles[0]['extraction_status'] == 'ok'
    assert articles[1]['extraction_status'] == 'metadata_only'
    assert articles[1]['summary'] == []


def test_stock_session_alignment():
    p = [StockPoint(date=date(2026, 10, 15), close=100, volume=1000),
         StockPoint(date=date(2026, 10, 16), close=105, volume=2000),
         StockPoint(date=date(2026, 10, 19), close=110, volume=1800)]
    assert session_context(p, date(2026, 10, 16), 'before_open') == (date(2026, 10, 16), date(2026, 10, 15), 5.0)
    assert session_context(p, date(2026, 10, 16), 'after_close')[0] == date(2026, 10, 19)
    assert session_context(p, date(2026, 10, 16), 'unknown') == (None, None, None)


def test_sentiment_is_estimate():
    assert rules_sentiment('Strong growth improved profit and exceeded estimates') == 'positive'
    assert classify('Risk and weaker loss pressured performance')[1].startswith('rules-v1')


def test_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv('FINPULSE_DB_PATH', str(tmp_path / 'cache.sqlite3'))
    monkeypatch.delenv('FINPULSE_DISABLE_CACHE', raising=False)
    response = client.post('/api/v1/analyze', json=body())
    assert response.status_code == 200
    key = response.json()['analysis_id']
    retrieved = client.get(f'/api/v1/analyses/{key}')
    assert retrieved.status_code == 200
    assert retrieved.json()['analysis_id'] == key
    assert client.get('/api/v1/analyses/not-valid').status_code == 404


def test_pdf_text_extraction():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 80), 'ExampleCorp earnings report. Revenue was $4.2 billion. ' * 4)
    binary = doc.tobytes()
    response = client.post('/api/v1/pdf/extract', files={'file': ('report.pdf', io.BytesIO(binary), 'application/pdf')})
    assert response.status_code == 200
    assert 'ExampleCorp' in response.json()['text']


def test_invalid_news_without_url_or_text():
    b = body()
    b['news_sources'] = [{'title': 'No content'}]
    assert client.post('/api/v1/analyze', json=b).status_code == 422


def test_no_made_up_stock_data(monkeypatch):
    with patch('app.main.get_stock') as mocked:
        from app.schemas import StockContextResponse
        mocked.return_value = StockContextResponse(ticker='TEST', earnings_date=date(2026, 10, 16), points=[], warning='Unavailable')
        response = client.get('/api/v1/stocks/TEST?announcement_date=2026-10-16')
    assert response.status_code == 200
    assert response.json()['points'] == []
    assert response.json()['session_close_change_percent'] is None
