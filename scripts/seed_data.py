"""
Seed REIOS database with realistic market data for top US investment markets.
Run: python scripts/seed_data.py
"""

import asyncio
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.database import async_session, engine, Base
import app.models
from app.models.market import MarketMetrics, NeighborhoodScore, RentComp, MarketForecast
from app.models.financing import Lender, LendingProduct
from app.models.property import Property

# ──────────────────────────────────────────────────────────────
# Market Data: Top 20 Investment Markets
# ──────────────────────────────────────────────────────────────

MARKETS = [
    # (zip, city, state, lat, lon, med_price, med_rent, pop, pop_growth, med_income, unemployment, crime, school, yoy_price, yoy_rent, dom, inventory, absorption)
    ("33602", "Tampa", "FL", 27.9506, -82.4572, 385000, 2100, 405000, 0.021, 58000, 3.2, 38, 7.2, 6.8, 4.2, 22, 1850, 3.1),
    ("27601", "Raleigh", "NC", 35.7796, -78.6382, 410000, 2050, 475000, 0.028, 68000, 2.8, 28, 8.1, 7.2, 4.8, 18, 1420, 2.4),
    ("35801", "Huntsville", "AL", 34.7304, -86.5861, 285000, 1650, 225000, 0.032, 62000, 2.5, 32, 7.5, 8.4, 5.1, 24, 980, 2.8),
    ("78701", "Austin", "TX", 30.2672, -97.7431, 475000, 2350, 1020000, 0.018, 72000, 3.1, 30, 7.8, 4.2, 3.8, 28, 4200, 3.8),
    ("37203", "Nashville", "TN", 36.1627, -86.7816, 420000, 2200, 690000, 0.016, 64000, 2.9, 35, 7.0, 5.5, 3.5, 25, 2800, 3.2),
    ("78205", "San Antonio", "TX", 29.4241, -98.4936, 295000, 1750, 1550000, 0.018, 54000, 3.5, 42, 6.5, 5.8, 3.9, 30, 3100, 3.5),
    ("43215", "Columbus", "OH", 39.9612, -82.9988, 265000, 1580, 905000, 0.015, 56000, 3.4, 40, 6.8, 6.2, 4.1, 26, 2200, 3.0),
    ("46204", "Indianapolis", "IN", 39.7684, -86.1581, 245000, 1450, 880000, 0.012, 52000, 3.6, 45, 6.2, 5.5, 3.8, 28, 2100, 3.3),
    ("28202", "Charlotte", "NC", 35.2271, -80.8431, 395000, 2000, 880000, 0.022, 65000, 3.0, 33, 7.4, 6.5, 4.3, 20, 2400, 2.6),
    ("32801", "Orlando", "FL", 28.5383, -81.3792, 370000, 2050, 310000, 0.019, 55000, 3.3, 38, 6.8, 6.0, 4.0, 24, 1800, 2.9),
    ("85001", "Phoenix", "AZ", 33.4484, -112.0740, 420000, 1950, 1680000, 0.014, 60000, 3.4, 42, 6.5, 3.2, 2.8, 32, 5200, 4.2),
    ("80202", "Denver", "CO", 39.7392, -104.9903, 550000, 2400, 715000, 0.010, 76000, 2.8, 30, 7.6, 2.5, 2.2, 30, 3100, 3.8),
    ("30303", "Atlanta", "GA", 33.7490, -84.3880, 365000, 1900, 500000, 0.017, 62000, 3.2, 44, 6.9, 5.8, 3.8, 26, 2600, 3.0),
    ("64106", "Kansas City", "MO", 39.0997, -94.5786, 235000, 1350, 505000, 0.008, 54000, 3.5, 48, 6.0, 5.2, 3.5, 28, 1900, 3.4),
    ("39201", "Jackson", "MS", 32.2988, -90.1848, 165000, 1100, 170000, 0.005, 42000, 4.2, 55, 5.2, 4.8, 3.2, 35, 750, 4.0),
    ("29401", "Charleston", "SC", 32.7765, -79.9311, 485000, 2250, 150000, 0.024, 70000, 2.6, 25, 8.0, 7.5, 4.5, 18, 950, 2.2),
    ("37402", "Chattanooga", "TN", 35.0456, -85.3097, 275000, 1550, 185000, 0.014, 50000, 3.2, 38, 6.5, 6.0, 3.8, 26, 800, 2.8),
    ("32301", "Tallahassee", "FL", 30.4383, -84.2807, 255000, 1400, 195000, 0.011, 48000, 3.4, 40, 6.8, 5.5, 3.5, 28, 850, 3.2),
    ("35203", "Birmingham", "AL", 33.5186, -86.8104, 210000, 1250, 200000, 0.006, 46000, 3.8, 50, 5.8, 4.5, 3.0, 32, 950, 3.6),
    ("73102", "Oklahoma City", "OK", 35.4676, -97.5164, 225000, 1300, 680000, 0.010, 52000, 3.3, 44, 6.0, 4.8, 3.2, 30, 2400, 3.5),
]

LENDERS = [
    {
        "name": "Kiavi",
        "type": "hard_money",
        "website": "https://www.kiavi.com",
        "geographic_areas": ["ALL"],
        "products": [
            {"name": "Fix & Flip Bridge Loan", "loan_type": "hard_money", "min_credit_score": 680, "max_ltv": 0.90, "rate_low": 0.095, "rate_high": 0.12, "min_loan": 100000, "max_loan": 1500000, "property_types": ["sfr", "duplex", "triplex", "quadplex"]},
            {"name": "DSCR Rental Loan", "loan_type": "dscr", "min_credit_score": 660, "max_ltv": 0.80, "rate_low": 0.07, "rate_high": 0.09, "min_loan": 75000, "max_loan": 2000000, "property_types": ["sfr", "duplex", "triplex", "quadplex", "multifamily"]},
        ],
    },
    {
        "name": "Lima One Capital",
        "type": "dscr_lender",
        "website": "https://www.limaone.com",
        "geographic_areas": ["ALL"],
        "products": [
            {"name": "Rental30 DSCR", "loan_type": "dscr", "min_credit_score": 680, "max_ltv": 0.80, "rate_low": 0.065, "rate_high": 0.085, "min_loan": 75000, "max_loan": 3000000, "property_types": ["sfr", "duplex", "triplex", "quadplex"]},
            {"name": "FixNFlip", "loan_type": "hard_money", "min_credit_score": 700, "max_ltv": 0.92, "rate_low": 0.09, "rate_high": 0.115, "min_loan": 75000, "max_loan": 2500000, "property_types": ["sfr"]},
        ],
    },
    {
        "name": "Visio Lending",
        "type": "dscr_lender",
        "website": "https://www.visiolending.com",
        "geographic_areas": ["ALL"],
        "products": [
            {"name": "Rental360 DSCR", "loan_type": "dscr", "min_credit_score": 680, "max_ltv": 0.80, "rate_low": 0.068, "rate_high": 0.088, "min_loan": 100000, "max_loan": 2000000, "property_types": ["sfr", "duplex", "triplex", "quadplex"]},
        ],
    },
    {
        "name": "Angel Oak Mortgage",
        "type": "portfolio_lender",
        "website": "https://angeloakmortgage.com",
        "geographic_areas": ["ALL"],
        "products": [
            {"name": "Investor Cash Flow", "loan_type": "dscr", "min_credit_score": 640, "max_ltv": 0.85, "rate_low": 0.072, "rate_high": 0.095, "min_loan": 150000, "max_loan": 3500000, "property_types": ["sfr", "duplex", "triplex", "quadplex", "multifamily"]},
            {"name": "Bank Statement Loan", "loan_type": "conventional", "min_credit_score": 700, "max_ltv": 0.80, "rate_low": 0.065, "rate_high": 0.08, "min_loan": 200000, "max_loan": 3000000, "property_types": ["sfr"]},
        ],
    },
    {
        "name": "RCN Capital",
        "type": "hard_money",
        "website": "https://www.rcncapital.com",
        "geographic_areas": ["ALL"],
        "products": [
            {"name": "Fix & Flip", "loan_type": "hard_money", "min_credit_score": 660, "max_ltv": 0.90, "rate_low": 0.099, "rate_high": 0.125, "min_loan": 50000, "max_loan": 2500000, "property_types": ["sfr", "duplex", "triplex", "quadplex"]},
            {"name": "Long-Term Rental", "loan_type": "dscr", "min_credit_score": 660, "max_ltv": 0.80, "rate_low": 0.069, "rate_high": 0.089, "min_loan": 75000, "max_loan": 2000000, "property_types": ["sfr", "duplex", "triplex", "quadplex", "multifamily"]},
        ],
    },
    {
        "name": "New Western Funding",
        "type": "hard_money",
        "website": "https://www.newwestern.com",
        "geographic_areas": ["TX", "FL", "GA", "NC", "TN"],
        "products": [
            {"name": "Wholesale Bridge", "loan_type": "hard_money", "min_credit_score": 620, "max_ltv": 0.85, "rate_low": 0.11, "rate_high": 0.14, "min_loan": 30000, "max_loan": 500000, "property_types": ["sfr"]},
        ],
    },
]

# Sample off-market properties for sourcing demo
OFF_MARKET_PROPERTIES = [
    ("45 Main Street", "Tampa", "FL", "33601", 27.9475, -82.4584, "sfr", 3, 2, 1680, 2004, 310000, "pre_foreclosure", 91, 0.22),
    ("789 Birch Road", "Austin", "TX", "78745", 30.2100, -97.7950, "sfr", 4, 2.5, 2100, 1998, 385000, "tax_lien", 76, 0.15),
    ("321 Willow Court", "Nashville", "TN", "37215", 36.1100, -86.8400, "sfr", 3, 1.5, 1420, 1985, 265000, "probate", 83, 0.18),
    ("1567 River Bend", "Raleigh", "NC", "27604", 35.8100, -78.6100, "sfr", 3, 2, 1550, 2001, 295000, "pre_foreclosure", 88, 0.20),
    ("422 Peachtree Ln", "Atlanta", "GA", "30308", 33.7700, -84.3700, "duplex", 4, 3, 2400, 1995, 340000, "divorce", 72, 0.12),
    ("890 Desert Vista", "Phoenix", "AZ", "85004", 33.4500, -112.0600, "sfr", 3, 2, 1750, 2006, 355000, "vacancy", 65, 0.08),
    ("234 Palmetto Way", "Charleston", "SC", "29403", 32.7900, -79.9400, "sfr", 3, 2, 1380, 1992, 420000, "absentee", 58, 0.10),
    ("678 Magnolia Dr", "Tampa", "FL", "33609", 27.9350, -82.5100, "sfr", 4, 2, 1920, 2000, 375000, "code_violation", 79, 0.17),
    ("1100 Oak Hill Rd", "Huntsville", "AL", "35802", 34.7000, -86.5500, "sfr", 3, 2, 1600, 2003, 225000, "tax_lien", 85, 0.25),
    ("555 Elm Street", "San Antonio", "TX", "78210", 29.4000, -98.4600, "sfr", 3, 1, 1200, 1978, 175000, "pre_foreclosure", 92, 0.28),
    ("901 Cherry Blossom", "Orlando", "FL", "32803", 28.5500, -81.3500, "sfr", 3, 2, 1550, 2005, 330000, "probate", 74, 0.14),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # ── Market Metrics (12 months per market) ──
        print("Seeding market metrics...")
        count = 0
        for zip_code, city, state, lat, lon, price, rent, pop, pop_g, income, unemp, crime, school, yoy_p, yoy_r, dom, inv, absorb in MARKETS:
            for months_ago in range(12):
                m = date(2026, 3, 1)
                month = date(m.year if m.month - months_ago > 0 else m.year - 1,
                            (m.month - months_ago - 1) % 12 + 1, 1)
                factor = 1 - months_ago * (yoy_p / 100 / 12)
                rent_factor = 1 - months_ago * (yoy_r / 100 / 12)

                metrics = MarketMetrics(
                    id=str(uuid.uuid4()),
                    geo_id=zip_code,
                    geo_type="zip",
                    month=month,
                    median_list_price=round(price * factor * 1.03, 2),
                    median_sold_price=round(price * factor, 2),
                    median_price_per_sqft=round(price * factor / 1500, 2),
                    median_dom=dom + months_ago,
                    active_inventory=inv + months_ago * 20,
                    monthly_sales=max(10, int(inv / absorb) - months_ago * 2),
                    absorption_rate=round(absorb + months_ago * 0.05, 2),
                    median_rent=round(rent * rent_factor, 2),
                    rent_yield=round((rent * 12) / price * 100, 3),
                    yoy_price_change=round(yoy_p - months_ago * 0.1, 2),
                    yoy_rent_change=round(yoy_r - months_ago * 0.05, 2),
                    population=pop,
                    population_growth=round(pop_g, 3),
                    median_income=income,
                    unemployment_rate=round(unemp, 2),
                    crime_index=round(crime, 2),
                    school_rating=round(school, 1),
                )
                session.add(metrics)
                count += 1
        print(f"  {count} market metric records")

        # ── Neighborhood Scores ──
        print("Seeding neighborhood scores...")
        for zip_code, city, state, lat, lon, price, rent, pop, pop_g, income, unemp, crime, school, yoy_p, yoy_r, *_ in MARKETS:
            # Composite score
            rent_yield = (rent * 12) / price * 100
            score = (
                (10 - school) * -3 +          # school (higher = better)
                (100 - crime) * 0.3 +          # crime (lower = better)
                pop_g * 500 +                  # population growth
                yoy_p * 2 +                    # appreciation
                rent_yield * 5 +               # rent yield
                (5 - unemp) * 3               # low unemployment
            )
            score = round(min(100, max(0, score)), 1)

            if score >= 85: grade = "A"
            elif score >= 75: grade = "A-"
            elif score >= 65: grade = "B+"
            elif score >= 55: grade = "B"
            elif score >= 45: grade = "B-"
            elif score >= 35: grade = "C+"
            else: grade = "C"

            ns = NeighborhoodScore(
                id=str(uuid.uuid4()),
                geo_id=zip_code,
                geo_type="zip",
                overall_grade=grade,
                overall_score=score,
                scores={
                    "school_rating": school,
                    "crime_safety": round(100 - crime, 1),
                    "population_growth": round(pop_g * 100, 2),
                    "price_appreciation": yoy_p,
                    "rent_yield": round(rent_yield, 2),
                    "job_market": round(100 - unemp * 10, 1),
                },
            )
            session.add(ns)
        print(f"  {len(MARKETS)} neighborhood scores")

        # ── Market Forecasts ──
        print("Seeding market forecasts...")
        for zip_code, city, state, _, _, price, rent, _, pop_g, _, _, _, _, yoy_p, yoy_r, *_ in MARKETS:
            for horizon in [6, 12, 24, 36]:
                base_price_growth = yoy_p / 100
                base_rent_growth = yoy_r / 100
                damped_price = base_price_growth * (1 - horizon / 72)
                damped_rent = base_rent_growth * (1 - horizon / 72)

                session.add(MarketForecast(
                    id=str(uuid.uuid4()),
                    geo_id=zip_code,
                    forecast_date=date(2026, 3, 16),
                    horizon_months=horizon,
                    metric="price_appreciation",
                    p10=round(damped_price * 0.5 * (horizon / 12), 4),
                    p50=round(damped_price * (horizon / 12), 4),
                    p90=round(damped_price * 1.5 * (horizon / 12), 4),
                    model_version="heuristic_v1",
                ))
                session.add(MarketForecast(
                    id=str(uuid.uuid4()),
                    geo_id=zip_code,
                    forecast_date=date(2026, 3, 16),
                    horizon_months=horizon,
                    metric="rent_growth",
                    p10=round(damped_rent * 0.5 * (horizon / 12), 4),
                    p50=round(damped_rent * (horizon / 12), 4),
                    p90=round(damped_rent * 1.5 * (horizon / 12), 4),
                    model_version="heuristic_v1",
                ))
        print(f"  {len(MARKETS) * 4 * 2} forecast records")

        # ── Rent Comps (5 per market) ──
        print("Seeding rent comps...")
        import random
        random.seed(42)
        rc = 0
        for zip_code, city, state, lat, lon, price, rent, *_ in MARKETS:
            for i in range(5):
                beds = random.choice([2, 3, 3, 3, 4])
                baths = random.choice([1, 1.5, 2, 2, 2.5])
                sqft = random.randint(900, 2200)
                rent_amt = round(rent * random.uniform(0.85, 1.15), 2)

                session.add(RentComp(
                    id=str(uuid.uuid4()),
                    address=f"{random.randint(100, 9999)} {random.choice(['Oak', 'Pine', 'Elm', 'Cedar', 'Maple'])} {random.choice(['St', 'Ave', 'Dr', 'Ln', 'Ct'])}",
                    latitude=round(lat + random.uniform(-0.02, 0.02), 6),
                    longitude=round(lon + random.uniform(-0.02, 0.02), 6),
                    bedrooms=beds,
                    bathrooms=baths,
                    sqft=sqft,
                    rent_amount=rent_amt,
                    source=random.choice(["zillow", "rentometer", "manual"]),
                    effective_date=date(2026, random.randint(1, 3), random.randint(1, 28)),
                ))
                rc += 1
        print(f"  {rc} rent comps")

        # ── Lenders & Products ──
        print("Seeding lenders and products...")
        lender_count = 0
        product_count = 0
        for ldata in LENDERS:
            lender = Lender(
                id=str(uuid.uuid4()),
                name=ldata["name"],
                type=ldata["type"],
                website=ldata["website"],
                geographic_areas=ldata["geographic_areas"],
                contact={"email": f"info@{ldata['name'].lower().replace(' ', '')}.com"},
            )
            session.add(lender)
            await session.flush()
            lender_count += 1

            for pdata in ldata["products"]:
                product = LendingProduct(
                    id=str(uuid.uuid4()),
                    lender_id=lender.id,
                    name=pdata["name"],
                    loan_type=pdata["loan_type"],
                    min_credit_score=pdata["min_credit_score"],
                    max_ltv=pdata["max_ltv"],
                    rate_range_low=pdata["rate_low"],
                    rate_range_high=pdata["rate_high"],
                    min_loan_amount=pdata["min_loan"],
                    max_loan_amount=pdata["max_loan"],
                    property_types=pdata["property_types"],
                )
                session.add(product)
                product_count += 1
        print(f"  {lender_count} lenders, {product_count} products")

        # ── Off-Market Properties (for sourcing) ──
        print("Seeding off-market properties...")
        for addr, city, state, zip_code, lat, lon, ptype, beds, baths, sqft, year, est_value, signal_type, motivation, discount in OFF_MARKET_PROPERTIES:
            prop = Property(
                id=str(uuid.uuid4()),
                address=addr,
                city=city,
                state=state,
                zip=zip_code,
                latitude=lat,
                longitude=lon,
                property_type=ptype,
                bedrooms=beds,
                bathrooms=baths,
                sqft=sqft,
                year_built=year,
                features={
                    "off_market": True,
                    "signal_type": signal_type,
                    "motivation_score": motivation,
                    "estimated_discount": discount,
                    "estimated_value": est_value,
                },
            )
            session.add(prop)
        print(f"  {len(OFF_MARKET_PROPERTIES)} off-market properties")

        await session.commit()
        print("\nSeed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
