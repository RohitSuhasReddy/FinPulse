"""Conservative metric extraction with evidence and explicit uncertainty."""
import re
from app.analysis.text import Passage, evidence_for, passages
from app.schemas import FinancialMetric

# Values are accepted only when in proximity to an explicit metric mention.
PATTERNS = [
    ("Revenue", re.compile(r"\b(?:total\s+)?revenues?\b", re.I), "money"),
    ("Diluted EPS", re.compile(r"\b(?:diluted\s+)?(?:earnings\s+per\s+(?:diluted\s+)?share|EPS)\b", re.I), "share"),
    ("Operating income", re.compile(r"\boperating\s+(?:income|profit)\b", re.I), "money"),
    ("Net income", re.compile(r"\bnet\s+(?:income|profit)\b", re.I), "money"),
    ("Operating margin", re.compile(r"\boperating\s+margin\b", re.I), "percent"),
    ("Gross margin", re.compile(r"\bgross\s+margin\b", re.I), "percent"),
    ("Free cash flow", re.compile(r"\bfree\s+cash\s+flow\b", re.I), "money"),
]

# Separate pattern because % followed by punctuation isn't a word-boundary.
VALUE = re.compile(r"(?P<currency>US\$|USD\s*|\$|₹|INR\s*)?\s*(?P<number>\(?-?\d[\d,]*(?:\.\d+)?\)?)\s*(?P<scale>billion|million|thousand|bn|mn|[BMK])?\s*(?P<pct>%|percent)?", re.I)
SCALES = {"billion": 1e9, "bn": 1e9, "b": 1e9, "million": 1e6, "mn": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3}


def _select_value(tail: str, kind: str):
    candidates = []
    for candidate in VALUE.finditer(tail[:100]):
        token = candidate.group(0).strip()
        if not token:
            continue
        digits = candidate.group("number")
        currency = candidate.group("currency")
        scale = candidate.group("scale")
        pct = candidate.group("pct")
        # Don't treat plain year references, percent changes, or isolated numbers as money.
        if kind == "percent" and pct is None:
            continue
        if kind == "money" and not (currency or scale):
            continue
        if kind == "share" and not currency and not re.search(r"\b(?:of|was|at|to)\s*$", tail[:candidate.start()], re.I):
            continue
        if kind != "percent" and pct:
            continue
        try:
            value = float(digits.strip("()").replace(",", ""))
            if digits.startswith("(") or digits.startswith("-"):
                value = -abs(value)
            if scale:
                value *= SCALES[scale.lower()]
        except (ValueError, KeyError):
            continue
        code = "INR" if currency and ("₹" in currency or "INR" in currency.upper()) else "USD" if currency else None
        candidates.append((candidate.start(), token, value, code))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])


def extract_metrics(text: str, fiscal_period: str) -> list[FinancialMetric]:
    items = []
    seen = set()
    for passage in passages(text):
        for label, pattern, kind in PATTERNS:
            match = pattern.search(passage.text)
            if not match:
                continue
            parsed = _select_value(passage.text[match.end():], kind)
            if not parsed:
                continue
            _, raw, numeric, currency = parsed
            basis = "YoY" if re.search(r"\b(?:YoY|year.over.year)\b", passage.text, re.I) else "QoQ" if re.search(r"\b(?:QoQ|quarter.over.quarter)\b", passage.text, re.I) else None
            variant = "adjusted" if re.search(r"\b(?:adjusted|non.GAAP)\b", passage.text[:match.end()+35], re.I) else "reported"
            key = (label, raw, variant)
            if key in seen:
                continue
            seen.add(key)
            items.append(FinancialMetric(
                name=label, raw_value=raw, normalized_value=numeric,
                unit="percent" if kind == "percent" else "per_share" if kind == "share" else "currency",
                currency=currency if kind != "percent" else None,
                reporting_period=fiscal_period, comparison_basis=basis, metric_variant=variant,
                extraction_status="extracted" if (currency or kind == "percent" or (kind == "money" and re.search(r"billion|million|thousand|\bbn\b|\bmn\b", raw, re.I))) else "needs_review",
                evidence=evidence_for(passage, "earnings"),
            ))
    return items
