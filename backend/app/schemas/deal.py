from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DealAssumptions(BaseModel):
    """Financial assumptions for deal analysis."""
    # Income
    monthly_rent: float = Field(0, ge=0, description="Expected monthly rental income")
    other_income: float = Field(0, ge=0, description="Parking, laundry, etc.")

    # Expenses (as percentages of gross income unless noted)
    vacancy_rate: float = Field(0.08, ge=0, le=1, description="Expected vacancy rate")
    management_fee_pct: float = Field(0.10, ge=0, le=1, description="Property management fee")
    maintenance_pct: float = Field(0.05, ge=0, le=1, description="Maintenance reserve")
    capex_reserve_pct: float = Field(0.05, ge=0, le=1, description="Capital expenditure reserve")

    # Fixed expenses (annual)
    property_tax_annual: float = Field(0, ge=0)
    insurance_annual: float = Field(0, ge=0)
    hoa_monthly: float = Field(0, ge=0)
    utilities_monthly: float = Field(0, ge=0)

    # Financing
    down_payment_pct: float = Field(0.25, gt=0, le=1, description="Down payment percentage")
    interest_rate: float = Field(0.07, gt=0, le=1, description="Annual interest rate")
    loan_term_years: int = Field(30, gt=0, le=40, description="Loan term in years")
    closing_cost_pct: float = Field(0.03, ge=0, le=0.15, description="Closing costs as % of purchase price")

    # Growth assumptions
    annual_rent_growth: float = Field(0.03, ge=-0.1, le=0.2)
    annual_appreciation: float = Field(0.03, ge=-0.2, le=0.3)
    annual_expense_growth: float = Field(0.02, ge=0, le=0.1)

    # Holding period
    holding_period_years: int = Field(10, ge=1, le=30)


class DealCreate(BaseModel):
    property_id: UUID | None = None
    source: str = "manual"
    purchase_price: float = Field(..., gt=0)
    notes: str | None = None
    tags: list[str] | None = None
    assumptions: DealAssumptions | None = None

    # If no property_id, provide address for property creation
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    property_type: str = "sfr"
    bedrooms: int | None = None
    bathrooms: float | None = None
    sqft: int | None = None
    year_built: int | None = None


class AnalysisResults(BaseModel):
    """Computed financial metrics."""
    # Income
    gross_monthly_income: float
    gross_annual_income: float
    effective_gross_income: float

    # Expenses
    total_monthly_expenses: float
    total_annual_expenses: float
    operating_expense_ratio: float

    # Key metrics
    noi: float
    cap_rate: float
    cash_on_cash_return: float
    monthly_cash_flow: float
    annual_cash_flow: float
    dscr: float
    grm: float

    # Financing
    loan_amount: float
    down_payment: float
    monthly_mortgage: float
    total_cash_needed: float

    # Returns
    total_return_pct: float
    annualized_return: float
    equity_multiple: float
    irr: float | None = None

    # Risk
    break_even_ratio: float
    rent_to_price_ratio: float
    price_per_sqft: float | None = None


class DealAnalysisResponse(BaseModel):
    id: UUID
    deal_id: UUID
    version: int
    assumptions: dict
    results: AnalysisResults
    score: float | None
    score_breakdown: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProFormaYear(BaseModel):
    year: int
    gross_income: float
    vacancy_loss: float
    operating_expenses: float
    noi: float
    debt_service: float
    cash_flow: float
    property_value: float
    equity: float
    cumulative_return: float


class DealResponse(BaseModel):
    id: UUID
    user_id: UUID
    property_id: UUID | None
    source: str
    status: str
    purchase_price: float | None
    notes: str | None
    tags: list[str] | None
    latest_analysis: DealAnalysisResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DealCompareRequest(BaseModel):
    deal_ids: list[UUID] = Field(..., min_length=2, max_length=5)


class DealCompareResponse(BaseModel):
    deals: list[DealResponse]
    ranking: list[dict]  # [{deal_id, rank, score, strengths, weaknesses}]
