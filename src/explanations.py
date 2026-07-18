"""Balanced rule-based explanations with an optional LLM enhancement."""
from __future__ import annotations
import os
import pandas as pd

LABELS = {"budget_fit":"预算", "location_fit":"目的地区域", "area_fit":"面积", "metro_fit":"地铁便利", "rental_type_fit":"租赁类型", "decoration_fit":"装修", "community_fit":"社区环境", "safety_fit":"安全"}

def rule_based_explanation(recommended, alternatives, preferences: dict) -> str:
    """Generate a factual Chinese explanation containing one benefit and drawback."""
    row = dict(recommended)
    avg_area = float(alternatives["area_sqm"].mean())
    if preferences.get("destination_district") not in (None, "暂不确定/不限") and row.get("district") == preferences.get("destination_district"):
        advantage = f"房源与目的地都位于{row['district']}"
    elif row["monthly_rent"] <= preferences["budget_max"]:
        advantage = f"月租{int(row['monthly_rent'])}元，在你的预算范围内"
    elif pd.notna(row.get("metro_distance_m")) and row["metro_distance_m"] < alternatives["metro_distance_m"].mean():
        advantage = f"距离地铁约{int(row['metro_distance_m'])}米，比本轮其他房源更近"
    else:
        advantage = f"面积为{int(row['area_sqm'])}平方米"
    if row["area_sqm"] < avg_area:
        drawback = f"面积比本轮平均少{round(avg_area-row['area_sqm'])}平方米"
    elif pd.notna(row.get("metro_distance_m")) and row["metro_distance_m"] > 1000:
        drawback = f"距离地铁约{int(row['metro_distance_m'])}米"
    else:
        drawback = f"月租为{int(row['monthly_rent'])}元，仍需结合支付压力判断"
    return f"根据你的声明偏好，我们推荐这套房源：其优点是{advantage}；主要不足是{drawback}。推荐仅供比较参考。"

def optional_llm_explanation(recommended, alternatives, preferences: dict) -> str:
    """Use an OpenAI-compatible API when enabled; otherwise safely use rules."""
    fallback = rule_based_explanation(recommended, alternatives, preferences)
    if os.getenv("ENABLE_LLM", "false").lower() != "true" or not os.getenv("OPENAI_API_KEY"):
        return fallback
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL") or None)
        prompt = f"请将以下租房推荐解释改写为50-100个中文字符，必须保留具体优点、不足和中性语气，不得添加事实：{fallback}"
        text = client.chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), messages=[{"role":"user","content":prompt}], temperature=0.2).choices[0].message.content.strip()
        return text if 35 <= len(text) <= 150 else fallback
    except Exception:
        return fallback
