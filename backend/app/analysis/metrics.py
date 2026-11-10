"""Conservative period-aware financial extraction; ambiguous numbers are held back.

FINPULSE_TABLE markers are introduced only by the line-aware SEC HTML importer.
Statement amounts are scaled only when the document explicitly declares units.
"""
import re
from app.analysis.text import Passage, evidence_for, passages
from app.analysis.filing_text import TABLE_START, TABLE_END
from app.schemas import FinancialMetric

PATTERNS = [
    ('Revenue', re.compile(r'\b(?:total\s+)?revenues?\b', re.I), 'money'),
    ('Diluted EPS', re.compile(r'\b(?:diluted\s+)?(?:earnings\s+per\s+(?:diluted\s+)?share|EPS)\b', re.I), 'share'),
    ('Operating income', re.compile(r'\boperating\s+(?:income|profit)\b', re.I), 'money'),
    ('Net income', re.compile(r'\bnet\s+(?:income|profit)\b', re.I), 'money'),
    ('Operating margin', re.compile(r'\boperating\s+margin\b', re.I), 'percent'),
    ('Gross margin', re.compile(r'\bgross\s+margin\b', re.I), 'percent'),
    ('Free cash flow', re.compile(r'\bfree\s+cash\s+flow\b', re.I), 'money'),
]
VALUE = re.compile(r'(?P<currency>US\$|USD\s*|\$|₹|INR\s*)?\s*(?P<number>\(?-?\d[\d,]*(?:\.\d+)?\)?)\s*(?P<scale>billion|million|thousand|bn|mn|[BMK])?\s*(?P<pct>%|percent)?', re.I)
SCALES = {'billion':1e9,'bn':1e9,'b':1e9,'million':1e6,'mn':1e6,'m':1e6,'thousand':1e3,'k':1e3}
# Row labels must be exact. "Cost of revenue" and "net income per share" are NOT revenue/net income.
ROW_LABELS = [
    ('Revenue', re.compile(r'^(?:total )?revenues?$', re.I), 'money'),
    ('Operating income', re.compile(r'^operating (?:income|profit)(?: \(loss\))?$', re.I), 'money'),
    ('Net income', re.compile(r'^net (?:income|profit)(?: \(loss\))?$', re.I), 'money'),
    ('Diluted EPS', re.compile(r'^(?:diluted|diluted earnings per share|diluted net income per share|earnings per (?:diluted )?share[,:]? diluted)$', re.I), 'share'),
]


def _select_value(tail: str, kind: str):
    for match in VALUE.finditer(tail[:110]):
        raw = match.group(0).strip()
        if not raw:
            continue
        currency, scale, pct = match.group('currency'), match.group('scale'), match.group('pct')
        if kind == 'percent' and not pct: continue
        if kind == 'money' and not (currency or scale): continue
        if kind != 'percent' and pct: continue
        if kind == 'share' and (not currency and not re.search(r'\b(?:of|was|at|to)\s*$', tail[:match.start()], re.I)):
            continue
        digits = match.group('number')
        try:
            num = float(digits.strip('()').replace(',', ''))
            if digits.startswith('(') or digits.startswith('-'): num = -abs(num)
            if scale: num *= SCALES[scale.lower()]
        except (ValueError, KeyError):
            continue
        code = 'INR' if currency and ('₹' in currency or 'INR' in currency.upper()) else 'USD' if currency else None
        # For money, a bare $96,221 in statement text is not safe without a
        # heading: it might mean dollars, thousands, or millions.
        verified = kind == 'percent' or bool(scale) or (kind == 'share' and bool(currency))
        return raw, num, code, verified
    return None


def _statement_metrics(text: str, fiscal_period: str) -> list[FinancialMetric]:
    out = []
    seen = set()
    block_pattern = re.compile(re.escape(TABLE_START) + r'\s*\n(.*?)\n' + re.escape(TABLE_END), re.S)
    for block in block_pattern.finditer(text):
        rows = block.group(1)
        # Requires an explicit 3-month heading, not an only-six-month cash-flow table.
        if not re.search(r'three\s+months\s+ended', rows[:2300], re.I):
            continue
        # Scale is stated adjacent to the table, not embedded in the row.
        preceding = text[max(0, block.start()-450):block.start()]
        units = list(re.finditer(r'\(\s*in\s+(millions|thousands|billions)\b[^)]*\)', preceding, re.I))
        if not units:
            continue
        scale_name = units[-1].group(1).lower()
        factor = SCALES[{'millions':'million', 'thousands':'thousand', 'billions':'billion'}[scale_name]]
        table_currency = 'USD' if '$' in rows else None
        # Require a consolidated income statement with multiple financial rows.
        if not (re.search(r'(?m)^Revenue\s*\|',rows,re.I) and re.search(r'(?m)^Net income\s*\|',rows,re.I)):
            continue
        previous_rows = []
        for line in rows.splitlines():
            if '|' not in line:
                previous_rows.append(line)
                continue
            cells = [part.strip() for part in line.split('|')]
            label = re.sub(r'\s+', ' ', cells[0])
            for metric_name, pattern, kind in ROW_LABELS:
                if metric_name in seen or not pattern.fullmatch(label):
                    continue
                if label.lower() == 'diluted' and not re.search(r'(?:net income|earnings) per share', ' '.join(previous_rows[-4:]), re.I):
                    continue
                # The first nonempty numeric financial cell corresponds to the
                # latest 'Three Months Ended' period. Never scan to 6-month values.
                amount = None
                has_dollar = False
                for cell in cells[1:]:
                    if cell in {'$', 'US$', 'USD'}:
                        has_dollar = True
                        continue
                    if cell in {'-', '—', '–', '%'}:
                        continue
                    simple = re.fullmatch(r'\(?-?\$?\s*\d[\d,]*(?:\.\d+)?\)?', cell)
                    if simple:
                        amount = cell
                        break
                if amount is None:
                    continue
                val = float(amount.replace('$','').strip(' ()').replace(',',''))
                if amount.strip().startswith(('(', '-')):
                    val = -abs(val)
                if kind == 'money':
                    val *= factor
                elif val > 100:
                    continue  # EPS cannot be a multi-million value
                start = text.find(line, block.start(), block.end())
                if start < 0:
                    continue
                p = Passage(line, start, start+len(line))
                code = 'USD' if table_currency or has_dollar or '$' in amount else None
                raw = (('$' if code else '') + amount.replace('$','').strip() +
                       (' ' + scale_name if kind == 'money' else ''))
                out.append(FinancialMetric(name=metric_name, raw_value=raw, normalized_value=val,
                    unit='per_share' if kind=='share' else 'currency', currency=code,
                    reporting_period=fiscal_period, comparison_basis=None,
                    metric_variant='reported', extraction_status='extracted' if code else 'needs_review',
                    evidence=evidence_for(p, 'earnings')))
                seen.add(metric_name)
            previous_rows.append(line)
    # A small, predictable set of quarterly values, not arbitrary YTD duplicates.
    priority = {'Revenue':0,'Net income':1,'Diluted EPS':2,'Operating income':3}
    return sorted(out, key=lambda m:priority.get(m.name,99))


def extract_metrics(text: str, fiscal_period: str) -> list[FinancialMetric]:
    results = _statement_metrics(text, fiscal_period)
    seen = {(m.name, m.metric_variant) for m in results}
    # For documents imported from SEC, do not infer missing metrics by reading
    # arbitrary narrative/table values. These often mix quarterly and YTD data.
    is_filing = TABLE_START in text
    if is_filing:
        return results
    for p in passages(text):
        if len(p.text) > 480 or '|' in p.text or len(re.findall(r'\d[\d,]*',p.text)) > 6:
            continue
        for label, pattern, kind in PATTERNS:
            match = pattern.search(p.text)
            if not match:
                continue
            if label == 'Revenue' and re.search(r'\b(?:cost|deferred|unearned)\s+of\s*$', p.text[max(0,match.start()-40):match.start()], re.I):
                continue
            variant = 'adjusted' if re.search(r'\b(?:adjusted|non.GAAP)\b', p.text[:match.end()+35], re.I) else 'reported'
            key = (label, variant)
            if key in seen:
                continue
            value = _select_value(p.text[match.end():], kind)
            if not value:
                continue
            raw, numeric, code, verified = value
            basis = 'YoY' if re.search(r'\b(?:YoY|year.over.year)\b', p.text, re.I) else 'QoQ' if re.search(r'\b(?:QoQ|quarter.over.quarter)\b', p.text, re.I) else None
            results.append(FinancialMetric(name=label, raw_value=raw, normalized_value=numeric,
                unit='percent' if kind=='percent' else 'per_share' if kind=='share' else 'currency',
                currency=code if kind!='percent' else None, reporting_period=fiscal_period,
                comparison_basis=basis, metric_variant=variant,
                extraction_status='extracted' if verified else 'needs_review',
                evidence=evidence_for(p,'earnings')))
            seen.add(key)
    # Priority: safely scaled money, then EPS, then percentages.
    order = {'Revenue':0,'Net income':1,'Diluted EPS':2,'Operating income':3,'Gross margin':4,'Operating margin':5,'Free cash flow':6}
    return sorted(results,key=lambda m:(m.extraction_status!='extracted',order.get(m.name,99)))
