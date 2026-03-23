"""
Automated Valuation Model (AVM)

Phase 1: Comparable-based weighted average
Phase 2: FAISS + CatBoost adjustment model
"""

import math
import time
from dataclasses import dataclass

from app.ai.base import HeuristicModel, ModelOutput


@dataclass
class PropertyFeatures:
    latitude: float
    longitude: float
    bedrooms: int
    bathrooms: float
    sqft: int
    year_built: int
    property_type: str = "sfr"
    lot_sqft: int = 0
    pool: bool = False
    garage_spaces: int = 0


@dataclass
class CompSale:
    address: str
    sale_price: float
    sale_date: str
    bedrooms: int
    bathrooms: float
    sqft: int
    year_built: int
    latitude: float
    longitude: float
    distance_miles: float = 0.0
    similarity_score: float = 0.0
    adjusted_price: float = 0.0
    adjustments: dict = None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in miles between two coordinates."""
    R = 3959  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


class AVMHeuristic(HeuristicModel):
    """Comparable-based AVM for MVP."""

    def __init__(self):
        super().__init__("avm_heuristic")
        self.load()

        # Per-unit adjustment rates (dollars per unit of difference)
        self.sqft_adj_rate = 100.0  # $ per sqft difference
        self.bed_adj_rate = 10000.0  # $ per bedroom difference
        self.bath_adj_rate = 7500.0  # $ per bathroom difference
        self.age_adj_rate = 500.0  # $ per year of age difference
        self.pool_adj = 15000.0  # $ for pool
        self.garage_adj_rate = 8000.0  # $ per garage space

    def calculate_similarity(self, subject: PropertyFeatures, comp: CompSale) -> float:
        """Score how similar a comp is to the subject (0-1)."""
        distance = haversine_distance(
            subject.latitude, subject.longitude,
            comp.latitude, comp.longitude,
        )
        comp.distance_miles = round(distance, 2)

        # Distance weight (exponential decay)
        dist_score = math.exp(-distance / 0.5)  # Half-life at 0.5 miles

        # Size similarity
        sqft_diff_pct = abs(subject.sqft - comp.sqft) / max(subject.sqft, 1)
        size_score = max(0, 1 - sqft_diff_pct)

        # Bedroom match
        bed_score = max(0, 1 - abs(subject.bedrooms - comp.bedrooms) * 0.25)

        # Age similarity
        age_diff = abs(subject.year_built - comp.year_built)
        age_score = max(0, 1 - age_diff / 30)

        # Weighted composite
        similarity = (
            dist_score * 0.35
            + size_score * 0.30
            + bed_score * 0.20
            + age_score * 0.15
        )
        return round(similarity, 3)

    def adjust_comp(self, subject: PropertyFeatures, comp: CompSale) -> CompSale:
        """Adjust comp price to subject's characteristics."""
        adjustments = {}
        total_adj = 0.0

        # Square footage
        sqft_diff = subject.sqft - comp.sqft
        sqft_adj = sqft_diff * self.sqft_adj_rate
        adjustments["sqft"] = round(sqft_adj)
        total_adj += sqft_adj

        # Bedrooms
        bed_diff = subject.bedrooms - comp.bedrooms
        bed_adj = bed_diff * self.bed_adj_rate
        adjustments["bedrooms"] = round(bed_adj)
        total_adj += bed_adj

        # Bathrooms
        bath_diff = subject.bathrooms - comp.bathrooms
        bath_adj = bath_diff * self.bath_adj_rate
        adjustments["bathrooms"] = round(bath_adj)
        total_adj += bath_adj

        # Age
        age_diff = comp.year_built - subject.year_built  # Newer comp = negative adj
        age_adj = age_diff * self.age_adj_rate
        adjustments["age"] = round(age_adj)
        total_adj += age_adj

        comp.adjustments = adjustments
        comp.adjusted_price = round(comp.sale_price + total_adj, 2)
        return comp

    def predict(self, features: dict) -> ModelOutput:
        start = time.time()

        subject = PropertyFeatures(**{k: v for k, v in features.get("subject", {}).items()
                                      if hasattr(PropertyFeatures, k)})
        comps_data = features.get("comps", [])

        if not comps_data:
            return ModelOutput(
                prediction={"estimated_value": None, "confidence_interval": None, "comps": []},
                confidence=0.0,
                model_version=self.model_version,
            )

        # Build comp objects
        comps = []
        for c in comps_data:
            comp = CompSale(**{k: v for k, v in c.items() if hasattr(CompSale, k)})
            comp.similarity_score = self.calculate_similarity(subject, comp)
            comp = self.adjust_comp(subject, comp)
            comps.append(comp)

        # Sort by similarity and take top 5
        comps.sort(key=lambda x: x.similarity_score, reverse=True)
        top_comps = comps[:5]

        # Weighted average of adjusted prices
        total_weight = sum(c.similarity_score for c in top_comps)
        if total_weight > 0:
            estimated_value = sum(
                c.adjusted_price * c.similarity_score for c in top_comps
            ) / total_weight
        else:
            estimated_value = sum(c.adjusted_price for c in top_comps) / len(top_comps)

        estimated_value = round(estimated_value, 2)

        # Confidence interval (simple: ±1 std dev of adjusted prices)
        prices = [c.adjusted_price for c in top_comps]
        if len(prices) > 1:
            mean = sum(prices) / len(prices)
            variance = sum((p - mean) ** 2 for p in prices) / (len(prices) - 1)
            std = math.sqrt(variance)
            ci_low = round(estimated_value - std, 2)
            ci_high = round(estimated_value + std, 2)
        else:
            ci_low = round(estimated_value * 0.9, 2)
            ci_high = round(estimated_value * 1.1, 2)

        confidence = min(0.95, 0.5 + len(top_comps) * 0.09)

        latency = (time.time() - start) * 1000

        return ModelOutput(
            prediction={
                "estimated_value": estimated_value,
                "confidence_interval": {"low": ci_low, "high": ci_high},
                "comps_used": len(top_comps),
                "comps": [
                    {
                        "address": c.address,
                        "sale_price": c.sale_price,
                        "adjusted_price": c.adjusted_price,
                        "similarity_score": c.similarity_score,
                        "distance_miles": c.distance_miles,
                        "adjustments": c.adjustments,
                    }
                    for c in top_comps
                ],
            },
            confidence=confidence,
            model_version=self.model_version,
            latency_ms=latency,
        )
