"""Convert the supplied Fang.com Shanghai rental CSV to the app schema.

The script never modifies the source file. It preserves source text, parses only
explicit numeric facts, marks implausible rows, and leaves unavailable fields
blank instead of inventing values.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


def extract_number(series: pd.Series, pattern: str) -> pd.Series:
    """Extract the first numeric capture group as a nullable float."""
    return pd.to_numeric(series.astype("string").str.extract(pattern)[0], errors="coerce")


def transform(source: Path) -> pd.DataFrame:
    """Return a standardized, traceable listing table from the source CSV."""
    raw = pd.read_csv(source, encoding="utf-8-sig")
    required = {"房源标题", "租房类型", "房屋规模", "房屋大小", "房屋朝向", "房屋位置", "地铁信息", "房租"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"源文件缺少字段：{', '.join(sorted(missing))}")

    location = raw["房屋位置"].astype("string").str.split("-", expand=True)
    rent = extract_number(raw["房租"], r"(\d+(?:\.\d+)?)")
    area = extract_number(raw["房屋大小"], r"(\d+(?:\.\d+)?)")
    metro = extract_number(raw["地铁信息"], r"约(\d+)米")
    bedrooms = extract_number(raw["房屋规模"], r"(\d+)室")
    living_rooms = extract_number(raw["房屋规模"], r"(\d+)厅")

    def stable_id(row: pd.Series) -> str:
        payload = "|".join(str(row[c]) for c in ["房源标题", "房屋位置", "房屋大小", "房租"])
        return "SH-" + hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12].upper()

    quality = np.where(
        rent.between(500, 100000) & area.between(5, 1000), "eligible", "outlier_excluded"
    )
    result = pd.DataFrame({
        "listing_id": raw.apply(stable_id, axis=1),
        "title": raw["房源标题"].astype("string").str.slice(0, 100),
        "district": location[0].fillna("未知"),
        "subdistrict": location[1] if 1 in location else pd.NA,
        "community": location[2] if 2 in location else pd.NA,
        "monthly_rent": rent,
        "area_sqm": area,
        "commute_minutes": pd.NA,
        "metro_distance_m": metro,
        "rental_type": np.where(raw["租房类型"].eq("整租"), "whole", "shared"),
        "source_rental_type": raw["租房类型"],
        "bedrooms": bedrooms,
        "living_rooms": living_rooms,
        "orientation": raw["房屋朝向"],
        "decoration_score": pd.NA,
        "community_score": pd.NA,
        "safety_score": pd.NA,
        "has_elevator": pd.NA,
        "deposit_months": pd.NA,
        "agency_fee": pd.NA,
        "short_description": raw["房屋规模"].astype(str) + " · " + raw["房屋朝向"].fillna("朝向未提供").astype(str),
        "location_text": raw["房屋位置"],
        "metro_info": raw["地铁信息"],
        "source_rent_text": raw["房租"],
        "source_area_text": raw["房屋大小"],
        "data_source": "房天下-上海租房房源数据.csv（用户提供快照）",
        "source_record_type": "租赁挂牌记录（非成交记录）",
        "data_quality_flag": quality,
    })
    if result["listing_id"].duplicated().any():
        result["listing_id"] = result["listing_id"] + "-" + result.groupby("listing_id").cumcount().astype(str)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/listings.csv"))
    args = parser.parse_args()
    result = transform(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"WROTE {len(result)} rows; eligible={(result.data_quality_flag == 'eligible').sum()}; output={args.output}")


if __name__ == "__main__":
    main()
