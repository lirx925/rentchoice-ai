"""Small analysis helpers shared by result and admin pages."""
import pandas as pd

def participant_summary(choices: pd.DataFrame) -> dict:
    """Calculate participant-level summary statistics."""
    return {
        "avg_time": float(choices["decision_time_seconds"].mean()),
        "avg_satisfaction": float(choices["satisfaction"].mean()),
        "follow_rate": float(choices["recommendation_followed"].mean()),
    }

def group_summary(choices: pd.DataFrame) -> pd.DataFrame:
    """Aggregate primary outcomes by treatment group."""
    if choices.empty: return pd.DataFrame()
    return choices.groupby("treatment_group", as_index=False).agg(participants=("participant_id","nunique"), avg_decision_time=("decision_time_seconds","mean"), avg_satisfaction=("satisfaction","mean"), recommendation_follow_rate=("recommendation_followed","mean"), avg_wtp=("willingness_to_pay","mean"), avg_welfare_loss=("welfare_loss","mean"))
