# FinPulse visual direction — v2

The UI uses an intentional three-color system, not random accents:

| Token | Color | Purpose |
|---|---|---|
| `--onyx` | `#01010D` | Canvas and calm negative space |
| `--indigo` | `#6331FB` | Chart signal, immersive art, featured metric, market depth |
| `--mint` | `#88F9C0` | A single high-attention accent for action buttons, event markers, source affordances, and select typography |

Secondary surfaces use dark tinted shades of Onyx with restrained indigo borders and glows. White is reserved for primary content, muted lilac for supporting labels. Semantic adverse values use accessible text and a quiet pink; they are never indicated by color alone.

## Typography

- DM Sans — straightforward, compact UI labels and numeric readouts.
- Instrument Serif — editorial italics used selectively in large headings.
- Both load via Google Fonts with local fallbacks, so the layout remains functional offline.

## Composition

1. Uncluttered top navigation: Market lens, Earnings, Perspectives. No decorative sidebar.
2. Editorial introduction with an original pulse sculpture, subtle orbit animation, and a clear analysis action.
3. Clearly labeled company report context; fictional demo is never presented as live data.
4. Market hero: price and volume views, data tooltips, event marker, honest window comparison, chart draw animation, explicit missing-data state.
5. Primary extracted metric given an indigo feature treatment; supporting figures stay on dark cards with their evidence attached.
6. Company claims and media emphasis side-by-side on wide screens, stacked on narrow screens; collapsible sources and thematic comparison.
7. New analysis opens in a scrollable slide-over without taking permanent space from the report.

## Interaction and motion

- Motion uses transforms and opacity for section reveals, hover, drawer entry, chart transitions, and background sculpture.
- CSS `prefers-reduced-motion` disables animations and transitions.
- Focus indicators remain visible; the analysis drawer closes via Escape and has a labeled dialog role.
- The chart's earnings annotation is keyed to the actual supplied date (or to explicitly illustrative demo data). A price-window comparison is not labeled an earnings-caused return.

## Developer rules

- Don't introduce loud labels about implementation choices into the marketing experience (e.g., API provider or backend stack).
- Never invent financial values, dates, correlations, evidence, or positive/negative classifications for live results.
- If there are no stock points, show an intentional empty state, not demo market points.
- Keep chart payloads derived from the API schema; maintain source links and source attribution.
- Keep `frontend/src/styles.css` as the single source for theme tokens.
