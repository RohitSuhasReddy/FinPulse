from app.analysis.metrics import extract_metrics


def test_margin_vs_growth():
    data = extract_metrics("Operating margin was 27.3%, an increase of 1.5 percentage points YoY.", "Q1 2026")
    margin = next(m for m in data if m.name == "Operating margin")
    assert margin.normalized_value == 27.3
    assert margin.unit == "percent"
    assert margin.comparison_basis == "YoY"


def test_does_not_confuse_growth_with_revenue_value():
    metrics = extract_metrics("Revenue increased 18% YoY to $2.6 billion for the quarter.", "Q1 2026")
    assert metrics[0].normalized_value == 2_600_000_000


def test_no_plain_number_without_unit():
    assert extract_metrics("Revenue was strong in the quarter with 400 new customers.", "Q1 2026") == []
