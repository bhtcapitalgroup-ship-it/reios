"""
REIOS Deal Analysis Engine

Core financial computation engine for real estate investment analysis.
Calculates: NOI, cap rate, CoC return, IRR, DSCR, GRM, pro forma projections.
"""

import math
from dataclasses import dataclass, field


@dataclass
class DealInputs:
    """Raw deal inputs for analysis."""
    purchase_price: float
    monthly_rent: float
    other_income: float = 0.0
    sqft: int | None = None

    # Expense rates
    vacancy_rate: float = 0.08
    management_fee_pct: float = 0.10
    maintenance_pct: float = 0.05
    capex_reserve_pct: float = 0.05

    # Fixed expenses
    property_tax_annual: float = 0.0
    insurance_annual: float = 0.0
    hoa_monthly: float = 0.0
    utilities_monthly: float = 0.0

    # Financing
    down_payment_pct: float = 0.25
    interest_rate: float = 0.07
    loan_term_years: int = 30
    closing_cost_pct: float = 0.03

    # Growth
    annual_rent_growth: float = 0.03
    annual_appreciation: float = 0.03
    annual_expense_growth: float = 0.02

    # Holding
    holding_period_years: int = 10


@dataclass
class AnalysisResult:
    """Computed financial metrics."""
    # Income
    gross_monthly_income: float = 0.0
    gross_annual_income: float = 0.0
    effective_gross_income: float = 0.0

    # Expenses
    total_monthly_expenses: float = 0.0
    total_annual_expenses: float = 0.0
    operating_expense_ratio: float = 0.0

    # Key metrics
    noi: float = 0.0
    cap_rate: float = 0.0
    cash_on_cash_return: float = 0.0
    monthly_cash_flow: float = 0.0
    annual_cash_flow: float = 0.0
    dscr: float = 0.0
    grm: float = 0.0

    # Financing
    loan_amount: float = 0.0
    down_payment: float = 0.0
    monthly_mortgage: float = 0.0
    total_cash_needed: float = 0.0

    # Returns
    total_return_pct: float = 0.0
    annualized_return: float = 0.0
    equity_multiple: float = 0.0
    irr: float | None = None

    # Risk
    break_even_ratio: float = 0.0
    rent_to_price_ratio: float = 0.0
    price_per_sqft: float | None = None


@dataclass
class ProFormaYear:
    """Single year of pro forma projection."""
    year: int
    gross_income: float = 0.0
    vacancy_loss: float = 0.0
    operating_expenses: float = 0.0
    noi: float = 0.0
    debt_service: float = 0.0
    cash_flow: float = 0.0
    property_value: float = 0.0
    loan_balance: float = 0.0
    equity: float = 0.0
    cumulative_return: float = 0.0


def calculate_monthly_mortgage(principal: float, annual_rate: float, term_years: int) -> float:
    """Calculate monthly mortgage payment using standard amortization formula."""
    if principal <= 0 or annual_rate <= 0:
        return 0.0
    monthly_rate = annual_rate / 12
    n_payments = term_years * 12
    payment = principal * (monthly_rate * (1 + monthly_rate) ** n_payments) / (
        (1 + monthly_rate) ** n_payments - 1
    )
    return round(payment, 2)


def calculate_loan_balance(principal: float, annual_rate: float, term_years: int, months_elapsed: int) -> float:
    """Calculate remaining loan balance after n months."""
    if principal <= 0 or annual_rate <= 0 or months_elapsed <= 0:
        return principal
    monthly_rate = annual_rate / 12
    n_payments = term_years * 12
    if months_elapsed >= n_payments:
        return 0.0
    balance = principal * (
        (1 + monthly_rate) ** n_payments - (1 + monthly_rate) ** months_elapsed
    ) / ((1 + monthly_rate) ** n_payments - 1)
    return max(0.0, round(balance, 2))


def calculate_irr(cash_flows: list[float], max_iterations: int = 1000, tolerance: float = 1e-7) -> float | None:
    """Calculate IRR using Newton's method."""
    if not cash_flows or all(cf == 0 for cf in cash_flows):
        return None

    # Initial guess
    rate = 0.10

    for _ in range(max_iterations):
        npv = sum(cf / (1 + rate) ** i for i, cf in enumerate(cash_flows))
        dnpv = sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cash_flows))

        if abs(dnpv) < 1e-12:
            return None

        new_rate = rate - npv / dnpv

        if abs(new_rate - rate) < tolerance:
            return round(new_rate, 6)

        rate = new_rate

        # Guard against divergence
        if abs(rate) > 10:
            return None

    return None


def analyze_deal(inputs: DealInputs) -> AnalysisResult:
    """Run full financial analysis on a deal."""
    result = AnalysisResult()

    # === INCOME ===
    result.gross_monthly_income = inputs.monthly_rent + inputs.other_income
    result.gross_annual_income = result.gross_monthly_income * 12
    vacancy_loss = result.gross_annual_income * inputs.vacancy_rate
    result.effective_gross_income = result.gross_annual_income - vacancy_loss

    # === EXPENSES ===
    variable_expenses = result.effective_gross_income * (
        inputs.management_fee_pct + inputs.maintenance_pct + inputs.capex_reserve_pct
    )
    fixed_expenses = (
        inputs.property_tax_annual
        + inputs.insurance_annual
        + (inputs.hoa_monthly * 12)
        + (inputs.utilities_monthly * 12)
    )
    result.total_annual_expenses = variable_expenses + fixed_expenses
    result.total_monthly_expenses = result.total_annual_expenses / 12

    if result.gross_annual_income > 0:
        result.operating_expense_ratio = result.total_annual_expenses / result.gross_annual_income
    else:
        result.operating_expense_ratio = 0.0

    # === NOI ===
    result.noi = result.effective_gross_income - result.total_annual_expenses

    # === FINANCING ===
    result.down_payment = inputs.purchase_price * inputs.down_payment_pct
    result.loan_amount = inputs.purchase_price - result.down_payment
    closing_costs = inputs.purchase_price * inputs.closing_cost_pct
    result.total_cash_needed = result.down_payment + closing_costs

    result.monthly_mortgage = calculate_monthly_mortgage(
        result.loan_amount, inputs.interest_rate, inputs.loan_term_years
    )
    annual_debt_service = result.monthly_mortgage * 12

    # === KEY METRICS ===
    if inputs.purchase_price > 0:
        result.cap_rate = result.noi / inputs.purchase_price
        result.rent_to_price_ratio = (inputs.monthly_rent * 12) / inputs.purchase_price
    if result.gross_annual_income > 0:
        result.grm = inputs.purchase_price / result.gross_annual_income

    result.annual_cash_flow = result.noi - annual_debt_service
    result.monthly_cash_flow = result.annual_cash_flow / 12

    if result.total_cash_needed > 0:
        result.cash_on_cash_return = result.annual_cash_flow / result.total_cash_needed

    if annual_debt_service > 0:
        result.dscr = result.noi / annual_debt_service
    else:
        result.dscr = float("inf") if result.noi > 0 else 0.0

    if result.gross_annual_income > 0:
        result.break_even_ratio = (result.total_annual_expenses + annual_debt_service) / result.gross_annual_income

    if inputs.sqft and inputs.sqft > 0:
        result.price_per_sqft = inputs.purchase_price / inputs.sqft

    # === IRR & TOTAL RETURN ===
    cash_flows = [-result.total_cash_needed]
    for year in range(1, inputs.holding_period_years + 1):
        rent_factor = (1 + inputs.annual_rent_growth) ** year
        expense_factor = (1 + inputs.annual_expense_growth) ** year

        yr_gross = result.gross_annual_income * rent_factor
        yr_vacancy = yr_gross * inputs.vacancy_rate
        yr_egi = yr_gross - yr_vacancy
        yr_var_exp = yr_egi * (inputs.management_fee_pct + inputs.maintenance_pct + inputs.capex_reserve_pct)
        yr_fixed = fixed_expenses * expense_factor
        yr_noi = yr_egi - yr_var_exp - yr_fixed
        yr_cf = yr_noi - annual_debt_service

        if year == inputs.holding_period_years:
            # Sale proceeds
            sale_price = inputs.purchase_price * (1 + inputs.annual_appreciation) ** year
            selling_costs = sale_price * 0.06  # 6% selling costs
            remaining_balance = calculate_loan_balance(
                result.loan_amount, inputs.interest_rate, inputs.loan_term_years, year * 12
            )
            net_sale_proceeds = sale_price - selling_costs - remaining_balance
            cash_flows.append(yr_cf + net_sale_proceeds)
        else:
            cash_flows.append(yr_cf)

    result.irr = calculate_irr(cash_flows)

    total_cash_received = sum(cash_flows[1:])
    if result.total_cash_needed > 0:
        result.total_return_pct = (total_cash_received - result.total_cash_needed) / result.total_cash_needed
        result.equity_multiple = total_cash_received / result.total_cash_needed
        if inputs.holding_period_years > 0:
            result.annualized_return = (
                (1 + result.total_return_pct) ** (1 / inputs.holding_period_years) - 1
            )

    # Round everything
    for attr in vars(result):
        val = getattr(result, attr)
        if isinstance(val, float):
            setattr(result, attr, round(val, 4))

    return result


def generate_pro_forma(inputs: DealInputs, years: int | None = None) -> list[ProFormaYear]:
    """Generate year-by-year pro forma projections."""
    years = years or inputs.holding_period_years
    result = analyze_deal(inputs)

    projections = []
    cumulative_cash_flow = 0.0
    annual_debt_service = result.monthly_mortgage * 12

    fixed_expenses_base = (
        inputs.property_tax_annual
        + inputs.insurance_annual
        + (inputs.hoa_monthly * 12)
        + (inputs.utilities_monthly * 12)
    )

    for year in range(1, years + 1):
        rent_factor = (1 + inputs.annual_rent_growth) ** year
        expense_factor = (1 + inputs.annual_expense_growth) ** year

        gross = result.gross_annual_income * rent_factor
        vacancy = gross * inputs.vacancy_rate
        egi = gross - vacancy

        variable_exp = egi * (inputs.management_fee_pct + inputs.maintenance_pct + inputs.capex_reserve_pct)
        fixed_exp = fixed_expenses_base * expense_factor
        total_exp = variable_exp + fixed_exp

        noi = egi - total_exp
        cash_flow = noi - annual_debt_service
        cumulative_cash_flow += cash_flow

        property_value = inputs.purchase_price * (1 + inputs.annual_appreciation) ** year
        loan_balance = calculate_loan_balance(
            result.loan_amount, inputs.interest_rate, inputs.loan_term_years, year * 12
        )
        equity = property_value - loan_balance

        projections.append(ProFormaYear(
            year=year,
            gross_income=round(gross, 2),
            vacancy_loss=round(vacancy, 2),
            operating_expenses=round(total_exp, 2),
            noi=round(noi, 2),
            debt_service=round(annual_debt_service, 2),
            cash_flow=round(cash_flow, 2),
            property_value=round(property_value, 2),
            loan_balance=round(loan_balance, 2),
            equity=round(equity, 2),
            cumulative_return=round(cumulative_cash_flow, 2),
        ))

    return projections


def score_deal_heuristic(result: AnalysisResult, inputs: DealInputs) -> tuple[float, dict]:
    """
    Heuristic deal scoring (0-100) used before ML model is trained.
    Returns (score, breakdown).
    """
    breakdown = {}

    # Cap rate score (0-25 points)
    # < 4% = 0pts, 4-6% = 5-15pts, 6-8% = 15-20pts, 8%+ = 20-25pts
    if result.cap_rate >= 0.08:
        breakdown["cap_rate"] = 25.0
    elif result.cap_rate >= 0.06:
        breakdown["cap_rate"] = 15.0 + (result.cap_rate - 0.06) / 0.02 * 10
    elif result.cap_rate >= 0.04:
        breakdown["cap_rate"] = 5.0 + (result.cap_rate - 0.04) / 0.02 * 10
    else:
        breakdown["cap_rate"] = max(0, result.cap_rate / 0.04 * 5)

    # Cash-on-cash return score (0-25 points)
    if result.cash_on_cash_return >= 0.12:
        breakdown["cash_on_cash"] = 25.0
    elif result.cash_on_cash_return >= 0.08:
        breakdown["cash_on_cash"] = 15.0 + (result.cash_on_cash_return - 0.08) / 0.04 * 10
    elif result.cash_on_cash_return >= 0.04:
        breakdown["cash_on_cash"] = 5.0 + (result.cash_on_cash_return - 0.04) / 0.04 * 10
    else:
        breakdown["cash_on_cash"] = max(0, result.cash_on_cash_return / 0.04 * 5)

    # DSCR score (0-20 points)
    dscr = min(result.dscr, 3.0) if result.dscr != float("inf") else 3.0
    if dscr >= 1.5:
        breakdown["dscr"] = 20.0
    elif dscr >= 1.25:
        breakdown["dscr"] = 12.0 + (dscr - 1.25) / 0.25 * 8
    elif dscr >= 1.0:
        breakdown["dscr"] = 4.0 + (dscr - 1.0) / 0.25 * 8
    else:
        breakdown["dscr"] = max(0, dscr * 4)

    # Cash flow score (0-15 points)
    monthly_cf_per_unit = result.monthly_cash_flow  # per unit for single-family
    if monthly_cf_per_unit >= 300:
        breakdown["cash_flow"] = 15.0
    elif monthly_cf_per_unit >= 200:
        breakdown["cash_flow"] = 10.0 + (monthly_cf_per_unit - 200) / 100 * 5
    elif monthly_cf_per_unit >= 100:
        breakdown["cash_flow"] = 5.0 + (monthly_cf_per_unit - 100) / 100 * 5
    elif monthly_cf_per_unit > 0:
        breakdown["cash_flow"] = monthly_cf_per_unit / 100 * 5
    else:
        breakdown["cash_flow"] = 0.0

    # 1% rule / rent-to-price ratio (0-15 points)
    rtp = result.rent_to_price_ratio * 12 if result.rent_to_price_ratio else 0
    # rtp is annual rent / price; monthly rent / price = rtp/12
    monthly_rtp = rtp / 12
    if monthly_rtp >= 0.01:
        breakdown["rent_to_price"] = 15.0
    elif monthly_rtp >= 0.008:
        breakdown["rent_to_price"] = 8.0 + (monthly_rtp - 0.008) / 0.002 * 7
    elif monthly_rtp >= 0.006:
        breakdown["rent_to_price"] = 3.0 + (monthly_rtp - 0.006) / 0.002 * 5
    else:
        breakdown["rent_to_price"] = max(0, monthly_rtp / 0.006 * 3)

    total_score = sum(breakdown.values())
    total_score = round(min(100, max(0, total_score)), 1)

    # Round breakdown
    breakdown = {k: round(v, 1) for k, v in breakdown.items()}

    return total_score, breakdown
