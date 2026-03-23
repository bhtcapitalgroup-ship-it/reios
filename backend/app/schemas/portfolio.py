from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PortfolioCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None


class PortfolioPropertyCreate(BaseModel):
    property_id: UUID
    acquisition_date: date
    acquisition_price: float = Field(..., gt=0)
    acquisition_costs: float = 0
    current_value: float | None = None


class LoanCreate(BaseModel):
    lender_name: str | None = None
    loan_type: str = "conventional"
    original_balance: float = Field(..., gt=0)
    current_balance: float = Field(..., gt=0)
    interest_rate: float = Field(..., gt=0, le=1)
    term_months: int = Field(..., gt=0)
    amortization_months: int | None = None
    monthly_payment: float = Field(..., gt=0)
    escrow_amount: float = 0
    origination_date: date
    maturity_date: date


class IncomeCreate(BaseModel):
    type: str = "rent"
    amount: float = Field(..., gt=0)
    due_date: date
    paid_date: date | None = None
    status: str = "pending"
    payment_method: str | None = None


class ExpenseCreate(BaseModel):
    category: str
    vendor_name: str | None = None
    amount: float = Field(..., gt=0)
    date: date
    description: str | None = None
    tax_deductible: bool = True


class PortfolioSummary(BaseModel):
    portfolio_id: UUID
    name: str
    total_properties: int
    total_value: float
    total_equity: float
    total_debt: float
    monthly_cash_flow: float
    annual_cash_flow: float
    weighted_cap_rate: float
    average_coc_return: float
    total_appreciation: float
    portfolio_ltv: float
    occupancy_rate: float | None = None


class PortfolioPropertyResponse(BaseModel):
    id: UUID
    portfolio_id: UUID
    property_id: UUID
    acquisition_date: date
    acquisition_price: float
    current_value: float | None
    status: str
    monthly_cash_flow: float | None = None
    cap_rate: float | None = None
    equity: float | None = None

    model_config = {"from_attributes": True}


class PortfolioResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str | None
    holdings: list[PortfolioPropertyResponse] = []
    summary: PortfolioSummary | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
