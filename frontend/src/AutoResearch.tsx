import { useState, type FormEvent } from 'react'
import { ArrowRight, ArrowUpRight, Database, Globe2, LoaderCircle, Radio, Search, X } from 'lucide-react'
import type { Analysis, SocialPost } from './types'
import './auto-research.css'

interface Props {
  onClose: () => void
  onComplete: (analysis: Analysis) => void
  onManual: () => void
}

export default function AutoResearch({ onClose, onComplete, onManual }: Props) {
  const [ticker, setTicker] = useState('')
  const [period, setPeriod] = useState('')
  const [announcementDate, setAnnouncementDate] = useState('')
  const [social, setSocial] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!/^[a-zA-Z0-9.-]{1,12}$/.test(ticker.trim())) {
      setError('Enter a valid stock ticker, such as GOOGL or MSFT.')
      return
    }
    setError('')
    setBusy(true)
    try {
      const response = await fetch('/api/v1/research/auto', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: ticker.trim().toUpperCase(),
          ...(period ? { period_end: period } : {}),
          ...(announcementDate ? { announcement_date: announcementDate } : {}),
          include_social: social,
          max_articles: 5,
        }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Research could not be completed.')
      onComplete(payload as Analysis)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reach the research server. Check your backend terminal.')
    } finally {
      setBusy(false)
    }
  }

  return <div className="auto-overlay" onMouseDown={e => { if (e.target === e.currentTarget && !busy) onClose() }}>
    <section className="auto-panel" role="dialog" aria-modal="true" aria-label="Automatic company research">
      <div className="auto-top"><span className="auto-top-label"><Radio size={16} /> AUTOMATED RESEARCH</span><button className="auto-close" type="button" aria-label="Close automatic research" disabled={busy} onClick={onClose}><X size={22}/></button></div>
      <div className="auto-heading"><p>ONE COMPANY. ALL THE CONTEXT.</p><h2>Research, <em>on demand.</em></h2><span>Just enter a stock ticker. FinPulse will collect the latest available official filing, relevant news coverage and public discussion, then save the evidence-linked results.</span></div>
      <div className="auto-steps" aria-label="Automatic research sources">
        <div><Database size={19} /><strong>SEC filings</strong><small>10-Q / 10-K</small></div>
        <div><Globe2 size={19} /><strong>Web coverage</strong><small>GDELT + RSS</small></div>
        <div><Radio size={19} /><strong>Public posts</strong><small>Bluesky · X if enabled</small></div>
      </div>
      <form onSubmit={e => void submit(e)} className="auto-form">
        <label htmlFor="auto-ticker">STOCK SYMBOL</label>
        <div className="auto-symbol-field"><Search size={20}/><input id="auto-ticker" value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())} maxLength={12} required autoFocus placeholder="e.g. GOOGL" autoComplete="off" /></div>
        <div className="auto-more">
          <div><label htmlFor="auto-period">REPORT PERIOD END <small>optional</small></label><input id="auto-period" type="date" value={period} onChange={e => setPeriod(e.target.value)} /><small>Leave blank for the latest SEC filing</small></div>
          <div><label htmlFor="auto-date">EARNINGS ANNOUNCEMENT <small>optional</small></label><input id="auto-date" type="date" value={announcementDate} onChange={e => setAnnouncementDate(e.target.value)} /><small>Add only if you know the actual date</small></div>
        </div>
        <label className="auto-social-toggle"><input type="checkbox" checked={social} onChange={e => setSocial(e.target.checked)}/><span>Include public discussion <small>Public posts are opinions, not verified facts</small></span></label>
        {error && <p className="auto-error" role="alert">{error}</p>}
        <button type="submit" className="auto-launch" disabled={busy}>{busy ? <><LoaderCircle className="auto-spinning" size={19}/> Gathering sources and analyzing…</> : <>Start automatic research <ArrowRight size={20}/></>}</button>
      </form>
      <button type="button" className="auto-manual" disabled={busy} onClick={onManual}>Have your own PDF or article text? Use manual analysis <ArrowUpRight size={15}/></button>
      <p className="auto-footnote">First-time SEC setup requires a contact User-Agent. Blocked articles remain headline-only; no source text or claims will be invented. You can always use the manual PDF workflow.</p>
    </section>
  </div>
}

export function SocialLens({ posts }: { posts: SocialPost[] }) {
  if (!posts?.length) return null
  return <section className="social-lens" id="social-voice">
    <div className="social-head"><span className="social-eyebrow"><Radio size={15}/> PUBLIC DISCUSSION</span><h2>Beyond the <em>headlines.</em></h2><p>Selected public posts mentioning this company's earnings. Individual opinions, not a representative sample or a source of reported financial figures.</p></div>
    <div className="social-grid">{posts.slice(0, 8).map((post, i) => <a href={post.url} target="_blank" rel="noreferrer noopener" className="social-post" key={`${post.platform}-${post.url}-${i}`}>
      <div className="social-post-top"><span className="social-service">{post.platform}</span><ArrowUpRight size={17}/></div>
      <p>{post.text}</p>
      <div className="social-post-foot"><span>{post.author}</span><time dateTime={post.created_at}>{post.created_at?.slice(0, 10) || 'Undated'}</time></div>
    </a>)}</div>
  </section>
}
