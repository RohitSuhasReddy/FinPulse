import { useState } from 'react'
import { ArrowRight, FileSearch, LoaderCircle, Newspaper, WandSparkles } from 'lucide-react'
import type { NewsInput } from './types'

type Filing = {
  ticker: string; company_name: string; form: string; accession: string;
  period_end: string; filed_at: string; document: string
}
type FilingImport = {
  text: string; company_name: string; ticker: string; fiscal_period: string;
  notice: string; form: string; period_end: string
}
type Discovered = {
  title: string; url: string; outlet: string; feed_published_at: string;
  body_available: boolean; origin: string
}

type Props = {
  ticker: string; company: string; date: string | null | undefined;
  onFiling: (f: FilingImport) => void; onNews: (items: NewsInput[]) => void;
}

async function readJson<T>(response: Response): Promise<T> {
  const body = await response.json()
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Request failed')
  return body as T
}

export default function ResearchTools({ ticker, company, date, onFiling, onNews }: Props) {
  const [filings, setFilings] = useState<Filing[]>([])
  const [articles, setArticles] = useState<Discovered[]>([])
  const [mode, setMode] = useState<'filings' | 'news' | null>(null)
  const [busy, setBusy] = useState<'filings' | 'news' | 'import' | null>(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function findFilings() {
    setError(''); setMessage(''); setBusy('filings'); setMode('filings')
    try {
      const data = await readJson<{ filings: Filing[]; notice: string }>(await fetch(`/api/v1/filings/${encodeURIComponent(ticker.trim())}`))
      setFilings(data.filings)
      setMessage(data.notice)
    } catch (err) { setError(err instanceof Error ? err.message : 'SEC filings unavailable') }
    finally { setBusy(null) }
  }

  async function loadFiling(item: Filing) {
    setBusy('import'); setError('')
    try {
      const data = await readJson<FilingImport>(await fetch('/api/v1/filings/import', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: item.ticker, accession: item.accession }),
      }))
      onFiling(data)
      setMessage(data.notice)
    } catch (err) { setError(err instanceof Error ? err.message : 'Filing import unavailable') }
    finally { setBusy(null) }
  }

  async function findNews() {
    setError(''); setMessage(''); setBusy('news'); setMode('news')
    try {
      const query = new URLSearchParams({ company: company.trim(), ticker: ticker.trim() })
      if (date) query.set('date', date)
      const data = await readJson<{ items: Discovered[]; notice: string }>(await fetch(`/api/v1/news/discover?${query}`))
      setArticles(data.items)
      setMessage(data.notice)
    } catch (err) { setError(err instanceof Error ? err.message : 'News discovery unavailable') }
    finally { setBusy(null) }
  }

  function selectNews() {
    const picked: Discovered[] = []
    const outlets = new Set<string>()
    for (const item of articles) {
      if (!outlets.has(item.outlet.toLowerCase())) { picked.push(item); outlets.add(item.outlet.toLowerCase()) }
      if (picked.length === 3) break
    }
    if (picked.length === 0) picked.push(...articles.slice(0, 3))
    onNews(picked.map(a => ({ title: a.title, outlet: a.outlet, url: a.url, headline_only: true })))
    setMessage(`${picked.length} source${picked.length !== 1 ? 's' : ''} added. FinPulse will try to read article bodies; inaccessible links remain clearly marked headline-only.`)
  }

  return <section className="research-tools" aria-label="Automated research inputs">
    <div className="research-tools-head"><span className="eyebrow"><WandSparkles size={14}/> LESS TYPING, MORE ANALYSIS</span><p>Find public filings and news coverage, then import directly.</p></div>
    <div className="research-tool-buttons">
      <button type="button" className="research-tool-action" disabled={!ticker.trim() || busy !== null} onClick={() => void findFilings()}>
        {busy === 'filings' ? <LoaderCircle className="spin" size={18}/> : <FileSearch size={18}/>}<span>Find SEC filings<small>10-Q / 10-K</small></span><ArrowRight size={16}/>
      </button>
      <button type="button" className="research-tool-action" disabled={company.trim().length < 2 || busy !== null} onClick={() => void findNews()}>
        {busy === 'news' ? <LoaderCircle className="spin" size={18}/> : <Newspaper size={18}/>}<span>Discover coverage<small>News headlines & links</small></span><ArrowRight size={16}/>
      </button>
    </div>
    {mode === 'filings' && filings.length > 0 && <div className="research-results">
      <div className="research-results-label">OFFICIAL SEC FILINGS · CHOOSE ONE</div>
      {filings.slice(0, 12).map(f => <button type="button" className="research-item" key={f.accession} disabled={busy !== null} onClick={() => void loadFiling(f)}>
        <span><b>{f.form}</b> · Period ended {f.period_end}<small>Filed {f.filed_at}</small></span>{busy === 'import' ? <LoaderCircle size={15} className="spin"/> : <ArrowRight size={16}/>}</button>)}
    </div>}
    {mode === 'news' && <div className="research-results">
      <div className="research-results-label">NEWS DISCOVERY · METADATA, NOT FULL ARTICLES</div>
      {articles.length === 0 && !busy && <p className="research-message">No matching articles returned for these search terms and dates.</p>}
      {articles.slice(0, 8).map((a, i) => <div className="research-news-item" key={a.url + i}>
        <span>{a.outlet}<small>{a.title}</small></span><a href={a.url} target="_blank" rel="noopener noreferrer" aria-label={`Open ${a.title}`}>↗</a>
      </div>)}
      {articles.length > 0 && <button className="research-add" type="button" onClick={selectNews}>Auto-add up to 3 different outlets <ArrowRight size={15}/></button>}
    </div>}
    {error && <p className="research-error" role="alert">{error}</p>}
    {message && <p className="research-message">{message}</p>}
    <p className="research-hint">Your own PDFs can still be imported below. News-feed titles aren't treated as verified article evidence.</p>
  </section>
}
