"""Fact-first, deterministic earnings briefing.

This is constrained NLP/extractive summarization, not an LLM paraphraser.
Financial claims are constructed only from confidently extracted, source-linked
metrics. Each operational observation is selected from a dated input passage.
"""
import re
from app.analysis.text import Passage, evidence_for, report_passages
from app.schemas import Evidence, FinancialMetric, ReportBrief, ReportFinding

# Labels are intentionally financial-report categories, not sentiment guesses.
TOPICS = (
    ("drivers", "What drove the quarter", r"\b(?:driven|driving|reflect(?:ed|s)?|due to|because of|supported by|attribut(?:ed|able)|contribut(?:ed|ion)|fuel(?:ed|ing)|benefit(?:ed)? from|demand|churn|pricing|membership gains|advertising growth)\b"),
    ("profitability", "Profitability and costs", r"\b(?:operating (?:income|profit|margin)|profitability|net income|gross margin|expenses?|cash flow|free cash flow|costs?|efficien(?:cy|cies)|investment spending)\b"),
    ("outlook", "Guidance and expectations", r"\b(?:forecast|outlook|guidance|expect(?:ed|s|ing)?|project(?:ed|s|ion)|anticipat(?:e|ed)|next quarter|following quarter|full.year|q[1-4] 20\d\d)\b"),
    ("risks", "Risks and watchpoints", r"\b(?:headwinds?|uncertain(?:ty|ties)|risk(?:s)?|delays?|pressures?|challenge(?:s|d)?|slowdown|weaker|reduced|downward)\b"),
    ("operations", "Business developments", r"\b(?:subscribers?|memberships?|engagement|viewership|content|films?|series|programming|product|service|partner(?:ship)?s?|licensed|live events|launched|regional|countries|customer(?:s)?|technology)\b"),
)
RX = {topic: re.compile(pattern, re.I) for topic, _, pattern in TOPICS}
OUTCOME = re.compile(r"\b(?:reported|grew|growth|increased?|decreased?|rose|fell|reached|generated|improv(?:ed|ing)|declined?|reduced?|raised?|exceeded|higher|lower|recorded|accelerated|expanded?|reflected|driven|drove|contributed|achieved|launched|delivered|forecast|expects?|projected|anticipates?|adjusted|noted|highlighted|saw|remained|beat|missed)\b", re.I)
NUMERIC = re.compile(r"(?:[$₹]\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:%|billion|million|bn|mn)\b)", re.I)
DEFINITION = re.compile(
    r"^\s*(?:f/?x[- ]neutral|constant currency|currency[- ]neutral|adjusted operating margin|"
    r"note(?:s)?:|footnotes?:)|"
    r"\b(?:excludes? the year.over.year effect|impact of hedging|defined as|is calculated by|"
    r"to calculate|the following table|see (?:page|note|appendix)|non.gap measures|"
    r"for a reconciliation|refer to the accompanying|please refer to|"
    r"unless otherwise specified|may not be comparable|see our website|"
    r"for more information|form 10-[qk]|not the full original|testing brief|"
    r"source integrity|important document notice)\b", re.I,
)
ASPIRATION = re.compile(r"^\s*(?:our goal is|our mission is|our aim is|we aim to|we strive to|we aspire to|we seek to|our objective is|we are focused on)", re.I)
HEADING = re.compile(r"^(?:[A-Z][A-Z0-9 &/,:()\-]{5,80})\s*\n\s*(?=[A-Z][a-z])")


def plain(text: str) -> str:
    text = HEADING.sub("", text.strip())
    return re.sub(r"\s+", " ", text).strip()


def summary_candidates(text: str) -> list[tuple[Passage, str]]:
    """Find actual observations, not footnotes, definitions or management aspirations."""
    found = []
    for passage in report_passages(text):
        sentence = plain(passage.text)
        if len(sentence) < 53 or len(sentence) > 395:
            continue
        if DEFINITION.search(sentence) or ASPIRATION.search(sentence):
            continue
        if '[FINPULSE_' in sentence or '|' in sentence:
            continue
        if len(re.findall(r"\b\d[\d,]*(?:\.\d+)?\b", sentence)) > 8:
            continue
        if sum(c.isdigit() for c in sentence) / len(sentence) > .19:
            continue
        if len(re.findall(r"[A-Za-z]{3,}", sentence)) < 7:
            continue
        if not (OUTCOME.search(sentence) or NUMERIC.search(sentence)):
            continue
        found.append((passage, sentence))
    return found


def metric_view(metric: FinancialMetric) -> str:
    val = metric.normalized_value
    assert val is not None
    if metric.unit == "percent":
        value = f"{val:,.1f}".rstrip('0').rstrip('.') if '.' in f"{val:,.1f}" else f"{val:,.0f}"
        return value + "%"
    prefix = "$" if metric.currency == "USD" else "₹" if metric.currency == "INR" else (metric.currency + " " if metric.currency else "")
    if metric.unit == "per_share":
        return prefix + f"{val:,.2f}"
    amount = abs(val)
    if amount >= 1e12:
        return prefix + f"{val / 1e12:,.2f}".rstrip('0').rstrip('.') + " trillion"
    if amount >= 1e9:
        return prefix + f"{val / 1e9:,.2f}".rstrip('0').rstrip('.') + " billion"
    if amount >= 1e6:
        return prefix + f"{val / 1e6:,.2f}".rstrip('0').rstrip('.') + " million"
    return prefix + f"{val:,.0f}"


def build_overview(metrics: list[FinancialMetric], company: str, period: str) -> tuple[str, list[Evidence]]:
    good = [m for m in metrics if m.extraction_status == "extracted" and m.normalized_value is not None
            and m.metric_variant != "adjusted"]
    priority = {"Revenue": 0, "Operating income": 1, "Operating margin": 2,
                "Net income": 3, "Diluted EPS": 4, "Free cash flow": 5, "Gross margin": 6}
    good.sort(key=lambda m: priority.get(m.name, 99))
    selected = []
    seen = set()
    for metric in good:
        if metric.name not in seen:
            selected.append(metric)
            seen.add(metric.name)
        if len(selected) == 4:
            break
    if not selected:
        return (
            "Reliable quarterly financial totals could not be established from the supplied text. "
            "The observations below are source-linked but should be checked against the official report.",
            [],
        )
    statements = [f"{m.name.lower()} of {metric_view(m)}" for m in selected]
    if len(statements) == 1:
        amounts = statements[0]
    elif len(statements) == 2:
        amounts = " and ".join(statements)
    else:
        amounts = ", ".join(statements[:-1]) + ", and " + statements[-1]
    return (f"For {period}, {company} reported {amounts}. "
            "These are extracted reported figures, not a stock-price forecast.",
            [m.evidence for m in selected])


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in {
        'reported', 'company', 'quarter', 'their', 'this', 'that', 'with', 'from', 'were',
        'year', 'over', 'which', 'and', 'the', 'have', 'will', 'revenue', 'growth',
    }}


def _score(topic: str, sentence: str, index: int, total: int) -> float:
    topical = len(RX[topic].findall(sentence))
    score = topical * 3
    score += min(3, len(OUTCOME.findall(sentence))) * 1.6
    score += 2.5 if NUMERIC.search(sentence) else 0
    score += 1.2 if 70 <= len(sentence) <= 260 else -0.5
    score += 1.4 if re.search(r"\b(?:compared|versus|year.over.year|yoy|from .* to |due to|because|reflect(?:ed|s)|driven)\b", sentence, re.I) else 0
    score += max(0, 1 - index/max(total, 1)) * .6
    if topic == "drivers" and not re.search(r"\b(?:reflect(?:ed|s)|driven|drove|due to|because|supported by|attribut|contribut|fuel|benefit)\b", sentence, re.I):
        score -= 3
    if topic == "profitability" and re.search(r"\b(?:exceeded|below|improved|decreased|increased|margin|expenses|cost)\b", sentence, re.I):
        score += 2
    if topic == "outlook" and re.search(r"\b(?:forecast|guidance|outlook|projected|expect|anticipate)\b", sentence, re.I):
        score += 3
    if topic == "risks" and not RX["risks"].search(sentence):
        score -= 5
    # First-person mission statements without metrics should never win.
    if re.search(r"\b(?:commitment to|our strategy is|continue to invest|opportunities to|our priority is)\b", sentence, re.I) and not NUMERIC.search(sentence):
        score -= 4
    return score


def build_report_brief(text: str, metrics: list[FinancialMetric], company: str, period: str) -> ReportBrief:
    overview, overview_evidence = build_overview(metrics, company, period)
    candidates = summary_candidates(text)
    scored: list[tuple[str, Passage, str, float]] = []
    for index, (source, sentence) in enumerate(candidates):
        for topic, _, _ in TOPICS:
            if RX[topic].search(sentence):
                score = _score(topic, sentence, index, len(candidates))
                if score >= 5.0:
                    scored.append((topic, source, sentence, score))
    # Prefer the most informative statement for each topic, with one complementary
    # passage when it adds new information. No invented connective prose.
    chosen: set[int] = set()
    findings: list[ReportFinding] = []
    for topic, heading, _ in TOPICS:
        ranked = sorted((x for x in scored if x[0] == topic and x[1].start not in chosen),
                        key=lambda v: v[3], reverse=True)
        picked = []
        for _, source, sentence, score in ranked:
            if picked and (
                len(picked) >= 2 or
                len(picked[0][2]) + len(sentence) > 400 or
                len(_tokens(picked[0][2]) & _tokens(sentence))/max(len(_tokens(picked[0][2]) | _tokens(sentence)), 1) > .34
            ):
                continue
            picked.append((source, sentence, score))
            if len(picked) == 2:
                break
        if not picked:
            continue
        evidence = [evidence_for(p, "earnings") for p, _, _ in picked]
        body = " ".join(s.rstrip(". ") + "." for _, s, _ in picked)
        findings.append(ReportFinding(
            category=topic, heading=heading, body=body, evidence=evidence,
        ))
        chosen.update(p.start for p, _, _ in picked)
        if len(findings) == 4:
            break
    return ReportBrief(
        overview=overview,
        overview_evidence=overview_evidence,
        findings=findings,
        method="grounded-nlp-v3",
    )
