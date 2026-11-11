# FinPulse

**One report. A whole new perspective.**

FinPulse is a local-first earnings intelligence studio. Upload a quarterly earnings **PDF or TXT**, extract source-linked financial figures with deterministic NLP, follow the report through an animated earnings story, inspect historical market movement, add manually curated news coverage, compare **any number of saved quarters**, and return to a company-organized archive.

Unlike the previous version, FinPulse does **not** run ticker-first auto research, scrape publishers, ingest social media, or require SEC credentials. A failed optional Gemini request can never prevent an earnings report from being analyzed or saved.

## The six screens

| Section | Experience |
|---|---|
| **Studio** | Enter company/ticker/quarter and optionally announcement timing. Upload PDF/TXT or paste text; add outlet, headline, optional source URL and manually supplied full article text. |
| **Earnings** | Staggered scroll-reveal of confidently extracted metrics connected by a vertical signal line, followed by an evidence-linked NLP narrative. |
| **Market** | Daily historical closes, the seven calendar days before and after the announced date, and optional Gemini commentary about observed movements and possible report context. |
| **Coverage** | Outlet picker with animated switching; headline and source link, and an NLP summary **only** if the article body was supplied. |
| **Compare** | Choose 2, 3 or more quarters of **one company**; timeline, cross-period metric matrix, evidence excerpts and deterministic trend commentary. Missing figures remain blank. |
| **Library** | Persistent saved analyses grouped by company, fiscal year and quarter. Reopen or delete locally. |

The navigation is **section-based**, not one endless app page. The Earnings experience intentionally uses scroll storytelling *within its own section*. Animations respect reduced-motion settings.

## Stack

- **Frontend:** React 18, TypeScript, Vite, Recharts, Lucide, CSS.
- **Backend:** Python 3.11+, FastAPI, Pydantic, PyMuPDF, yfinance and local deterministic text/financial extraction.
- **Persistence:** SQLite in `backend/.local/finpulse.sqlite3` (unless configured otherwise).
- **Optional AI:** Gemini API **only for stock-price interpretation**, not metrics, report summaries, article summaries or multi-quarter financial comparisons.

## First run (Windows PowerShell)

Requirements: **Python 3.11+**, **Node.js 20+**, npm and internet access to install packages.

From the project root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..\frontend
npm install
cd ..
.\run-dev.ps1
```

Two terminals start: API at **http://127.0.0.1:8000** and web at **http://localhost:5173**. Close them with `Ctrl+C`. If PowerShell blocks script execution, run `Set-ExecutionPolicy -Scope Process Bypass` for that terminal.

### Every later run

From the repository root:

```powershell
.\run-dev.ps1
```

`.\start.ps1` is also supported. Both reuse the installed local backend venv and frontend node modules.

For macOS/Linux: create/activate `backend/.venv`, install `backend/requirements.txt`, then launch `uvicorn app.main:app --reload --port 8000` from `backend`; separately `cd frontend && npm install && npm run dev`.

## Optional Gemini interpretation

**No key is required for core reports, coverage, comparisons or charts.**

To enable the optional historical market explanation:

1. Copy `backend/.env.example` to `backend/.env`.
2. Put your actual key on the `GEMINI_API_KEY=` line.
3. Restart the backend. `backend/.env` is loaded automatically and is ignored by Git.

The default model is `gemini-3.5-flash`; change `FINPULSE_GEMINI_MODEL` if your key has access to a different supported model. See [Google's Gemini model list](https://ai.google.dev/gemini-api/docs/models).

Only the selected report's **extracted metrics, excerpts and observed pre/post price windows** are sent to Gemini. The full uploaded PDF is not sent to Gemini for analysis. The output is a possible contextual interpretation, **not proof of causality, forecast probabilities or trading advice**. Responses are cached locally with the report ID when available. If the key, model or provider fails, price observations continue to render.

## Reliability rules

- **Manual sources only:** TXT is read in the browser, PDFs through the local backend (16 MB / 150 pages maximum; up to 350,000 extracted characters). Scanned documents without machine-readable text need OCR before upload.
- **No invented financial facts:** value, unit, reporting period, adjustment basis and source excerpt must be traceable. Ambiguous amounts are withheld/marked for review.
- **No fake news summaries:** for manually entered headline-only links, FinPulse displays a source link and explicitly does not summarize the article or infer its sentiment.
- **No automatic SEC or news lookup:** filing and web research pipelines have been retired.
- **Event discipline:** the pre/post windows show calendar dates with available trading sessions, not invented daily data. Earnings announcement timing may be unknown; an observed move does not prove why it happened.
- **Comparability first:** multi-quarter columns match metric name, units, currency and reported/adjusted basis, and ignore older unverified extraction versions. A selected-period change is **not automatically labeled QoQ**.
- **Preserved archives:** existing saved analyses remain in the local SQLite database after upgrading. Older SEC-based analyses remain readable, though unverified metrics may be excluded from comparisons.
- **Privacy:** earnings extracts and summaries are stored locally; optional Gemini is an outbound API request. Do not upload confidential reports without permission.

## Tests

```powershell
cd backend
pip install -r requirements-dev.txt
pytest -q
cd ..\frontend
npm run build
```

The GitHub Actions workflow runs Python tests and the TypeScript/Vite production build for pull requests.

## API overview

| Method / path | Purpose |
|---|---|
| `POST /api/v1/pdf/extract` | Extract selectable text from a manually uploaded PDF |
| `POST /api/v1/analyze` | NLP analysis and local save of one report plus optional pasted articles |
| `GET /api/v1/analyses` | Browse saved report metadata |
| `GET /api/v1/analyses/{id}` | Reopen a report |
| `DELETE /api/v1/analyses/{id}` | Delete saved analysis |
| `POST /api/v1/compare/multi` | Compare an array of saved analysis IDs for the same ticker |
| `GET /api/v1/stocks/{ticker}` | Historical closes around a supplied announcement date |
| `GET /api/v1/market/interpret/{id}` | Price windows plus optional Gemini commentary |

Swagger API docs: **http://127.0.0.1:8000/docs**.

## Design

Colors: Onyx `#01010D`, Electric Indigo `#6331FB`, Tropical Mint `#88F9C0`. Typography: DM Sans + Instrument Serif. The sections, animated story rail, blur/transform reveals, news orbit and report comparison matrix live in `frontend/src/App.tsx` and `frontend/src/experience.css`.

**FinPulse is an educational research tool, not investment advice. Verify every material reported figure against the original company filing or earnings release.**
