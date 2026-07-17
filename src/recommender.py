"""Transparent, deterministic rental recommendation scoring."""
from __future__ import annotations
import numpy as np
import pandas as pd

def _clamp(value: float) -> float:
    """Clamp a numeric value to the inclusive 0–100 range."""
    return float(np.clip(value, 0, 100))

def _weights(preferences: dict) -> dict[str, float]:
    """Convert importance ratings to normalized model weights."""
    raw = {
        "budget_fit": preferences["importance_rent"],
        "commute_fit": preferences["importance_commute"],
        "area_fit": preferences["importance_area"],
        "metro_fit": preferences["importance_metro"] if preferences["metro_priority"] else 1,
        "rental_type_fit": 3,
        "decoration_fit": preferences["importance_decoration"],
        "community_fit": preferences["importance_community"],
        "safety_fit": preferences["importance_safety"],
    }
    total = sum(raw.values()) or 1
    return {key: value / total for key, value in raw.items()}

def component_scores(listing: pd.Series | dict, preferences: dict) -> dict[str, float]:
    """Calculate eight interpretable 0–100 fit components for one listing."""
    x = dict(listing)
    rent, ideal, maximum = x["monthly_rent"], preferences["ideal_rent"], preferences["budget_max"]
    if rent <= ideal:
        budget = 100 - 20 * max(0, ideal - rent) / max(ideal, 1)
    elif rent <= maximum:
        budget = 100 - 35 * (rent - ideal) / max(maximum - ideal, 1)
    else:
        budget = 55 - 80 * (rent - maximum) / max(maximum, 1)
    commute = 100 - (35 * x["commute_minutes"] / max(preferences["max_commute"], 1))
    if x["commute_minutes"] > preferences["max_commute"]:
        commute -= 40 * (x["commute_minutes"] - preferences["max_commute"]) / max(preferences["max_commute"], 1)
    area = 100 if x["area_sqm"] >= preferences["min_area"] else 100 * x["area_sqm"] / max(preferences["min_area"], 1) - 25
    metro = 100 - x["metro_distance_m"] / 25
    pref = preferences["rental_type_preference"]
    rental = 100 if pref == "no_preference" else (10 if pref == "no_shared" and x["rental_type"] == "shared" else 90)
    return {
        "budget_fit": _clamp(budget), "commute_fit": _clamp(commute),
        "area_fit": _clamp(area), "metro_fit": _clamp(metro),
        "rental_type_fit": _clamp(rental),
        "decoration_fit": _clamp(x["decoration_score"] * 20),
        "community_fit": _clamp(x["community_score"] * 20),
        "safety_fit": _clamp(x["safety_score"] * 20),
    }

def score_listing(listing: pd.Series | dict, preferences: dict) -> tuple[float, dict[str, float]]:
    """Return deterministic recommendation score and component scores."""
    parts = component_scores(listing, preferences)
    weights = _weights(preferences)
    final = sum(parts[key] * weights[key] for key in parts)
    return round(_clamp(final), 2), parts

def score_listings(listings: pd.DataFrame, preferences: dict) -> pd.DataFrame:
    """Append recommendation and component scores to a listings frame."""
    result = listings.copy()
    scored = [score_listing(row, preferences) for _, row in result.iterrows()]
    result["recommendation_score"] = [x[0] for x in scored]
    for key in scored[0][1]:
        result[key] = [x[1][key] for x in scored]
    return result

