# FinPulse

**Evidence-linked earnings & news intelligence** — compare what a company said with how the media covered it.

FinPulse is a local-first research dashboard built with **React, TypeScript, Recharts, FastAPI, Python and SQLite**. It analyzes pasted earnings transcripts/press releases alongside up to three independently attributed articles, then connects financial metrics, extractive highlights and common themes to source passages. Historical market context uses yfinance when available. No paid LLM API is required.

> **Status: working MVP / initial implementation.** The demo is fictional. Financial metric extraction and media comparison are rule-based baselines, not audited facts. This is **not investment advice**, a stock predictor, or a fact-checker.

## Screens and functionality

- Company, ticker, fiscal period, announcement date and announcement timing inputs.
- Earnings text paste; best-effort PDF-to-text import (8 MB / 80 pages max).
- Financial metric extraction (revenue, EPS, margins, operating/net income, cash flow) with unit, period, variant and supporting passage.
- Text highlights and visible citations with source identifiers and offsets.
- Up to three public article URLs or user-pasted article bodies, processed independently, with graceful failures.
- Shared and distinct themes between reported earnings and each media source.
- Estimated sentiment labels (simple local rules by default; optional pre-cached offline FinBERT).
- Historical daily closing price and volume around an event, with conservative announcement-session alignment.
- Local SQLite persistence of structured analyses, an API and responsive interactive dashboard.

## Run locally

Requires **Python 3.11+**, **Node.js 20+** and internet access for initial dependency installation. Use two terminals at the repository root.

**Backend** (macOS/Linux):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Backend** (Windows PowerShell):

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend** (a second terminal):

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`. API reference: **http://localhost:8000/docs**. Run `npm run build` to build the frontend.

Start with **Explore demo** to view a clearly labeled *fictional ExampleCorp* dashboard, including illustrative (not live) stock prices. To analyze your own documents, expand **Start an analysis**, provide a company and earnings text, add optional news URLs/pasted articles, and click **Analyze intelligence**. Providing a date allows the backend to fetch historical market context separately.

## Test

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

Frontend build check: `cd frontend && npm install && npm run build`. GitHub Actions runs both checks on pushes and pull requests when enabled.

## API

| Endpoint | Function |
|---|---|
| `GET /api/health` | Health check |
| `POST /api/v1/analyze` | Typed company/earnings/news request → evidence-linked analysis |
| `GET /api/v1/analyses/{id}` | Retrieve a locally cached analysis |
| `POST /api/v1/articles/extract` | Extract an article from a public HTTP(S) URL |
| `POST /api/v1/pdf/extract` | Generic PDF-to-text extraction via multipart upload |
| `GET /api/v1/stocks/{ticker}?announcement_date=YYYY-MM-DD&market_timing=unknown` | Historical market context |

Schema and request examples: [`frontend/src/data/sample-request.json`](frontend/src/data/sample-request.json) and interactive API docs at `/docs`.

## Palette and design

| Role | Color | Hex |
|---|---|---|
| Main background / canvas | Midnight Black | `#02070A` |
| Graphs / interactive data | Electric Blue | `#0297DE` |
| Event markers / selective emphasis | Cantaloupe Orange | `#FC734D` |

Styles are centrally tokenized in `frontend/src/styles.css`. **Typography is intentionally provisional**; it can be changed later without redesigning the application. Colors distinguish roles, but status and meaning also use text labels.

## Project layout

```text
backend/
  app/main.py              # HTTP routes
  app/schemas.py           # API contracts and validation
  app/analysis/            # metrics, extractive text, comparison, sentiment
  app/ingest.py            # URL validation and article extraction
  app/stock.py             # yfinance historical session context
  app/cache.py             # SQLite derived-analysis store
  tests/                  # pytest suite
frontend/
  src/App.tsx              # responsive dashboard, upload and input flow
  src/styles.css          # centralized design tokens
  src/data/               # explicitly fictional demo only
  src/types.ts            # TypeScript API contracts
docs/architecture.md      # design, limitations and security notes
```

## Known limitations

- Financial extraction relies on patterns and may miss context, tables, or alternative presentation formats; check each passage before drawing conclusions.
- Theme overlap represents topic similarity, **not** truth, factual agreement, causality or contradiction. The sentiment heuristic is a **language estimate**, not a market measurement.
- Article fetching may be blocked by paywalls, anti-bot measures or network restrictions; paste the article instead. **Public deployment requires stronger outbound network controls / DNS pinning** to mitigate DNS rebinding; this service is intended for trusted local use.
- PDF extraction works best with digitally generated text; scanned files, complex tables and repeated headers may be inaccurate.
- Stock price/volume comes from a third-party source and may be unavailable, delayed or incomplete. No event-reaction figure is computed when announcement timing is unknown.
- Results and evidence are cached in a **local SQLite file** by default (`backend/.local/finpulse.sqlite3`). Set `FINPULSE_DISABLE_CACHE=1` to disable storage or `FINPULSE_DB_PATH` to set a different path. Do not process confidential texts on shared computers.
- Optional FinBERT inference requires installing `backend/requirements-ml.txt`, pre-caching model weights, and setting `FINPULSE_SENTIMENT=finbert`. No model is downloaded during requests. Basic rule sentiment runs by default.

For architecture details and future improvements, see [`docs/architecture.md`](docs/architecture.md). The full project roadmap is retained under `docs/FinPulse_Project_Description_v1.3.txt`.
