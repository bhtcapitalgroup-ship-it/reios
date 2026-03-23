"""Financing marketplace API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.financing import Lender, LendingProduct
from app.models.user import User

router = APIRouter(prefix="/financing", tags=["financing"])


class LenderResponse(BaseModel):
    id: str
    name: str
    type: str
    website: str | None
    geographic_areas: list | None
    products: list[dict] = []

    model_config = {"from_attributes": True}


class LoanScenario(BaseModel):
    """Input for loan scenario comparison."""
    property_value: float = Field(..., gt=0)
    loan_amount: float = Field(..., gt=0)
    property_type: str = "sfr"
    credit_score: int = 700
    state: str = ""
    purpose: str = "purchase"  # purchase, refinance, cash_out_refi


class LoanScenarioResult(BaseModel):
    lender: str
    product: str
    loan_type: str
    rate_low: float
    rate_high: float
    estimated_rate: float
    monthly_payment_low: float
    monthly_payment_high: float
    ltv: float
    estimated_closing_costs: float
    meets_criteria: bool
    notes: list[str] = []


class QuickQuoteRequest(BaseModel):
    property_value: float = Field(..., gt=0)
    down_payment_pct: float = Field(0.25, gt=0, le=1)
    credit_score: int = Field(700, ge=500, le=850)
    property_type: str = "sfr"
    loan_type: str | None = None  # dscr, hard_money, conventional, or None for all


def calculate_payment(principal: float, annual_rate: float, term_years: int = 30) -> float:
    monthly_rate = annual_rate / 12
    n = term_years * 12
    if monthly_rate <= 0:
        return principal / n
    return round(principal * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1), 2)


@router.get("/lenders", response_model=list[LenderResponse])
async def list_lenders(
    lender_type: str | None = None,
    loan_type: str | None = None,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List available lenders with their products."""
    query = select(Lender).options(selectinload(Lender.products)).where(Lender.active == True)

    if lender_type:
        query = query.where(Lender.type == lender_type)

    result = await db.execute(query)
    lenders = result.scalars().all()

    responses = []
    for lender in lenders:
        products = []
        for p in lender.products:
            if loan_type and p.loan_type != loan_type:
                continue
            if not p.active:
                continue
            products.append({
                "id": str(p.id),
                "name": p.name,
                "loan_type": p.loan_type,
                "rate_range": f"{float(p.rate_range_low)*100:.2f}% - {float(p.rate_range_high)*100:.2f}%",
                "rate_low": float(p.rate_range_low),
                "rate_high": float(p.rate_range_high),
                "max_ltv": f"{float(p.max_ltv)*100:.0f}%",
                "min_credit_score": p.min_credit_score,
                "loan_range": f"${int(p.min_loan_amount):,} - ${int(p.max_loan_amount):,}",
                "property_types": p.property_types,
            })

        if products or not loan_type:
            responses.append(LenderResponse(
                id=str(lender.id),
                name=lender.name,
                type=lender.type,
                website=lender.website,
                geographic_areas=lender.geographic_areas,
                products=products,
            ))

    return responses


@router.post("/compare", response_model=list[LoanScenarioResult])
async def compare_loan_scenarios(
    scenario: LoanScenario,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compare loan options across all matching lenders/products."""
    ltv = scenario.loan_amount / scenario.property_value

    result = await db.execute(
        select(LendingProduct)
        .options(selectinload(LendingProduct.lender))
        .where(LendingProduct.active == True)
    )
    products = result.scalars().all()

    results = []
    for product in products:
        notes = []
        meets = True

        # Check LTV
        if product.max_ltv and ltv > float(product.max_ltv):
            notes.append(f"LTV {ltv*100:.0f}% exceeds max {float(product.max_ltv)*100:.0f}%")
            meets = False

        # Check credit score
        if product.min_credit_score and scenario.credit_score < product.min_credit_score:
            notes.append(f"Credit score {scenario.credit_score} below min {product.min_credit_score}")
            meets = False

        # Check loan amount
        if product.min_loan_amount and scenario.loan_amount < float(product.min_loan_amount):
            notes.append(f"Loan amount below minimum ${int(product.min_loan_amount):,}")
            meets = False
        if product.max_loan_amount and scenario.loan_amount > float(product.max_loan_amount):
            notes.append(f"Loan amount exceeds maximum ${int(product.max_loan_amount):,}")
            meets = False

        # Check property type
        if product.property_types and scenario.property_type not in product.property_types:
            notes.append(f"Property type '{scenario.property_type}' not supported")
            meets = False

        # Estimate rate based on credit score and LTV
        rate_low = float(product.rate_range_low)
        rate_high = float(product.rate_range_high)
        rate_spread = rate_high - rate_low

        credit_factor = max(0, min(1, (scenario.credit_score - 620) / 180))
        ltv_factor = max(0, min(1, 1 - (ltv - 0.5) / 0.5))
        estimated_rate = round(rate_high - rate_spread * (credit_factor * 0.6 + ltv_factor * 0.4), 4)

        term = 12 if product.loan_type == "hard_money" else 30
        closing_pct = 0.04 if product.loan_type == "hard_money" else 0.025

        results.append(LoanScenarioResult(
            lender=product.lender.name,
            product=product.name,
            loan_type=product.loan_type,
            rate_low=rate_low,
            rate_high=rate_high,
            estimated_rate=estimated_rate,
            monthly_payment_low=calculate_payment(scenario.loan_amount, rate_low, term),
            monthly_payment_high=calculate_payment(scenario.loan_amount, rate_high, term),
            ltv=round(ltv, 4),
            estimated_closing_costs=round(scenario.loan_amount * closing_pct, 2),
            meets_criteria=meets,
            notes=notes,
        ))

    # Sort: matching products first, then by estimated rate
    results.sort(key=lambda x: (not x.meets_criteria, x.estimated_rate))
    return results


@router.post("/quick-quote", response_model=list[LoanScenarioResult])
async def quick_quote(
    data: QuickQuoteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get quick rate quotes without a full application."""
    loan_amount = data.property_value * (1 - data.down_payment_pct)

    return await compare_loan_scenarios(
        LoanScenario(
            property_value=data.property_value,
            loan_amount=loan_amount,
            property_type=data.property_type,
            credit_score=data.credit_score,
        ),
        db=db,
        user=user,
    )
