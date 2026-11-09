# FinPulse

**Earnings & News Intelligence Analyzer**

FinPulse is a financial intelligence project for understanding **what a company reported** and **how news outlets covered it**—without manually reading lengthy earnings transcripts and scattered articles.

The core idea is **Earnings vs. Media Perspective**: compare company-reported information with independently attributed news coverage, with source evidence attached to important claims.

## Planned MVP

- **Earnings analysis:** extract key points, financial metrics, and management commentary from pasted earnings text.
- **Evidence-linked insights:** preserve original passages, units, reporting periods, and sources.
- **News perspectives:** analyze up to three article URLs separately and compare their themes, emphasis, and potential disagreements.
- **Market context:** display historical price and volume around an earnings event, with clear event annotations.
- **Interactive dashboard:** make the results readable through responsive cards, charts, and source references.

## Planned stack

- **Backend:** Python, FastAPI
- **NLP:** spaCy, TextRank, YAKE, FinBERT; rules-based financial metric extraction
- **News extraction:** trafilatura
- **Stock data:** yfinance
- **Storage:** SQLite
- **Frontend:** React, Tailwind CSS (chart library to be selected)

The core pipeline is intended to use local/open NLP tools, **without requiring a paid LLM API**.

## Visual direction

- **Midnight Black:** `#02070A` — application background and primary surfaces
- **Electric Blue:** `#0297DE` — data visualizations and interactive emphasis
- **Cantaloupe Orange:** `#FC734D` — selective highlights and key events

Typography and final chart styling will be refined during frontend development.

## Status

**Early development / project setup.** The features above describe the intended MVP, not functionality already delivered. The README and setup instructions will evolve with implementation.

> **Disclaimer:** FinPulse is an informational analysis tool, not a stock-price predictor, trading signal, fact-checking authority, or source of investment advice.
