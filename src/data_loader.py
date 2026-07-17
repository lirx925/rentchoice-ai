"""Load and validate simulated rental listings."""
from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = {
    "listing_id", "title", "district", "monthly_rent", "area_sqm",
    "commute_minutes", "metro_distance_m", "rental_type", "bedrooms",
    "decoration_score", "community_score", "safety_score", "has_elevator",
    "deposit_months", "agency_fee", "short_description",
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
    return df

