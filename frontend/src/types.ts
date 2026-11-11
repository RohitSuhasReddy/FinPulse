export interface Evidence { source_id: string; text: string; start_offset: number; end_offset: number; source_url?: string | null }
export interface Highlight { text: string; evidence: Evidence }
export interface FinancialMetric {
  name: string; raw_value: string; normalized_value: number | null; unit: string;
  currency: string | null; reporting_period: string; comparison_basis: 'YoY' | 'QoQ' | null;
  metric_variant: 'reported' | 'adjusted' | null; extraction_status: 'extracted' | 'needs_review'; evidence: Evidence;
}
export interface ReportFinding { category: 'drivers' | 'profitability' | 'outlook' | 'risks' | 'operations'; heading: string; body: string; evidence: Evidence[] }
export interface ReportBrief { overview: string; overview_evidence: Evidence[]; findings: ReportFinding[]; method: string }
export interface SourceAnalysis {
  source_id: string; title: string; outlet: string; url: string | null; published_at: string | null;
  summary: Highlight[]; themes: string[]; sentiment_label: 'positive' | 'negative' | 'neutral' | null;
  sentiment_method: string | null; input_origin: 'url' | 'pasted_text' | 'headline_only';
  extraction_status: 'ok' | 'failed' | 'metadata_only'; warning: string | null;
}
export interface ThemeComparison {
  theme: string; relationship: 'shared' | 'earnings_only' | 'news_only';
  earnings_evidence: Evidence | null;
  news_evidence: { source_id: string; outlet: string; evidence: Evidence }[];
}
export interface SocialPost {
  platform: 'Bluesky' | 'X'; author: string; url: string;
  text: string; created_at: string; likes: number;
}
export interface Analysis {
  analysis_id: string; company_name: string; ticker: string; fiscal_period: string;
  announcement_date: string | null; market_timing: 'before_open' | 'after_close' | 'unknown';
  analyzed_at: string; summary: Highlight[]; report_brief?: ReportBrief | null; metrics: FinancialMetric[];
  earnings_themes: string[]; sources: SourceAnalysis[];
  comparison: ThemeComparison[]; warnings: string[]; sentiment_model: string;
  data_origin: 'user_supplied_text' | 'sec_filing';
  source_document_url?: string | null; source_document_type?: string | null;
  social_posts?: SocialPost[];
  extraction_version?: number;
}
export interface NewsInput { title?: string; outlet?: string; text?: string; url?: string; headline_only?: boolean }
export interface AnalysisInput {
  company_name: string; ticker: string; fiscal_period: string; announcement_date?: string | null;
  market_timing?: 'before_open' | 'after_close' | 'unknown';
  earnings_text: string; news_sources: NewsInput[];
}
export interface StockPoint { date: string; close: number; volume: number }
export interface StockContext {
  ticker: string; points: StockPoint[]; earnings_date: string | null; market_timing: string;
  first_session_on_or_after_date: string | null; previous_session_date: string | null;
  session_close_change_percent: number | null; price_basis: string; currency: string | null; warning: string | null;
}
