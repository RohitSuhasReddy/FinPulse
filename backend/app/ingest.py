"""Best-effort public HTML article extraction with SSRF protections.

Reject non-public DNS addresses, restricted ports and redirects; never use
ambient proxies. DNS rebinding between validation and connection is still a
risk; do not deploy as an unrestricted public fetch service without IP pinning
and egress firewall rules.
"""
from datetime import datetime
import ipaddress
import socket
from urllib.parse import urlsplit, urljoin
import httpx
from app.schemas import ArticleResponse

MAX_HTML = 2_000_000
MAX_REDIRECTS = 3


class ArticleError(ValueError):
    pass


def verify_public_url(value: str) -> None:
    try:
        url = urlsplit(value)
        if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
            raise ArticleError('Only public HTTP(S) article URLs are supported')
        if url.port not in (None, 80, 443):
            raise ArticleError('Nonstandard article URL ports are not allowed')
        host = url.hostname.rstrip('.').lower()
        if host == 'localhost' or host.endswith('.localhost') or host.endswith('.local'):
            raise ArticleError('Local network hosts are blocked')
        try:
            infos = socket.getaddrinfo(host, url.port or (443 if url.scheme == 'https' else 80), type=socket.SOCK_STREAM)
        except (socket.gaierror, UnicodeError, OSError) as exc:
            raise ArticleError('Could not resolve article host') from exc
        addresses = {i[4][0].split('%')[0] for i in infos}
        if not addresses or any(not ipaddress.ip_address(addr).is_global for addr in addresses):
            raise ArticleError('Private, local, reserved or otherwise non-public destinations are blocked')
    except ValueError as exc:
        if isinstance(exc, ArticleError):
            raise
        raise ArticleError('Invalid article URL') from exc


def fetch_article(url: str) -> ArticleResponse:
    """Extract a public article. Network failures are per-source errors upstream."""
    current = url
    try:
        with httpx.Client(follow_redirects=False, trust_env=False,
                          timeout=httpx.Timeout(7.0, connect=4.0),
                          headers={'User-Agent': 'FinPulse/0.1 (educational article reader)'}) as client:
            for _ in range(MAX_REDIRECTS + 1):
                verify_public_url(current)
                with client.stream('GET', current) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get('location')
                        if not location:
                            raise ArticleError('Article redirected without a destination')
                        current = urljoin(current, location)
                        continue
                    if response.status_code >= 400:
                        raise ArticleError(f'Article unavailable (HTTP {response.status_code})')
                    media_type = response.headers.get('content-type', '').lower()
                    if media_type and not (media_type.startswith('text/html') or media_type.startswith('text/plain')):
                        raise ArticleError('Article URL did not return HTML or plain text')
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data) > MAX_HTML:
                            raise ArticleError('Article exceeds the 2 MB download limit')
                    html = bytes(data).decode(response.encoding or 'utf-8', errors='replace')
                    if media_type.startswith('text/plain'):
                        extracted = html
                        metadata = None
                    else:
                        try:
                            import trafilatura
                            extracted = trafilatura.extract(html, include_comments=False,
                                                              include_tables=False, favor_precision=True)
                            metadata = trafilatura.extract_metadata(html)
                        except ImportError as exc:
                            raise ArticleError('Article extraction dependency missing: install backend requirements') from exc
                    if not extracted or len(extracted.strip()) < 80:
                        raise ArticleError('Article text unavailable or too short; paste the text instead')
                    published_at = None
                    if metadata and metadata.date:
                        try:
                            published_at = datetime.fromisoformat(metadata.date.replace('Z', '+00:00'))
                        except ValueError:
                            pass
                    host = urlsplit(current).hostname or 'Unknown source'
                    return ArticleResponse(title=(metadata.title if metadata else None) or host,
                                           outlet=(metadata.sitename if metadata else None) or host,
                                           text=extracted[:100_000], url=current,
                                           published_at=published_at)
        raise ArticleError('Too many article redirects')
    except (httpx.HTTPError, UnicodeError) as exc:
        raise ArticleError('Could not retrieve article; check connectivity or paste article text') from exc
