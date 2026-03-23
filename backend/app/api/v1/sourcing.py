"""Off-market deal sourcing API endpoints."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.property import Property
from app.models.market import MarketMetrics, NeighborhoodScore
from app.models.user import User
from app.services.deal_sourcer import (
    DistressSignal,
    OffMarketLead,
    evaluate_lead,
    rank_leads,
)

router = APIRouter(prefix="/sourcing", tags=["sourcing"])


class LeadResponse(BaseModel):
    property_id: str
    address: str
    city: str
    state: str
    estimated_value: float
    motivation_score: float
    estimated_discount: float
    potential_deal_price: float
    source: str
    status: str
    signals: list[dict]
    property_details: dict | None = None


class LeadEvaluateRequest(BaseModel):
    property_id: str | None = None
    address: str
    city: str
    state: str
    estimated_value: float
    signals: list[dict]  # [{"type": "pre_foreclosure", "severity": 0.9, "details": {...}}]
    equity_pct: float = 0.5
    ownership_years: int = 10


@router.get("/leads", response_model=list[LeadResponse])
async def get_sourced_leads(
    min_motivation: float = Query(0, ge=0, le=100),
    signal_type: str | None = None,
    state: str | None = None,
    city: str | None = None,
    sort_by: str = "motivation",
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get AI-sourced off-market leads."""
    # Query properties with off-market features
    query = select(Property).where(
        Property.features.isnot(None)
    )

    result = await db.execute(query)
    properties = result.scalars().all()

    leads = []
    for prop in properties:
        features = prop.features or {}
        if not features.get("off_market"):
            continue

        sig_type = features.get("signal_type", "unknown")
        motivation = features.get("motivation_score", 0)
        discount = features.get("estimated_discount", 0)
        est_value = features.get("estimated_value", 0)

        # Apply filters
        if motivation < min_motivation:
            continue
        if signal_type and sig_type != signal_type:
            continue
        if state and prop.state != state:
            continue
        if city and prop.city.lower() != city.lower():
            continue

        lead = LeadResponse(
            property_id=str(prop.id),
            address=prop.address,
            city=prop.city,
            state=prop.state,
            estimated_value=est_value,
            motivation_score=motivation,
            estimated_discount=discount,
            potential_deal_price=round(est_value * (1 - discount), 2),
            source=sig_type,
            status="new",
            signals=[{
                "type": sig_type,
                "severity": motivation / 100,
                "details": {},
            }],
            property_details={
                "bedrooms": prop.bedrooms,
                "bathrooms": float(prop.bathrooms) if prop.bathrooms else None,
                "sqft": prop.sqft,
                "year_built": prop.year_built,
                "property_type": prop.property_type,
            },
        )
        leads.append(lead)

    # Sort
    if sort_by == "motivation":
        leads.sort(key=lambda x: x.motivation_score, reverse=True)
    elif sort_by == "discount":
        leads.sort(key=lambda x: x.estimated_discount, reverse=True)
    elif sort_by == "price":
        leads.sort(key=lambda x: x.potential_deal_price)

    return leads[:limit]


@router.post("/evaluate", response_model=LeadResponse)
async def evaluate_lead_endpoint(
    data: LeadEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Evaluate a potential off-market lead with AI scoring."""
    lead = evaluate_lead(
        property_data={
            "id": data.property_id or "",
            "address": data.address,
            "city": data.city,
            "state": data.state,
            "estimated_value": data.estimated_value,
            "equity_pct": data.equity_pct,
            "ownership_years": data.ownership_years,
        },
        signals=data.signals,
    )

    return LeadResponse(
        property_id=lead.property_id,
        address=lead.address,
        city=lead.city,
        state=lead.state,
        estimated_value=lead.estimated_value,
        motivation_score=lead.motivation_score,
        estimated_discount=lead.estimated_discount,
        potential_deal_price=lead.potential_deal_price,
        source=lead.source,
        status=lead.status,
        signals=[{
            "type": s.signal_type,
            "severity": s.severity,
            "details": s.details,
        } for s in lead.signals],
    )


@router.get("/stats")
async def sourcing_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get sourcing pipeline statistics."""
    result = await db.execute(select(Property).where(Property.features.isnot(None)))
    properties = result.scalars().all()

    total = 0
    by_type = {}
    by_state = {}
    high_motivation = 0
    total_potential_savings = 0

    for prop in properties:
        features = prop.features or {}
        if not features.get("off_market"):
            continue
        total += 1

        sig = features.get("signal_type", "unknown")
        by_type[sig] = by_type.get(sig, 0) + 1
        by_state[prop.state] = by_state.get(prop.state, 0) + 1

        if features.get("motivation_score", 0) >= 75:
            high_motivation += 1

        est_val = features.get("estimated_value", 0)
        discount = features.get("estimated_discount", 0)
        total_potential_savings += est_val * discount

    return {
        "total_leads": total,
        "high_motivation_leads": high_motivation,
        "by_signal_type": by_type,
        "by_state": by_state,
        "total_potential_savings": round(total_potential_savings, 2),
        "avg_discount": round(total_potential_savings / max(1, sum(
            (p.features or {}).get("estimated_value", 0)
            for p in properties if (p.features or {}).get("off_market")
        )) * 100, 1),
    }
