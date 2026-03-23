from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.deal import Deal, DealAnalysis, ProFormaProjection
from app.models.property import Property
from app.models.user import User
from app.schemas.deal import (
    AnalysisResults,
    DealAssumptions,
    DealCompareRequest,
    DealCompareResponse,
    DealCreate,
    DealResponse,
    DealAnalysisResponse,
    ProFormaYear,
)
from app.services.deal_analyzer import (
    DealInputs,
    analyze_deal,
    generate_pro_forma,
    score_deal_heuristic,
)

router = APIRouter(prefix="/deals", tags=["deals"])


def _build_analysis_response(analysis) -> DealAnalysisResponse:
    return DealAnalysisResponse(
        id=analysis.id,
        deal_id=analysis.deal_id,
        version=analysis.version,
        assumptions=analysis.assumptions,
        results=AnalysisResults(**analysis.results),
        score=float(analysis.score) if analysis.score else None,
        score_breakdown=analysis.score_breakdown,
        created_at=analysis.created_at,
    )


def _build_deal_response(deal) -> DealResponse:
    resp = DealResponse.model_validate(deal)
    if deal.analyses:
        resp.latest_analysis = _build_analysis_response(deal.analyses[0])
    return resp


@router.post("", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
async def create_deal(
    data: DealCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    property_id = data.property_id
    if not property_id and data.address:
        prop = Property(
            address=data.address,
            city=data.city or "",
            state=data.state or "",
            zip=data.zip_code or "",
            property_type=data.property_type,
            bedrooms=data.bedrooms,
            bathrooms=data.bathrooms,
            sqft=data.sqft,
            year_built=data.year_built,
        )
        db.add(prop)
        await db.flush()
        property_id = prop.id

    deal = Deal(
        user_id=user.id,
        property_id=property_id,
        source=data.source,
        purchase_price=data.purchase_price,
        notes=data.notes,
        tags=data.tags,
    )
    db.add(deal)
    await db.flush()
    await db.refresh(deal)
    return deal


@router.get("", response_model=list[DealResponse])
async def list_deals(
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        select(Deal)
        .options(selectinload(Deal.analyses), selectinload(Deal.property))
        .where(Deal.user_id == user.id)
        .order_by(Deal.created_at.desc())
    )
    if status_filter:
        query = query.where(Deal.status == status_filter)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    deals = result.scalars().all()
    return [_build_deal_response(d) for d in deals]


@router.get("/count")
async def count_deals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(func.count(Deal.id)).where(Deal.user_id == user.id))
    return {"count": result.scalar()}


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal)
        .options(selectinload(Deal.analyses), selectinload(Deal.property))
        .where(Deal.id == deal_id, Deal.user_id == user.id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _build_deal_response(deal)


class DealUpdate(BaseModel):
    purchase_price: float | None = None
    notes: str | None = None
    tags: list[str] | None = None
    status: str | None = None


@router.patch("/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: str,
    data: DealUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal).options(selectinload(Deal.analyses))
        .where(Deal.id == deal_id, Deal.user_id == user.id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    if data.purchase_price is not None:
        deal.purchase_price = data.purchase_price
    if data.notes is not None:
        deal.notes = data.notes
    if data.tags is not None:
        deal.tags = data.tags
    if data.status is not None:
        deal.status = data.status

    await db.flush()
    await db.refresh(deal)
    return _build_deal_response(deal)


@router.delete("/{deal_id}", status_code=204)
async def delete_deal(
    deal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Deal).where(Deal.id == deal_id, Deal.user_id == user.id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    await db.delete(deal)


@router.post("/{deal_id}/analyze", response_model=DealAnalysisResponse)
async def analyze(
    deal_id: str,
    assumptions: DealAssumptions | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal).options(selectinload(Deal.analyses))
        .where(Deal.id == deal_id, Deal.user_id == user.id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    if not assumptions:
        assumptions = DealAssumptions()
    if assumptions.monthly_rent <= 0:
        raise HTTPException(status_code=400, detail="monthly_rent must be > 0")

    inputs = DealInputs(
        purchase_price=float(deal.purchase_price),
        monthly_rent=assumptions.monthly_rent,
        other_income=assumptions.other_income,
        vacancy_rate=assumptions.vacancy_rate,
        management_fee_pct=assumptions.management_fee_pct,
        maintenance_pct=assumptions.maintenance_pct,
        capex_reserve_pct=assumptions.capex_reserve_pct,
        property_tax_annual=assumptions.property_tax_annual,
        insurance_annual=assumptions.insurance_annual,
        hoa_monthly=assumptions.hoa_monthly,
        utilities_monthly=assumptions.utilities_monthly,
        down_payment_pct=assumptions.down_payment_pct,
        interest_rate=assumptions.interest_rate,
        loan_term_years=assumptions.loan_term_years,
        closing_cost_pct=assumptions.closing_cost_pct,
        annual_rent_growth=assumptions.annual_rent_growth,
        annual_appreciation=assumptions.annual_appreciation,
        annual_expense_growth=assumptions.annual_expense_growth,
        holding_period_years=assumptions.holding_period_years,
    )

    if deal.property_id:
        prop_result = await db.execute(select(Property).where(Property.id == deal.property_id))
        prop = prop_result.scalar_one_or_none()
        if prop and prop.sqft:
            inputs.sqft = prop.sqft

    analysis_result = analyze_deal(inputs)
    score, score_breakdown = score_deal_heuristic(analysis_result, inputs)

    version = len(deal.analyses) + 1
    result_dict = {k: v for k, v in vars(analysis_result).items()}

    analysis = DealAnalysis(
        deal_id=deal.id,
        version=version,
        assumptions=assumptions.model_dump(),
        results=result_dict,
        score=score,
        score_breakdown=score_breakdown,
        model_version="heuristic_v1",
    )
    db.add(analysis)
    deal.status = "scored"
    await db.flush()
    await db.refresh(analysis)
    return _build_analysis_response(analysis)


@router.get("/{deal_id}/proforma", response_model=list[ProFormaYear])
async def get_pro_forma(
    deal_id: str,
    years: int = 10,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal).options(selectinload(Deal.analyses))
        .where(Deal.id == deal_id, Deal.user_id == user.id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if not deal.analyses:
        raise HTTPException(status_code=400, detail="Run analysis first")

    latest = deal.analyses[0]
    assumptions = DealAssumptions(**latest.assumptions)

    inputs = DealInputs(
        purchase_price=float(deal.purchase_price),
        monthly_rent=assumptions.monthly_rent,
        other_income=assumptions.other_income,
        vacancy_rate=assumptions.vacancy_rate,
        management_fee_pct=assumptions.management_fee_pct,
        maintenance_pct=assumptions.maintenance_pct,
        capex_reserve_pct=assumptions.capex_reserve_pct,
        property_tax_annual=assumptions.property_tax_annual,
        insurance_annual=assumptions.insurance_annual,
        hoa_monthly=assumptions.hoa_monthly,
        utilities_monthly=assumptions.utilities_monthly,
        down_payment_pct=assumptions.down_payment_pct,
        interest_rate=assumptions.interest_rate,
        loan_term_years=assumptions.loan_term_years,
        closing_cost_pct=assumptions.closing_cost_pct,
        annual_rent_growth=assumptions.annual_rent_growth,
        annual_appreciation=assumptions.annual_appreciation,
        annual_expense_growth=assumptions.annual_expense_growth,
        holding_period_years=years,
    )

    projections = generate_pro_forma(inputs, years)
    return [ProFormaYear(**{k: getattr(p, k) for k in ['year','gross_income','vacancy_loss','operating_expenses','noi','debt_service','cash_flow','property_value','equity','cumulative_return']}) for p in projections]


@router.post("/compare", response_model=DealCompareResponse)
async def compare_deals(
    data: DealCompareRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    str_ids = [str(did) for did in data.deal_ids]
    result = await db.execute(
        select(Deal).options(selectinload(Deal.analyses))
        .where(Deal.id.in_(str_ids), Deal.user_id == user.id)
    )
    deals = result.scalars().all()
    if len(deals) != len(data.deal_ids):
        raise HTTPException(status_code=404, detail="One or more deals not found")

    deal_responses = []
    ranking = []
    for deal in deals:
        resp = _build_deal_response(deal)
        deal_responses.append(resp)
        if deal.analyses:
            latest = deal.analyses[0]
            ranking.append({
                "deal_id": str(deal.id),
                "score": float(latest.score) if latest.score else 0,
                "cap_rate": latest.results.get("cap_rate", 0),
                "cash_on_cash_return": latest.results.get("cash_on_cash_return", 0),
                "monthly_cash_flow": latest.results.get("monthly_cash_flow", 0),
            })

    ranking.sort(key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(ranking):
        r["rank"] = i + 1

    return DealCompareResponse(deals=deal_responses, ranking=ranking)
