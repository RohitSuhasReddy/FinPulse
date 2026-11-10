# FinPulse

**Evidence-linked earnings & news intelligence** — compare what a company said with how the media covered it.

FinPulse is a local-first research dashboard built with **React, TypeScript, Recharts, FastAPI, Python and SQLite**. It analyzes pasted earnings transcripts/press releases alongside up to three independently attributed articles, then connects financial metrics, extractive highlights and common themes to source passages. Historical market context uses yfinance when available.

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

## Quick start on Windows

After the initial backend and frontend dependencies have been installed, run this from the **FinPulse repository root** in PowerShell:

```powershell
.\run-dev.ps1
```

Or use the equivalent shortcut:

```powershell
.\start.ps1
```

Both commands open **two PowerShell windows**: FastAPI on `http://127.0.0.1:8000` and React/Vite on `http://localhost:5173`. Leave those windows open while using FinPulse. Press `Ctrl+C` in each window to stop the servers.

The launcher uses `backend/.venv/Scripts/python.exe` and the installed `frontend/node_modules`. If either is missing, it shows the required setup commands rather than silently installing packages. If PowerShell prevents running a script, run `Set-ExecutionPolicy -Scope Process Bypass` in that terminal and retry.

## Automatic research mode (v0.3)

**Enter a ticker and click Auto research.** FinPulse selects the latest SEC filing or a chosen reporting period, searches GDELT for relevant online coverage, attempts to extract readable article bodies, and queries public Bluesky discussion. It saves results in the Library, with an optional comparison of reports. A valid **SEC User-Agent** (name/app plus contact email) must be configured once; see [Auto research setup](docs/auto-research.md).

- No news URLs or transcript pasting required for supported SEC-listed companies.
- When publishers block an article, only the **headline and link** are retained; FinPulse does not fabricate its text, sentiment, or source evidence.
- X is optional and requires `FINPULSE_X_BEARER_TOKEN` and an account with potentially billable X API read access. Instagram is **not scraped**, because generic public keyword searches are not openly available through official APIs.
- Social posts are displayed as **public opinions**, never as company-reported financial facts.
- A SEC filing is a **10-Q/10-K**, not an earnings call; dates are kept distinct.
- If an earnings date is unknown, the stock chart automatically shows recent historical price and volume without an earnings marker.

## Research workflow (v0.2)

- **Saved library:** click **Library** to reopen previous reports (across browser/server restarts), delete local reports or compare two reports' similarly defined metrics.
- **Less manual entry:** from **New analysis**, use **Find SEC filings** to choose a 10-Q/10-K and automatically load its text, or **Import PDF** for an investor earnings-release file.
- **Automated news discovery:** click **Discover coverage** to find article headlines and links through Google News RSS. Choose up to three different outlets automatically. **If an article cannot be read, it stays headline-only**: no fabricated article analysis, sentiment, or evidence.
- **One-time SEC setup:** configure `FINPULSE_SEC_USER_AGENT` with your own app/name and real contact email to comply with SEC access requirements. See [docs/research-workflow.md](docs/research-workflow.md).
- **Multiple periods and companies:** create as many reports as needed; each run analyzes one earnings document, while Library compares two saved reports side by side.

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

The dashboard opens directly on a clearly labeled *fictional ExampleCorp* report with illustrative (not live) stock prices. Use **Price / Volume** in the market lens to change the interactive chart. To analyze your own documents, click **New analysis** or **Analyze a company**, supply company details and earnings text, add optional news URLs or pasted articles, then click **Generate analysis**. The form opens as a slide-over, keeping the report uncluttered. Supplying an announcement date allows historical market data to load separately. Click **Demo** at any time to reset to the fictional sample.

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
| Foundation / negative space | Onyx Black | `#01010D` |
| Data and visual depth | Electric Indigo | `#6331FB` |
| Signal, focus, earnings marker, actions | Tropical Mint | `#88F9C0` |

This is the **second-generation visual direction**, inspired by the owner's color reference. It uses a full-width editorial layout **without a sidebar**, a custom pulse symbol and favicon, expressive **DM Sans + Instrument Serif** typography, animated yet reduced-motion-safe visual elements, and a large interactive price / volume hero chart. Source citations remain accessible in expandable evidence panels. **No fake live quotes:** the default demo is fictional and labeled as such; live data is historical and may be missing. Color tokens are centralized in `frontend/src/styles.css` and the browser theme color is configured in `frontend/index.html`. See [`docs/design-system.md`](docs/design-system.md).

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
  src/styles.css          # palette, transitions, layout and motion
  public/finpulse-mark.svg # custom favicon
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
