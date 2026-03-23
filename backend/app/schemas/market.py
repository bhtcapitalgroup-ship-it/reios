from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MarketMetricsResponse(BaseModel):
    geo_id: str
    geo_type: str
    month: date
    median_list_price: float | None
    median_sold_price: float | None
    median_price_per_sqft: float | None
    median_dom: int | None
    active_inventory: int | None
    absorption_rate: float | None
    median_rent: float | None
    rent_yield: float | None
    yoy_price_change: float | None
    yoy_rent_change: float | None
    population: int | None
    population_growth: float | None
    median_income: float | None
    unemployment_rate: float | None
    crime_index: float | None
    school_rating: float | None

    model_config = {"from_attributes": True}


class MarketForecastResponse(BaseModel):
    geo_id: str
    metric: str
    horizon_months: int
    p10: float | None
    p50: float | None
    p90: float | None
    model_version: str | None
    generated_at: datetime

    model_config = {"from_attributes": True}


class NeighborhoodScoreResponse(BaseModel):
    geo_id: str
    geo_type: str
    overall_grade: str | None
    overall_score: float | None
    scores: dict | None
    computed_at: datetime

    model_config = {"from_attributes": True}


class MarketHeatmapEntry(BaseModel):
    geo_id: str
    latitude: float
    longitude: float
    score: float
    label: str
    metrics: dict


class MarketSearchRequest(BaseModel):
    states: list[str] | None = None
    min_population: int | None = None
    max_median_price: float | None = None
    min_rent_yield: float | None = None
    min_appreciation: float | None = None
    max_crime_index: float | None = None
    min_school_rating: float | None = None
    sort_by: str = "overall_score"
    limit: int = Field(50, ge=1, le=200)


class MarketRankingResponse(BaseModel):
    rank: int
    geo_id: str
    geo_type: str
    name: str
    overall_score: float
    metrics: MarketMetricsResponse
    neighborhood: NeighborhoodScoreResponse | None
    forecast: MarketForecastResponse | None
