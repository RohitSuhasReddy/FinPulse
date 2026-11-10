import { ArrowUpRight, Newspaper } from 'lucide-react'
import type { SourceAnalysis } from './types'
import './headlines.css'

// News discovery does not imply we can read a publisher's article body.
// The headline itself is a useful, attributable link even when the body is blocked.
export default function Headlines({ sources }: { sources: SourceAnalysis[] }) {
  const items = sources.filter(s => Boolean(s.title?.trim()) && Boolean(s.url?.match(/^https:\/\//i)))
  return <div className="headline-board" aria-label="Discovered news headlines">
    <div className="headline-board-top">
      <div><span className="headline-kicker"><Newspaper size={15} /> DISCOVERED COVERAGE</span>
        <h3>Top <em>headlines.</em></h3></div>
      <span className="headline-count">{items.length} LINK{items.length === 1 ? '' : 'S'} FOUND</span>
    </div>
    {items.length ? <div className="headline-feed">{items.slice(0, 8).map((s, i) => {
      const aggregated = /^https:\/\/news\.google\.com\//i.test(s.url ?? '')
      return <a key={s.source_id + i} className="headline-story" href={s.url!} target="_blank" rel="noopener noreferrer">
        <span className="headline-rank">{String(i + 1).padStart(2, '0')}</span>
        <span className="headline-copy"><small>{s.outlet || 'News source'} <span aria-hidden="true">·</span> {s.extraction_status === 'ok' ? 'FULL ARTICLE AVAILABLE' : 'HEADLINE & LINK'}</small>
          <strong>{s.title}</strong></span>
        <span className="headline-action">{aggregated ? 'OPEN NEWS LISTING' : 'READ AT SOURCE'} <ArrowUpRight size={16} /></span>
      </a>
    })}</div> : <p className="headline-empty">No relevant public headlines were returned by the news feeds for this reporting window. Try another period or check connectivity.</p>}
    <p className="headline-disclosure">Headlines link to external publishers or, where only an aggregated link is available, Google News. A headline is not a verified article summary or financial statement.</p>
  </div>
}
