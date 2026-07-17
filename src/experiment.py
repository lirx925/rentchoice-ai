"""Participant assignment and reproducible choice-set construction."""
from __future__ import annotations
import hashlib, os
import numpy as np
import pandas as pd

GROUPS = ("control", "score_only", "explained")
TOTAL_ROUNDS = 6

def assign_treatment(participant_id: str, seed: str | None = None) -> str:
    """Assign one stable treatment using a salted participant hash."""
    salt = seed if seed is not None else os.getenv("EXPERIMENT_SEED", "rentchoice-production")
    number = int(hashlib.sha256(f"{salt}:{participant_id}".encode()).hexdigest()[:12], 16)
    return GROUPS[number % len(GROUPS)]

def build_choice_sets(listings: pd.DataFrame, participant_id: str, rounds: int = TOTAL_ROUNDS) -> list[list[str]]:
    """Build rounds of three distinct, randomized listings with attribute trade-offs."""
    seed = int(hashlib.sha256(participant_id.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    pool = listings.copy()
    pool["rent_band"] = pd.qcut(pool["monthly_rent"], 3, labels=False, duplicates="drop")
    sets = []
    for r in range(rounds):
        chosen = []
        for band in sorted(pool["rent_band"].unique()):
            candidates = pool[pool["rent_band"] == band]
            available = candidates[~candidates["listing_id"].isin(chosen)]
            chosen.append(str(rng.choice(available["listing_id"].to_numpy())))
        rng.shuffle(chosen)
        sets.append(chosen)
    return sets

def welfare_metrics(scored_options: pd.DataFrame, chosen_id: str) -> tuple[float, float, float]:
    """Return chosen utility, best utility, and non-negative proxy welfare loss."""
    chosen = float(scored_options.loc[scored_options["listing_id"] == chosen_id, "recommendation_score"].iloc[0])
    best = float(scored_options["recommendation_score"].max())
    return chosen, best, round(max(0.0, best - chosen), 2)

