import { useEffect, useState } from 'react'
import { ArrowUpRight, Check, ChevronDown, LibraryBig, LoaderCircle, Trash2, X } from 'lucide-react'
import type { Analysis } from './types'

type Saved = {
  analysis_id: string; company_name: string; ticker: string; fiscal_period: string;
  announcement_date: string | null; analyzed_at: string; metric_count: number; news_count: number
}
type Comparison = {
  left: { analysis_id: string; ticker: string; company_name: string; fiscal_period: string }
  right: { analysis_id: string; ticker: string; company_name: string; fiscal_period: string }
  metrics: { name: string; unit: string; currency: string | null; metric_variant: string | null;
    left_value: number; right_value: number; left_evidence: {text:string}; right_evidence: {text:string} }[]
  notes: string[]
}

export default function ReportLibrary({ onClose, onOpen }: { onClose: () => void; onOpen: (data: Analysis) => void }) {
  const [items, setItems] = useState<Saved[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [comparison, setComparison] = useState<Comparison | null>(null)
  const [filter, setFilter] = useState('')
  useEffect(() => {
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', escape)
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', escape); document.body.style.overflow = '' }
  }, [onClose])
  useEffect(() => {
    fetch('/api/v1/analyses').then(async response => {
      if (!response.ok) throw Error('Saved reports unavailable')
      setItems(await response.json())
    }).catch(err => setError(err instanceof Error ? err.message : 'Could not load saved reports'))
  }, [])

  async function openReport(id: string) {
    setBusy(true); setError('')
    try {
      const response = await fetch(`/api/v1/analyses/${id}`)
      if (!response.ok) throw Error('Report not found on this backend')
      const data: Analysis = await response.json()
      onOpen(data); onClose()
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not open report') }
    finally { setBusy(false) }
  }
  function toggle(id: string) { setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s.slice(-1), id]); setComparison(null) }
  async function compare() {
    if (selected.length !== 2) return
    setBusy(true); setError('')
    try {
      const query = new URLSearchParams({left: selected[0], right: selected[1]})
      const response = await fetch(`/api/v1/compare?${query}`)
      if (!response.ok) throw Error('Could not compare these two saved reports')
      setComparison(await response.json())
    } catch (err) { setError(err instanceof Error ? err.message : 'Comparison failed') }
    finally { setBusy(false) }
  }
  async function remove(id: string) {
    if (!window.confirm('Delete this saved analysis from your local library?')) return
    setBusy(true)
    try {
      const response = await fetch(`/api/v1/analyses/${id}`, { method: 'DELETE' })
      if (!response.ok) throw Error('Could not delete this report')
      setItems(s => s.filter(x => x.analysis_id !== id))
      setSelected(s => s.filter(x => x !== id)); setComparison(null)
    } catch (err) { setError(err instanceof Error ? err.message : 'Deletion failed') }
    finally { setBusy(false) }
  }
  const shown = items.filter(x => `${x.company_name} ${x.ticker} ${x.fiscal_period}`.toLowerCase().includes(filter.toLowerCase()))
  const fmt = (v: number, unit: string, cur: string | null) =>
    `${cur === 'USD' ? '$' : cur === 'INR' ? '₹' : cur ? `${cur} ` : ''}${Intl.NumberFormat('en-US', {maximumFractionDigits: 2, notation: Math.abs(v) > 99999 ? 'compact' : 'standard'}).format(v)}${unit === 'percent' ? '%' : ''}`
  return <div className="library-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}>
    <section className="library-panel" role="dialog" aria-modal="true" aria-label="Saved analysis library">
      <div className="library-heading"><div><span className="eyebrow"><LibraryBig size={14}/> YOUR RESEARCH ARCHIVE</span><h2>Saved <em>analyses.</em></h2><p>Reopen any report or compare metrics across quarters and companies.</p></div><button className="icon-button" aria-label="Close library" onClick={onClose}><X size={22}/></button></div>
      <div className="library-controls"><input aria-label="Filter saved analyses" placeholder="Find a ticker, company, or quarter…" value={filter} onChange={e => setFilter(e.target.value)}/><button type="button" onClick={() => void compare()} disabled={selected.length !== 2 || busy}>{busy ? <LoaderCircle className="spin" size={15}/> : <Check size={15}/>} Compare selected ({selected.length}/2)</button></div>
      {error && <p className="research-error" role="alert">{error}</p>}
      <div className="library-list">{shown.length ? shown.map(item => <article className="library-report" key={item.analysis_id}>
        <button type="button" onClick={() => toggle(item.analysis_id)} aria-pressed={selected.includes(item.analysis_id)} className={`library-select ${selected.includes(item.analysis_id) ? 'active' : ''}`} aria-label={`Select ${item.company_name} ${item.fiscal_period} for comparison`}>{selected.includes(item.analysis_id) ? <Check size={15}/> : '+'}</button>
        <div className="library-report-info"><strong>{item.company_name} <span>{item.ticker}</span></strong><p>{item.fiscal_period} · {item.announcement_date || 'Date not specified'}</p><small>{item.metric_count} metrics · {item.news_count} news sources · Saved {new Date(item.analyzed_at).toLocaleDateString()}</small></div>
        <button type="button" className="library-open" onClick={() => void openReport(item.analysis_id)} disabled={busy}>Open <ArrowUpRight size={15}/></button>
        <button type="button" className="library-delete" onClick={() => void remove(item.analysis_id)} title="Delete report" disabled={busy}><Trash2 size={16}/></button>
      </article>) : <p className="library-empty">No saved reports found. Generate a live analysis to begin building your library.</p>}</div>
      {comparison && <section className="library-comparison"><h3>{comparison.left.ticker} {comparison.left.fiscal_period} <span>vs.</span> {comparison.right.ticker} {comparison.right.fiscal_period}</h3><p className="library-subnote">Matched metrics · exact names, units, currencies and reported/adjusted basis</p>
        {comparison.metrics.map((metric,i)=>{const max = Math.max(Math.abs(metric.left_value), Math.abs(metric.right_value), 1);return <div className="library-metric" key={i}>
          <h4>{metric.name} <small>{metric.metric_variant || 'basis unspecified'}</small></h4>
          <div className="library-barline"><span>{fmt(metric.left_value,metric.unit,metric.currency)}</span><div className="library-bar-bg"><div className="library-bar indigo" style={{width:`${100*Math.abs(metric.left_value)/max}%`}}/></div></div>
          <div className="library-barline"><span>{fmt(metric.right_value,metric.unit,metric.currency)}</span><div className="library-bar-bg"><div className="library-bar mint" style={{width:`${100*Math.abs(metric.right_value)/max}%`}}/></div></div>
          <details className="library-evidence"><summary>Compare supporting passages <ChevronDown size={13}/></summary><p><b>{comparison.left.fiscal_period}:</b> {metric.left_evidence.text}</p><p><b>{comparison.right.fiscal_period}:</b> {metric.right_evidence.text}</p></details>
        </div>})}
        {comparison.notes.map((note,i)=><p className="library-subnote" key={i}>{note}</p>)}
      </section>}
    </section>
  </div>
}
