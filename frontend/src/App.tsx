import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import {
  ArrowDownRight, ArrowUpRight, ChevronDown, ExternalLink,
  FileUp, Info, LibraryBig, LoaderCircle, Plus, RotateCcw, X,
} from 'lucide-react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { Analysis, AnalysisInput, Evidence, NewsInput, StockContext } from './types'
import demoResponse from './data/demo-response.json'
import { PREVIEW_STOCK } from './data/preview-stock'
import ResearchTools from './ResearchTools'
import ReportLibrary from './ReportLibrary'
import AutoResearch, { SocialLens } from './AutoResearch'
import './research.css'

type Mode = 'demo' | 'live'
type ChartTab = 'price' | 'volume'
type ChartPoint = { date: string; close: number; volume: number }

const blank: AnalysisInput = {
  company_name: '', ticker: '', fiscal_period: '', announcement_date: null,
  market_timing: 'unknown', earnings_text: '', news_sources: [],
}
const compact = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1, notation: 'compact' })
const signed = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(2)}%`
const labelDate = (value: string | null) => value
  ? new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  : 'Date not provided'
const currencySymbol = (currency: string | null) => currency === 'USD' ? '$' : currency === 'INR' ? '₹' : currency ? `${currency} ` : ''
const safeLink = (url: string | null) => url && /^https?:\/\//i.test(url) ? url : null

function metricValue(value: number | null, unit: string, currency: string | null, raw: string) {
  if (value === null) return raw
  if (unit === 'percent') return `${Number(value.toFixed(2))}%`
  if (unit === 'per_share') return `${currencySymbol(currency)}${value.toFixed(2)}`
  return `${currencySymbol(currency)}${compact.format(value)}`
}

function Brand({ onClick }: { onClick?: () => void }) {
  return <a className="brand" href="#top" onClick={onClick} aria-label="FinPulse — top of page">
    <span className="brand-symbol" aria-hidden="true">
      <svg viewBox="0 0 44 44" fill="none" role="presentation">
        <path d="M5 23h8l5-12 7 24 6-12h8" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="37" cy="23" r="3" fill="currentColor" />
      </svg>
    </span>
    <span className="brand-word">fin<span>pulse</span><b>.</b></span>
  </a>
}

function EvidenceLink({ evidence, children = 'See source' }: { evidence: Evidence; children?: ReactNode }) {
  return <details className="evidence-link">
    <summary>{children}<ChevronDown size={14} aria-hidden="true" /></summary>
    <div className="evidence-detail">
      <p>“{evidence.text}”</p>
      <span>{evidence.source_id} · character range {evidence.start_offset}–{evidence.end_offset}</span>
    </div>
  </details>
}

function MiniLabel({ number, children }: { number: string; children: ReactNode }) {
  return <div className="section-kicker"><span>{number}</span><i aria-hidden="true" />{children}</div>
}

function Reveal({ children, className = '', id }: { children: ReactNode; className?: string; id?: string }) {
  return <div id={id} className={`reveal ${className}`}>{children}</div>
}

function MarketChart({ stock, mode, ticker }: { stock: StockContext | null; mode: Mode; ticker: string }) {
  const [tab, setTab] = useState<ChartTab>('price')
  const points: ChartPoint[] = useMemo(() => mode === 'demo'
    ? PREVIEW_STOCK.map(p => ({ date: p.date, close: p.price, volume: p.volume * 1_000_000 }))
    : (stock?.points ?? []), [mode, stock])
  const first = points[0]
  const last = points[points.length - 1]
  const windowMove = first && last && first.close !== 0 ? (last.close / first.close - 1) * 100 : null
  const positive = windowMove !== null && windowMove >= 0
  const marker = mode === 'demo' ? 'Oct 16' : stock?.first_session_on_or_after_date ?? null
  const symbol = mode === 'demo' ? '$' : currencySymbol(stock?.currency ?? null)

  return <section className="market-section" id="market" aria-label="Market context">
    <div className="market-topline"><MiniLabel number="01">MARKET LENS</MiniLabel><span className="market-context">{mode === 'demo' ? 'ILLUSTRATIVE PRICE SERIES' : `${ticker} · HISTORICAL DATA`}</span></div>
    <div className="market-head">
      <div><h2>The market <em>in motion.</em></h2><p>A closer look at the trading window surrounding earnings.</p></div>
      <div className="chart-tabs" role="group" aria-label="Chart view">
        <button className={tab === 'price' ? 'selected' : ''} aria-pressed={tab === 'price'} onClick={() => setTab('price')}>Price</button>
        <button className={tab === 'volume' ? 'selected' : ''} aria-pressed={tab === 'volume'} onClick={() => setTab('volume')}>Volume</button>
      </div>
    </div>
    <div className="market-stage">
      <div className="market-stage-glow" aria-hidden="true" />
      {points.length > 0 ? <>
        <div className="market-stat-row">
          <div className="last-close"><span>{tab === 'price' ? 'LAST PLOTTED CLOSE' : 'LAST PLOTTED VOLUME'}</span>
            <strong key={tab}>{tab === 'price' ? `${symbol}${last.close.toFixed(2)}` : compact.format(last.volume)}</strong>
            <small>{mode === 'demo' ? 'Fictional example · not live' : `${labelDate(last.date)} · not real-time`}</small>
          </div>
          <div className="market-move"><span>WINDOW CHANGE</span><strong className={positive ? 'up' : 'down'}>
            {windowMove !== null ? <>{positive ? <ArrowUpRight size={20} /> : <ArrowDownRight size={20} />}{signed(windowMove)}</> : '—'}
          </strong><small>First to last plotted close</small></div>
        </div>
        <div className="chart-composition" key={`${mode}-${tab}-${ticker}`}>
          <div className="main-chart" role="img" aria-label={`${ticker} ${tab === 'price' ? 'daily closing price' : 'trading volume'} chart with earnings event marker`}>
            <ResponsiveContainer width="100%" height="100%">
              {tab === 'price' ? <AreaChart data={points} margin={{ top: 32, right: 10, left: -12, bottom: 10 }}>
                <defs><linearGradient id="priceUnder" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#6331FB" stopOpacity="0.43" /><stop offset="67%" stopColor="#6331FB" stopOpacity="0.08" /><stop offset="100%" stopColor="#6331FB" stopOpacity="0" /></linearGradient></defs>
                <CartesianGrid stroke="#282342" strokeDasharray="3 8" vertical={false} />
                <XAxis dataKey="date" axisLine={false} tickLine={false} minTickGap={24} tick={{ fill: '#8d8ba6', fontSize: 11 }} tickFormatter={v => String(v).includes('-') ? String(v).slice(5) : v} />
                <YAxis domain={['auto', 'auto']} axisLine={false} tickLine={false} width={54} tick={{ fill: '#8d8ba6', fontSize: 11 }} tickFormatter={v => Number(v).toFixed(0)} />
                <Tooltip cursor={{ stroke: '#88F9C0', strokeDasharray: '3 5', strokeWidth: 1 }} contentStyle={{ background: '#16112C', border: '1px solid #55458d', borderRadius: 12, color: '#fff', boxShadow: '0 20px 40px #0008' }} labelStyle={{ color: '#BDB6DF', marginBottom: 8 }} formatter={value => [`${symbol}${Number(value).toFixed(2)}`, 'Closing price']} />
                <Area type="monotone" name="Close" dataKey="close" stroke="#9677FF" strokeWidth={3.5} fill="url(#priceUnder)" dot={false} activeDot={{ r: 6, fill: '#88F9C0', stroke: '#01010D', strokeWidth: 3 }} animationDuration={1250} animationEasing="ease-out" />
                {marker && <ReferenceLine x={marker} stroke="#88F9C0" strokeDasharray="4 6" strokeWidth={1.6} label={{ value: 'EARNINGS', position: 'insideTopRight', fill: '#88F9C0', fontSize: 10, fontWeight: 700 }} />}
              </AreaChart> : <BarChart data={points} margin={{ top: 32, right: 10, left: -12, bottom: 10 }}>
                <CartesianGrid stroke="#282342" strokeDasharray="3 8" vertical={false} />
                <XAxis dataKey="date" axisLine={false} tickLine={false} minTickGap={24} tick={{ fill: '#8d8ba6', fontSize: 11 }} tickFormatter={v => String(v).includes('-') ? String(v).slice(5) : v} />
                <YAxis axisLine={false} tickLine={false} width={54} tick={{ fill: '#8d8ba6', fontSize: 11 }} tickFormatter={v => compact.format(Number(v))} />
                <Tooltip cursor={{ fill: '#6331FB24' }} contentStyle={{ background: '#16112C', border: '1px solid #55458d', borderRadius: 12, color: '#fff' }} labelStyle={{ color: '#BDB6DF', marginBottom: 8 }} formatter={value => [Number(value).toLocaleString('en-US'), 'Volume · shares']} />
                <Bar dataKey="volume" fill="#8461FF" radius={[4, 4, 0, 0]} animationDuration={900} />
                {marker && <ReferenceLine x={marker} stroke="#88F9C0" strokeDasharray="4 6" strokeWidth={1.6} label={{ value: 'EARNINGS', position: 'insideTopRight', fill: '#88F9C0', fontSize: 10, fontWeight: 700 }} />}
              </BarChart>}
            </ResponsiveContainer>
          </div>
          <div className="chart-below"><div className="chart-key"><span className="key-line" />{tab === 'price' ? 'DAILY CLOSE' : 'DAILY VOLUME'}</div><div className="chart-key"><span className="key-event" />EARNINGS DATE</div><div className="chart-key chart-hint">HOVER TO EXPLORE <span aria-hidden="true">↗</span></div></div>
        </div>
      </> : <div className="chart-unavailable"><div className="ghost-wave" aria-hidden="true"><svg viewBox="0 0 360 120"><path d="M0 85L45 80L88 95L138 46L190 66L225 31L270 48L310 20L360 45" /></svg></div><strong>Market chart awaiting data</strong><span>Add an earnings date to retrieve historical price and volume for this ticker.</span></div>}
      <div className="market-footnote"><span>{mode === 'demo' ? 'Fictional market series. For layout preview only.' : stock?.warning ?? 'Closing prices and volumes are historical; movement does not establish cause.'}</span><span>{points.length ? `${points.length} SESSIONS` : 'NO SESSIONS'}</span></div>
    </div>
  </section>
}

function Metrics({ data }: { data: Analysis }) {
  return <section className="metrics-section" aria-label="Extracted financial metrics">
    <div className="metrics-heading"><MiniLabel number="02">THE NUMBERS</MiniLabel><span>Extracted from company text</span></div>
    <div className="metric-grid">
      {data.metrics.length ? data.metrics.slice(0, 4).map((m, i) => <article key={`${m.name}-${i}`} className={`metric-tile metric-${i}`}>
        <div className="metric-top"><span>{String(i + 1).padStart(2, '0')}</span><span>{m.extraction_status === 'needs_review' ? 'NEEDS REVIEW' : 'SOURCE LINKED'}</span></div>
        <div className="metric-main"><span className="metric-value">{metricValue(m.normalized_value, m.unit, m.currency, m.raw_value)}</span><h3>{m.name}</h3></div>
        <div className="metric-foot"><span>{m.reporting_period}{m.metric_variant === 'adjusted' ? ' · Adjusted' : ''}</span><EvidenceLink evidence={m.evidence}>Source <ArrowUpRight size={13} /></EvidenceLink></div>
      </article>) : <div className="metrics-missing">No confident financial metrics extracted. Try a more detailed earnings release.</div>}
    </div>
  </section>
}

function Earnings({ data }: { data: Analysis }) {
  return <section className="earnings-section" id="earnings">
    <MiniLabel number="03">THE COMPANY VIEW</MiniLabel>
    <h2>What they <em>said.</em></h2>
    <p className="section-subtitle">Key passages from the earnings material, kept close to their source.</p>
    {data.summary.length ? <div className="earnings-quotes">{data.summary.slice(0, 4).map((item, i) => <article className="quote-row" key={`${item.evidence.start_offset}-${i}`}><div className="quote-index">0{i + 1}</div><div className="quote-copy"><p>{item.text}</p><EvidenceLink evidence={item.evidence}>Original passage</EvidenceLink></div><span className="quote-glyph" aria-hidden="true">↗</span></article>)}</div> : <div className="detail-empty">No key passages found in the provided text.</div>}
    {data.earnings_themes.length > 0 && <div className="theme-chips"><span>RECURRING THEMES</span><div>{data.earnings_themes.slice(0, 7).map(t => <span key={t}>{t}</span>)}</div></div>}
  </section>
}

function Perspective({ data }: { data: Analysis }) {
  const shared = data.comparison.filter(t => t.relationship === 'shared')
  const other = data.comparison.filter(t => t.relationship !== 'shared')
  return <section className="perspective-section" id="perspectives">
    <MiniLabel number="04">THE OUTSIDE VIEW</MiniLabel>
    <h2>Beyond the <em>headline.</em></h2>
    <p className="section-subtitle">A look at where coverage overlaps—and where the attention shifts.</p>
    <div className="media-rows">
      {data.sources.length ? data.sources.map((source, i) => <article className="media-card" key={source.source_id}>
        <div className="media-card-head"><span className="media-index">{String(i + 1).padStart(2, '0')}</span><span className="media-outlet">{source.outlet}</span>{safeLink(source.url) && <a href={safeLink(source.url)!} target="_blank" rel="noopener noreferrer" aria-label={`Open ${source.outlet} article`}><ExternalLink size={16} /></a>}</div>
        <h3>{source.title}</h3>
        <div className="media-bottom"><span className={`sentiment sentiment-${source.sentiment_label || 'unknown'}`}>{source.sentiment_label ? `${source.sentiment_label} tone` : 'Tone unavailable'}</span><span>ESTIMATED LANGUAGE TONE</span></div>
        {source.extraction_status !== 'ok' ? <p className="media-warning">{source.warning ?? 'Article unavailable.'}</p> : source.summary[0] && <div className="media-excerpt"><p>{source.summary[0].text}</p><EvidenceLink evidence={source.summary[0].evidence}>Source passage</EvidenceLink></div>}
      </article>) : <div className="detail-empty">No articles added yet. Create an analysis with news sources to compare perspectives.</div>}
    </div>
    <div className="perspective-compare" id="comparison"><div className="comparison-heading"><span>THE OVERLAP</span><strong>{shared.length} shared {shared.length === 1 ? 'theme' : 'themes'}</strong></div>
      {shared.length ? <div className="overlap-list">{shared.slice(0, 6).map(t => <details className="overlap-item" key={t.theme}><summary><span className="mint-bullet" />{t.theme}<ChevronDown size={15}/></summary><div className="overlap-evidence">{t.earnings_evidence && <EvidenceLink evidence={t.earnings_evidence}>Company evidence</EvidenceLink>}{t.news_evidence.slice(0, 3).map((ev, i) => <EvidenceLink key={`${ev.source_id}-${i}`} evidence={ev.evidence}>{ev.outlet} evidence</EvidenceLink>)}</div></details>)}</div> : <p className="overlap-empty">No shared themes identified in these sources.</p>}
      {other.length > 0 && <div className="different-themes"><span>OTHER EMPHASES</span><div>{other.slice(0, 8).map(t => <span key={`${t.relationship}-${t.theme}`}>{t.theme} <small>{t.relationship === 'earnings_only' ? 'COMPANY' : 'MEDIA'}</small></span>)}</div></div>}
    </div>
  </section>
}

function AnalysisDrawer({ initial, onClose, onSubmit, loading, uploading, error, onUpload }: {
  initial: AnalysisInput; onClose: () => void; onSubmit: (input: AnalysisInput) => Promise<void>;
  loading: boolean; uploading: boolean; error: string; onUpload: (file: File) => Promise<string | null>;
}) {
  const [form, setForm] = useState<AnalysisInput>(() => ({ ...initial, news_sources: initial.news_sources.map(n => ({ ...n })) }))
  const [localError, setLocalError] = useState('')
  const pdfRef = useRef<HTMLInputElement>(null)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const update = <K extends keyof AnalysisInput>(key: K, value: AnalysisInput[K]) => setForm(prev => ({ ...prev, [key]: value }))
  const updateNews = (index: number, key: keyof NewsInput, value: string) => setForm(prev => ({ ...prev, news_sources: prev.news_sources.map((n, i) => i === index ? { ...n, [key]: value } : n) }))

  useEffect(() => {
    headingRef.current?.focus()
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape' && !loading && !uploading) onClose() }
    document.addEventListener('keydown', escape)
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', escape); document.body.style.overflow = '' }
  }, [onClose, loading, uploading])

  async function loadPdf(file?: File) {
    if (!file) return
    setLocalError('')
    const text = await onUpload(file)
    if (text) update('earnings_text', text)
    else setLocalError('Could not extract text from this PDF. You can paste the earnings text instead.')
    if (pdfRef.current) pdfRef.current.value = ''
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setLocalError('')
    const news = form.news_sources.filter(s => !!s.url?.trim() || !!s.text?.trim())
    if (news.some(s => !s.url?.trim() && (s.text?.trim().length ?? 0) < 50)) { setLocalError('Pasted news articles need at least 50 characters, or provide a URL.'); return }
    void onSubmit({ ...form, news_sources: news })
  }

  return <div className="drawer-backdrop" onMouseDown={event => { if (event.target === event.currentTarget && !loading && !uploading) onClose() }}>
    <aside className="analysis-drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
      <div className="drawer-top"><Brand onClick={onClose} /><button type="button" className="icon-button" aria-label="Close analysis panel" onClick={onClose} disabled={loading || uploading}><X size={21}/></button></div>
      <div className="drawer-intro"><span className="eyebrow">YOUR NEXT DEEP DIVE</span><h2 id="drawer-title" tabIndex={-1} ref={headingRef}>Start with <em>a story.</em></h2><p>Add an earnings release, then optionally bring in up to three news perspectives.</p></div>
      <form className="analysis-form" onSubmit={submit}>
        <div className="form-group"><label htmlFor="company">Company name</label><input id="company" required minLength={2} maxLength={120} placeholder="e.g. Microsoft" value={form.company_name} onChange={e => update('company_name', e.target.value)}/></div>
        <div className="form-pair"><div className="form-group"><label htmlFor="ticker">Ticker</label><input id="ticker" required maxLength={12} placeholder="MSFT" value={form.ticker} onChange={e => update('ticker', e.target.value.toUpperCase())}/></div><div className="form-group"><label htmlFor="quarter">Fiscal period</label><input id="quarter" required minLength={3} maxLength={40} placeholder="FY2026 Q2" value={form.fiscal_period} onChange={e => update('fiscal_period', e.target.value)}/></div></div>
        <div className="form-pair"><div className="form-group"><label htmlFor="event-date">Announcement date <small>optional</small></label><input id="event-date" type="date" value={form.announcement_date ?? ''} onChange={e => update('announcement_date', e.target.value || null)}/></div><div className="form-group"><label htmlFor="timing">Announcement timing</label><select id="timing" value={form.market_timing ?? 'unknown'} onChange={e => update('market_timing', e.target.value as AnalysisInput['market_timing'])}><option value="unknown">Unknown</option><option value="before_open">Before market open</option><option value="after_close">After market close</option></select></div></div>
        <ResearchTools ticker={form.ticker} company={form.company_name} date={form.announcement_date} onFiling={filing => setForm(prev => ({...prev, ticker: filing.ticker, company_name: filing.company_name, fiscal_period: filing.fiscal_period, earnings_text: filing.text }))} onNews={sources => setForm(prev => ({...prev, news_sources: sources }))}/>
        <div className="form-group"><div className="field-title"><label htmlFor="earnings-text">Earnings text</label><button type="button" className="mini-action" disabled={uploading} onClick={() => pdfRef.current?.click()}><FileUp size={15}/>{uploading ? 'Importing…' : 'Import PDF'}</button><input hidden ref={pdfRef} type="file" accept=".pdf,application/pdf" onChange={e => void loadPdf(e.target.files?.[0])}/></div><textarea id="earnings-text" required minLength={80} rows={6} placeholder="Paste an earnings press release or transcript (at least 80 characters)…" value={form.earnings_text} onChange={e => update('earnings_text', e.target.value)}/></div>
        <div className="field-title news-field-title"><label>News coverage <small>optional</small></label><button type="button" className="mini-action" disabled={form.news_sources.length >= 3} onClick={() => update('news_sources', [...form.news_sources, { url: '', title: '', outlet: '', text: '' }])}><Plus size={15}/>Add article</button></div>
        {form.news_sources.map((source, i) => <div className="news-input-group" key={i}><div className="news-input-head"><span>ARTICLE {String(i + 1).padStart(2, '0')}</span><button type="button" aria-label={`Remove article ${i + 1}`} onClick={() => update('news_sources', form.news_sources.filter((_, j) => j !== i))}><X size={16}/></button></div><div className="form-group"><label htmlFor={`article-url-${i}`}>Article URL</label><input id={`article-url-${i}`} type="url" value={source.url ?? ''} placeholder="https://…" onChange={e => updateNews(i, 'url', e.target.value)}/></div><div className="form-pair"><div className="form-group"><label htmlFor={`article-outlet-${i}`}>Outlet <small>optional</small></label><input id={`article-outlet-${i}`} value={source.outlet ?? ''} maxLength={100} onChange={e => updateNews(i, 'outlet', e.target.value)}/></div><div className="form-group"><label htmlFor={`article-title-${i}`}>Title <small>optional</small></label><input id={`article-title-${i}`} value={source.title ?? ''} maxLength={240} onChange={e => updateNews(i, 'title', e.target.value)}/></div></div><div className="form-group"><label htmlFor={`article-text-${i}`}>Pasted article text <small>URL fallback</small></label><textarea id={`article-text-${i}`} rows={3} value={source.text ?? ''} placeholder="Paste article text if the link cannot be read…" onChange={e => updateNews(i, 'text', e.target.value)}/></div></div>)}
        {(localError || error) && <div className="form-error" role="alert"><Info size={17}/>{localError || error}</div>}
        <button className="submit-analysis" type="submit" disabled={loading || uploading}>{loading ? <><LoaderCircle size={17} className="spin"/>Analyzing your sources…</> : <>Generate analysis<ArrowUpRight size={19}/></>}</button>
      </form>
      <p className="drawer-disclaimer">Results are exploratory. Always verify key figures against the original material.</p>
    </aside>
  </div>
}

export default function App() {
  // A fictional report is shown on first load so the product opens with a useful visual preview.
  const [data, setData] = useState<Analysis>(demoResponse as Analysis)
  const [input, setInput] = useState<AnalysisInput>(blank)
  const [mode, setMode] = useState<Mode>('demo')
  const [stock, setStock] = useState<StockContext | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [libraryOpen, setLibraryOpen] = useState(false)
  const [autoOpen, setAutoOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { document.title = 'FinPulse — Beyond the headline' }, [])
  useEffect(() => {
    const sections = document.querySelectorAll<HTMLElement>('.reveal')
    if (!('IntersectionObserver' in window)) { sections.forEach(s => s.classList.add('is-visible')); return }
    const observer = new IntersectionObserver(entries => { entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target) } }) }, { threshold: .08, rootMargin: '0px 0px -30px 0px' })
    sections.forEach(section => observer.observe(section))
    return () => observer.disconnect()
  }, [data])

  function resetDemo() { setData(demoResponse as Analysis); setInput(blank); setStock(null); setMode('demo'); setError(''); setDrawerOpen(false); window.scrollTo({ top: 0, behavior: 'smooth' }) }

  async function importPdf(file: File): Promise<string | null> {
    setUploading(true); setError('')
    try {
      const body = new FormData(); body.append('file', file)
      const response = await fetch('/api/v1/pdf/extract', { method: 'POST', body })
      const json = await response.json()
      if (!response.ok) throw new Error(typeof json.detail === 'string' ? json.detail : 'Could not read PDF')
      return typeof json.text === 'string' ? json.text : null
    } catch (err) { setError(err instanceof Error ? err.message : 'PDF extraction failed'); return null }
    finally { setUploading(false) }
  }

  async function submit(next: AnalysisInput) {
    setError(''); setLoading(true)
    try {
      const sources = next.news_sources.filter(s => s.url?.trim() || s.text?.trim()).map(s => ({
        ...(s.url?.trim() ? { url: s.url.trim() } : {}), ...(s.text?.trim() ? { text: s.text.trim() } : {}),
        ...(s.title?.trim() ? { title: s.title.trim() } : {}), ...(s.outlet?.trim() ? { outlet: s.outlet.trim() } : {}), ...(s.headline_only ? { headline_only: true } : {}),
      }))
      const response = await fetch('/api/v1/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...next, news_sources: sources }) })
      const json = await response.json()
      if (!response.ok) throw new Error(response.status === 422 ? 'Check your company details, transcript length, and article fields.' : typeof json.detail === 'string' ? json.detail : 'Analysis request failed.')
      const report = json as Analysis
      setInput(next); setData(report); setMode('live'); setStock(null); setDrawerOpen(false)
      window.scrollTo({ top: 0, behavior: 'smooth' })
      if (report.announcement_date) {
        const params = new URLSearchParams({ announcement_date: report.announcement_date, market_timing: report.market_timing })
        fetch(`/api/v1/stocks/${encodeURIComponent(report.ticker)}?${params}`).then(r => r.ok ? r.json() as Promise<StockContext> : null).then(setStock).catch(() => setStock(null))
      }
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not connect to the server. Check that the backend is running on port 8000.') }
    finally { setLoading(false) }
  }

  function openSaved(report: Analysis) {
    setData(report); setMode('live'); setInput(blank); setStock(null); setError('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
    if (report.announcement_date) {
      const params = new URLSearchParams({ announcement_date: report.announcement_date, market_timing: report.market_timing })
      fetch(`/api/v1/stocks/${encodeURIComponent(report.ticker)}?${params}`)
        .then(r => r.ok ? r.json() as Promise<StockContext> : null)
        .then(setStock).catch(() => setStock(null))
    }
  }

  return <div className="app-page" id="top">
    <div className="global-aura" aria-hidden="true" />
    <header className="site-header"><div className="header-inner"><Brand/><nav className="site-nav" aria-label="Main sections"><a href="#market">Market lens</a><a href="#earnings">Earnings</a><a href="#perspectives">Perspectives</a></nav><div className="header-actions"><button className="demo-reset" onClick={() => setLibraryOpen(true)}><LibraryBig size={15}/> <span>Library</span></button><button className="demo-reset" onClick={resetDemo}><RotateCcw size={15}/> <span>Demo</span></button><button className="header-cta" onClick={() => { setError(''); setAutoOpen(true) }}>Auto research <ArrowUpRight size={17}/></button></div></div></header>
    <main className="site-main">
      <section className="editorial-hero" aria-label="FinPulse overview"><div className="hero-copy"><div className="hero-eyebrow"><span className="live-spark"/> AN EARNINGS INTELLIGENCE STUDIO</div><h1>Find the <em>signal.</em><br/>See the <span className="stroked">whole story.</span></h1><p>Company earnings, market movement, and the media narrative—all in one clear perspective.</p><button onClick={() => { setError(''); setAutoOpen(true) }} className="hero-action">Research any stock <ArrowUpRight size={19}/></button></div><div className="hero-art" aria-hidden="true"><div className="art-grid"/><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit orbit-three"/><div className="art-core"><svg viewBox="0 0 250 250" fill="none"><path d="M10 128h50l24-62 45 122 34-72h77" stroke="url(#waveStroke)" strokeWidth="13" strokeLinecap="round" strokeLinejoin="round"/><defs><linearGradient id="waveStroke" x1="10" y1="128" x2="235" y2="128"><stop stopColor="#ffffff"/><stop offset=".54" stopColor="#88F9C0"/><stop offset="1" stopColor="#ffffff"/></linearGradient></defs></svg></div><span className="orbit-caption top">01 / THE NUMBERS</span><span className="orbit-caption bottom">02 / THE NARRATIVE</span><span className="star star-a">✳</span><span className="star star-b">✦</span></div></section>
      <Reveal className="focus-strip"><div className="focus-mark"><span>{data.ticker.slice(0, 2).toUpperCase()}</span></div><div className="focus-copy"><span>IN FOCUS / {data.ticker}</span><h2>{data.company_name}</h2></div><div className="focus-period"><span>REPORTING PERIOD</span><strong>{data.fiscal_period}</strong></div><div className="focus-date"><span>ANNOUNCED</span><strong>{labelDate(data.announcement_date)}</strong></div><div className={`report-state ${mode === 'demo' ? 'demo-state' : ''}`}><span/>{mode === 'demo' ? 'FICTIONAL DEMO' : 'YOUR ANALYSIS'}</div></Reveal>
      <Reveal><MarketChart stock={stock} mode={mode} ticker={data.ticker}/></Reveal>
      <Reveal><Metrics data={data}/></Reveal>
      <Reveal className="narrative-grid"><Earnings data={data}/><Perspective data={data}/></Reveal>
      {data.social_posts && data.social_posts.length > 0 && <Reveal><SocialLens posts={data.social_posts}/></Reveal>}
      <Reveal className="closing-band"><div><span className="closing-kicker">FOLLOW THE EVIDENCE</span><h2>Every number<br/>has a <em>story.</em></h2></div><div className="closing-action"><p>Ready to explore a different company?</p><button onClick={() => { setError(''); setAutoOpen(true) }}>Research another stock <ArrowUpRight size={18}/></button></div><div className="closing-decoration" aria-hidden="true">✳</div></Reveal>
      {data.warnings.length > 0 && <details className="report-warnings"><summary><Info size={15}/> {data.warnings.length} analysis {data.warnings.length === 1 ? 'note' : 'notes'} <ChevronDown size={14}/></summary><ul>{data.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></details>}
      <footer className="site-footer"><Brand/><span>Source-aware earnings intelligence.</span><span>Informational only · Not investment advice</span></footer>
    </main>
    {libraryOpen && <ReportLibrary onClose={() => setLibraryOpen(false)} onOpen={openSaved}/>}
    {autoOpen && <AutoResearch onClose={() => setAutoOpen(false)} onComplete={openSaved} onManual={() => { setAutoOpen(false); setDrawerOpen(true) }}/>}
    {drawerOpen && <AnalysisDrawer initial={input} onClose={() => setDrawerOpen(false)} onSubmit={submit} loading={loading} uploading={uploading} onUpload={importPdf} error={error}/>}
  </div>
}
