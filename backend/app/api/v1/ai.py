from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.models.user import User
from app.ai.models.deal_scorer import DealScorerHeuristic
from app.ai.models.avm import AVMHeuristic
from app.ai.models.rent_predictor import RentPredictorHeuristic
from app.ai.models.market_predictor import MarketPredictorHeuristic

router = APIRouter(prefix="/ai", tags=["ai"])

# Singleton model instances
deal_scorer = DealScorerHeuristic()
avm = AVMHeuristic()
rent_predictor = RentPredictorHeuristic()
market_predictor = MarketPredictorHeuristic()


class ScoreDealRequest(BaseModel):
    cap_rate: float = 0.0
    cash_on_cash_return: float = 0.0
    dscr: float = 0.0
    grm: float = 0.0
    price_per_sqft: float = 0.0
    noi: float = 0.0
    monthly_cash_flow: float = 0.0
    break_even_ratio: float = 0.0
    crime_score: float = 50.0
    school_rating: float = 5.0
    population_growth: float = 0.01
    job_growth: float = 0.01
    rent_growth_yoy: float = 0.03
    price_growth_yoy: float = 0.03


class AVMRequest(BaseModel):
    subject: dict
    comps: list[dict]


class RentEstimateRequest(BaseModel):
    sqft: int = 1200
    bedrooms: int = 3
    bathrooms: float = 2.0
    property_type: str = "sfr"
    year_built: int = 2000
    school_rating: float = 5.0
    crime_score: float = 50.0
    median_market_rent: float | None = None
    month: int = 6


class MarketForecastRequest(BaseModel):
    current_median_price: float
    current_median_rent: float
    yoy_price_change: float = 0.03
    yoy_rent_change: float = 0.03
    population_growth: float = 0.01
    job_growth: float = 0.01
    months_supply: float = 4.0
    unemployment_rate: float = 0.04
    horizon_months: int = 12


@router.post("/score-deal")
async def score_deal(data: ScoreDealRequest, user: User = Depends(get_current_user)):
    result = deal_scorer.predict(data.model_dump())
    return {
        "score": result.prediction["score"],
        "breakdown": result.prediction["breakdown"],
        "confidence": result.confidence,
        "model_version": result.model_version,
        "latency_ms": round(result.latency_ms, 2),
    }


@router.post("/valuation")
async def estimate_value(data: AVMRequest, user: User = Depends(get_current_user)):
    result = avm.predict(data.model_dump())
    return {
        "estimated_value": result.prediction["estimated_value"],
        "confidence_interval": result.prediction["confidence_interval"],
        "comps_used": result.prediction["comps_used"],
        "comps": result.prediction["comps"],
        "confidence": result.confidence,
        "model_version": result.model_version,
    }


@router.post("/rent-estimate")
async def estimate_rent(data: RentEstimateRequest, user: User = Depends(get_current_user)):
    result = rent_predictor.predict(data.model_dump())
    return {
        "estimated_rent": result.prediction["estimated_rent"],
        "rent_range": result.prediction["rent_range"],
        "pricing_tiers": result.prediction["pricing_tiers"],
        "factors": result.prediction["factors"],
        "confidence": result.confidence,
        "model_version": result.model_version,
    }


@router.post("/market-forecast")
async def forecast_market(data: MarketForecastRequest, user: User = Depends(get_current_user)):
    result = market_predictor.predict(data.model_dump())
    return {
        "summary": result.prediction["summary"],
        "price_forecast": result.prediction["price_forecast"],
        "rent_forecast": result.prediction["rent_forecast"],
        "drivers": result.prediction["drivers"],
        "confidence": result.confidence,
        "model_version": result.model_version,
    }


@router.get("/models/health")
async def models_health(user: User = Depends(get_current_user)):
    return {
        "models": {
            "deal_scorer": {
                "status": "healthy" if deal_scorer.health_check() else "unavailable",
                "version": deal_scorer.get_version(),
            },
            "avm": {
                "status": "healthy" if avm.health_check() else "unavailable",
                "version": avm.get_version(),
            },
            "rent_predictor": {
                "status": "healthy" if rent_predictor.health_check() else "unavailable",
                "version": rent_predictor.get_version(),
            },
            "market_predictor": {
                "status": "healthy" if market_predictor.health_check() else "unavailable",
                "version": market_predictor.get_version(),
            },
        }
    }
