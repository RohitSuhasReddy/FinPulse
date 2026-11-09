# Architecture and implementation notes

## Data flow

1. React collects one company's ticker, fiscal period, earnings text and up to three URL/pasted news sources.
2. FastAPI validates the request. Public article URL fetching uses explicit DNS checks for global addresses, HTTP(S)/port restrictions, redirect re-validation, response-size/time limits and no inherited proxy configuration.
3. Source-specific text is cleaned, extractive highlights are selected, financial metrics and their evidence are captured, and finance-related language sentiment is heuristically labeled.
4. The comparison engine matches conservative domain themes and stores representative evidence per document. Sources remain independent, including failed sources.
5. Typed Pydantic models serialize structured results. SQLite caches analysis results locally for later retrieval.
6. The dashboard renders metric evidence, per-source media cards, overlaps and historical stock visuals. Stock data is fetched separately from yfinance, not blended into earnings facts.

## Evidence design

An evidence record contains `source_id`, text and 0-based character offsets into the **cleaned** source. Normalized metric values are separate from the original literal number. Every financial metric includes a reporting period (provided by the user), comparison basis where identifiable, and a reported/adjusted variant. Unknown/ambiguous facts are left null or flagged for review. This is a rules-based initial system, not professional audit-grade parsing.

## Interpretation safeguards

- "Shared" means keyword-based topical overlap; it never asserts that sources agree on the exact numerical claim.
- "News only" and "Earnings only" mean the term matcher did not see the theme on the other side. They are not proofs of omission.
- Heuristic sentiment is a reading of passage language only. Use optional pre-cached local FinBERT for richer estimates, never as factual ground truth.
- An after-close announcement aligns to the next trading session; before-open aligns to that day if it trades. Unknown timing suppresses the calculated event-session percentage altogether.
- Stock-context values are descriptive historical prices, not recommendations or evidence of causation.

## Network/security boundary

URL extraction is intended for **local development on a trusted machine**. The best-effort checks reject private, reserved, loopback, multicast and non-global IPv4/IPv6 resolutions; check each redirect; enforce port restrictions; and limit downloads. They do not pin the validated DNS address to the TCP connection and therefore cannot eliminate DNS-rebinding attacks. Before exposing to unknown users: move fetching into an isolated egress-restricted worker or use IP-pinned clients; add auth, rate limits, and resource quotas. Pages are treated as untrusted data and never executed.

## Extensibility roadmap

- Evaluate more flexible metric grammar against manually labeled transcripts, including negatives, ranges, units and year-over-year vs quarter-over-quarter comparisons.
- Add benchmarked TextRank/YAKE/spaCy models where they demonstrably outperform the simple extractive/keyword baseline; report measured precision and attribution accuracy.
- Validate theme groupings and potential conflicts against manually reviewed claim pairs before automating contradiction flags.
- Add immutable source fingerprints, cache retention settings, richer date handling, accessible chart alternatives and downloadable reports.
- Create high-quality demo sets for multiple real companies with explicit citations and permissions.
