"""One-ticker research orchestration. Every external source is attributed and optional.

Only fixed official provider endpoints are called by this module. News articles are
fetched by the existing URL validator, never by blindly trusting an API result.
A discovered headline is never treated as full-text evidence.
"""
from datetime import date, datetime, timedelta, timezone
import json
import os
import re
from urllib.parse import urlencode, urlsplit

import httpx
from pydantic import BaseModel, Field

from app import cache, research
from app.analysis.service import analyze
from app.schemas import AnalyzeRequest, AnalyzeResponse, NewsSourceInput, SocialPost


class AutoResearchInput(BaseModel):
    ticker: str = Field(min_length=1, max_length=12, pattern=r'^[A-Za-z0-9.\-]+$')
    period_end: date | None = None
    announcement_date: date | None = None
    market_timing: str = Field(default='unknown', pattern=r'^(unknown|before_open|after_close)$')
    include_social: bool = True
    max_articles: int = Field(default=5, ge=1, le=8)


def _fixed_json(url: str, params: dict, headers: dict | None = None) -> dict:
    """Read only capped JSON from provider URLs; no automatic redirects or proxies."""
    allowed = {'api.gdeltproject.org', 'public.api.bsky.app', 'api.x.com'}
    if urlsplit(url).hostname not in allowed or urlsplit(url).scheme != 'https':
        raise ValueError('Unexpected upstream host')
    with httpx.Client(timeout=httpx.Timeout(9.0, connect=4.0), trust_env=False,
                      follow_redirects=False) as client:
        with client.stream('GET', url, params=params, headers=headers or {}) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > 1_500_000:
                    raise ValueError('Provider response too large')
    result = json.loads(data)
    if not isinstance(result, dict):
        raise ValueError('Provider returned an unexpected response')
    return result


def _first_seen(raw: str) -> str | None:
    # GDELT seendate means FIRST SEEN in its index, not publication date.
    if re.fullmatch(r'\d{14}', raw):
        return datetime.strptime(raw, '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc).isoformat()
    return None


def discover_gdelt(company: str, around: date | None, max_articles: int) -> list[dict]:
    """Discover external article URLs, never article content or verified publication dates."""
    now = datetime.now(timezone.utc).date()
    if around and (now - around).days > 89:
        return []  # GDELT DOC API recent history is limited; avoid invented older matches.
    name = re.sub(r'[^\w .&\-]', ' ', company).strip()[:90]
    query = f'"{name}" earnings'
    params = {'query': query, 'mode': 'artlist', 'format': 'json',
              'maxrecords': '35', 'sort': 'datedesc'}
    if around:
        start = max(around - timedelta(days=3), now - timedelta(days=89))
        end = min(around + timedelta(days=10), now + timedelta(days=1))
        if end <= start:
            return []
        params['startdatetime'] = start.strftime('%Y%m%d000000')
        params['enddatetime'] = end.strftime('%Y%m%d235959')
    output: list[dict] = []
    seen_urls: set[str] = set()
    seen_domains: set[str] = set()
    for item in _fixed_json('https://api.gdeltproject.org/api/v2/doc/doc', params).get('articles', []):
        if not isinstance(item, dict):
            continue
        url = str(item.get('url') or '')
        parsed = urlsplit(url)
        host = (parsed.hostname or '').lower()
        if parsed.scheme != 'https' or not host or len(url) > 1800:
            continue
        if host in seen_domains or url in seen_urls:
            continue
        title = str(item.get('title') or '').strip()[:240]
        if len(title) < 12:
            continue
        seen_domains.add(host)
        seen_urls.add(url)
        output.append({'title': title, 'url': url, 'outlet': host,
                       'first_seen': _first_seen(str(item.get('seendate') or '')),
                       'provider': 'GDELT index'})
        if len(output) >= max_articles:
            break
    return output


def _social_date_ok(timestamp: str | None, around: date | None) -> bool:
    if not around:
        return True
    if not timestamp:
        return False
    try:
        day = date.fromisoformat(timestamp[:10])
    except ValueError:
        return False
    return around - timedelta(days=4) <= day <= around + timedelta(days=10)


def bluesky_posts(company: str, ticker: str, around: date | None) -> list[SocialPost]:
    params = {'q': f'"{company}" earnings', 'limit': 35, 'sort': 'latest'}
    response = _fixed_json('https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts', params)
    posts: list[SocialPost] = []
    authors: set[str] = set()
    for item in response.get('posts', []):
        if not isinstance(item, dict):
            continue
        author = item.get('author') or {}
        record = item.get('record') or {}
        if not isinstance(author, dict) or not isinstance(record, dict):
            continue
        handle = str(author.get('handle') or '')
        uri = str(item.get('uri') or '')
        text = str(record.get('text') or '').strip()
        created_at = str(record.get('createdAt') or '')
        if (len(text) < 25 or len(text) > 1500 or not _social_date_ok(created_at, around)
                or not re.fullmatch(r'[a-zA-Z0-9.\-]{3,253}', handle)
                or not re.fullmatch(r'at://[^/]+/app\.bsky\.feed\.post/[a-zA-Z0-9]+', uri)
                or handle in authors):
            continue
        authors.add(handle)
        rkey = uri.rsplit('/', 1)[-1]
        posts.append(SocialPost(platform='Bluesky', author=handle,
                                url=f'https://bsky.app/profile/{handle}/post/{rkey}',
                                text=text, created_at=created_at,
                                likes=max(0, int(item.get('likeCount') or 0))))
        if len(posts) == 8:
            break
    return posts


def x_posts(company: str, ticker: str, around: date | None) -> list[SocialPost]:
    token = os.getenv('FINPULSE_X_BEARER_TOKEN', '').strip()
    if not token:
        return []
    # Recent Search is available only with an authorized X developer account and
    # may be billable. We never fall back to scraping login-protected pages.
    params = {'query': f'("{company}" OR ${ticker}) earnings lang:en -is:retweet',
              'max_results': 10, 'tweet.fields': 'created_at,public_metrics'}
    data = _fixed_json('https://api.x.com/2/tweets/search/recent', params,
                       headers={'Authorization': f'Bearer {token}'})
    posts: list[SocialPost] = []
    for item in data.get('data', []):
        if not isinstance(item, dict):
            continue
        pid = str(item.get('id') or '')
        text = str(item.get('text') or '').strip()
        created = str(item.get('created_at') or '')
        if not pid.isdecimal() or not 25 <= len(text) <= 1500 or not _social_date_ok(created, around):
            continue
        metrics = item.get('public_metrics') or {}
        posts.append(SocialPost(platform='X', author='Public X account',
                                url=f'https://x.com/i/web/status/{pid}',
                                text=text, created_at=created,
                                likes=max(0, int(metrics.get('like_count') or 0))))
    return posts[:8]


def auto_research(request: AutoResearchInput) -> AnalyzeResponse:
    """One ticker in; best-effort filing + news + social research saved locally."""
    ticker = request.ticker.strip().upper()
    company, available = research._filings_for_ticker(ticker)
    filings = [f for f in available if f['period_end'] == request.period_end.isoformat()] if request.period_end else available
    if not filings:
        raise research.ResearchError('No official SEC 10-Q/10-K for this ticker and period. Pick another period or use manual PDF upload.')
    chosen = filings[0]
    filing = research.import_filing(ticker, chosen['accession'])
    # SEC filing date is NEVER silently treated as the earnings announcement date.
    around = request.announcement_date or date.fromisoformat(chosen['filed_at'])
    articles: list[dict] = []
    warnings = []
    try:
        articles = discover_gdelt(company, around, request.max_articles)
    except (httpx.HTTPError, ValueError, json.JSONDecodeError, KeyError) as exc:
        warnings.append(f'GDELT discovery unavailable ({type(exc).__name__}).')
    if not articles:
        try:
            feed = research.discover_news(company, ticker, around)
            articles = [dict(title=item['title'], url=item['url'], outlet=item['outlet'], provider='Google News RSS')
                        for item in feed.get('items', [])[:request.max_articles]]
            warnings.append('Using RSS headline links because full article index results were unavailable.')
        except (research.ResearchError, ValueError, KeyError) as exc:
            warnings.append(f'News discovery unavailable ({type(exc).__name__}).')
    source_inputs = [NewsSourceInput(title=a['title'], outlet=a['outlet'], url=a['url'], headline_only=True)
                     for a in articles[:request.max_articles]]
    report = analyze(AnalyzeRequest(company_name=company, ticker=ticker,
        fiscal_period=filing['fiscal_period'], earnings_text=filing['text'],
        announcement_date=request.announcement_date,
        market_timing=request.market_timing, news_sources=source_inputs))
    report.data_origin = 'sec_filing'
    report.source_document_url = filing['source_url']
    report.source_document_type = filing['form']
    report.warnings.append('SEC filing date was used to discover nearby coverage; it is not necessarily the earnings announcement date.')
    report.warnings.append('Discovered news headlines and social posts do not prove financial facts; full-article evidence is analyzed only when the body was retrieved.')
    report.warnings.extend(warnings)
    if request.include_social:
        try:
            report.social_posts.extend(bluesky_posts(company, ticker, around))
        except (httpx.HTTPError, ValueError, json.JSONDecodeError, KeyError) as exc:
            report.warnings.append(f'Bluesky search unavailable ({type(exc).__name__}).')
        if os.getenv('FINPULSE_X_BEARER_TOKEN', '').strip():
            try:
                report.social_posts.extend(x_posts(company, ticker, around))
            except (httpx.HTTPError, ValueError, json.JSONDecodeError, KeyError) as exc:
                report.warnings.append(f'X search unavailable or account not entitled ({type(exc).__name__}).')
        report.warnings.append('Social posts are a small, non-representative sample of public opinion, not audited company facts or broad market sentiment.')
    try:
        cache.store(report)
    except OSError:
        report.warnings.append('Unable to save to the local library.')
    return report
