"""Transparent, deterministic rental recommendation scoring."""
from __future__ import annotations
import numpy as np
import pandas as pd

def _clamp(value: float) -> float:
    """Clamp a numeric value to the inclusive 0–100 range."""
    return float(np.clip(value, 0, 100))

def _weights(preferences: dict) -> dict[str, float]:
    """Convert importance ratings to normalized model weights."""
    # Accept both names during rolling deployments and for sessions that were
    # created before commute importance was replaced by location importance.
    location_importance = preferences.get(
        "importance_location", preferences.get("importance_commute", 3)
    )
    raw = {
        "budget_fit": preferences["importance_rent"],
        "location_fit": location_importance,
        "area_fit": preferences["importance_area"],
        "metro_fit": preferences["importance_metro"] if preferences["metro_priority"] else 1,
        "rental_type_fit": 3,
    }
    total = sum(raw.values()) or 1
    return {key: value / total for key, value in raw.items()}

def component_scores(listing: pd.Series | dict, preferences: dict) -> dict[str, float]:
    """Calculate five interpretable 0–100 fit components for one listing."""
    x = dict(listing)
    rent, ideal, maximum = x["monthly_rent"], preferences["ideal_rent"], preferences["budget_max"]
    if rent <= ideal:
        budget = 100 - 20 * max(0, ideal - rent) / max(ideal, 1)
    elif rent <= maximum:
        budget = 100 - 35 * (rent - ideal) / max(maximum - ideal, 1)
    else:
        budget = 55 - 80 * (rent - maximum) / max(maximum, 1)
    destination = preferences.get("destination_district", "暂不确定/不限")
    listing_district = x.get("district")
    if pd.isna(listing_district):
        location = 50
    elif destination == "暂不确定/不限":
        location = 50
    elif str(listing_district) == str(destination):
        location = 100
    else:
        location = 40
    area = 100 if x["area_sqm"] >= preferences["min_area"] else 100 * x["area_sqm"] / max(preferences["min_area"], 1) - 25
    metro = 100 - x["metro_distance_m"] / 25 if pd.notna(x.get("metro_distance_m")) else np.nan
    pref = preferences["rental_type_preference"]
    rental = 100 if pref == "no_preference" else (10 if pref == "no_shared" and x["rental_type"] == "shared" else 90)
    return {
        "budget_fit": _clamp(budget), "location_fit": _clamp(location),
        "area_fit": _clamp(area), "metro_fit": _clamp(metro),
        "rental_type_fit": _clamp(rental),
    }

def score_listing(listing: pd.Series | dict, preferences: dict) -> tuple[float, dict[str, float]]:
    """Return deterministic recommendation score and component scores."""
    parts = component_scores(listing, preferences)
    weights = _weights(preferences)
    available = [key for key, value in parts.items() if pd.notna(value)]
    denominator = sum(weights[key] for key in available) or 1
    final = sum(parts[key] * weights[key] for key in available) / denominator
    return round(_clamp(final), 2), parts

def score_listings(listings: pd.DataFrame, preferences: dict) -> pd.DataFrame:
    """Append recommendation and component scores to a listings frame."""
    result = listings.copy()
    scored = [score_listing(row, preferences) for _, row in result.iterrows()]
    result["recommendation_score"] = [x[0] for x in scored]
    for key in scored[0][1]:
        result[key] = [x[1][key] for x in scored]
    return result
