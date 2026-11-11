import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import {
  ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3, Check, ChevronLeft,
  ChevronRight, ExternalLink, FileText, FileUp, Info, LibraryBig,
  LoaderCircle, Newspaper, Plus, Sparkles, Trash2, TrendingUp,
} from 'lucide-react'
import {
  CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import type { Analysis, AnalysisInput, FinancialMetric, NewsInput, SourceAnalysis, StockContext } from './types'
import './experience.css'

type Page = 'studio' | 'earnings' | 'market' | 'coverage' | 'compare' | 'library'
type Saved = {
  analysis_id: string; company_name: string; ticker: string; fiscal_period: string;
  announcement_date: string | null; analyzed_at: string; metric_count: number;
  news_count: number; extraction_version?: number
}
type ComparisonMetric = {
  name: string; unit: string; currency: string | null; metric_variant: string | null;
  values: Array<number | null>; evidence: Array<{ text: string } | null>;
  available_periods: number; change_percent: number | null
}
type MultiComparison = {
  ticker: string; company_name: string;
  periods: Array<{ analysis_id: string; fiscal_period: string; announcement_date: string | null }>;
  metrics: ComparisonMetric[]; narrative: string[]; warnings: string[]
}
type MarketReading = {
  status: string; interpretation: string | null; model?: string;
  stock: StockContext | null;
  before: PriceWindow | null; after: PriceWindow | null; notice: string
}
type PriceWindow = {
  start: string; end: string; start_close: number; end_close: number;
  trading_sessions: number; change_percent: number | null
}

const nav: Array<{ id: Page; label: string; number: string }> = [
  { id: 'studio', label: 'Studio', number: '01' },
  { id: 'earnings', label: 'Earnings', number: '02' },
  { id: 'market', label: 'Market', number: '03' },
  { id: 'coverage', label: 'Coverage', number: '04' },
  { id: 'compare', label: 'Compare', number: '05' },
  { id: 'library', label: 'Library', number: '06' },
]
const emptyInput: AnalysisInput = {
  company_name: '', ticker: '', fiscal_period: '', announcement_date: null,
  market_timing: 'unknown', earnings_text: '', news_sources: [],
}
const formatCompact = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2, notation: 'compact' })
const formatNumber = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })
const dateLabel = (value: string | null) => value
  ? new Date(value.slice(0, 10) + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  : 'Announcement date not supplied'
const marker = (value: number) => (value > 0 ? '+' : '') + value.toFixed(2) + '%'
const safeUrl = (value?: string | null) => value && /^https?:\/\//i.test(value) ? value : null
const numberValue = (value: number | null, unit: string, currency: string | null) => {
  if (value === null) return 'Not available'
  const prefix = currency === 'USD' ? '$' : currency === 'INR' ? '₹' : currency ? currency + ' ' : ''
  if (unit === 'percent') return formatNumber.format(value) + '%'
  if (unit === 'per_share') return prefix + value.toFixed(2)
  return prefix + (Math.abs(value) >= 100000 ? formatCompact.format(value) : formatNumber.format(value))
}
async function readResponse<T>(response: Response): Promise<T> {
  const json = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message = typeof json.detail === 'string' ? json.detail : 'The request could not be completed'
    throw new Error(message)
  }
  return json as T
}

function Reveal({ children, className = '' }: { children: ReactNode; className?: string }) {
  const element = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const node = element.current
    if (!node) return
    if (!('IntersectionObserver' in window)) { node.classList.add('is-visible'); return }
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target) } })
    }, { threshold: 0.13, rootMargin: '0px 0px -40px 0px' })
    observer.observe(node)
    return () => observer.disconnect()
  }, [])
  return <div className={'fp-reveal ' + className} ref={element}>{children}</div>
}
function Empty({ onNew, title, description }: { onNew: () => void; title: string; description: string }) {
  return <div className="fp-empty">
    <span className="fp-eyebrow">NO REPORT SELECTED</span><h2>{title}</h2><p>{description}</p>
    <button type="button" className="fp-primary" onClick={onNew}>Start with an earnings report <ArrowRight size={16}/></button>
  </div>
}
function Metric({ metric, index }: { metric: FinancialMetric; index: number }) {
  return <Reveal className="fp-metric-slide">
    <div className="fp-metric-index">{String(index + 1).padStart(2, '0')} / EARNINGS SIGNAL</div>
    <h3>{metric.name}</h3>
    <div className="fp-metric-number">{metric.normalized_value === null ? metric.raw_value : numberValue(metric.normalized_value, metric.unit, metric.currency)}</div>
    <p>{metric.reporting_period} · {metric.metric_variant || 'Basis not stated'} · {metric.extraction_status === 'needs_review' ? 'Check source before relying on this figure' : 'Extracted from supplied report'}</p>
    <details className="fp-evidence"><summary>View source evidence <ChevronRight size={14}/></summary><blockquote>{metric.evidence.text}</blockquote></details>
  </Reveal>
}
function Studio({ onAnalyze, loading, error }: {
  onAnalyze: (value: AnalysisInput) => Promise<void>; loading: boolean; error: string
}) {
  const [form, setForm] = useState<AnalysisInput>(emptyInput)
  const [fileName, setFileName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [articleRows, setArticleRows] = useState<NewsInput[]>([])
  const [showText, setShowText] = useState(false)
  const patch = (value: Partial<AnalysisInput>) => setForm(prev => ({ ...prev, ...value }))
  async function upload(file?: File) {
    if (!file) return
    setUploadError(''); setUploading(true)
    try {
      let text = ''
      if (/\.pdf$/i.test(file.name)) {
        const body = new FormData(); body.append('file', file)
        const response = await fetch('/api/v1/pdf/extract', { method: 'POST', body })
        text = (await readResponse<{ text: string }>(response)).text
      } else if (/\.txt$/i.test(file.name)) {
        if (file.size > 1_000_000) throw new Error('TXT files must be 1 MB or smaller')
        text = await file.text()
      } else throw new Error('Choose a PDF or TXT earnings report')
      if (text.trim().length < 80) throw new Error('The document does not contain enough readable text')
      patch({ earnings_text: text })
      setFileName(file.name)
    } catch (e) { setUploadError(e instanceof Error ? e.message : 'File could not be read') }
    finally { setUploading(false) }
  }
  function updateArticle(index: number, item: Partial<NewsInput>) {
    setArticleRows(prev => prev.map((source, i) => i === index ? { ...source, ...item } : source))
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    const news_sources = articleRows
      .filter(row => Boolean(row.text?.trim()) || Boolean(row.url?.trim()))
      .map(row => ({ ...row, headline_only: !Boolean(row.text?.trim()) }))
    setUploadError('')
    if (news_sources.some(row => row.text?.trim() && row.text.trim().length < 50)) {
      setUploadError('To summarize an article, paste at least 50 characters of its body text')
      return
    }
    if (news_sources.some(row => row.headline_only && (!row.title || row.title.trim().length < 15 || !safeUrl(row.url)))) {
      setUploadError('Headline-only sources need a title of at least 15 characters and a valid source URL')
      return
    }
    void onAnalyze({ ...form, ticker: form.ticker.toUpperCase().trim(), news_sources })
  }
  return <div className="fp-layout">
    <section className="fp-studio-intro">
      <Reveal><span className="fp-eyebrow"><Sparkles size={14}/> THE EARNINGS STUDIO</span>
        <h1>One report.<br/><em>A whole new</em><br/>perspective.</h1>
        <p>Bring the source. FinPulse turns a quarterly report into verifiable numbers, an evidence-linked story, and a market lens—without automatic research chains.</p>
        <div className="fp-trust"><span><Check size={13}/> Local report library</span><span><Check size={13}/> NLP-first analysis</span><span><Check size={13}/> No fabricated numbers</span></div>
      </Reveal>
      <div className="fp-watermark" aria-hidden="true">FP<span>—</span>02</div>
    </section>
    <form className="fp-studio-form" onSubmit={submit}>
      <div className="fp-form-heading"><span className="fp-eyebrow">01 — BRING THE EVIDENCE</span><h2>Start with <em>the source.</em></h2><p>One company and fiscal quarter per analysis. Your previous analyses stay in the Library.</p></div>
      <div className="fp-fields">
        <label>Company name<input required minLength={2} maxLength={120} placeholder="e.g. Microsoft" value={form.company_name} onChange={e => patch({ company_name: e.target.value })}/></label>
        <label>Ticker<input required maxLength={12} pattern="[A-Za-z0-9.\-]+" placeholder="e.g. MSFT" value={form.ticker} onChange={e => patch({ ticker: e.target.value })}/></label>
        <label>Fiscal quarter<input required minLength={3} placeholder="e.g. FY2026 Q2" value={form.fiscal_period} onChange={e => patch({ fiscal_period: e.target.value })}/></label>
        <label>Earnings announcement date <small>Optional</small><input type="date" value={form.announcement_date || ''} onChange={e => patch({ announcement_date: e.target.value || null })}/></label>
        <label className="fp-wide">Announcement timing <small>Helps interpret the trading session</small>
          <select value={form.market_timing} onChange={e => patch({ market_timing: e.target.value as AnalysisInput['market_timing'] })}>
            <option value="unknown">Unknown — do not infer reaction session</option>
            <option value="before_open">Before market open</option><option value="after_close">After market close</option>
          </select>
        </label>
      </div>
      <label className={'fp-upload ' + (fileName ? 'fp-upload-complete' : '')}>
        {uploading ? <LoaderCircle className="fp-spin" size={30}/> : fileName ? <Check size={30}/> : <FileUp size={30}/>}
        <strong>{uploading ? 'Reading document…' : fileName || 'Drop in the quarterly report'}</strong>
        <span>PDF or TXT · Best with selectable, machine-readable text</span>
        <input type="file" accept=".pdf,.txt,application/pdf,text/plain" onChange={e => void upload(e.target.files?.[0])} disabled={uploading || loading}/>
      </label>
      <button type="button" className="fp-text-toggle" onClick={() => setShowText(prev => !prev)}>
        {showText ? 'Hide' : 'Paste or review'} extracted report text <ChevronRight size={14}/>
      </button>
      {showText && <label className="fp-block-label">Source document text<textarea rows={8} placeholder="Paste an investor earnings release or a machine-readable quarterly report…" value={form.earnings_text} onChange={e => { patch({ earnings_text: e.target.value }); setFileName('') }}/></label>}
      <p className="fp-form-hint">{form.earnings_text.length.toLocaleString()} characters prepared. Nothing is sent to Gemini for financial metric extraction.</p>

      <div className="fp-news-input">
        <div className="fp-news-heading"><div><span className="fp-eyebrow">02 — OPTIONAL OUTSIDE VIEW</span><h3>Curate the <em>coverage.</em></h3><p>Add article text to generate a source-grounded summary. A headline and link alone are shown without an invented summary.</p></div>
          <button type="button" className="fp-outline" onClick={() => setArticleRows(prev => prev.length < 8 ? [...prev, { title: '', outlet: '', text: '', url: '' }] : prev)} disabled={articleRows.length >= 8}><Plus size={15}/> Add outlet</button></div>
        {articleRows.map((row, index) => <div className="fp-article-form" key={index}>
          <div className="fp-article-number">SOURCE {String(index + 1).padStart(2, '0')} <button type="button" onClick={() => setArticleRows(prev => prev.filter((_, i) => i !== index))}>Remove</button></div>
          <div className="fp-fields"><label>Outlet<input placeholder="e.g. Reuters" value={row.outlet || ''} onChange={e => updateArticle(index, { outlet: e.target.value })}/></label>
            <label>Headline<input placeholder="Article title" value={row.title || ''} onChange={e => updateArticle(index, { title: e.target.value })}/></label>
            <label className="fp-wide">Source link <small>Optional when full text is pasted</small><input type="url" placeholder="https://…" value={row.url || ''} onChange={e => updateArticle(index, { url: e.target.value })}/></label>
          </div>
          <label className="fp-block-label">Article body <small>For NLP summarization; no automated article fetching</small><textarea rows={3} placeholder="Paste article text here. Leave blank to keep a headline-only link." value={row.text || ''} onChange={e => updateArticle(index, { text: e.target.value })}/></label>
        </div>)}
      </div>
      {(error || uploadError) && <p className="fp-error" role="alert">{uploadError || error}</p>}
      <button className="fp-primary fp-submit" type="submit" disabled={loading || uploading || form.earnings_text.trim().length < 80 || !form.company_name.trim() || !form.ticker.trim() || !form.fiscal_period.trim()}>
        {loading ? <LoaderCircle className="fp-spin" size={18}/> : <Sparkles size={18}/>}
        {loading ? 'Analyzing and saving…' : 'Generate the earnings experience'} <ArrowRight size={17}/>
      </button>
      <p className="fp-disclaimer">Numbers are extracted conservatively; review quoted source evidence before relying on any metric.</p>
    </form>
  </div>
}

function Earnings({ data }: { data: Analysis }) {
  const strong = data.metrics.filter(m => m.extraction_status === 'extracted')
  const metrics = (strong.length ? strong : data.metrics).slice(0, 8)
  return <main className="fp-report">
    <section className="fp-report-opening"><Reveal><span className="fp-eyebrow">{data.ticker} / {data.fiscal_period} / THE EARNINGS STORY</span>
      <h1>Behind <em>the quarter.</em></h1>
      <p>{data.company_name} · {dateLabel(data.announcement_date)}</p>
      <span className="fp-scroll-prompt">SCROLL TO FOLLOW THE NUMBERS <span>↓</span></span>
    </Reveal></section>
    <section className="fp-story-sequence">
      <span className="fp-story-rail" aria-hidden="true"/>
      {metrics.length ? metrics.map((metric, i) => <Metric key={metric.name + i} metric={metric} index={i}/>)
        : <Reveal className="fp-metric-slide"><span className="fp-eyebrow">NO CONFIDENT METRICS</span><h2>Evidence before estimation.</h2><p>No values met the extractor's confidence checks. Review the uploaded document rather than filling gaps with guessed figures.</p></Reveal>}
    </section>
    <section className="fp-story-summary">
      <Reveal><span className="fp-eyebrow">THE REPORT, IN CONTEXT</span><h2>The story behind <em>the numbers.</em></h2>
      <p className="fp-summary-sub">A continuous NLP-selected account from the supplied document—not an AI-invented earnings thesis.</p></Reveal>
      {data.summary.length ? data.summary.map((highlight, i) => <Reveal key={i} className="fp-summary-passage">
        <span className="fp-passage-no">{String(i + 1).padStart(2, '0')}</span><p>{highlight.text}</p>
        <details className="fp-evidence"><summary>Original report passage <ChevronRight size={14}/></summary><blockquote>{highlight.evidence.text}</blockquote></details>
      </Reveal>) : <p>No reliable narrative passages could be extracted. This result remains saved for review.</p>}
      {data.earnings_themes.length > 0 && <Reveal><div className="fp-theme-list">{data.earnings_themes.map(t => <span key={t}>{t}</span>)}</div></Reveal>}
    </section>
    <section className="fp-report-footnote"><span className="fp-eyebrow">DATA INTEGRITY</span>
      <h3>Know what is <em>known.</em></h3>
      {data.warnings.map((w, i) => <p key={i}><Info size={14}/>{w}</p>)}
    </section>
  </main>
}

function Market({ report, result, loading, error }: { report: Analysis; result: MarketReading | null; loading: boolean; error: string }) {
  const pts = result?.stock?.points || []
  const currency = result?.stock?.currency || ''
  return <main className="fp-section fp-market">
    <Reveal><span className="fp-eyebrow">03 / THE MARKET LENS</span><h1>Before. <em>After.</em><br/>What actually moved?</h1>
      <p className="fp-lead">Two calendar weeks around {report.ticker}'s earnings date, with historical daily closes and an optional Gemini interpretation grounded in the reported figures.</p></Reveal>
    {loading && <p className="fp-status"><LoaderCircle className="fp-spin" size={18}/> Loading market observations…</p>}
    {error && <p className="fp-error">{error}</p>}
    {result && <>
      <div className="fp-window-grid">
        {([{ title: 'THE WEEK BEFORE', value: result.before }, { title: 'THE WEEK AFTER', value: result.after }] as const).map(window => <Reveal key={window.title} className="fp-window">
          <span className="fp-eyebrow">{window.title}</span><strong>{window.value?.change_percent === null || !window.value ? '—' : marker(window.value.change_percent)}</strong>
          <p>{window.value ? dateLabel(window.value.start) + ' to ' + dateLabel(window.value.end) + ' · ' + window.value.trading_sessions + ' sessions' : 'Insufficient daily market data'}</p>
        </Reveal>)}
      </div>
      <div className="fp-chart-shell">
        <div className="fp-chart-label"><span>HISTORICAL DAILY CLOSE · {currency || 'CURRENCY NOT SUPPLIED'}</span><span>Source: yfinance · {result.stock?.price_basis || 'Market data unavailable'}</span></div>
        {pts.length ? <div className="fp-chart"><ResponsiveContainer width="100%" height="100%">
          <LineChart data={pts} margin={{ top: 20, right: 22, left: 0, bottom: 8 }}>
            <CartesianGrid stroke="#302941" strokeDasharray="2 8" vertical={false}/>
            <XAxis dataKey="date" stroke="#8D87A5" tick={{ fill: '#8D87A5', fontSize: 11 }} minTickGap={30}/>
            <YAxis stroke="#8D87A5" tick={{ fill: '#8D87A5', fontSize: 11 }} domain={['auto','auto']} width={57}/>
            <Tooltip contentStyle={{ background: '#17132A', border: '1px solid #514476', borderRadius: 12 }} formatter={(value: number) => [formatNumber.format(value) + ' ' + currency, 'Close']}/>
            {report.announcement_date && <ReferenceLine x={report.announcement_date} stroke="#88F9C0" strokeDasharray="3 4" label={{ position: 'top', fill: '#88F9C0', value: 'Earnings', fontSize: 11 }}/>}
            <Line dataKey="close" type="monotone" stroke="#88F9C0" strokeWidth={3} dot={false} isAnimationActive={true} connectNulls={false}/>
          </LineChart>
        </ResponsiveContainer></div> : <p className="fp-empty-chart">Historical prices are unavailable for this ticker or date.</p>}
      </div>
      <Reveal className="fp-interpretation"><span className="fp-eyebrow"><Sparkles size={14}/> GEMINI / OPTIONAL MARKET INTERPRETATION</span><h2>The measured move. <em>The possible context.</em></h2>
        {result.interpretation ? <div className="fp-generated">{result.interpretation}</div> : <p>Observed market data remains accessible without Gemini. {result.status === 'not_configured' ? 'Add GEMINI_API_KEY to the backend environment to enable interpretation.' : 'No model interpretation is available for this report.'}</p>}
        <p className="fp-disclaimer">{result.notice}</p>
        <p className="fp-disclaimer">Interpretations are hypotheses based only on the uploaded report and historical price windows—not explanations of proven causality or return forecasts.</p>
      </Reveal>
    </>}
  </main>
}

function Coverage({ data }: { data: Analysis }) {
  const outlets = Array.from(new Set(data.sources.map(s => s.outlet)))
  const [selected, setSelected] = useState('')
  const [articleIndex, setArticleIndex] = useState(0)
  const currentOutlet = outlets.includes(selected) ? selected : outlets[0]
  const stories = data.sources.filter(s => s.outlet === currentOutlet)
  const story: SourceAnalysis | undefined = stories[articleIndex] || stories[0]
  const choose = (name: string) => { setSelected(name); setArticleIndex(0) }
  return <main className="fp-section fp-coverage">
    <Reveal><span className="fp-eyebrow">04 / THE OUTSIDE VIEW</span><h1>Every outlet.<br/><em>Another angle.</em></h1><p className="fp-lead">Select a publisher to revolve through its stories. Summaries come only from article text you supplied.</p></Reveal>
    {outlets.length ? <>
      <div className="fp-outlet-orbit" aria-label="Select a news outlet">
        {outlets.map((outlet, i) => <button key={outlet} type="button" className={'fp-outlet ' + (outlet === currentOutlet ? 'fp-outlet-active' : '')} onClick={() => choose(outlet)}>
          <span>{String(i + 1).padStart(2,'0')}</span>{outlet}
        </button>)}
      </div>
      {story && <article key={story.source_id} className="fp-featured-story">
        <div className="fp-story-backdrop" aria-hidden="true">{currentOutlet}</div>
        <div className="fp-featured-body"><span className="fp-eyebrow">{currentOutlet} · {story.extraction_status === 'ok' ? 'ARTICLE SUMMARY' : 'HEADLINE ONLY'}</span>
          <h2>{story.title}</h2>
          {story.summary.length ? <div className="fp-featured-summaries">{story.summary.map((x, i) => <p key={i}>{x.text}</p>)}</div>
            : <p className="fp-unavailable">Full article text was not supplied. No article summary or sentiment has been invented.</p>}
          {story.themes.length > 0 && <div className="fp-theme-list">{story.themes.map(t => <span key={t}>{t}</span>)}</div>}
          {safeUrl(story.url) && <a className="fp-source-link" href={story.url!} target="_blank" rel="noopener noreferrer">Read original article <ExternalLink size={16}/></a>}
          {stories.length > 1 && <div className="fp-news-pager"><button type="button" aria-label="Previous story" onClick={() => setArticleIndex(i => (i - 1 + stories.length) % stories.length)}><ChevronLeft size={18}/></button><span>{articleIndex + 1} / {stories.length}</span><button type="button" aria-label="Next story" onClick={() => setArticleIndex(i => (i + 1) % stories.length)}><ChevronRight size={18}/></button></div>}
        </div>
      </article>}
      <div className="fp-coverage-compare"><h3>Where the narratives <em>meet.</em></h3>
        {data.comparison.slice(0, 8).map((item, i) => <div className="fp-theme-row" key={i}><span>{item.theme}</span><small>{item.relationship.replace(/_/g,' ')}</small></div>)}
        <p className="fp-disclaimer">Theme overlap describes words and topics; it does not prove a publisher agrees with a company's claims.</p>
      </div>
    </> : <div className="fp-no-news"><Newspaper size={32}/><h2>Silence is not a failure.</h2><p>No news sources were supplied with this report. Analyze another quarter with manually curated publisher content to populate this experience.</p></div>}
  </main>
}

function Compare({ items }: { items: Saved[] }) {
  const companies = Array.from(new Set(items.map(i => i.ticker))).sort()
  const [company, setCompany] = useState('')
  const ticker = companies.includes(company) ? company : companies[0]
  const pool = items.filter(i => i.ticker === ticker).sort((a, b) => a.fiscal_period.localeCompare(b.fiscal_period, undefined, { numeric: true }))
  const [selected, setSelected] = useState<string[]>([])
  const validSelected = selected.filter(id => pool.some(i => i.analysis_id === id))
  const [comparison, setComparison] = useState<MultiComparison | null>(null)
  const [metricName, setMetricName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  async function generate() {
    if (validSelected.length < 2) return
    setLoading(true); setError('')
    try {
      const data = await readResponse<MultiComparison>(await fetch('/api/v1/compare/multi', {
        method:'POST', headers: { 'Content-Type': 'application/json' },
        body:JSON.stringify({ analysis_ids: validSelected }),
      }))
      setComparison(data); setMetricName(data.metrics[0]?.name || '')
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not compare selected quarters') }
    finally { setLoading(false) }
  }
  const metric = comparison?.metrics.find(m => m.name === metricName) || comparison?.metrics[0]
  const chart = comparison?.periods.map((p, i) => ({ period: p.fiscal_period, value: metric?.values[i] ?? null })) || []
  return <main className="fp-section fp-compare">
    <Reveal><span className="fp-eyebrow">05 / MULTI-QUARTER INTELLIGENCE</span><h1>Every quarter.<br/><em>One clear picture.</em></h1><p className="fp-lead">Choose two, three, five or more saved quarters. Compare matched reported values, preserve gaps and follow the evidence behind every number.</p></Reveal>
    <section className="fp-selection">
      <label>Choose company<select value={ticker || ''} onChange={e => { setCompany(e.target.value); setSelected([]); setComparison(null) }}>
        {companies.length ? companies.map(c => <option key={c}>{c}</option>) : <option value="">No companies saved</option>}
      </select></label>
      <span className="fp-eyebrow">SELECT AS MANY QUARTERS AS YOU NEED</span>
      <div className="fp-quarter-chips">{pool.map(item => <button type="button" key={item.analysis_id} aria-pressed={validSelected.includes(item.analysis_id)} className={'fp-quarter ' + (validSelected.includes(item.analysis_id) ? 'is-selected' : '')}
        onClick={() => { setComparison(null); setSelected(prev => prev.includes(item.analysis_id) ? prev.filter(id => id !== item.analysis_id) : [...prev, item.analysis_id]) }}>
        <Check size={14}/>{item.fiscal_period}</button>)}</div>
      <button className="fp-primary" type="button" disabled={validSelected.length < 2 || loading} onClick={() => void generate()}>
        {loading ? <LoaderCircle className="fp-spin" size={17}/> : <BarChart3 size={17}/>} Compare {validSelected.length} quarters <ArrowRight size={16}/></button>
      {error && <p className="fp-error">{error}</p>}
      {pool.length < 2 && <p className="fp-disclaimer">Save at least two different quarters for the same company to begin.</p>}
    </section>
    {comparison && <section className="fp-comparison-result">
      <Reveal><span className="fp-eyebrow">{comparison.ticker} / {comparison.periods.length} SELECTED PERIODS</span><h2>Trends, <em>not guesswork.</em></h2></Reveal>
      {metric ? <div className="fp-trend-shell">
        <label className="fp-trend-selector">Metric<select value={metric.name} onChange={e => setMetricName(e.target.value)}>{comparison.metrics.map(m => <option key={m.name + m.unit + (m.metric_variant || '')} value={m.name}>{m.name} · {m.metric_variant || 'reported'}</option>)}</select></label>
        <div className="fp-trend-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={chart} margin={{ top:20,right:26,left:0,bottom:20 }}>
          <CartesianGrid stroke="#38304e" strokeDasharray="3 8" vertical={false}/>
          <XAxis dataKey="period" tick={{ fill:'#A49CBF',fontSize:11 }} stroke="#A49CBF"/>
          <YAxis tick={{ fill:'#A49CBF',fontSize:11 }} stroke="#A49CBF" width={65} tickFormatter={v => formatCompact.format(v)}/>
          <Tooltip formatter={(value: number) => [numberValue(value,metric.unit,metric.currency),metric.name]} contentStyle={{background:'#17132A',border:'1px solid #514476',borderRadius:12}}/>
          <Line type="monotone" dataKey="value" stroke="#88F9C0" strokeWidth={3} connectNulls={false} dot={{r:5,fill:'#88F9C0'}}/>
        </LineChart></ResponsiveContainer></div>
        <div className="fp-trend-stats"><span>{metric.available_periods} / {comparison.periods.length} periods supported</span><strong>{metric.change_percent === null ? 'Trend unavailable' : marker(metric.change_percent) + ' across available selected periods'}</strong></div>
      </div> : <div className="fp-no-news">No reliable matched metrics. Review source evidence or reanalyze older saved reports.</div>}
      <div className="fp-matrix-scroll"><table className="fp-matrix"><thead><tr><th>Financial metric</th>{comparison.periods.map(p => <th key={p.analysis_id}>{p.fiscal_period}</th>)}</tr></thead><tbody>
        {comparison.metrics.map((m, i) => <tr key={i}><th>{m.name}<small>{m.metric_variant || 'Basis unspecified'}</small></th>{m.values.map((v, j) => <td key={j}>{numberValue(v,m.unit,m.currency)}{m.evidence[j] && <details className="fp-cell-evidence"><summary>Source</summary><p>{m.evidence[j]?.text}</p></details>}</td>)}</tr>)}
      </tbody></table></div>
      <Reveal className="fp-trend-narrative"><span className="fp-eyebrow">QUICK PATTERN READ / DETERMINISTIC</span><h3>At a <em>glance.</em></h3>
        {comparison.narrative.length ? comparison.narrative.map((line,i)=><p key={i}>{line}</p>) : <p>Not enough like-for-like values to describe a meaningful change.</p>}
        {comparison.warnings.map((w,i)=><small key={i}>{w}</small>)}
      </Reveal>
    </section>}
  </main>
}

function Library({ items, onOpen, onDelete }: {
  items: Saved[]; onOpen: (id: string) => Promise<void>; onDelete: (id: string) => Promise<void>
}) {
  const [filter, setFilter] = useState('')
  const [expanded, setExpanded] = useState('')
  const filtered = items.filter(item => (item.company_name + item.ticker + item.fiscal_period).toLowerCase().includes(filter.toLowerCase()))
  const groups = Array.from(new Set(filtered.map(item => item.ticker))).sort()
  return <main className="fp-section fp-library">
    <Reveal><span className="fp-eyebrow">06 / SAVED RESEARCH LIBRARY</span><h1>Companies first.<br/><em>History within.</em></h1><p className="fp-lead">Your saved analyses persist in SQLite across visits and are organized by company, fiscal year, then quarter.</p></Reveal>
    <input className="fp-library-search" value={filter} placeholder="Search companies, tickers or quarters…" aria-label="Search saved reports" onChange={e=>setFilter(e.target.value)}/>
    <div className="fp-company-groups">{groups.map(ticker => {
      const companyReports = filtered.filter(item => item.ticker === ticker)
      const years = Array.from(new Set(companyReports.map(r => {
        const match = r.fiscal_period.match(/20\d{2}/)
        return match ? match[0] : 'Other periods'
      }))).sort().reverse()
      const isOpen = expanded === ticker || (!expanded && groups.length === 1)
      return <section key={ticker} className={'fp-company-group ' + (isOpen ? 'is-open' : '')}>
        <button type="button" className="fp-company-head" aria-expanded={isOpen} onClick={() => setExpanded(isOpen ? '!' : ticker)}>
          <span className="fp-company-monogram">{ticker.slice(0,2)}</span>
          <span><strong>{companyReports[0].company_name}</strong><small>{ticker} · {companyReports.length} saved quarter{companyReports.length !== 1 ? 's' : ''}</small></span>
          <ChevronRight size={20}/>
        </button>
        {isOpen && <div className="fp-company-content">{years.map(year => <section key={year}><h3>FY {year}</h3>
          {companyReports.filter(r => (r.fiscal_period.match(/20\d{2}/)?.[0] || 'Other periods') === year)
            .sort((a,b)=>b.fiscal_period.localeCompare(a.fiscal_period,undefined,{numeric:true}))
            .map(report => <div className="fp-saved-quarter" key={report.analysis_id}>
            <FileText size={19}/><div><strong>{report.fiscal_period}</strong><p>{report.metric_count} extracted metrics · {report.news_count} sources · {dateLabel(report.announcement_date)}</p></div>
            <button type="button" className="fp-saved-open" onClick={() => void onOpen(report.analysis_id)}>Open <ArrowUpRight size={15}/></button>
            <button type="button" className="fp-saved-delete" title="Delete saved analysis" aria-label={'Delete '+report.fiscal_period} onClick={() => void onDelete(report.analysis_id)}><Trash2 size={17}/></button>
          </div>)}</section>)}</div>}
      </section>
    })}</div>
    {groups.length===0 && <div className="fp-no-news"><LibraryBig size={32}/><h2>Your archive begins here.</h2><p>Upload an earnings report in Studio; its analysis will appear in the appropriate company archive.</p></div>}
  </main>
}

export default function App() {
  const [page, setPage] = useState<Page>('studio')
  const [active, setActive] = useState<Analysis | null>(null)
  const [saved, setSaved] = useState<Saved[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [market, setMarket] = useState<MarketReading | null>(null)
  const [marketBusy, setMarketBusy] = useState(false)
  const [marketError, setMarketError] = useState('')
  function navigate(next: Page) { setPage(next); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  async function refreshSaved() {
    try { setSaved(await readResponse<Saved[]>(await fetch('/api/v1/analyses?limit=200'))) }
    catch { /* The editor continues to work even if the Library is unavailable. */ }
  }
  useEffect(() => {
    void refreshSaved()
    const id = window.localStorage.getItem('finpulse:last-analysis')
    if (!id || !/^[a-f0-9]{16}$/.test(id)) return
    fetch('/api/v1/analyses/' + id).then(response => readResponse<Analysis>(response)).then(setActive).catch(() => { window.localStorage.removeItem('finpulse:last-analysis') })
  }, [])
  useEffect(() => {
    if (page !== 'market' || !active) return
    let alive = true
    setMarket(null); setMarketError(''); setMarketBusy(true)
    fetch('/api/v1/market/interpret/' + active.analysis_id)
      .then(response => readResponse<MarketReading>(response))
      .then(data => { if (alive) setMarket(data) })
      .catch(e => { if (alive) setMarketError(e instanceof Error ? e.message : 'Market data could not be loaded') })
      .finally(() => { if (alive) setMarketBusy(false) })
    return () => { alive = false }
  }, [page, active?.analysis_id])
  async function analyze(input: AnalysisInput) {
    setBusy(true); setError('')
    try {
      const response = await fetch('/api/v1/analyze', {
        method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(input),
      })
      const data = await readResponse<Analysis>(response)
      setActive(data)
      window.localStorage.setItem('finpulse:last-analysis', data.analysis_id)
      await refreshSaved()
      navigate('earnings')
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not analyze the document') }
    finally { setBusy(false) }
  }
  async function openSaved(id: string) {
    try {
      const data = await readResponse<Analysis>(await fetch('/api/v1/analyses/' + id))
      setActive(data); window.localStorage.setItem('finpulse:last-analysis', id)
      navigate('earnings')
    } catch (e) { setError(e instanceof Error ? e.message : 'Saved report is unavailable') }
  }
  async function deleteSaved(id: string) {
    if (!window.confirm('Delete this saved analysis from the local Library?')) return
    try {
      const response = await fetch('/api/v1/analyses/' + id, {method:'DELETE'})
      if (!response.ok) throw new Error('Could not delete the report')
      if (active?.analysis_id === id) {
        setActive(null); window.localStorage.removeItem('finpulse:last-analysis')
      }
      await refreshSaved()
    } catch (e) { setError(e instanceof Error ? e.message : 'Delete failed') }
  }
  return <div className="fp-app">
    <header className="fp-header"><div className="fp-header-inner">
      <button className="fp-brand" onClick={() => navigate('studio')} aria-label="FinPulse studio">
        <span className="fp-brand-mark"><TrendingUp size={23} strokeWidth={2.7}/></span><span>finpulse<b>.</b></span>
      </button>
      <nav className="fp-navigation" aria-label="Primary navigation">{nav.map(item => <button type="button" key={item.id} aria-current={page === item.id ? 'page' : undefined}
        className={page === item.id ? 'is-active' : ''} onClick={() => navigate(item.id)}><small>{item.number}</small>{item.label}</button>)}</nav>
      <div className="fp-header-last">{active ? <span>{active.ticker} · {active.fiscal_period}</span> : <span>Manual research studio</span>}</div>
    </div></header>
    {page === 'studio' && <Studio onAnalyze={analyze} loading={busy} error={error}/>}
    {page === 'earnings' && (active ? <Earnings key={active.analysis_id} data={active}/> : <Empty title="An earnings story starts with a report." description="Upload a quarterly document or reopen an existing saved analysis." onNew={() => navigate('studio')}/>)}
    {page === 'market' && (active ? <Market report={active} result={market} loading={marketBusy} error={marketError}/> : <Empty title="Nothing to plot yet." description="Select a saved report with an announcement date to explore its historical price context." onNew={() => navigate('studio')}/>)}
    {page === 'coverage' && (active ? <Coverage key={active.analysis_id} data={active}/> : <Empty title="Every story needs a source." description="Add manually curated articles or source links when uploading an earnings report." onNew={() => navigate('studio')}/>)}
    {page === 'compare' && <Compare items={saved}/>}
    {page === 'library' && <Library items={saved} onOpen={openSaved} onDelete={deleteSaved}/>}
    {error && page === 'library' && <div className="fp-global-error" role="alert">{error}</div>}
    <footer className="fp-footer"><span>finpulse<span className="fp-accent">.</span></span><p>Source first. Signals second. Conclusions, with context.</p><small>Not investment advice · Historical prices may be incomplete</small></footer>
  </div>
}
