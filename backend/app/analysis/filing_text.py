"""Turn SEC inline-XBRL HTML into line-aware text without collapsing tables.

Does not reinterpret financial amounts. Statement tables are bracketed so the
metric engine can require a unit heading and an explicit quarterly column.
"""
from bs4 import BeautifulSoup, NavigableString
import re

TABLE_START = '[FINPULSE_TABLE_START]'
TABLE_END = '[FINPULSE_TABLE_END]'


def extract_filing_text(document: bytes, limit: int = 350_000) -> str:
    soup = BeautifulSoup(document, 'html.parser')
    for element in soup(['script', 'style', 'noscript', 'ix:header']):
        element.decompose()
    for table in list(soup.find_all('table')):
        rows = []
        for tr in table.find_all('tr'):
            cells = tr.find_all(['td', 'th'], recursive=False)
            if not cells:
                continue
            values = [re.sub(r'\s+', ' ', cell.get_text(' ', strip=True)).strip() for cell in cells]
            # Preserve column boundaries and remove entirely empty rows.
            if any(values):
                rows.append(' | '.join(values))
        if rows:
            table.replace_with(NavigableString('\n' + TABLE_START + '\n' + '\n'.join(rows)
                                                    + '\n' + TABLE_END + '\n'))
        else:
            table.decompose()
    # Keep paragraph and heading boundaries, but avoid creating double text.
    for block in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'li', 'section']):
        block.insert_before(NavigableString('\n'))
        block.insert_after(NavigableString('\n'))
    text = soup.get_text(' ', strip=False)
    text = re.sub(r'[\t ]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()[:limit]
