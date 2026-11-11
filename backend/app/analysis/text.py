"""Evidence-linked text cleanup and selective narrative highlights."""
from dataclasses import dataclass
from collections import Counter
from math import log
import re
from app.schemas import Evidence, Highlight

STOPWORDS = set("the a an and or to of for in on by with from was were is are as at this that it its we our their have has had will can be been about into over more than also not they company quarter year which while during these those".split())
THEME_TERMS = {
    'Revenue growth': ('revenue', 'sales', 'growth', 'grew', 'top line'),
    'Profitability': ('profit', 'earnings', 'income', 'eps', 'margin', 'operating'),
    'Guidance': ('guidance', 'outlook', 'forecast', 'expects', 'expectation'),
    'Demand': ('demand', 'orders', 'customer', 'consumer', 'bookings'),
    'Costs & efficiency': ('cost', 'expense', 'efficiency', 'restructur', 'saving'),
    'Risks': ('risk', 'uncertain', 'headwind', 'challeng', 'pressure'),
    'AI & technology': ('artificial intelligence', 'generative ai', 'ai ', 'cloud', 'technology'),
    'Cash flow': ('cash flow', 'liquidity', 'free cash', 'capital expenditure'),
}

@dataclass(frozen=True)
class Passage:
    text: str
    start: int
    end: int


def clean_text(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\u00a0',' ')
    return re.sub(r'[ \t]+', ' ', text).strip()


def passages(text: str) -> list[Passage]:
    bounds = [0]
    for match in re.finditer(r'(?<=[.!?])\s+(?=[A-Z₹$0-9])|\n+',text):
        bounds.append(match.end())
    bounds.append(len(text))
    output = []
    for start,end in zip(bounds,bounds[1:]):
        sentence = text[start:end].strip()
        if len(sentence) < 15: continue
        begin = text.find(sentence,start,end)
        if begin >= 0:
            output.append(Passage(sentence,begin,begin+len(sentence)))
    return output




def report_passages(text: str) -> list[Passage]:
    """Read PDF-wrapped sentences without treating every visual line as a sentence.

    Preserve raw source offsets for expandable citations; UI may collapse display
    whitespace, but evidence.text always equals text[start_offset:end_offset].
    """
    separator = re.compile(r'(?<=[.!?])\s+(?=[A-Z₹$0-9])|\n[ \t]*\n+')
    starts = [0] + [match.end() for match in separator.finditer(text)]
    ends = [match.start() for match in separator.finditer(text)] + [len(text)]
    result = []
    for start, end in zip(starts, ends):
        raw = text[start:end]
        leading = len(raw) - len(raw.lstrip())
        stripped = raw.strip()
        if len(stripped) < 30:
            continue
        offset = start + leading
        result.append(Passage(text=stripped, start=offset, end=offset+len(stripped)))
    return result

def evidence_for(passage: Passage, source_id: str) -> Evidence:
    return Evidence(source_id=source_id,text=passage.text,start_offset=passage.start,end_offset=passage.end)


def tokens(text: str) -> list[str]:
    return [word for word in re.findall(r'[a-z][a-z\-]{2,}',text.lower()) if word not in STOPWORDS]


def _narrative(p: Passage) -> bool:
    s=p.text
    if not 65 <= len(s) <= 390: return False
    if '[FINPULSE_TABLE_' in s or '|' in s: return False
    if len(re.findall(r'\b\d[\d,]*(?:\.\d+)?\b',s)) >= 7: return False
    if sum(ch.isdigit() for ch in s)/len(s) > 0.15: return False
    if len(tokens(s)) < 9: return False
    if re.search(r'(?:condensed consolidated statements|\bunaudited\b|see accompanying notes|table of contents|sec form 10-[qk]|\bitem\s+\d\b|registrant|stock-based compensation expense|weighted.average shares|accounts receivable\s*\()',s,re.I):
        return False
    return True


def summarize(text: str, source_id: str, count: int = 3) -> list[Highlight]:
    """Select short, source-exact narrative sentences; never select raw tables."""
    candidates = [p for p in report_passages(text) if _narrative(p) and not re.search(
        r'^(?:our goal is|our mission|we aim|f/?x[- ]neutral .*excludes|constant currency .*excludes)',
        re.sub(r'\\s+', ' ', p.text).strip(), re.I)]
    if not candidates:
        return []
    docs = [set(tokens(p.text)) for p in candidates]
    freqs = Counter(word for doc in docs for word in doc)
    scored = []
    emphasis = re.compile(r'\b(revenue|growth|demand|profitability|guidance|outlook|customers?|products?|margin|cash flow|investments?|increased?|decreased?|driven|reflects?|expects?|reported|data center)\b',re.I)
    for i,(p,doc) in enumerate(zip(candidates,docs)):
        informative = min(3, len(emphasis.findall(p.text)))*2.1
        rare = sum(log((len(docs)+1)/(freqs[w]+1))+1 for w in doc)/max(len(doc),1)**0.7
        length = 2.0 if 100 <= len(p.text) <= 270 else 0.0
        # SEC legal boilerplate and enumerated table notes are poor highlights.
        boilerplate = 5 if re.search(r'\b(securities act|exhibit|hereby|forward-looking statements|refer to|accounting standards|subject to change)\b',p.text,re.I) else 0
        scored.append((informative+rare+length-boilerplate,i))
    selected = []
    for _,i in sorted(scored,reverse=True):
        if any(len(docs[i] & docs[j])/max(len(docs[i] | docs[j]),1) > .55 for j in selected):
            continue
        selected.append(i)
        if len(selected)==count:
            break
    # Return source-document order, not ranked order, for natural reading.
    return [Highlight(text=candidates[i].text,evidence=evidence_for(candidates[i],source_id)) for i in sorted(selected)]


def detected_themes(text: str) -> dict[str, Passage]:
    found = {}
    for p in passages(text):
        if not _narrative(p):
            continue
        lower = ' '+p.text.lower()+' '
        for theme,words in THEME_TERMS.items():
            if theme not in found and any(word in lower for word in words):
                found[theme]=p
    return found
