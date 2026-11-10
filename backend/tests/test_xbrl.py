"""Offline regression against representative SEC XBRL records for NVIDIA-like quarter."""
import json
from app import research, xbrl

FILING = {'cik': 1045810, 'accession': '0001045810-26-000100',
          'period_end': '2026-07-26', 'form': '10-Q'}


def fact(v, start='2026-04-27', end='2026-07-26', accn=FILING['accession'], form='10-Q'):
    return {'val': v, 'start': start, 'end': end, 'accn': accn, 'form': form, 'fy': 2027, 'fp': 'Q2'}


def data():
    return {'facts': {'us-gaap': {
        'RevenueFromContractWithCustomerExcludingAssessedTax': {'units': {'USD': [
            fact(96221000000),
            fact(175100000000, '2026-01-26', '2026-07-26'),  # six-month YTD must be ignored
            fact(64000000000, accn='0001045810-25-000100')]}},
        'NetIncomeLoss': {'units': {'USD': [fact(59688000000), fact(118010000000, '2026-01-26', '2026-07-26')]}},
        'OperatingIncomeLoss': {'units': {'USD': [fact(63734000000)]}},
        'EarningsPerShareDiluted': {'units': {'USD/shares': [fact(2.46)]}},
    }}}


def test_sec_exact_quarter_and_not_six_months(monkeypatch):
    monkeypatch.setattr(research, '_get', lambda *args, **kwargs: json.dumps(data()).encode())
    metrics, notes = xbrl.extract_companyfacts(FILING, 'Q2 FY2027')
    values = {m.name: m.normalized_value for m in metrics}
    assert values == {'Revenue': 96221000000, 'Net income': 59688000000,
                      'Operating income': 63734000000, 'Diluted EPS': 2.46}
    assert all(m.evidence.source_url.startswith('https://data.sec.gov/') for m in metrics)
    assert all(m.evidence.start_offset == 0 == m.evidence.end_offset for m in metrics)
    assert len(metrics) == 4
    assert 'structured' in notes[0]


def test_rejects_ytd_only_and_other_accession(monkeypatch):
    payload = data()
    payload['facts']['us-gaap']['RevenueFromContractWithCustomerExcludingAssessedTax']['units']['USD'] = [
        fact(118010000000, '2026-01-26', '2026-07-26'),
        fact(101000000000, accn='0001045810-25-000100')]
    monkeypatch.setattr(research, '_get', lambda *args, **kwargs: json.dumps(payload).encode())
    metrics, _ = xbrl.extract_companyfacts(FILING, 'Q2 FY2027')
    assert 'Revenue' not in {m.name for m in metrics}


def test_conflicting_same_context_withheld(monkeypatch):
    payload = data()
    payload['facts']['us-gaap']['NetIncomeLoss']['units']['USD'].append(fact(1))
    monkeypatch.setattr(research, '_get', lambda *args, **kwargs: json.dumps(payload).encode())
    metrics, _ = xbrl.extract_companyfacts(FILING, 'Q2 FY2027')
    assert 'Net income' not in [m.name for m in metrics]


def test_empty_sec_result_never_guesses(monkeypatch):
    monkeypatch.setattr(research, '_get', lambda *args, **kwargs: b'{"facts": {}}')
    metrics, warnings = xbrl.extract_companyfacts(FILING, 'FY2027 Q2')
    assert metrics == []
    assert 'No financial amounts were guessed' in warnings[0]


def test_network_error_becomes_warning(monkeypatch):
    def fail(*args, **kwargs):
        raise research.ResearchError('SEC unavailable')
    monkeypatch.setattr(research, '_get', fail)
    metrics, notes = xbrl.extract_companyfacts(FILING, 'Q2')
    assert metrics == [] and len(notes) == 1
