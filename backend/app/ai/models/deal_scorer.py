"""
Deal Scoring AI Model

Phase 1: Heuristic scoring (rules-based)
Phase 2: XGBoost + Neural Network ensemble (requires training data)
"""

import time
from dataclasses import dataclass

from app.ai.base import HeuristicModel, ModelBase, ModelOutput


@dataclass
class DealFeatures:
    """Feature vector for deal scoring."""
    # Financial (10)
    cap_rate: float = 0.0
    cash_on_cash_return: float = 0.0
    dscr: float = 0.0
    grm: float = 0.0
    price_per_sqft: float = 0.0
    price_to_rent_ratio: float = 0.0
    expense_ratio: float = 0.0
    noi: float = 0.0
    monthly_cash_flow: float = 0.0
    break_even_ratio: float = 0.0

    # Neighborhood (8)
    crime_score: float = 50.0
    school_rating: float = 5.0
    population_growth: float = 0.01
    job_growth: float = 0.01
    median_income: float = 60000.0
    rent_growth_yoy: float = 0.03
    price_growth_yoy: float = 0.03
    unemployment_rate: float = 0.04

    # Market (4)
    months_supply: float = 4.0
    dom_avg: float = 30.0
    migration_net: float = 0.0
    interest_rate_30yr: float = 0.07

    # Property (4)
    age_years: int = 20
    sqft: int = 1500
    property_type: str = "sfr"
    has_pool: bool = False


class DealScorerHeuristic(HeuristicModel):
    """Rule-based deal scoring for MVP."""

    def __init__(self):
        super().__init__("deal_scorer_heuristic")
        self.load()

    def predict(self, features: dict) -> ModelOutput:
        start = time.time()
        f = DealFeatures(**{k: v for k, v in features.items() if hasattr(DealFeatures, k)})

        score = 0.0
        breakdown = {}

        # Cap rate (0-20)
        cap_pct = f.cap_rate * 100
        breakdown["cap_rate"] = min(20, max(0, (cap_pct - 3) / 7 * 20))

        # Cash-on-cash (0-20)
        coc_pct = f.cash_on_cash_return * 100
        breakdown["cash_on_cash"] = min(20, max(0, (coc_pct - 2) / 10 * 20))

        # DSCR (0-15)
        dscr = min(f.dscr, 3.0) if f.dscr < float("inf") else 3.0
        breakdown["dscr"] = min(15, max(0, (dscr - 0.8) / 1.2 * 15))

        # Monthly cash flow (0-15)
        breakdown["cash_flow"] = min(15, max(0, f.monthly_cash_flow / 400 * 15))

        # Neighborhood (0-15)
        school_score = (f.school_rating / 10) * 5
        crime_score = ((100 - f.crime_score) / 100) * 5
        growth_score = min(5, max(0, f.population_growth * 100))
        breakdown["neighborhood"] = min(15, school_score + crime_score + growth_score)

        # Market conditions (0-15)
        supply_score = min(5, max(0, (8 - f.months_supply) / 4 * 5))
        rent_growth_score = min(5, max(0, f.rent_growth_yoy * 100))
        appreciation_score = min(5, max(0, f.price_growth_yoy * 100))
        breakdown["market"] = min(15, supply_score + rent_growth_score + appreciation_score)

        score = sum(breakdown.values())
        score = round(min(100, max(0, score)), 1)
        breakdown = {k: round(v, 1) for k, v in breakdown.items()}

        latency = (time.time() - start) * 1000

        return ModelOutput(
            prediction={"score": score, "breakdown": breakdown},
            confidence=0.65,  # Lower confidence for heuristic model
            features_used=features,
            model_version=self.model_version,
            latency_ms=latency,
        )


class DealScorerML(ModelBase):
    """
    XGBoost + Neural Network ensemble deal scorer.
    Placeholder for Phase 2 implementation.
    """

    def __init__(self):
        super().__init__("deal_scorer_ml")

    def load(self, model_path: str | None = None) -> None:
        path = model_path or self.get_model_path()
        # Phase 2: Load XGBoost and PyTorch models
        # self.xgb_model = xgb.XGBRegressor()
        # self.xgb_model.load_model(path / "xgb_model.json")
        # self.nn_model = torch.load(path / "nn_model.pt")
        # self.meta_model = joblib.load(path / "meta_model.pkl")
        self.is_loaded = False  # Not yet trained
        self.model_version = "ml_v0"

    def predict(self, features: dict) -> ModelOutput:
        if not self.is_loaded:
            raise RuntimeError("ML model not trained yet. Use heuristic scorer.")

        # Phase 2: Run ensemble
        # xgb_pred = self.xgb_model.predict(feature_vector)
        # nn_pred = self.nn_model(feature_tensor)
        # meta_input = [xgb_pred, nn_pred, features["cap_rate"], features["cash_on_cash"]]
        # final_score = self.meta_model.predict(meta_input)
        return ModelOutput(prediction={"score": 0}, model_version=self.model_version)
