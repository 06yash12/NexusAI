from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Any

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""

class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str
    created_at: datetime

class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    filename: str
    file_type: str
    file_size: int = 0
    table_name: str | None = None
    row_count: int = 0
    status: str
    created_at: datetime | None = None

class DatasetPreviewOut(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int
    table_name: str

class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    mode: Literal["auto", "structured", "documents", "hybrid"] = "auto"
    selected_dataset_ids: list[str] | None = None

class SourceCitation(BaseModel):
    filename: str
    page_number: int | None = None
    chunk_index: int = 0
    score: float = 0.0
    excerpt: str

class ChartSuggestion(BaseModel):
    type: Literal["bar", "line", "pie", "area"] = "bar"
    x_key: str
    y_keys: list[str]
    title: str = ""

class ChatResponse(BaseModel):
    answer: str
    mode: str
    sql: str | None = None
    columns: list[str] = []
    rows: list[dict[str, Any]] = []
    sources: list[SourceCitation] = []
    warnings: list[str] = []
    chart_suggestion: ChartSuggestion | None = None
    execution_time_ms: int = 0
    analysis_steps: list[dict[str, Any]] = []

class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    question: str
    answer: str
    mode: str
    sql_query: str | None = None
    execution_time_ms: int = 0
    sources: list[SourceCitation] = []
    created_at: datetime

class KPICard(BaseModel):
    id: str
    label: str
    value: str | int | float
    formatted: str = ""
    subtext: str = ""
    is_available: bool = True

class DashboardOut(BaseModel):
    dataset_count: int
    structured_dataset_count: int
    document_count: int
    total_rows: int
    tables: dict[str, list[dict[str, str]]]
    domain: str = "general"
    domain_label: str = "General Analytics"
    kpis: list[KPICard]
    charts: list[dict[str, Any]] = []
    monthly_sales: list[dict[str, Any]] = []
    yearly_comparison: list[dict[str, Any]] = []
    regional_sales: list[dict[str, Any]] = []
    category_sales: list[dict[str, Any]] = []
    top_products: list[dict[str, Any]] = []
    available_years: list[int] = []
    selected_year: int | None = None
    currency_symbol: str = "$"
    column_mapping: dict[str, str | None] = {}
    unavailable_explanations: dict[str, str] = {}
    data_freshness: str = "No data"
    source_datasets: list[str] = []
    available_dimensions: dict[str, list[str]] = {}

class InsightItem(BaseModel):
    type: Literal["trend", "anomaly", "underperformance", "opportunity"]
    title: str
    description: str
    supporting_metric: str
    importance: Literal["high", "medium", "low"] = "medium"

class RecommendationItem(BaseModel):
    recommendation: str
    rationale: str
    expected_impact: str
    supporting_data: str

class InsightsOut(BaseModel):
    project_id: str
    generated_at: str
    insights: list[InsightItem] = []
    recommendations: list[RecommendationItem] = []
    summary: str = ""
