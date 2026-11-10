"""Typed API contracts. Unavailable financial facts remain explicitly unknown."""
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, model_validator, field_validator


class NewsSourceInput(BaseModel):
    """Either a URL to fetch, pasted article text, or both."""
    title: str | None = Field(default=None, max_length=240)
    outlet: str | None = Field(default=None, max_length=100)
    text: str | None = Field(default=None, max_length=100_000)
    url: HttpUrl | None = None
    published_at: datetime | None = None
    headline_only: bool = False

    @model_validator(mode='after')
    def require_article(self):
        if self.headline_only and self.url and self.title and len(self.title.strip()) >= 15:
            return self
        if not self.url and not (self.text and len(self.text.strip()) >= 50):
            raise ValueError('Provide an article URL or at least 50 characters of article text')
        if self.text and len(self.text.strip()) < 50:
            raise ValueError('Pasted article text must contain at least 50 characters')
        return self


class AnalyzeRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=120)
    ticker: str = Field(min_length=1, max_length=12, pattern=r'^[A-Za-z0-9.\-]+$')
    fiscal_period: str = Field(min_length=3, max_length=40)
    earnings_text: str = Field(min_length=80, max_length=350_000)
    announcement_date: date | None = None
    market_timing: Literal['before_open', 'after_close', 'unknown'] = 'unknown'
    news_sources: list[NewsSourceInput] = Field(default_factory=list, max_length=8)

    @field_validator('company_name', 'fiscal_period', 'earnings_text')
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Must not be blank')
        return value.strip()


class Evidence(BaseModel):
    source_id: str
    text: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)


class FinancialMetric(BaseModel):
    name: str
    raw_value: str
    normalized_value: float | None
    unit: str
    currency: str | None = None
    reporting_period: str
    comparison_basis: Literal['YoY', 'QoQ'] | None = None
    metric_variant: Literal['reported', 'adjusted'] | None = None
    extraction_status: Literal['extracted', 'needs_review']
    evidence: Evidence


class Highlight(BaseModel):
    text: str
    evidence: Evidence


class SourceAnalysis(BaseModel):
    source_id: str
    title: str
    outlet: str
    url: str | None
    published_at: datetime | None
    summary: list[Highlight]
    themes: list[str]
    sentiment_label: Literal['positive', 'negative', 'neutral'] | None = None
    sentiment_method: str | None = None
    input_origin: Literal['url', 'pasted_text', 'headline_only'] = 'pasted_text'
    extraction_status: Literal['ok', 'failed', 'metadata_only'] = 'ok'
    warning: str | None = None


class ThemeEvidence(BaseModel):
    source_id: str
    outlet: str
    evidence: Evidence


class ThemeComparison(BaseModel):
    theme: str
    relationship: Literal['shared', 'earnings_only', 'news_only']
    earnings_evidence: Evidence | None = None
    news_evidence: list[ThemeEvidence] = Field(default_factory=list)


class SocialPost(BaseModel):
    platform: Literal['Bluesky', 'X']
    author: str
    url: str
    text: str
    created_at: str
    likes: int = Field(default=0, ge=0)


class AnalyzeResponse(BaseModel):
    analysis_id: str
    company_name: str
    ticker: str
    fiscal_period: str
    announcement_date: date | None
    market_timing: str = 'unknown'
    analyzed_at: datetime
    summary: list[Highlight]
    metrics: list[FinancialMetric]
    earnings_themes: list[str]
    sources: list[SourceAnalysis]
    comparison: list[ThemeComparison]
    warnings: list[str]
    sentiment_model: str = 'rules-v1'
    data_origin: Literal['user_supplied_text', 'sec_filing'] = 'user_supplied_text'
    source_document_url: str | None = None
    source_document_type: str | None = None
    social_posts: list[SocialPost] = Field(default_factory=list)


class ArticleRequest(BaseModel):
    url: HttpUrl


class ArticleResponse(BaseModel):
    title: str | None = None
    outlet: str | None = None
    text: str
    url: str
    published_at: datetime | None = None


class StockPoint(BaseModel):
    date: date
    close: float
    volume: int


class StockContextResponse(BaseModel):
    ticker: str
    currency: str | None = None
    price_basis: str = 'Unadjusted daily close'
    points: list[StockPoint]
    earnings_date: date
    market_timing: str = 'unknown'
    first_session_on_or_after_date: date | None = None
    previous_session_date: date | None = None
    session_close_change_percent: float | None = None
    warning: str | None = None
