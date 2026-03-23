from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.portfolio import Portfolio, PortfolioProperty, Loan, IncomeRecord, ExpenseRecord
from app.models.property import Property
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioPropertyCreate,
    LoanCreate,
    IncomeCreate,
    ExpenseCreate,
    PortfolioSummary,
    PortfolioResponse,
    PortfolioPropertyResponse,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    data: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = Portfolio(user_id=user.id, name=data.name, description=data.description)
    db.add(portfolio)
    await db.flush()
    await db.refresh(portfolio)
    return PortfolioResponse(
        id=portfolio.id,
        user_id=portfolio.user_id,
        name=portfolio.name,
        description=portfolio.description,
        created_at=portfolio.created_at,
    )


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.holdings))
        .where(Portfolio.user_id == user.id)
        .order_by(Portfolio.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Portfolio)
        .options(
            selectinload(Portfolio.holdings).selectinload(PortfolioProperty.loans),
            selectinload(Portfolio.holdings).selectinload(PortfolioProperty.property),
        )
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.get("/{portfolio_id}/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    portfolio_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Portfolio)
        .options(
            selectinload(Portfolio.holdings).selectinload(PortfolioProperty.loans),
            selectinload(Portfolio.holdings).selectinload(PortfolioProperty.income_records),
            selectinload(Portfolio.holdings).selectinload(PortfolioProperty.expense_records),
        )
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    total_value = 0.0
    total_debt = 0.0
    total_acquisition = 0.0
    monthly_income = 0.0
    monthly_expenses = 0.0
    active_count = 0

    for holding in portfolio.holdings:
        if holding.status != "active":
            continue
        active_count += 1

        value = float(holding.current_value or holding.acquisition_price)
        total_value += value
        total_acquisition += float(holding.acquisition_price)

        for loan in holding.loans:
            if loan.status == "active":
                total_debt += float(loan.current_balance)
                monthly_expenses += float(loan.monthly_payment)

        # Approximate monthly income from recent records
        for inc in holding.income_records:
            if inc.status == "paid" and inc.type == "rent":
                monthly_income += float(inc.amount)
                break  # just latest

    total_equity = total_value - total_debt
    monthly_cash_flow = monthly_income - monthly_expenses
    portfolio_ltv = total_debt / total_value if total_value > 0 else 0
    appreciation = (total_value - total_acquisition) / total_acquisition if total_acquisition > 0 else 0

    # Weighted cap rate approximation
    annual_noi = (monthly_income - (monthly_expenses * 0.4)) * 12  # rough OpEx estimate
    weighted_cap = annual_noi / total_value if total_value > 0 else 0

    avg_coc = monthly_cash_flow * 12 / total_equity if total_equity > 0 else 0

    return PortfolioSummary(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        total_properties=active_count,
        total_value=round(total_value, 2),
        total_equity=round(total_equity, 2),
        total_debt=round(total_debt, 2),
        monthly_cash_flow=round(monthly_cash_flow, 2),
        annual_cash_flow=round(monthly_cash_flow * 12, 2),
        weighted_cap_rate=round(weighted_cap, 4),
        average_coc_return=round(avg_coc, 4),
        total_appreciation=round(appreciation, 4),
        portfolio_ltv=round(portfolio_ltv, 4),
    )


@router.post("/{portfolio_id}/properties", response_model=PortfolioPropertyResponse, status_code=status.HTTP_201_CREATED)
async def add_property_to_portfolio(
    portfolio_id: UUID,
    data: PortfolioPropertyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify portfolio ownership
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holding = PortfolioProperty(
        portfolio_id=portfolio_id,
        property_id=data.property_id,
        acquisition_date=data.acquisition_date,
        acquisition_price=data.acquisition_price,
        acquisition_costs=data.acquisition_costs,
        current_value=data.current_value,
    )
    db.add(holding)
    await db.flush()
    await db.refresh(holding)
    return holding


@router.post("/{portfolio_id}/properties/{holding_id}/loans", status_code=status.HTTP_201_CREATED)
async def add_loan(
    portfolio_id: UUID,
    holding_id: UUID,
    data: LoanCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify ownership chain
    result = await db.execute(
        select(PortfolioProperty)
        .join(Portfolio)
        .where(
            PortfolioProperty.id == holding_id,
            PortfolioProperty.portfolio_id == portfolio_id,
            Portfolio.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Holding not found")

    loan = Loan(
        portfolio_property_id=holding_id,
        **data.model_dump(),
    )
    db.add(loan)
    await db.flush()
    await db.refresh(loan)
    return {"id": str(loan.id), "status": "created"}


@router.post("/{portfolio_id}/properties/{holding_id}/income", status_code=status.HTTP_201_CREATED)
async def add_income(
    portfolio_id: UUID,
    holding_id: UUID,
    data: IncomeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PortfolioProperty)
        .join(Portfolio)
        .where(
            PortfolioProperty.id == holding_id,
            PortfolioProperty.portfolio_id == portfolio_id,
            Portfolio.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Holding not found")

    record = IncomeRecord(portfolio_property_id=holding_id, **data.model_dump())
    db.add(record)
    await db.flush()
    return {"id": str(record.id), "status": "created"}


@router.post("/{portfolio_id}/properties/{holding_id}/expenses", status_code=status.HTTP_201_CREATED)
async def add_expense(
    portfolio_id: UUID,
    holding_id: UUID,
    data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PortfolioProperty)
        .join(Portfolio)
        .where(
            PortfolioProperty.id == holding_id,
            PortfolioProperty.portfolio_id == portfolio_id,
            Portfolio.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Holding not found")

    record = ExpenseRecord(portfolio_property_id=holding_id, **data.model_dump())
    db.add(record)
    await db.flush()
    return {"id": str(record.id), "status": "created"}
