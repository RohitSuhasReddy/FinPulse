from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
SAMPLE = """ExampleCorp reported revenue of $24.5 billion for fiscal Q2 2026, up 12% year-over-year.
Adjusted diluted EPS was $2.15 compared with $1.92 in the prior-year quarter.
Operating margin reached 24.2%, reflecting cost efficiencies.
Management expects demand to remain steady but cautioned that supply chain risks may pressure future margins."""


def request_body():
    return {"company_name": "ExampleCorp", "ticker": "EXMP", "fiscal_period": "FY2026 Q2", "earnings_text": SAMPLE,
            "news_sources": [{"title": "Company sees growth", "outlet": "Example News",
                              "text": "ExampleCorp reported healthy revenue growth this quarter. Demand remains steady, though management sees some supply chain risk and margin pressure."}]}


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_evidence_and_metrics():
    response = client.post("/api/v1/analyze", json=request_body())
    assert response.status_code == 200, response.text
    data = response.json()
    revenue = next(metric for metric in data["metrics"] if metric["name"] == "Revenue")
    assert revenue["normalized_value"] == 24_500_000_000
    assert revenue["currency"] == "USD"
    assert revenue["reporting_period"] == "FY2026 Q2"
    assert revenue["evidence"]["text"] in SAMPLE
    assert data["sources"][0]["source_id"] == "news_1"
    assert any(x["relationship"] == "shared" for x in data["comparison"])
    assert data["sources"][0]["sentiment_label"] in ("positive", "negative", "neutral")
    assert data["sources"][0]["sentiment_method"] == "rules-v1 (estimated)"
    for metric in data["metrics"]:
        ev = metric["evidence"]
        assert SAMPLE[ev["start_offset"]:ev["end_offset"]] == ev["text"]


def test_invalid_ticker_rejected():
    body = request_body()
    body["ticker"] = "ABC/../../"
    assert client.post("/api/v1/analyze", json=body).status_code == 422


def test_news_limit():
    body = request_body()
    body["news_sources"] *= 9
    assert client.post("/api/v1/analyze", json=body).status_code == 422


def test_no_made_up_metrics():
    body = request_body()
    body["earnings_text"] = "Management discussed operations and future planning, without announcing any financial figures. " * 3
    data = client.post("/api/v1/analyze", json=body).json()
    assert data["metrics"] == []
    assert any("No high-confidence" in warning for warning in data["warnings"])
