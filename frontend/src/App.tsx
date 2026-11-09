import { useRef, useState, useEffect } from 'react'
import type { ReactNode, FormEvent } from 'react'
import {
  Activity, ArrowRight, ArrowUpRight, BarChart3, ChevronDown,
  CircleHelp, ExternalLink, FileText, GitCompareArrows, Info, Layers3,
  LoaderCircle, Menu, Newspaper, Plus, Radio, Search, ShieldCheck, Sparkles,
  TrendingUp, UploadCloud, X, Zap,
} from 'lucide-react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { Analysis, AnalysisInput, Evidence, NewsInput, StockContext } from './types'
import demoRequest from './data/sample-request.json'
import demoResponse from './data/demo-response.json'
import { PREVIEW_STOCK } from './data/preview-stock'

const emptyInput: AnalysisInput = {
  company_name: '', ticker: '', fiscal_period: '', announcement_date: null,
  market_timing: 'unknown', earnings_text: '', news_sources: [],
}

type ActiveMode = 'demo' | 'live' | 'empty'
const toNumber = (value: number) => Intl.NumberFormat('en-US', { maximumFractionDigits: 1, notation: 'compact' }).format(value)
const dateLabel = (value: string | null) => value ? new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Not provided'

function formatMetric(value: number | null, unit: string, currency: string | null, raw: string) {
  if (value === null) return raw
  if (unit === 'percent') return `${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}%`
  const symbol = currency === 'INR' ? '₹' : currency === 'USD' ? '$' : currency || ''
  if (unit === 'per_share') return `${symbol}${value.toFixed(2)}`
  return `${symbol}${toNumber(value)}`
}

function SourceEvidence({ evidence, label = 'View source passage' }: { evidence: Evidence; label?: string }) {
  return <details className="evidence"><summary>{label} <ChevronDown size={13} /></summary>
    <blockquote>“{evidence.text}”</blockquote><small>Source: {evidence.source_id} · characters {evidence.start_offset}–{evidence.end_offset}</small>
  </details>
}

function Tag({ children, tone = 'blue' }: { children: ReactNode; tone?: 'blue' | 'orange' | 'muted' | 'green' }) {
  return <span className={`tag ${tone}`}>{children}</span>
}

function PanelTitle({ eyebrow, title, meta, icon: Icon }: { eyebrow: string; title: string; meta?: string; icon: typeof Activity }) {
  return <div className="panel-heading"><div><span className="eyebrow"><Icon size={13}/>{eyebrow}</span><h2>{title}</h2></div>{meta && <span className="subtle">{meta}</span>}</div>
}

function LineGraph({ stock, demo }: { stock: StockContext | null; demo: boolean }) {
  const points = demo ? PREVIEW_STOCK.map(p => ({ ...p, close: p.price, volume: p.volume * 1_000_000 })) : (stock?.points || [])
  const marker = demo ? 'Oct 16' : stock?.first_session_on_or_after_date || undefined
  const label = demo ? 'Illustrative market data · not real stock prices' : `${stock?.ticker || ''} · ${stock?.price_basis || 'daily close'}`
  const [tab, setTab] = useState<'price' | 'volume'>('price')
  return <section id="market" className="panel market-panel">
    <PanelTitle eyebrow="03 / Market context" title="Price & volume" icon={TrendingUp} meta={demo ? 'Illustrative preview' : 'Historical context'} />
    <div className="chart-top"><div><div className="subtle small">{label}</div><div className="chart-large">{points.length ? (tab === 'price' ? `${demo ? '$' : stock?.currency === 'INR' ? '₹' : stock?.currency === 'USD' ? '$' : ''}${Number(points[points.length - 1].close).toFixed(2)}` : toNumber(points[points.length - 1].volume)) : '—'}<small>{tab === 'price' ? 'last plotted close' : 'last plotted volume'}</small></div></div>
      <div className="segment"><button className={tab === 'price' ? 'active' : ''} onClick={() => setTab('price')}>Price</button><button className={tab === 'volume' ? 'active' : ''} onClick={() => setTab('volume')}>Volume</button></div></div>
    {points.length ? <div className="chart"><ResponsiveContainer width="100%" height="100%">
      {tab === 'price' ? <AreaChart data={points} margin={{ top: 8, right: 10, left: -25, bottom: 2 }}><defs><linearGradient id="lineFade" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#0297DE" stopOpacity={0.24} /><stop offset="100%" stopColor="#0297DE" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#24313C" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fill: '#8996A6', fontSize: 11 }} tickFormatter={v => String(v).includes('-') ? String(v).slice(5) : v} /><YAxis domain={['auto', 'auto']} tickLine={false} axisLine={false} tick={{ fill: '#8996A6', fontSize: 11 }} /><Tooltip contentStyle={{ background: '#101820', border: '1px solid #263846', borderRadius: 12 }} labelStyle={{ color: '#f2f7fa' }} formatter={(value) => [`${Number(value).toFixed(2)}`, 'Close']} /><Area type="monotone" dataKey="close" stroke="#0297DE" strokeWidth={2.8} fill="url(#lineFade)" dot={false} activeDot={{ fill: '#FC734D', r: 5, strokeWidth: 0 }}/>{marker && <ReferenceLine x={marker} stroke="#FC734D" strokeDasharray="4 5" label={{ value: 'Earnings', fill: '#FC734D', fontSize: 10, position: 'insideTopLeft' }} />}</AreaChart>
      : <BarChart data={points} margin={{ top: 8, right: 10, left: -12, bottom: 2 }}><CartesianGrid stroke="#24313C" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fill: '#8996A6', fontSize: 11 }} tickFormatter={v => String(v).includes('-') ? String(v).slice(5) : v} /><YAxis tickLine={false} axisLine={false} tick={{ fill: '#8996A6', fontSize: 11 }} tickFormatter={v => toNumber(Number(v))} /><Tooltip contentStyle={{ background: '#101820', border: '1px solid #263846', borderRadius: 12 }} formatter={(value) => [Number(value).toLocaleString(), 'Shares']}/><Bar dataKey="volume" fill="#0297DE" radius={[4, 4, 0, 0]}/>{marker && <ReferenceLine x={marker} stroke="#FC734D" strokeDasharray="4 5" />}</BarChart>}
    </ResponsiveContainer></div> : <div className="empty-chart"><BarChart3 size={34}/><strong>No market data available</strong><p>Add an announcement date and a valid ticker. Market data requires an internet connection.</p></div>}
    <div className="market-footer"><span><span className="legend-dot blue-dot"/> Historical {tab === 'price' ? 'closing price' : 'volume'}</span><span><span className="legend-dot orange-dot"/> Earnings reference</span></div>
    {!demo && stock?.session_close_change_percent != null && <div className="note">Eligible session close change: <strong>{stock.session_close_change_percent > 0 ? '+' : ''}{stock.session_close_change_percent}%</strong> ({stock.previous_session_date} → {stock.first_session_on_or_after_date}); not proof of causation.</div>}
    {!demo && stock?.warning && <div className="note warning"><Info size={14}/>{stock.warning}</div>}
  </section>
}

function Results({ data, mode, stock }: { data: Analysis; mode: ActiveMode; stock: StockContext | null }) {
  const metrics = data.metrics.slice(0, 4)
  const shared = data.comparison.filter(c => c.relationship === 'shared')
  return <div className="results" id="overview">
    <div className="section-intro"><div><span className="eyebrow"><Radio size={13}/> ANALYSIS WORKSPACE</span><h1>Clarity in every <em>market move.</em></h1><p>Understand the earnings. Compare the coverage. Follow the evidence.</p></div><Tag tone={mode === 'demo' ? 'orange' : 'green'}>{mode === 'demo' ? '● Fictional demo' : '● Live analysis'}</Tag></div>
    <section className="company-strip"><div className="company-avatar">{data.ticker.slice(0, 2).toUpperCase()}</div><div className="company-info"><span className="eyebrow">COMPANY FOCUS</span><h2>{data.company_name}</h2><p>{data.ticker} <span>·</span> {data.fiscal_period} <span>·</span> {dateLabel(data.announcement_date)}</p></div><div className="strip-detail"><span>Analysis ID</span><strong>{data.analysis_id.slice(0, 8)}</strong></div></section>
    <section className="metric-grid" aria-label="Extracted metrics">
      {metrics.length ? metrics.map((metric, i) => <article className="metric-card" key={`${metric.name}-${i}`}><span className="metric-index">0{i + 1} / METRIC</span><div className="metric-value">{formatMetric(metric.normalized_value, metric.unit, metric.currency, metric.raw_value)}</div><div className="metric-name">{metric.name}</div><div className="metric-bottom"><span>{metric.reporting_period}{metric.metric_variant === 'adjusted' ? ' · Adjusted' : ''}</span><Tag tone={metric.extraction_status === 'needs_review' ? 'orange' : 'muted'}>{metric.extraction_status === 'needs_review' ? 'Review' : 'Source linked'}</Tag></div><SourceEvidence evidence={metric.evidence}/></article>) : <div className="no-metrics">No reliably extracted financial metrics. Check source wording and units.</div>}
    </section>
    <div className="main-grid"><section id="earnings" className="panel summary-panel"><PanelTitle icon={FileText} eyebrow="01 / Company perspective" title="Earnings intelligence" meta={`${data.summary.length} evidence-backed highlights`} /><div className="summary-list">{data.summary.length ? data.summary.map((item, index) => <div className="highlight" key={index}><div className="number-circle">{String(index + 1).padStart(2, '0')}</div><div><p>{item.text}</p><SourceEvidence evidence={item.evidence}/></div></div>) : <p className="muted">No extractable highlights.</p>}</div><div className="theme-list">{data.earnings_themes.map(theme => <Tag key={theme} tone="muted">{theme}</Tag>)}</div></section>
      <LineGraph stock={stock} demo={mode === 'demo'} />
    </div>
    <section id="comparison" className="panel compare-panel"><PanelTitle icon={GitCompareArrows} eyebrow="04 / Perspective comparison" title="Earnings vs. the media" meta={`${shared.length} shared themes`} /><p className="panel-description">Where company statements and independent coverage meet. Themes indicate topical overlap—not agreement on truth.</p><div className="compare-grid">{data.comparison.length ? data.comparison.map((item, i) => <div className="compare-card" key={item.theme}><div className="compare-top"><span className="compare-num">{String(i+1).padStart(2, '0')}</span><Tag tone={item.relationship === 'shared' ? 'blue' : item.relationship === 'news_only' ? 'orange' : 'muted'}>{item.relationship.replace('_', ' ')}</Tag></div><h3>{item.theme}</h3><span className="subtle small">{item.news_evidence.length} media source{item.news_evidence.length === 1 ? '' : 's'}</span>{item.earnings_evidence && <SourceEvidence evidence={item.earnings_evidence} label="Company passage" />}{item.news_evidence.map((news, j) => <SourceEvidence key={j} evidence={news.evidence} label={`${news.outlet} passage`} />)}</div>) : <p className="muted">Add news sources to compare themes.</p>}</div></section>
    <section id="coverage" className="panel coverage-panel"><PanelTitle icon={Newspaper} eyebrow="02 / Media coverage" title="Independent perspectives" meta={`${data.sources.length} sources submitted`}/><div className="news-grid">{data.sources.length ? data.sources.map((source, i) => <article className="news-card" key={source.source_id}><div className="news-header"><div className="news-icon"><Newspaper size={18}/></div><span className="subtle small">SOURCE 0{i+1}</span><Tag tone={source.extraction_status === 'failed' ? 'orange' : 'muted'}>{source.extraction_status === 'failed' ? 'Unavailable' : source.input_origin === 'url' ? 'URL extracted' : 'Pasted text'}</Tag></div><div className="outlet">{source.outlet}</div><h3>{source.title}</h3><p className="subtle small">{source.published_at ? dateLabel(source.published_at) : 'Publication date unknown'}</p><div className="sentiment"><span>Estimated tone</span><Tag tone={source.sentiment_label === 'negative' ? 'orange' : source.sentiment_label === 'positive' ? 'green' : 'muted'}>{source.sentiment_label || 'Unavailable'}</Tag></div>{source.warning && <p className="warning-text">{source.warning}</p>}<div className="news-summary">{source.summary.map((s, j) => <div key={j}><p>{s.text}</p><SourceEvidence evidence={s.evidence}/></div>)}</div><div className="theme-list">{source.themes.slice(0, 4).map(t => <Tag tone="muted" key={t}>{t}</Tag>)}</div>{source.url && <a href={source.url} target="_blank" rel="noopener noreferrer" className="source-link">View original <ExternalLink size={14}/></a>}</article>) : <p className="muted">No media sources in this analysis.</p>}</div></section>
    <section id="methods" className="disclosure-panel"><div><ShieldCheck size={19}/><strong>Evidence-first, no prediction engine</strong></div><p>Each metric and highlight links to source passages. This tool uses extractive and rules-based methods, not generative claims. Estimated language sentiment is not a measure of factual performance. Stock movements do not establish earnings causality.</p>{data.warnings.length > 0 && <details><summary>{data.warnings.length} analysis notices <ChevronDown size={14}/></summary><ul>{data.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul></details>}</section>
  </div>
}

function App() {
  const [input, setInput] = useState<AnalysisInput>(emptyInput)
  const [result, setResult] = useState<Analysis | null>(null)
  const [stock, setStock] = useState<StockContext | null>(null)
  const [mode, setMode] = useState<ActiveMode>('empty')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(true)
  const [mobileMenu, setMobileMenu] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  function update<K extends keyof AnalysisInput>(key: K, value: AnalysisInput[K]) { setInput(prev => ({ ...prev, [key]: value })) }
  function updateNews(index: number, key: keyof NewsInput, value: string) {
    setInput(prev => ({ ...prev, news_sources: prev.news_sources.map((news, i) => i === index ? { ...news, [key]: value } : news) }))
  }
  function loadDemo() { setInput(demoRequest as AnalysisInput); setResult(demoResponse as Analysis); setStock(null); setMode('demo'); setFormOpen(false); setError('') }

  async function handlePdf(file: File) {
    if (!file) return
    setUploading(true); setError('')
    try {
      const form = new FormData(); form.append('file', file)
      const response = await fetch('/api/v1/pdf/extract', { method: 'POST', body: form })
      const body = await response.json()
      if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Could not extract PDF text')
      update('earnings_text', body.text)
    } catch (exc) { setError(exc instanceof Error ? exc.message : 'PDF extraction unavailable') }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = '' }
  }

  async function submit(e: FormEvent) {
    e.preventDefault(); setLoading(true); setError('')
    try {
      const body = { ...input, news_sources: input.news_sources.filter(s => (s.url || '').trim() || (s.text || '').trim()).map(s => ({ ...(s.url?.trim() ? { url: s.url.trim() } : {}), ...(s.text?.trim() ? { text: s.text.trim() } : {}), ...(s.title?.trim() ? { title: s.title.trim() } : {}), ...(s.outlet?.trim() ? { outlet: s.outlet.trim() } : {}) })) }
      const response = await fetch('/api/v1/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      const data = await response.json()
      if (!response.ok) throw new Error(response.status === 422 ? 'Review the company details, transcript length and news fields.' : data.detail || 'Analysis failed')
      setResult(data as Analysis); setMode('live'); setFormOpen(false); setStock(null)
      if (data.announcement_date) {
        const params = new URLSearchParams({ announcement_date: data.announcement_date, market_timing: data.market_timing })
        fetch(`/api/v1/stocks/${encodeURIComponent(data.ticker)}?${params}`).then(r => r.ok ? r.json() : null).then(setStock).catch(() => setStock(null))
      }
    } catch (exc) { setError(exc instanceof Error ? exc.message : 'Connection failed. Is the FastAPI server running on port 8000?') }
    finally { setLoading(false) }
  }

  useEffect(() => { document.title = 'FinPulse | Earnings & News Intelligence' }, [])
  return <div className="app-shell">
    <aside className={`sidebar ${mobileMenu ? 'show' : ''}`}><a href="#top" className="brand" onClick={() => setMobileMenu(false)}><span className="brand-mark"><Activity size={21} strokeWidth={2.5}/></span><span>fin<span>pulse</span><small>INTELLIGENCE ENGINE</small></span></a><div className="sidebar-label">WORKSPACE</div><nav>{[[Layers3, 'Overview', '#overview'], [FileText, 'Earnings', '#earnings'], [Newspaper, 'News coverage', '#coverage'], [GitCompareArrows, 'Comparison', '#comparison'], [BarChart3, 'Market context', '#market']].map(([Icon, name, href]) => { const I = Icon as typeof Activity; return <a href={href as string} key={name as string} onClick={() => setMobileMenu(false)}><I size={17}/>{name as string}</a> })}</nav><div className="sidebar-bottom"><div className="sidebar-tip"><Zap size={19}/><strong>Perspective, not prediction.</strong><p>Evidence-backed market intelligence, built to help you think clearly.</p></div><span className="build-version">FINPULSE MVP · V1.0</span></div></aside>
    <main id="top" className="main-content"><header className="topbar"><button className="mobile-toggle" onClick={() => setMobileMenu(!mobileMenu)} aria-label="Toggle menu"><Menu size={20}/></button><span className="breadcrumb">Workspace <span>/</span> <strong>Intelligence dashboard</strong></span><div className="top-actions"><span className="local-pill"><span/> LOCAL-FIRST</span><a target="_blank" rel="noreferrer" href="https://github.com/RohitSuhasReddy/FinPulse" className="github-link">View repository <ArrowUpRight size={15}/></a></div></header>
      <div className="content-wrap"><div className="welcome-row"><div><span className="micro-label"><Sparkles size={13}/> TURN INFORMATION INTO PERSPECTIVE</span><h1 className="welcome">Market intelligence, <em>without the noise.</em></h1><p className="intro-copy">From earnings to headlines, find the signal beneath the story.</p></div><button className="demo-button" onClick={loadDemo}><Sparkles size={16}/> Explore demo <ArrowRight size={15}/></button></div>
      <section className="input-panel"><button className="input-heading" onClick={() => setFormOpen(!formOpen)} aria-expanded={formOpen}><div className="input-icon"><Search size={20}/></div><div><strong>Start an analysis</strong><span>Company + earnings + up to three news sources</span></div><ChevronDown className={formOpen ? 'rotate' : ''} size={20}/></button>{formOpen && <form className="analysis-form" onSubmit={submit}><div className="form-row three"><label>Company name<input value={input.company_name} onChange={e => update('company_name', e.target.value)} required minLength={2} maxLength={120} placeholder="e.g. Microsoft"/></label><label>Stock ticker<input value={input.ticker} onChange={e => update('ticker', e.target.value.toUpperCase())} required maxLength={12} placeholder="MSFT"/></label><label>Reporting period<input value={input.fiscal_period} onChange={e => update('fiscal_period', e.target.value)} required minLength={3} placeholder="FY2026 Q1"/></label></div><div className="form-row two"><label>Earnings announcement date <small>optional</small><input type="date" value={input.announcement_date || ''} onChange={e => update('announcement_date', e.target.value || null)}/></label><label>Announcement timing<select value={input.market_timing || 'unknown'} onChange={e => update('market_timing', e.target.value as AnalysisInput['market_timing'])}><option value="unknown">Unknown</option><option value="before_open">Before market open</option><option value="after_close">After market close</option></select></label></div><div className="field-header"><label htmlFor="earnings-text">Earnings transcript / release</label><button type="button" className="text-button" onClick={() => fileRef.current?.click()} disabled={uploading}><UploadCloud size={15}/>{uploading ? 'Extracting…' : 'Import PDF text'}</button><input hidden ref={fileRef} type="file" accept=".pdf,application/pdf" onChange={e => e.target.files?.[0] && handlePdf(e.target.files[0])}/></div><textarea id="earnings-text" value={input.earnings_text} onChange={e => update('earnings_text', e.target.value)} required minLength={80} rows={5} placeholder="Paste the earnings transcript or press release (minimum 80 characters). Source passages stay linked to extracted insights."/><div className="field-header"><label>News coverage <small>optional · 3 max</small></label><button type="button" className="text-button" disabled={input.news_sources.length >= 3} onClick={() => update('news_sources', [...input.news_sources, { url: '', title: '', outlet: '', text: '' }])}><Plus size={15}/> Add source</button></div>{input.news_sources.map((news, i) => <div className="source-input" key={i}><div className="source-input-head"><span>NEWS SOURCE {i+1}</span><button type="button" aria-label={`Remove news source ${i+1}`} onClick={() => update('news_sources', input.news_sources.filter((_, j) => i !== j))}><X size={16}/></button></div><div className="form-row two"><label>Article URL<input type="url" value={news.url || ''} placeholder="https://example.com/article" onChange={e => updateNews(i, 'url', e.target.value)}/></label><label>Outlet<input value={news.outlet || ''} maxLength={100} placeholder="e.g. News outlet (optional)" onChange={e => updateNews(i, 'outlet', e.target.value)}/></label></div><label>Article title<input value={news.title || ''} maxLength={240} placeholder="Optional title" onChange={e => updateNews(i, 'title', e.target.value)}/></label><label>Paste article text <small>optional if URL is accessible; recommended for paywalls</small><textarea rows={2} value={news.text || ''} onChange={e => updateNews(i, 'text', e.target.value)} placeholder="Paste the article body as a fallback (minimum 50 characters)."/></label></div>)}<div className="form-footer"><span><ShieldCheck size={14}/> Local processing. No paid LLM API.</span><button className="primary-button" type="submit" disabled={loading || uploading}>{loading ? <><LoaderCircle className="spin" size={17}/> Analyzing…</> : <>Analyze intelligence <ArrowRight size={17}/></>}</button></div></form>}{error && <div className="error-banner" role="alert"><Info size={18}/>{error}</div>}</section>
      {result ? <Results data={result} mode={mode} stock={stock}/> : <div className="empty-state"><div className="orb"><Activity size={45}/></div><span className="eyebrow">YOUR WORKSPACE IS READY</span><h2>Every story has a signal.</h2><p>Start with an earnings transcript, or explore the fictional demo to see how analysis and evidence come together.</p><button onClick={loadDemo}>Preview FinPulse <ArrowRight size={16}/></button></div>}
      <footer><span>© 2026 FinPulse · Built for evidence-driven research</span><span>Not investment advice <CircleHelp size={13}/></span></footer></div>
    </main>
  </div>
}

export default App
