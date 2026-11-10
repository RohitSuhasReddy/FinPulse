# Automated research — FinPulse

Enter **one ticker** using **Auto research** from the dashboard. FinPulse will:

1. Resolve the company through the SEC ticker index and import its most recent (or a period-selected) **10-Q/10-K**. These are **regulatory filings, not earnings-call transcripts**; the filing date is not assumed to be an earnings announcement.
2. Search the [GDELT DOC API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) for relevant news near the selected filing. GDELT search has limited recent history and rate limits. On failure/older dates, attempt Google News RSS headline discovery.
3. Attempt publisher article text extraction using FinPulse's existing URL restrictions. **Only successfully retrieved article bodies contribute source-backed summaries, themes, and sentiment.** Blocked articles remain labeled `metadata_only` with their title and URL. Financial figures from those headlines are not extracted.
4. Search the [Bluesky public API](https://docs.bsky.app/) for recent public posts related to the company. These are a *small, nonrepresentative set of opinions* displayed separately, not evidence for reported financial results.
5. Optionally query the official [X API](https://developer.x.com/) when `FINPULSE_X_BEARER_TOKEN` is configured. **X may charge for reads.** Do not enable without checking billing, developer credentials, and permissions. Instagram general public-post keyword search is not provided through the supported official API workflow; no unauthorized scraping is included.
6. Store the results in the local SQLite Library. Reopen or compare reports from there.

## SEC configuration (one-time)

The SEC requires an identifiable User-Agent. Set your **own** contact identity (not a shared or invented email) in the backend's environment, e.g. in the PowerShell terminal **before launching**:

```powershell
$env:FINPULSE_SEC_USER_AGENT = 'FinPulse Research Your Name your-real-email@example.com'
.\run-dev.ps1
```

The `.env` template remains informational and is not automatically loaded. In a fresh terminal you must set the environment variable again; alternatively configure the variable in your Windows user environment before launching. Do not commit private credentials.

## Scope and caveats

- Auto research is a **bounded one-shot action**, not a continuous crawler or a background daemon.
- It is limited to companies with a usable SEC filing and the publicly available sources at request time. For non-US companies without a matching SEC ticker, use manual PDF import.
- To search a previous filing enter its **report period end**, which may not equal the earnings announcement date.
- If the announcement date is not known, stock context is not automatically attributed to an earnings event.
- GDELT's index timestamps are *first seen*, not guaranteed article publication dates. Some publishers forbid or block extraction.
- Keep social opinions and publisher reporting separate from financial disclosures. This is research support, not investment advice.
- If a social provider is offline or access is restricted, the earnings analysis remains available with an explicit warning.

## API

`POST /api/v1/research/auto`

```json
{"ticker":"GOOGL","include_social":true,"max_articles":5}
```

Optional: `period_end`, `announcement_date`, `market_timing`. Returns the same `AnalyzeResponse` schema as manual analysis, extended with `data_origin`, `source_document_url`, `source_document_type`, and `social_posts`.
