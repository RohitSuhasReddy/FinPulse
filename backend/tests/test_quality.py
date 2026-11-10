"""Prevent the exact SEC table/summary regression reported in a real NVIDIA run."""
from app.analysis.filing_text import extract_filing_text
from app.analysis.metrics import extract_metrics
from app.analysis.text import summarize

# Small, faithfully structured excerpt of NVDA's Q2 FY2027 financial statements.
# These are fixture values, not a live SEC API request.
NVDA_HTML = b'''
<html><body>
<h1>NVIDIA Corporation and Subsidiaries</h1>
<div>Condensed Consolidated Statements of Income</div>
<div>(In millions, except per share data)</div>
<table>
<tr><th></th><th>Three Months Ended</th><th>Six Months Ended</th></tr>
<tr><td></td><td>Jul 26, 2026</td><td>Jul 27, 2025</td><td>Jul 26, 2026</td></tr>
<tr><td>Revenue</td><td>$</td><td>96,221</td><td>$</td><td>46,743</td><td>$</td><td>177,837</td></tr>
<tr><td>Cost of revenue</td><td>24,079</td><td>12,890</td><td>44,538</td></tr>
<tr><td>Operating income</td><td>63,734</td><td>28,440</td><td>117,270</td></tr>
<tr><td>Net income</td><td>$</td><td>59,688</td><td>$</td><td>26,422</td><td>$</td><td>118,010</td></tr>
<tr><td>Net income per share:</td></tr>
<tr><td>Basic</td><td>$</td><td>2.47</td></tr>
<tr><td>Diluted</td><td>$</td><td>2.46</td><td>$</td><td>1.08</td><td>$</td><td>4.85</td></tr>
</table>
<div>Condensed Consolidated Statements of Cash Flows</div>
<div>(In millions)</div>
<table><tr><th>Six Months Ended</th></tr><tr><td>Net income</td><td>$</td><td>118,010</td></tr>
<tr><td>Cash used in investing activities</td><td>12,000</td></tr></table>
<p>Revenue increased as customer demand for accelerated computing services and data center products remained strong across the quarter.</p>
<p>We continue to invest in product development and AI infrastructure to support our customers across the business.</p>
</body></html>
'''


def test_nvda_quarterly_units_period_and_no_ytd_mix():
    text = extract_filing_text(NVDA_HTML)
    metrics = extract_metrics(text,'FY2027 Q2')
    actual = {m.name:m.normalized_value for m in metrics if m.extraction_status=='extracted'}
    assert actual['Revenue'] == 96_221_000_000
    assert actual['Net income'] == 59_688_000_000
    assert actual['Operating income'] == 63_734_000_000
    assert actual['Diluted EPS'] == 2.46
    assert len(metrics) == 4
    assert 118_010_000_000 not in actual.values()
    assert all(m.evidence.text == text[m.evidence.start_offset:m.evidence.end_offset] for m in metrics)


def test_summary_filters_statement_and_cash_flow_tables():
    text = extract_filing_text(NVDA_HTML)
    picks = summarize(text,'earnings')
    assert picks
    assert all('|' not in s.text and '[FINPULSE_' not in s.text for s in picks)
    assert all(len(s.text) < 400 for s in picks)
    assert any('demand' in s.text.lower() for s in picks)
    assert all(s.evidence.text == text[s.evidence.start_offset:s.evidence.end_offset] for s in picks)


def test_table_without_explicit_millions_is_not_scaled():
    html=NVDA_HTML.replace(b'(In millions, except per share data)',b'(Unaudited)')
    text=extract_filing_text(html)
    assert not [m for m in extract_metrics(text,'FY2027 Q2') if m.extraction_status=='extracted']


def test_six_month_only_table_never_used_as_quarter():
    html = b'<html><body><div>(In millions)</div><table><tr><th>Six Months Ended</th></tr><tr><td>Revenue</td><td>$</td><td>177,837</td></tr><tr><td>Net income</td><td>$</td><td>118,010</td></tr></table></body></html>'
    assert extract_metrics(extract_filing_text(html),'FY2027 Q2') == []


def test_plain_text_with_ambiguous_dollar_number_needs_review():
    metrics=extract_metrics('The company reported Revenue of $96,221 in its condensed consolidated statements.','FY2027 Q2')
    assert metrics and metrics[0].extraction_status=='needs_review'


def test_plain_text_clean_revenue_billion_still_works():
    metrics=extract_metrics('The company reported Revenue of $96.2 billion for the quarter.','FY2027 Q2')
    assert metrics and metrics[0].normalized_value==96_200_000_000
    assert metrics[0].extraction_status=='extracted'


def test_cost_of_revenue_is_not_total_revenue():
    assert extract_metrics('Cost of revenue was $71 billion for the quarter.','FY2027 Q2') == []
