"""Source-aware, deterministic text processing that preserves exact evidence offsets."""
from dataclasses import dataclass
import re
from collections import Counter
from math import log

from app.schemas import Evidence, Highlight

STOPWORDS = set("the a an and or to of for in on by with from was were is are as at this that it its we our their have has had will can be been about into over more than also not they company quarter year which while during these those".split())

THEME_TERMS = {
    "Revenue growth": ("revenue", "sales", "growth", "grew", "top line"),
    "Profitability": ("profit", "earnings", "income", "eps", "margin", "operating"),
    "Guidance": ("guidance", "outlook", "forecast", "expects", "expectation"),
    "Demand": ("demand", "orders", "customer", "consumer", "bookings"),
    "Costs & efficiency": ("cost", "expense", "efficiency", "restructur", "saving"),
    "Risks": ("risk", "uncertain", "headwind", "challeng", "pressure"),
    "AI & technology": ("artificial intelligence", "generative ai", "ai ", "cloud", "technology"),
    "Cash flow": ("cash flow", "liquidity", "free cash", "capital expenditure"),
}


@dataclass(frozen=True)
class Passage:
    text: str
    start: int
    end: int


def clean_text(text: str) -> str:
    """Normalize user input; downstream offsets reference this cleaned version."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    return re.sub(r"[ \t]+", " ", text).strip()


def passages(text: str) -> list[Passage]:
    # Do not split inside numerical decimals. Preserve full stop in evidence.
    boundaries = [0]
    for match in re.finditer(r"(?<=[.!?])\s+(?=[A-Z₹$0-9])|\n+", text):
        boundaries.append(match.end())
    boundaries.append(len(text))
    result: list[Passage] = []
    for start, end in zip(boundaries, boundaries[1:]):
        segment = text[start:end].strip()
        if len(segment) < 15:
            continue
        begin = text.find(segment, start, end)
        result.append(Passage(segment, begin, begin + len(segment)))
    return result


def evidence_for(passage: Passage, source_id: str) -> Evidence:
    return Evidence(source_id=source_id, text=passage.text, start_offset=passage.start, end_offset=passage.end)


def tokens(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z][a-z\-]{2,}", text.lower()) if word not in STOPWORDS]


def summarize(text: str, source_id: str, count: int = 3) -> list[Highlight]:
    """Lightweight extractive ranking; no invented connective prose."""
    items = passages(text)
    if not items:
        return []
    if len(items) <= count:
        return [Highlight(text=p.text, evidence=evidence_for(p, source_id)) for p in items]
    docs = [set(tokens(p.text)) for p in items]
    frequencies = Counter(t for doc in docs for t in doc)
    scores = []
    for i, doc in enumerate(docs):
        rarity = sum(log((len(docs) + 1) / (frequencies[t] + 1)) + 1 for t in doc)
        lexical = rarity / max(len(doc) ** 0.5, 1)
        overlap = sum(len(doc & other) / max(len(doc | other), 1) for j, other in enumerate(docs) if j != i)
        scores.append((lexical + 1.5 * overlap, i))
    chosen = sorted(i for _, i in sorted(scores, reverse=True)[:count])
    return [Highlight(text=items[i].text, evidence=evidence_for(items[i], source_id)) for i in chosen]


def detected_themes(text: str) -> dict[str, Passage]:
    found = {}
    for p in passages(text):
        lowercase = " " + p.text.lower() + " "
        for theme, terms in THEME_TERMS.items():
            if theme not in found and any(term in lowercase for term in terms):
                found[theme] = p
    return found
