"""One analysis per company and period, preserving independent source identity."""
from datetime import datetime, timezone
from hashlib import sha256
from app.analysis.text import clean_text, detected_themes, summarize
from app.analysis.metrics import extract_metrics
from app.analysis.comparison import compare
from app.analysis.sentiment import classify
from app.ingest import ArticleError, fetch_article
from app.schemas import AnalyzeRequest, AnalyzeResponse, SourceAnalysis


def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    earnings = clean_text(payload.earnings_text)
    sources = []
    source_responses = []
    warnings: list[str] = []
    for idx, item in enumerate(payload.news_sources, start=1):
        sid = f'news_{idx}'
        title, outlet = item.title, item.outlet
        text = clean_text(item.text or '')
        published, url = item.published_at, str(item.url) if item.url else None
        origin = 'pasted_text' if text else 'url'
        if not text and url:
            try:
                article = fetch_article(url)
                text = clean_text(article.text)
                title, outlet = title or article.title, outlet or article.outlet
                published = published or article.published_at
            except ArticleError as exc:
                warning = f'News source {idx}: {exc}'
                warnings.append(warning)
                source_responses.append(SourceAnalysis(source_id=sid, title=title or url,
                    outlet=outlet or 'Unavailable', url=url, published_at=published,
                    summary=[], themes=[], input_origin='url', extraction_status='failed', warning=warning))
                continue
        outlet = outlet or 'User-supplied article'
        title = title or (url or f'Pasted article {idx}')
        label, method = classify(text)
        sources.append((sid, outlet, text))
        source_responses.append(SourceAnalysis(
            source_id=sid, title=title, outlet=outlet, url=url, published_at=published,
            summary=summarize(text, sid, count=2), themes=list(detected_themes(text)),
            sentiment_label=label, sentiment_method=method, input_origin=origin,
        ))
    metrics = extract_metrics(earnings, payload.fiscal_period)
    themes, comparison = compare(earnings, sources)
    if not sources:
        warnings.append('No usable news passages; add article text or an accessible URL for cross-source analysis.')
    if not metrics:
        warnings.append('No high-confidence financial metric matches found; check wording and amounts in the source.')
    elif any(m.extraction_status == 'needs_review' for m in metrics):
        warnings.append('Some extracted metrics need manual review. Check the cited source text.')
    warnings.append('Sentiment is an estimated language signal, not factual financial performance.')
    digest = sha256(payload.model_dump_json(exclude_none=True).encode()).hexdigest()[:16]
    return AnalyzeResponse(analysis_id=digest, company_name=payload.company_name,
        ticker=payload.ticker.upper(), fiscal_period=payload.fiscal_period,
        announcement_date=payload.announcement_date, market_timing=payload.market_timing,
        analyzed_at=datetime.now(timezone.utc), summary=summarize(earnings, 'earnings'),
        metrics=metrics, earnings_themes=themes, sources=source_responses,
        comparison=comparison, warnings=warnings,
        sentiment_model=source_responses[0].sentiment_method if source_responses and source_responses[0].sentiment_method else 'rules-v1')
