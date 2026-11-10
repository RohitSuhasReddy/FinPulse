"""Optional, bounded external research discovery.

SEC documents and Google News RSS are public data sources. The SEC requires a
user-identifying User-Agent; configure FINPULSE_SEC_USER_AGENT once. An RSS item
is *metadata*, never a scraped full article, so it cannot substantiate claims.
"""
from datetime import date, timedelta, timezone, datetime
from functools import lru_cache
import os
import re
from urllib.parse import urlencode
from xml.etree import ElementTree
import httpx
from bs4 import BeautifulSoup

SEC_HEADER_ENV = 'FINPULSE_SEC_USER_AGENT'
SEC_HOSTS = {'www.sec.gov', 'data.sec.gov'}
MAX_RESPONSE = 3_000_000


class ResearchError(ValueError):
    pass


def _get(url: str, *, sec: bool = False, max_bytes: int = MAX_RESPONSE) -> bytes:
    """Calls only URLs created from fixed hosts and validated IDs (never arbitrary URLs)."""
    headers = {'User-Agent': 'FinPulse local research/0.2', 'Accept': 'application/json, text/html, application/xml, text/xml, */*'}
    if sec:
        agent = os.getenv(SEC_HEADER_ENV, '').strip()
        if not agent or '@' not in agent or len(agent) < 12:
            raise ResearchError('SEC import requires FINPULSE_SEC_USER_AGENT with your name/app and contact email. Set it once and restart the backend.')
        headers['User-Agent'] = agent
    try:
        with httpx.Client(timeout=httpx.Timeout(12.0, connect=5.0), follow_redirects=False,
                          trust_env=False, headers=headers) as client:
            with client.stream('GET', url) as response:
                if response.status_code != 200:
                    raise ResearchError(f'Data source unavailable (HTTP {response.status_code}); try again or upload a PDF.')
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > max_bytes:
                        raise ResearchError('Data source response is too large; upload a smaller document instead.')
                return bytes(data)
    except httpx.HTTPError as exc:
        raise ResearchError('Cannot reach external data source right now. Check internet access or import a PDF.') from exc


@lru_cache(maxsize=1)
def _ticker_index(agent: str) -> dict[str, tuple[int, str]]:
    """Cache ticker mapping per configured SEC identity."""
    import json
    raw = _get('https://www.sec.gov/files/company_tickers.json', sec=True)
    payload = json.loads(raw)
    return {str(item['ticker']).upper(): (int(item['cik_str']), str(item['title']))
            for item in payload.values()}


def _filings_for_ticker(ticker: str) -> tuple[str, list[dict]]:
    import json
    ticker = ticker.strip().upper()
    if not re.fullmatch(r'[A-Z0-9.\-]{1,12}', ticker):
        raise ResearchError('Invalid ticker symbol.')
    idx = _ticker_index(os.getenv(SEC_HEADER_ENV, ''))
    if ticker not in idx:
        raise ResearchError('Ticker was not found in the SEC company ticker index.')
    cik, company = idx[ticker]
    raw = _get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json', sec=True)
    recent = json.loads(raw).get('filings', {}).get('recent', {})
    entries = []
    for form, acc, period, filed, document in zip(
            recent.get('form', []), recent.get('accessionNumber', []),
            recent.get('reportDate', []), recent.get('filingDate', []), recent.get('primaryDocument', [])):
        if form not in ('10-Q', '10-K') or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', str(acc)):
            continue
        if not re.fullmatch(r'[\w.\-]{1,140}', str(document)):
            continue
        entries.append({'ticker': ticker, 'company_name': company, 'form': form,
                        'accession': acc, 'period_end': period, 'filed_at': filed,
                        'document': document, 'cik': cik})
    return company, entries[:30]


def filings(ticker: str) -> dict:
    company, entries = _filings_for_ticker(ticker)
    return {'ticker': ticker.upper(), 'company_name': company, 'filings': entries[:16],
            'notice': '10-Q/10-K filings are SEC disclosures, not earnings-call transcripts. Filing dates are not earnings announcement dates.'}


def import_filing(ticker: str, accession: str) -> dict:
    company, entries = _filings_for_ticker(ticker)
    match = next((entry for entry in entries if entry['accession'] == accession), None)
    if match is None:
        raise ResearchError('Filing not found in the official recent SEC filings list for this ticker.')
    cik = match['cik']
    acc_clean = accession.replace('-', '')
    html = _get(f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{match["document"]}',
                sec=True, max_bytes=12_000_000)
    from app.analysis.filing_text import extract_filing_text
    # Preserve statement rows and their unit headings; never collapse an entire
    # financial table into one sentence.
    text = extract_filing_text(html)
    if len(text) < 80:
        raise ResearchError('Filing does not contain usable extracted text. Try downloading the PDF instead.')
    year = match['period_end'][:4]
    fiscal_period = f'FY{year} (10-K, year-end {match["period_end"]})' if match['form'] == '10-K' else f'Quarter ending {match["period_end"]}'
    return {'text': text, 'company_name': company, 'ticker': ticker.upper(),
            'fiscal_period': fiscal_period, 'filing_date': match['filed_at'],
            'period_end': match['period_end'], 'form': match['form'],
            'source_url': f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{match["document"]}',
            'notice': 'This is filing text, not an earnings transcript. Confirm extracted tables and select the actual earnings announcement date separately.'}


def discover_news(company: str, ticker: str = '', around: date | None = None, limit: int = 12) -> dict:
    """Returns article titles/links and feed publication timestamps only.

    Google News RSS search is an optional, best-effort public discovery channel.
    It is *not* a source of full article bodies, and links may not be readable.
    """
    name = re.sub(r'[^\w .&\-]', ' ', company).strip()[:80]
    if len(name) < 2:
        raise ResearchError('Enter a company name to search for coverage.')
    query = f'"{name}" earnings'
    if around:
        start = around - timedelta(days=2)
        end = around + timedelta(days=9)
        query += f' after:{start.isoformat()} before:{end.isoformat()}'
    params = urlencode({'q': query, 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'})
    raw = _get('https://news.google.com/rss/search?' + params, max_bytes=800_000)
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        raise ResearchError('News discovery feed was malformed or unavailable.') from exc
    output = []
    unique = set()
    for item in root.findall('./channel/item'):
        title = (item.findtext('title') or '').strip()[:240]
        link = (item.findtext('link') or '').strip()
        outlet = (item.findtext('source') or 'News feed').strip()[:100]
        pub = (item.findtext('pubDate') or '').strip()
        if not title or not link.startswith('https://news.google.com/'):
            continue
        if (title.lower(), outlet.lower()) in unique:
            continue
        unique.add((title.lower(), outlet.lower()))
        output.append({'title': title, 'url': link, 'outlet': outlet,
                       'feed_published_at': pub, 'body_available': False,
                       'origin': 'Google News RSS headline/link'})
        if len(output) >= limit:
            break
    return {'items': output, 'notice': 'Discovered results contain headlines and links only, not full article text. Blocked articles remain metadata-only and do not count as verified source evidence.'}
