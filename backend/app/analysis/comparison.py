"""Transparent cross-document theme comparison, not automatic fact checking."""
from app.analysis.text import detected_themes, evidence_for
from app.schemas import SourceAnalysis, ThemeComparison, ThemeEvidence


def compare(earnings_text: str, sources: list[tuple[str, str, str]]) -> tuple[list[str], list[ThemeComparison]]:
    earnings = detected_themes(earnings_text)
    article_themes = [(source_id, outlet, detected_themes(text)) for source_id, outlet, text in sources]
    all_themes = dict.fromkeys([*earnings.keys(), *(t for _, _, themes in article_themes for t in themes)])
    output = []
    for theme in all_themes:
        news = [ThemeEvidence(source_id=sid, outlet=outlet, evidence=evidence_for(themes[theme], sid))
                for sid, outlet, themes in article_themes if theme in themes]
        in_earnings = theme in earnings
        output.append(ThemeComparison(
            theme=theme,
            relationship="shared" if in_earnings and news else "earnings_only" if in_earnings else "news_only",
            earnings_evidence=evidence_for(earnings[theme], "earnings") if in_earnings else None,
            news_evidence=news,
        ))
    return list(earnings), output
