"""Additional checks for guardrails and deterministic source handling."""
from datetime import date
from app.analysis.text import clean_text, passages, summarize
from app.analysis.metrics import extract_metrics
from app.schemas import AnalyzeRequest
from app.analysis.service import analyze


def test_distinguish_percent_magnitude():
    source = 'Revenue increased 12% year-over-year to $4.6 billion. Operating margin was 17.5%.'
    result = extract_metrics(source, 'Q1 2026')
    assert result[0].normalized_value == 4_600_000_000
    assert any(m.name == 'Operating margin' and m.normalized_value == 17.5 for m in result)


def test_evidence_offsets_after_normalization():
    text = clean_text('Revenue was $1 billion.\r\n\r\nExpenses were elevated.  Future demand remained stable.')
    for summary in summarize(text, 'earnings'):
        e = summary.evidence
        assert e.text == text[e.start_offset:e.end_offset]


def test_pasted_sources_have_independent_identity():
    data = AnalyzeRequest(
        company_name='Example Corporation', ticker='TEST', fiscal_period='Q2 2026',
        earnings_text='Revenue reached $3.3 billion and operating margin expanded to 24.5%. ' * 2,
        news_sources=[{'title':'Headline One', 'outlet':'Source One',
                       'text':'The company showed revenue growth and profit momentum. Costs remained stable and demand stayed resilient.'},
                      {'title':'Headline Two', 'outlet':'Source Two',
                       'text':'Investors emphasized new risks in operating margins. Revenue momentum was discussed alongside uncertain costs.'}])
    result = analyze(data)
    assert len(result.sources) == 2
    assert result.sources[0].source_id == 'news_1'
    assert result.sources[1].source_id == 'news_2'
    assert all(v.news_evidence[0].evidence.source_id.startswith('news_') for v in result.comparison if v.news_evidence)
