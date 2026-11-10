"""SEC companyfacts metrics with accession-, duration- and unit-verified provenance.

This module does NOT infer quarterly numbers by subtracting YTD values. It returns
only facts in the exact SEC filing accession and reporting period. Values come
from SEC structured XBRL data, not flattened HTML and not X/Twitter/social posts.
"""
from datetime import date
import math
import re
from app.schemas import Evidence, FinancialMetric
from app import research

# Preference order only; never double-count synonyms for a financial concept.
GAAP_CONCEPTS = (
    ('Revenue', ('RevenueFromContractWithCustomerExcludingAssessedTax',
                 'RevenueFromContractWithCustomerIncludingAssessedTax',
                 'Revenues', 'SalesRevenueNet'), 'USD'),
    ('Net income', ('NetIncomeLoss', 'ProfitLoss'), 'USD'),
    ('Operating income', ('OperatingIncomeLoss',), 'USD'),
    ('Diluted EPS', ('EarningsPerShareDiluted',), 'USD/shares'),
)


def _matches(fact: dict, *, accn: str, end: str, annual: bool) -> bool:
    if fact.get('accn') != accn or fact.get('end') != end:
        return False
    if fact.get('form') != ('10-K' if annual else '10-Q'):
        return False
    try:
        start = date.fromisoformat(fact['start'])
        finish = date.fromisoformat(fact['end'])
        days = (finish - start).days + 1
    except (ValueError, KeyError, TypeError):
        return False
    # Annual figures are NOT turned into fictitious fourth-quarter metrics.
    if not ((330 <= days <= 385) if annual else (70 <= days <= 112)):
        return False
    return isinstance(fact.get('val'), (int, float)) and not isinstance(fact['val'], bool) and math.isfinite(float(fact['val']))


def extract_companyfacts(filing: dict, fiscal_period: str) -> tuple[list[FinancialMetric], list[str]]:
    """Read companyfacts from SEC and return confirmed facts plus diagnostics.

    A company facts API value is already in absolute USD / USD-per-share units.
    The matching accession and quarter duration are mandatory: no YTD mixing,
    no guessed x1e6 multiplier, no fallback to arbitrary financial table rows.
    """
    cik = filing.get('cik')
    accession = str(filing.get('accession') or '')
    period_end = str(filing.get('period_end') or '')
    form = filing.get('form')
    if (not isinstance(cik, int) or cik <= 0 or
            not re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession) or
            not re.fullmatch(r'\d{4}-\d{2}-\d{2}', period_end) or form not in ('10-Q', '10-K')):
        return [], ['Structured financial facts unavailable: invalid or incomplete SEC filing identity.']
    source_url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json'
    try:
        import json
        facts = json.loads(research._get(source_url, sec=True, max_bytes=20_000_000))
        taxonomy = facts.get('facts', {}).get('us-gaap', {})
        if not isinstance(taxonomy, dict):
            raise ValueError('Missing us-gaap facts')
    except (research.ResearchError, ValueError, KeyError, TypeError, UnicodeDecodeError) as exc:
        return [], [f'Official SEC structured facts unavailable ({type(exc).__name__}); figures are not estimated.']

    results: list[FinancialMetric] = []
    for label, candidates, unit in GAAP_CONCEPTS:
        for tag in candidates:
            concept = taxonomy.get(tag, {})
            unit_rows = (concept.get('units') or {}).get(unit) if isinstance(concept, dict) else None
            if not isinstance(unit_rows, list):
                continue
            eligible = [f for f in unit_rows if isinstance(f, dict) and _matches(f, accn=accession,
                        end=period_end, annual=form == '10-K')]
            if not eligible:
                continue
            # Identical matching contexts ought to agree. If they don't, withhold.
            vals = {float(f['val']) for f in eligible}
            if len(vals) != 1:
                break
            fact = eligible[0]
            value = float(fact['val'])
            display_number = f'{value:,.2f}' if unit == 'USD/shares' else f'{value:,.0f}'
            provenance = (f'SEC structured XBRL fact us-gaap:{tag}; '
                          f'form {form}, accession {accession}, '
                          f'period {fact["start"]} to {fact["end"]}; '
                          f'unit {unit}, reported value {display_number}. '
                          'This is a structured data record, not a quotation from the document.')
            results.append(FinancialMetric(
                name=label, raw_value=f'{display_number} {unit}', normalized_value=value,
                unit='per_share' if unit == 'USD/shares' else 'currency', currency='USD',
                reporting_period=fiscal_period, comparison_basis=None, metric_variant='reported',
                extraction_status='extracted',
                evidence=Evidence(source_id=f'sec_xbrl:us-gaap:{tag}', text=provenance,
                                  start_offset=0, end_offset=0, source_url=source_url),
            ))
            break
    note = (f'{len(results)} reported financial figures sourced from official SEC XBRL facts '
            f'for {form}, accession {accession}, period ending {period_end}. '
            'Only matching reporting periods and monetary units were accepted.')
    if not results:
        note = ('SEC companyfacts returned no matching standard US-GAAP values for this '
                'filing and reporting duration. No financial amounts were guessed.')
    return results, [note]
