"""
Rent Prediction Model

Phase 1: Comparable-based with market adjustments
Phase 2: Two-Tower MLP with seasonal adjustment
"""

import math
import time

from app.ai.base import HeuristicModel, ModelOutput


# Baseline rent per sqft by property type (national averages)
BASE_RENT_PER_SQFT = {
    "sfr": 1.25,
    "duplex": 1.15,
    "triplex": 1.10,
    "quadplex": 1.05,
    "multifamily": 1.00,
    "condo": 1.35,
}

# Bedroom multipliers (relative to 3-bed baseline)
BED_MULTIPLIER = {
    0: 0.65,  # Studio
    1: 0.75,
    2: 0.90,
    3: 1.00,
    4: 1.08,
    5: 1.12,
}

# Seasonal adjustment factors (month -> multiplier)
SEASONAL_FACTOR = {
    1: 0.96, 2: 0.96, 3: 0.98, 4: 1.00,
    5: 1.02, 6: 1.04, 7: 1.04, 8: 1.03,
    9: 1.01, 10: 0.99, 11: 0.97, 12: 0.96,
}


class RentPredictorHeuristic(HeuristicModel):
    """Rule-based rent prediction for MVP."""

    def __init__(self):
        super().__init__("rent_predictor_heuristic")
        self.load()

    def predict(self, features: dict) -> ModelOutput:
        start = time.time()

        sqft = features.get("sqft", 1200)
        bedrooms = features.get("bedrooms", 3)
        bathrooms = features.get("bathrooms", 2.0)
        property_type = features.get("property_type", "sfr")
        year_built = features.get("year_built", 2000)
        school_rating = features.get("school_rating", 5.0)
        crime_score = features.get("crime_score", 50.0)
        median_market_rent = features.get("median_market_rent")
        month = features.get("month", 6)  # Current month for seasonality

        # Base calculation
        base_per_sqft = BASE_RENT_PER_SQFT.get(property_type, 1.15)
        bed_mult = BED_MULTIPLIER.get(min(bedrooms, 5), 1.0)
        base_rent = sqft * base_per_sqft * bed_mult

        # Bathroom premium (each half bath over 1 adds ~3%)
        bath_premium = 1.0 + max(0, bathrooms - 1) * 0.03
        base_rent *= bath_premium

        # Age adjustment (newer properties command premium)
        current_year = 2026
        age = current_year - year_built
        if age <= 5:
            age_factor = 1.10
        elif age <= 15:
            age_factor = 1.05
        elif age <= 30:
            age_factor = 1.00
        elif age <= 50:
            age_factor = 0.95
        else:
            age_factor = 0.90
        base_rent *= age_factor

        # Neighborhood adjustment
        school_factor = 1.0 + (school_rating - 5) * 0.02  # ±2% per point from average
        crime_factor = 1.0 - (crime_score - 50) * 0.002  # ±0.2% per point from average
        base_rent *= school_factor * crime_factor

        # If market data available, blend with market-based estimate
        if median_market_rent and median_market_rent > 0:
            market_estimate = median_market_rent * bed_mult * bath_premium
            # 60% market, 40% model
            base_rent = median_market_rent * 0.6 + base_rent * 0.4

        # Seasonal adjustment
        seasonal = SEASONAL_FACTOR.get(month, 1.0)
        final_rent = round(base_rent * seasonal, 2)

        # Pricing recommendations
        competitive = round(final_rent * 0.97, 2)
        premium = round(final_rent * 1.03, 2)

        # Confidence based on data availability
        confidence = 0.5
        if median_market_rent:
            confidence = 0.7
        if features.get("rent_comps_count", 0) >= 5:
            confidence = 0.8

        latency = (time.time() - start) * 1000

        return ModelOutput(
            prediction={
                "estimated_rent": final_rent,
                "rent_range": {"low": competitive, "high": premium},
                "pricing_tiers": {
                    "competitive": competitive,
                    "market_rate": final_rent,
                    "premium": premium,
                },
                "factors": {
                    "base_per_sqft": base_per_sqft,
                    "bedroom_multiplier": bed_mult,
                    "age_factor": age_factor,
                    "school_factor": round(school_factor, 3),
                    "crime_factor": round(crime_factor, 3),
                    "seasonal_factor": seasonal,
                },
            },
            confidence=confidence,
            features_used=features,
            model_version=self.model_version,
            latency_ms=latency,
        )
