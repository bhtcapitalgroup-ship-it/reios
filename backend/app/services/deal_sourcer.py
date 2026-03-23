"""
REIOS Off-Market Deal Sourcing Engine

Identifies distressed properties, scores seller motivation,
and ranks off-market opportunities for investors.
"""

import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class DistressSignal:
    """A detected distress indicator on a property."""
    signal_type: str  # pre_foreclosure, tax_lien, probate, divorce, code_violation, vacancy, absentee
    severity: float  # 0-1
    details: dict = field(default_factory=dict)
    detected_at: str = ""


@dataclass
class OffMarketLead:
    """A scored off-market opportunity."""
    property_id: str
    address: str
    city: str
    state: str
    estimated_value: float
    signals: list[DistressSignal]
    motivation_score: float  # 0-100
    estimated_discount: float  # 0-1 (percentage below market)
    potential_deal_price: float
    source: str
    status: str = "new"


# Signal severity weights for motivation scoring
SIGNAL_WEIGHTS = {
    "pre_foreclosure": 0.95,
    "tax_lien": 0.80,
    "probate": 0.85,
    "divorce": 0.75,
    "code_violation": 0.65,
    "vacancy": 0.60,
    "absentee": 0.45,
    "bankruptcy": 0.92,
    "lis_pendens": 0.90,
}

# Typical discount ranges by signal type
DISCOUNT_RANGES = {
    "pre_foreclosure": (0.15, 0.30),
    "tax_lien": (0.10, 0.25),
    "probate": (0.12, 0.25),
    "divorce": (0.08, 0.18),
    "code_violation": (0.10, 0.20),
    "vacancy": (0.05, 0.15),
    "absentee": (0.03, 0.12),
    "bankruptcy": (0.15, 0.35),
    "lis_pendens": (0.15, 0.30),
}


def score_motivation(signals: list[DistressSignal], equity_pct: float = 0.5, ownership_years: int = 10) -> float:
    """
    Score seller motivation from 0-100 based on distress signals.

    Factors:
    - Signal severity (higher = more motivated)
    - Multiple overlapping signals compound
    - Low equity = more desperate
    - Long ownership = more likely to have equity to negotiate
    """
    if not signals:
        return 0.0

    # Base score from strongest signal
    base_scores = [SIGNAL_WEIGHTS.get(s.signal_type, 0.3) * s.severity for s in signals]
    base_score = max(base_scores) * 60  # Strongest signal contributes 0-60 points

    # Compounding bonus for multiple signals (up to 20 points)
    overlap_bonus = min(20, (len(signals) - 1) * 8)

    # Equity factor (low equity = more pressure, up to 10 points)
    equity_factor = max(0, (1 - equity_pct)) * 10

    # Time pressure (recent signals = more urgent, up to 10 points)
    recency_bonus = 0
    for s in signals:
        if s.signal_type in ("pre_foreclosure", "lis_pendens", "bankruptcy"):
            recency_bonus = 10
            break
        elif s.signal_type in ("tax_lien", "code_violation"):
            recency_bonus = max(recency_bonus, 7)

    total = base_score + overlap_bonus + equity_factor + recency_bonus
    return round(min(100, max(0, total)), 1)


def estimate_discount(signals: list[DistressSignal], motivation_score: float) -> float:
    """Estimate likely discount from market value."""
    if not signals:
        return 0.0

    # Start with discount range from strongest signal
    strongest = max(signals, key=lambda s: SIGNAL_WEIGHTS.get(s.signal_type, 0.3) * s.severity)
    low, high = DISCOUNT_RANGES.get(strongest.signal_type, (0.05, 0.15))

    # Scale within range based on motivation
    discount = low + (high - low) * (motivation_score / 100)

    # Multi-signal boost
    if len(signals) > 1:
        discount *= 1.1

    return round(min(0.40, discount), 3)


def evaluate_lead(
    property_data: dict,
    signals: list[dict],
    market_data: dict | None = None,
) -> OffMarketLead:
    """
    Evaluate a potential off-market lead.

    Args:
        property_data: Property details (address, city, state, estimated_value, etc.)
        signals: List of distress signals detected
        market_data: Optional market context for the area
    """
    # Build signal objects
    distress_signals = []
    for s in signals:
        distress_signals.append(DistressSignal(
            signal_type=s.get("type", "unknown"),
            severity=s.get("severity", 0.7),
            details=s.get("details", {}),
            detected_at=s.get("detected_at", datetime.now(timezone.utc).isoformat()),
        ))

    estimated_value = property_data.get("estimated_value", 0)
    equity_pct = property_data.get("equity_pct", 0.5)
    ownership_years = property_data.get("ownership_years", 10)

    # Score motivation
    motivation = score_motivation(distress_signals, equity_pct, ownership_years)

    # Apply market context adjustments
    if market_data:
        months_supply = market_data.get("months_supply", 4)
        if months_supply < 3:
            motivation *= 0.9  # Tight market = seller has options
        elif months_supply > 6:
            motivation *= 1.1  # Loose market = seller more desperate
        motivation = min(100, motivation)

    # Estimate discount
    discount = estimate_discount(distress_signals, motivation)
    potential_price = round(estimated_value * (1 - discount), 2)

    return OffMarketLead(
        property_id=property_data.get("id", ""),
        address=property_data.get("address", ""),
        city=property_data.get("city", ""),
        state=property_data.get("state", ""),
        estimated_value=estimated_value,
        signals=distress_signals,
        motivation_score=round(motivation, 1),
        estimated_discount=discount,
        potential_deal_price=potential_price,
        source=distress_signals[0].signal_type if distress_signals else "unknown",
    )


def rank_leads(leads: list[OffMarketLead], investor_criteria: dict | None = None) -> list[OffMarketLead]:
    """
    Rank leads by investment potential.

    Considers: motivation score, discount, market strength, criteria match.
    """
    def lead_score(lead: OffMarketLead) -> float:
        score = lead.motivation_score * 0.4 + lead.estimated_discount * 200 * 0.3

        # Criteria matching bonus
        if investor_criteria:
            target_markets = investor_criteria.get("target_markets", [])
            if lead.city in target_markets or lead.state in target_markets:
                score += 15

            max_price = investor_criteria.get("max_price")
            if max_price and lead.potential_deal_price <= max_price:
                score += 10

            target_types = investor_criteria.get("property_types", [])
            # Would check property_type here with full data

        return score

    return sorted(leads, key=lead_score, reverse=True)
