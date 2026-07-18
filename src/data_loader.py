"""Load and validate simulated rental listings."""
from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = {
    "listing_id", "title", "district", "monthly_rent", "area_sqm",
    "commute_minutes", "metro_distance_m", "rental_type", "bedrooms",
    "decoration_score", "community_score", "safety_score", "has_elevator",
    "deposit_months", "agency_fee", "short_description", "data_source",
    "source_record_type", "data_quality_flag",
}

def load_listings(path: str | Path = "data/listings.csv") -> pd.DataFrame:
    """Return validated listing data from a UTF-8 CSV file."""
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"房源数据缺少字段：{', '.join(sorted(missing))}")
    if len(df) < 36 or df["listing_id"].duplicated().any():
        raise ValueError("房源数据至少需要36条，且 listing_id 必须唯一。")
    if not df["rental_type"].isin(["shared", "studio", "whole"]).all():
        raise ValueError("rental_type 只能为 shared、studio 或 whole。")
    numeric = ["monthly_rent", "area_sqm", "commute_minutes", "metro_distance_m", "bedrooms", "decoration_score", "community_score", "safety_score", "deposit_months", "agency_fee"]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def eligible_listings(df: pd.DataFrame) -> pd.DataFrame:
    """Return listings eligible for choice tasks while retaining the full archive."""
    eligible = df[df["data_quality_flag"].eq("eligible")].copy()
    if len(eligible) < 36:
        raise ValueError("通过质量检查的真实房源不足36条。")
    return eligible
