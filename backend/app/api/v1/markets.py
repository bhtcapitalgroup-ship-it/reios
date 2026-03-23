from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.market import MarketMetrics, MarketForecast, NeighborhoodScore
from app.models.user import User
from app.schemas.market import (
    MarketMetricsResponse,
    MarketForecastResponse,
    NeighborhoodScoreResponse,
    MarketSearchRequest,
    MarketRankingResponse,
    MarketHeatmapEntry,
)

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("/{geo_id}/metrics", response_model=list[MarketMetricsResponse])
async def get_market_metrics(
    geo_id: str,
    months: int = Query(12, ge=1, le=120),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MarketMetrics)
        .where(MarketMetrics.geo_id == geo_id)
        .order_by(desc(MarketMetrics.month))
        .limit(months)
    )
    return result.scalars().all()


@router.get("/{geo_id}/forecast", response_model=list[MarketForecastResponse])
async def get_market_forecast(
    geo_id: str,
    horizon: int = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MarketForecast)
        .where(MarketForecast.geo_id == geo_id, MarketForecast.horizon_months <= horizon)
        .order_by(MarketForecast.horizon_months)
    )
    return result.scalars().all()


@router.get("/{geo_id}/score", response_model=NeighborhoodScoreResponse)
async def get_neighborhood_score(
    geo_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(NeighborhoodScore)
        .where(NeighborhoodScore.geo_id == geo_id)
        .order_by(desc(NeighborhoodScore.computed_at))
        .limit(1)
    )
    score = result.scalar_one_or_none()
    if not score:
        return NeighborhoodScoreResponse(
            geo_id=geo_id, geo_type="zip", overall_grade=None,
            overall_score=None, scores=None, computed_at=None,
        )
    return score


@router.post("/search", response_model=list[MarketRankingResponse])
async def search_markets(
    data: MarketSearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Build query with filters
    query = (
        select(MarketMetrics, NeighborhoodScore)
        .outerjoin(
            NeighborhoodScore,
            MarketMetrics.geo_id == NeighborhoodScore.geo_id,
        )
        .where(MarketMetrics.geo_type == "zip")
    )

    if data.states:
        # ZIP codes are 5 chars, no direct state mapping in metrics
        # This would need a zip-to-state lookup in production
        pass

    if data.min_population:
        query = query.where(MarketMetrics.population >= data.min_population)
    if data.max_median_price:
        query = query.where(MarketMetrics.median_sold_price <= data.max_median_price)
    if data.min_rent_yield:
        query = query.where(MarketMetrics.rent_yield >= data.min_rent_yield)
    if data.min_appreciation:
        query = query.where(MarketMetrics.yoy_price_change >= data.min_appreciation)
    if data.max_crime_index:
        query = query.where(MarketMetrics.crime_index <= data.max_crime_index)
    if data.min_school_rating:
        query = query.where(MarketMetrics.school_rating >= data.min_school_rating)

    # Get latest month per geo_id
    query = query.order_by(desc(MarketMetrics.month)).limit(data.limit)

    result = await db.execute(query)
    rows = result.all()

    rankings = []
    for i, row in enumerate(rows):
        metrics = row[0]
        neighborhood = row[1]
        rankings.append(MarketRankingResponse(
            rank=i + 1,
            geo_id=metrics.geo_id,
            geo_type=metrics.geo_type,
            name=f"ZIP {metrics.geo_id}",
            overall_score=float(neighborhood.overall_score) if neighborhood and neighborhood.overall_score else 0,
            metrics=MarketMetricsResponse.model_validate(metrics),
            neighborhood=NeighborhoodScoreResponse.model_validate(neighborhood) if neighborhood else None,
            forecast=None,
        ))

    return rankings


@router.get("/heatmap/{metric}", response_model=list[MarketHeatmapEntry])
async def get_heatmap(
    metric: str = "rent_yield",
    state: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get heatmap data for a given metric (rent_yield, yoy_price_change, etc.)."""
    # In production, this would join with a geo table that has lat/lng per zip
    # For now, return from market_metrics
    query = (
        select(MarketMetrics)
        .where(MarketMetrics.geo_type == "zip")
        .order_by(desc(MarketMetrics.month))
        .limit(limit)
    )
    result = await db.execute(query)
    metrics = result.scalars().all()

    entries = []
    for m in metrics:
        value = getattr(m, metric, None)
        if value is not None:
            entries.append(MarketHeatmapEntry(
                geo_id=m.geo_id,
                latitude=0.0,  # Would come from geo lookup
                longitude=0.0,
                score=float(value),
                label=f"ZIP {m.geo_id}",
                metrics={
                    "median_price": float(m.median_sold_price) if m.median_sold_price else None,
                    "median_rent": float(m.median_rent) if m.median_rent else None,
                    "rent_yield": float(m.rent_yield) if m.rent_yield else None,
                },
            ))
    return entries
