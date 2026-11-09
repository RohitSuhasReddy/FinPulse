export interface Evidence { source_id: string; text: string; start_offset: number; end_offset: number }
export interface Highlight { text: string; evidence: Evidence }
export interface FinancialMetric {
  name: string; raw_value: string; normalized_value: number | null; unit: string;
  currency: string | null; reporting_period: string; comparison_basis: 'YoY' | 'QoQ' | null;
  metric_variant: 'reported' | 'adjusted' | null; extraction_status: 'extracted' | 'needs_review'; evidence: Evidence;
}
export interface SourceAnalysis {
  source_id: string; title: string; outlet: string; url: string | null; published_at: string | null;
  summary: Highlight[]; themes: string[]; sentiment_label: 'positive' | 'negative' | 'neutral' | null;
  sentiment_method: string | null; input_origin: 'url' | 'pasted_text';
  extraction_status: 'ok' | 'failed'; warning: string | null;
}
export interface ThemeComparison {
  theme: string; relationship: 'shared' | 'earnings_only' | 'news_only';
  earnings_evidence: Evidence | null;
  news_evidence: { source_id: string; outlet: string; evidence: Evidence }[];
}
export interface Analysis {
  analysis_id: string; company_name: string; ticker: string; fiscal_period: string;
  announcement_date: string | null; market_timing: 'before_open' | 'after_close' | 'unknown';
  analyzed_at: string; summary: Highlight[]; metrics: FinancialMetric[];
  earnings_themes: string[]; sources: SourceAnalysis[];
  comparison: ThemeComparison[]; warnings: string[]; sentiment_model: string;
  data_origin: 'user_supplied_text';
}
export interface NewsInput { title?: string; outlet?: string; text?: string; url?: string }
export interface AnalysisInput {
  company_name: string; ticker: string; fiscal_period: string; announcement_date?: string | null;
  market_timing?: 'before_open' | 'after_close' | 'unknown';
  earnings_text: string; news_sources: NewsInput[];
}
export interface StockPoint { date: string; close: number; volume: number }
export interface StockContext {
  ticker: string; points: StockPoint[]; earnings_date: string; market_timing: string;
  first_session_on_or_after_date: string | null; previous_session_date: string | null;
  session_close_change_percent: number | null; price_basis: string; currency: string | null; warning: string | null;
}
