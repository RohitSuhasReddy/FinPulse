# FinPulse research workflow (v0.2)

## Short route

1. Run `./run-dev.ps1` (PowerShell) in the project root after installing the dependencies.
2. Click **New analysis** and enter the company ticker and name.
3. Click **Find SEC filings**, choose an official 10-Q/10-K to import its text automatically. Or upload a publicly available earnings-release PDF. **SEC import is optional and requires one-time identification configuration** (below).
4. Click **Discover coverage** to find up to three news outlets. FinPulse discovers Google News RSS headlines and article links. It will attempt full-article extraction for accessible source URLs; blocked RSS links remain *metadata-only*, excluded from sentiment/evidence comparison. This is **not a bypass for paywalls**.
5. Generate the analysis. Click **Library** to revisit it later, or select two analyses and compare their source-linked metrics.

## One-time SEC configuration

The SEC requires a user-identifying `User-Agent` containing contact information. Set your **own real contact details** as an environment variable (do not paste an email you do not control):

```powershell
setx FINPULSE_SEC_USER_AGENT "FinPulse Local Research Your Name your-email@example.com"
```

Replace the example name and email. Close and restart the backend terminal after running `setx`, then click **Find SEC filings**. The value is transmitted to the SEC as the HTTP `User-Agent` and is **not stored in your GitHub repository**. The SEC may restrict or temporarily block requests; this feature doesn't scrape private or paywalled sources. `company_tickers.json` provides the CIK and `data.sec.gov` provides recent 10-Q/10-K metadata. Selecting one downloads the linked official primary document. Some tables and XBRL markup may not parse correctly; use cited figures with care.

## What is saved?

Finished structured reports are saved to the local SQLite file `backend/.local/finpulse.sqlite3` (unless `FINPULSE_DISABLE_CACHE=1`). Your Library lists saved reports across browser and backend restarts; open an entry to show its result. You may delete reports manually. Reports are local to this installation, not synced to GitHub or across devices. The source text is not separately stored as an uploaded PDF; **source passages embedded in the structured output are retained** and may contain sensitive text. Back up the SQLite file if you move computers.

## Honest limitations

- The underlying NLP is an extractive/rule-based first iteration, not an audited earnings model.
- SEC 10-Q/10-K documents are not earnings calls or investor-relations press releases. Filing date and report period-end are **not** the earnings announcement date; add that date manually for stock-event alignment.
- News search returns *headlines, publisher names and feed links* (metadata). If the original article cannot be accessed, FinPulse **does not** pretend to know its content, derive body sentiment, or claim the source agrees/disagrees with the earnings release. Some feed links cannot be resolved to the originating publisher and will stay metadata-only.
- The report library offers side-by-side comparisons of metrics where units, currency, label and reported/adjusted basis match. Differing fiscal periods, differently defined metrics or accounting approaches require user judgment. Comparison is not investment advice.
- Current per-report analysis accepts one company's earnings document and up to three articles. The library supports **many companies and periods** and can compare two saved results; automatic consolidated multi-quarter narrative analysis is future work.
