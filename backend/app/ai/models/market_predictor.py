"""
Market Prediction Model

Phase 1: Trend extrapolation with momentum
Phase 2: Temporal Fusion Transformer
"""

import math
import time
from datetime import datetime

from app.ai.base import HeuristicModel, ModelOutput


class MarketPredictorHeuristic(HeuristicModel):
    """Trend-based market prediction for MVP."""

    def __init__(self):
        super().__init__("market_predictor_heuristic")
        self.load()

    def predict(self, features: dict) -> ModelOutput:
        start = time.time()

        # Historical data points (monthly)
        price_history = features.get("price_history", [])  # list of monthly median prices
        rent_history = features.get("rent_history", [])
        horizon_months = features.get("horizon_months", 12)

        # Current metrics
        current_price = features.get("current_median_price", 0)
        current_rent = features.get("current_median_rent", 0)
        yoy_price_change = features.get("yoy_price_change", 0.03)
        yoy_rent_change = features.get("yoy_rent_change", 0.03)
        population_growth = features.get("population_growth", 0.01)
        job_growth = features.get("job_growth", 0.01)
        inventory_months = features.get("months_supply", 4.0)
        unemployment = features.get("unemployment_rate", 0.04)

        # === Price Prediction ===
        # Base trend: use recent YoY change with mean reversion
        long_term_avg_appreciation = 0.035  # 3.5% national average
        trend_weight = 0.6
        reversion_weight = 0.4
        base_monthly_price_growth = (
            trend_weight * (yoy_price_change / 12) +
            reversion_weight * (long_term_avg_appreciation / 12)
        )

        # Demand signal (population + jobs)
        demand_boost = (population_growth + job_growth) * 0.5  # annualized, so divide for monthly
        base_monthly_price_growth += demand_boost / 12

        # Supply signal (inventory)
        if inventory_months < 3:
            supply_factor = 1.1  # Very tight supply → prices up faster
        elif inventory_months < 5:
            supply_factor = 1.0
        elif inventory_months < 7:
            supply_factor = 0.95
        else:
            supply_factor = 0.85  # Oversupply → slow down

        monthly_price_growth = base_monthly_price_growth * supply_factor

        # Generate forecast
        price_forecast = []
        current = current_price
        for m in range(1, horizon_months + 1):
            # Dampen growth over longer horizons (uncertainty increases)
            damping = 1.0 - (m / horizon_months) * 0.15
            current *= (1 + monthly_price_growth * damping)
            price_forecast.append(round(current, 2))

        # === Rent Prediction ===
        base_monthly_rent_growth = yoy_rent_change / 12
        # Rents are stickier than prices
        monthly_rent_growth = base_monthly_rent_growth * 0.85

        rent_forecast = []
        current_r = current_rent
        for m in range(1, horizon_months + 1):
            current_r *= (1 + monthly_rent_growth)
            rent_forecast.append(round(current_r, 2))

        # Confidence intervals (widen with horizon)
        def compute_ci(forecast: list[float], base_volatility: float = 0.02) -> list[dict]:
            cis = []
            for i, val in enumerate(forecast):
                months_out = i + 1
                spread = base_volatility * math.sqrt(months_out / 12)
                cis.append({
                    "month": months_out,
                    "p10": round(val * (1 - spread * 1.28), 2),
                    "p50": val,
                    "p90": round(val * (1 + spread * 1.28), 2),
                })
            return cis

        price_ci = compute_ci(price_forecast, 0.04)
        rent_ci = compute_ci(rent_forecast, 0.02)

        # Appreciation summary
        if current_price > 0:
            total_price_change = (price_forecast[-1] - current_price) / current_price
            annualized_price_change = (1 + total_price_change) ** (12 / horizon_months) - 1
        else:
            total_price_change = 0
            annualized_price_change = 0

        if current_rent > 0:
            total_rent_change = (rent_forecast[-1] - current_rent) / current_rent
            annualized_rent_change = (1 + total_rent_change) ** (12 / horizon_months) - 1
        else:
            total_rent_change = 0
            annualized_rent_change = 0

        # Market cycle classification
        if yoy_price_change > 0.08 and inventory_months < 3:
            cycle_phase = "expansion"
        elif yoy_price_change > 0.04:
            cycle_phase = "growth"
        elif yoy_price_change > 0:
            cycle_phase = "stable"
        elif yoy_price_change > -0.05:
            cycle_phase = "cooling"
        else:
            cycle_phase = "contraction"

        confidence = 0.55 - (horizon_months / 36 * 0.2)  # Decreases with horizon

        latency = (time.time() - start) * 1000

        return ModelOutput(
            prediction={
                "price_forecast": price_ci,
                "rent_forecast": rent_ci,
                "summary": {
                    "total_price_appreciation": round(total_price_change, 4),
                    "annualized_price_appreciation": round(annualized_price_change, 4),
                    "total_rent_growth": round(total_rent_change, 4),
                    "annualized_rent_growth": round(annualized_rent_change, 4),
                    "cycle_phase": cycle_phase,
                    "horizon_months": horizon_months,
                },
                "drivers": {
                    "population_growth": population_growth,
                    "job_growth": job_growth,
                    "inventory_months_supply": inventory_months,
                    "unemployment_rate": unemployment,
                    "supply_factor": supply_factor,
                },
            },
            confidence=max(0.3, confidence),
            features_used=features,
            model_version=self.model_version,
            latency_ms=latency,
        )
