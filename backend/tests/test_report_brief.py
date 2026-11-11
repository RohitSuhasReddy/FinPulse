"""Regression: an earnings summary must not be a list of footnotes or aspirations."""
from app.analysis.service import analyze
from app.analysis.text import report_passages, summarize
from app.schemas import AnalyzeRequest

NETFLIX_LIKE = """Netflix reported revenue of $12.874 billion for Q3 2026, increasing year over year.
Operating income was $4.459 billion, while operating margin reached 34.6% for the quarter.
Our goal is to sustain healthy revenue growth, expand operating profit and margin, and improve free cash flow for the long term.
F/X Neutral revenue growth excludes the year over year effect of foreign exchange rate movements and the impact of hedging.
Revenue growth reflected subscriptions, membership gains, pricing, advertising and the impact of exchange rates.
Operating profitability exceeded its forecast because certain expenses occurred later than expected in the financial year.
Netflix reduced its projected 2026 advertising revenue to $2.7 billion from the previous projection of $3.0 billion.
Management noted delays in advertising capabilities that would take more time to reach the market.
Management forecast full-year revenue of $51.1 billion, while projecting a lower operating margin for the fourth quarter.
The company highlighted continued investment in premium series, films, and live events to serve its global membership.
"""


def test_discard_goals_and_fx_definitions_from_report_brief():
    result = analyze(AnalyzeRequest(
        company_name="Netflix", ticker="NFLX", fiscal_period="FY2026 Q3",
        earnings_text=NETFLIX_LIKE,
    ))
    brief = result.report_brief
    assert brief is not None
    assert "Netflix" in brief.overview and "revenue" in brief.overview.lower()
    assert "$12.87" in brief.overview
    assert len(brief.findings) >= 2
    content = " ".join(x.body for x in brief.findings).lower()
    assert "our goal is" not in content
    assert "excludes the year over year effect" not in content
    assert any(x.category == "outlook" for x in brief.findings)
    assert any("advertising" in x.body.lower() for x in brief.findings)
    for finding in brief.findings:
        assert finding.heading and finding.body
        for evidence in finding.evidence:
            assert NETFLIX_LIKE[evidence.start_offset:evidence.end_offset] == evidence.text


def test_pdf_wrapped_sentence_remains_whole_with_source_offsets():
    text = ("Revenue growth reflected subscriptions,\n"
            "membership gains, pricing, and advertising across several regions.\n"
            "\nF/X Neutral revenue growth excludes the year over year effect of foreign exchange movements.\n"
            "\nOperating profitability exceeded the company forecast because of lower expenses.\n")
    excerpts = report_passages(text)
    assert any("subscriptions,\nmembership gains" in p.text for p in excerpts)
    for passage in excerpts:
        assert text[passage.start:passage.end] == passage.text
    picks = summarize(text, "earnings")
    assert picks
    assert not any("excludes the year over year" in x.text.lower() for x in picks)
    assert any("membership gains" in x.text.lower() for x in picks)


def test_old_saved_analysis_without_brief_is_still_loadable():
    result = analyze(AnalyzeRequest(
        company_name="Netflix", ticker="NFLX", fiscal_period="FY2026 Q3",
        earnings_text=NETFLIX_LIKE,
    ))
    dumped = result.model_dump()
    dumped.pop("report_brief")
    from app.schemas import AnalyzeResponse
    historic = AnalyzeResponse.model_validate(dumped)
    assert historic.report_brief is None


def test_no_invented_metrics_in_overview():
    result = analyze(AnalyzeRequest(
        company_name="Example", ticker="EXMP", fiscal_period="FY2026 Q3",
        earnings_text="Management described customer service investments and operations without announcing any financial performance figures. " * 4,
    ))
    assert not result.metrics
    assert result.report_brief
    assert "could not be established" in result.report_brief.overview
