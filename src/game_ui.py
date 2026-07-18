"""Game-styled presentation layer for RentChoice AI (v4 - Mario-style street).

Design note on what's technically possible in Streamlit: Streamlit is a
server-rerun framework, not a real-time game engine — a generic
components.html() iframe cannot send keyboard/mouse events back to the
Python session without building a full custom bidirectional component
(components.declare_component with a JS<->Python bridge), which is a
much bigger undertaking than a course-project UI skin. So instead of
fake "arrow key control" that silently wouldn't work, this module gives
the player REAL left/right movement through ordinary Streamlit buttons:
each press changes st.session_state.street_x and triggers a rerun, and
the street scene re-renders the character at the new position — so
movement, door proximity, and coin pickups are all genuinely stateful,
not just decorative. Sprite bobbing/idle animation is CSS, driven by the
iframe's own JS clock (safe, one-directional, doesn't need a bridge).

Everything in this module is presentation/interaction sugar layered on
top of the untouched experiment logic. Coins, collected-coin positions,
and street position live in st.session_state under game-only keys and
are NEVER passed to save_participant / save_choice / save_post_survey —
the saved dataset schema in docs/variable_dictionary.md is unaffected.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------------------------------
# Theme / CSS
# --------------------------------------------------------------------------

GAME_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --dusk-top:#241645; --dusk-bot:#ff8a5b; --panel:#241a40; --panel-2:#2f2354;
  --amber:#FFD166; --coral:#FF6B5C; --mint:#6FCF97; --ink:#F4EFFF; --mist:#B7A9E0;
}
.block-container{max-width:1100px; padding-top:1.4rem;}
.stApp{ background:#150c29; }
h1,h2,h3,h4{ color:var(--ink) !important; }
p, span, label, .stMarkdown{ color:var(--ink); }
.pxl{ font-family:'Press Start 2P', monospace; color:var(--amber); letter-spacing:.5px; }
.story-box{
  background:var(--panel); border:2px solid #4a3b78; border-radius:14px;
  padding:14px 18px; color:#E4DBFF; font-size:.95rem; line-height:1.7; margin-bottom:14px;
}
.game-card{
  background:linear-gradient(180deg,#2f2354,#241a40); border:2px solid #4a3b78; border-radius:16px;
  padding:16px; min-height:360px; color:var(--ink); position:relative; transition:transform .15s ease;
}
.game-card.recommended{ border-color:var(--amber); box-shadow:0 0 0 2px rgba(255,209,102,.25); }
.game-card.locked{ opacity:.55; filter:grayscale(.4); }
.game-badge{
  display:inline-block; background:var(--coral); color:#3a0f0a; font-size:.72rem; font-weight:700;
  padding:3px 9px; border-radius:20px; margin-bottom:6px;
}
.game-muted{ color:var(--mist); font-size:.85rem; }
.game-price{ font-family:'Space Grotesk',sans-serif; font-size:1.6rem; font-weight:700; color:var(--amber); }
.landlord-tag{
  font-size:.72rem; color:var(--mist); display:flex; align-items:center; gap:5px; margin-bottom:6px;
}
.quest-row{ display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 14px; }
.quest-chip{
  font-family:'Space Grotesk',sans-serif; font-size:.72rem; color:var(--mist);
  border:1px solid #4a3b78; padding:4px 10px; border-radius:20px;
}
.hud-row{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:10px; font-family:'Space Grotesk',sans-serif; }
.hud-chip{ display:flex; align-items:center; gap:6px; background:var(--panel-2); border:1px solid #4a3b78; border-radius:20px; padding:5px 12px; font-size:.82rem; color:var(--ink); }
.hud-chip.coin{ color:var(--amber); border-color:#8a6a1f; }
.hud-chip.streak{ color:var(--mint); border-color:#2f6d4e; }
.badge-shelf{ display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; }
.badge-pill{ background:linear-gradient(180deg,#2f2354,#241a40); border:2px solid var(--amber); border-radius:14px; padding:10px 14px; min-width:150px; text-align:center; animation: popin .3s ease; }
.badge-pill .ic{ font-size:1.6rem; }
.badge-pill .t{ font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:.85rem; margin-top:2px; }
.badge-pill .d{ color:var(--mist); font-size:.72rem; margin-top:2px; }
.avatar-caption{ text-align:center; font-size:.78rem; color:var(--mist); margin-top:2px; }
.dialogue-box{
  background:var(--panel); border:3px solid var(--amber); border-radius:14px; padding:14px 18px;
  margin:8px 0 4px; animation: doorpop .35s cubic-bezier(.34,1.56,.64,1);
}
.dialogue-head{ display:flex; align-items:center; gap:10px; margin-bottom:6px; }
.dialogue-portrait{ width:38px;height:38px;border-radius:10px;background:var(--coral); display:flex;align-items:center;justify-content:center;font-size:20px; flex-shrink:0; }
.dialogue-name{ font-family:'Space Grotesk',sans-serif; font-weight:700; color:var(--amber); }
.dialogue-text{ font-size:.9rem; line-height:1.7; color:#F4EFFF; min-height:44px; }
.dialogue-page{ text-align:right; font-size:.72rem; color:var(--mist); margin-top:6px; }
.clear-banner{
  text-align:center; padding:22px 10px; background:linear-gradient(180deg,#2f2354,#1c1240);
  border:2px solid var(--amber); border-radius:16px; margin-bottom:12px; animation: popin .4s ease;
}
.stButton>button{ border-radius:10px; font-weight:700; transition:transform .1s ease; }
.stButton>button:active{ transform:scale(.97); }
button[kind="primary"]{ background:var(--amber) !important; color:#3a2205 !important; border:none !important; box-shadow:0 4px 0 #b8862f !important; }
button[kind="secondary"]{ background:transparent !important; border:1px solid #4a3b78 !important; color:var(--mist) !important; }
@keyframes fadein{ from{opacity:0; transform:translateY(4px);} to{opacity:1; transform:translateY(0);} }
@keyframes popin{ from{opacity:0; transform:scale(.85);} to{opacity:1; transform:scale(1);} }
@keyframes doorpop{ from{opacity:0; transform:scale(.9) translateY(6px);} to{opacity:1; transform:scale(1) translateY(0);} }
</style>
"""

ROUND_STORY = {
    1: ("第一站", "刚下地铁，你打开「落脚」，划到了这一片的房源——"),
    2: ("第二站", "继续往前走，中介发来了新一批选项——"),
    3: ("第三站", "天色渐暗，你决定再往前多看看——"),
    4: ("第四站", "路过一条老街，这里的价格实在诱人——"),
    5: ("第五站", "眼看快到公司附近了，通勤会不会更短——"),
    6: ("最后一站", "如果只能选一个「家」，会是哪一套——"),
}

# --------------------------------------------------------------------------
# Street geometry — shared constants so app.py and game_ui.py agree on
# where doors/coins sit without duplicating magic numbers.
# --------------------------------------------------------------------------

STREET_WIDTH = 820
DOOR_X = {"A": 140, "B": 400, "C": 660}
COIN_X = [55, 270, 530, 760]
MOVE_STEP = 55
RUN_STEP = 130
KNOCK_RANGE = 60
COIN_RANGE = 28

AVATARS = [
    {"id": "scout", "emoji": "🧑‍🎒", "name": "背包客", "desc": "轻装上阵，什么都想去看看", "color": "#FF6B5C", "cap": "#7a1f14"},
    {"id": "planner", "emoji": "🧑‍💻", "name": "精算派", "desc": "每一分钱都要花在刀刃上", "color": "#6FCF97", "cap": "#2f6d4e"},
    {"id": "night", "emoji": "🧑‍🚀", "name": "夜归人", "desc": "通勤和安全感是第一位的", "color": "#B7A9E0", "cap": "#4a3b78"},
    {"id": "social", "emoji": "🧑‍🎨", "name": "生活家", "desc": "在意社区氛围和装修质感", "color": "#FFD166", "cap": "#8a6a1f"},
]

LANDLORDS = [
    {"emoji": "🧔", "name": "老张", "line": "这套我自己都想住，采光是真的好。"},
    {"emoji": "👩‍🦳", "name": "王阿姨", "line": "小伙子/小姑娘看着就靠谱，价格还能聊。"},
    {"emoji": "🧑‍💼", "name": "中介小李", "line": "这套挂出来没两天，手慢无哦。"},
    {"emoji": "👨‍🔧", "name": "房东老周", "line": "楼下就是菜市场，生活方便得很。"},
    {"emoji": "👵", "name": "刘婆婆", "line": "我在这住了十几年，邻里都熟。"},
    {"emoji": "🧑‍🚀", "name": "合租室友阿飞", "line": "我们几个都挺好相处，随时来看房。"},
    {"emoji": "👨‍💼", "name": "地产顾问陈生", "line": "地铁口就在旁边，通勤能省不少时间。"},
    {"emoji": "🧑‍🎨", "name": "二房东小美", "line": "刚重新装修过，家具家电都是新的。"},
]


def landlord_for(round_number: int, label: str) -> dict:
    idx = (round_number * 3 + (ord(label) - ord("A"))) % len(LANDLORDS)
    return LANDLORDS[idx]


def _avatar(avatar_id: Optional[str]) -> dict:
    return next((a for a in AVATARS if a["id"] == avatar_id), AVATARS[0])


# --------------------------------------------------------------------------
# Basic chrome
# --------------------------------------------------------------------------

def inject_game_css() -> None:
    st.markdown(GAME_CSS, unsafe_allow_html=True)


def quest_log(steps: list[str], current: int) -> None:
    chips = ""
    for i, step in enumerate(steps):
        state = "done" if i < current else ("now" if i == current else "")
        opacity = "1" if state in ("done", "now") else ".5"
        border = "var(--amber)" if state == "now" else "#4a3b78"
        chips += f"<span class='quest-chip' style='opacity:{opacity};border-color:{border};'>{step}</span>"
    st.markdown(f"<div class='quest-row'>{chips}</div>", unsafe_allow_html=True)


def hud_bar(coins: int, streak: int, badges_count: int) -> None:
    st.markdown(
        f"""<div class='hud-row'>
          <span class='hud-chip coin'>🪙 {coins} 积分</span>
          <span class='hud-chip streak'>🔥 连续满意 {streak}</span>
          <span class='hud-chip'>🏅 成就 {badges_count}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def intro_skyline(height: int = 150) -> None:
    heights = [40, 70, 55, 95, 60, 80, 45, 60]
    bldgs = ""
    for h in heights:
        wins = ""
        for r in range(max(1, h // 20)):
            for c in range(2):
                lit = "background:#FFD166;box-shadow:0 0 6px 1px rgba(255,209,102,.6);" if (r + c) % 2 == 0 else "background:rgba(255,255,255,.08);"
                wins += f"<div style='position:absolute;width:5px;height:5px;border-radius:1px;left:{6+c*14}px;bottom:{8+r*16}px;{lit}'></div>"
        bldgs += f"<div style='position:relative;flex:1;height:{h}px;background:linear-gradient(180deg,#4a3b78,#241a40);border-radius:3px 3px 0 0;'>{wins}</div>"
    html = f"""
    <div style="height:{height}px;border-radius:14px;overflow:hidden;border:2px solid #4a3b78;
      background:linear-gradient(180deg,#241645 0%, #ff8a5b 100%); display:flex; align-items:flex-end; gap:6px; padding:0 8px;">
      {bldgs}
    </div>
    """
    components.html(html, height=height + 10)


def avatar_picker(key: str = "avatar") -> str:
    if key not in st.session_state:
        st.session_state[key] = AVATARS[0]["id"]
    st.markdown("<div class='game-muted' style='margin-bottom:6px;'>先选一个探索者形象（会出现在街景里，仅用于装饰不会被记录）：</div>", unsafe_allow_html=True)
    cols = st.columns(4)
    for i, av in enumerate(AVATARS):
        active = st.session_state[key] == av["id"]
        with cols[i]:
            if st.button(av["emoji"], key=f"{key}_btn_{av['id']}", type="primary" if active else "secondary", use_container_width=True):
                st.session_state[key] = av["id"]
                st.rerun()
            st.markdown(f"<div class='avatar-caption'><b>{av['name']}</b><br>{av['desc']}</div>", unsafe_allow_html=True)
    return st.session_state[key]


# --------------------------------------------------------------------------
# Interactive street — real left/right movement via Streamlit buttons,
# door proximity, coin pickups, NPC standees with proximity speech bubbles.
# --------------------------------------------------------------------------

_SKY_STAGES = [
    ("#274690 0%, #ff9a5b 100%", "☀️", 0),
    ("#243b6b 0%, #ff8a5b 100%", "🌤️", 3),
    ("#241645 0%, #ff7a5b 100%", "🌇", 6),
    ("#1c1240 0%, #6b4a8a 100%", "🌆", 12),
    ("#120b2c 0%, #3a2a63 100%", "🌃", 20),
    ("#0a0620 0%, #241645 100%", "🌌", 30),
]


def interactive_street(
    round_number: int,
    total_rounds: int,
    x: int,
    avatar: Optional[str],
    doors: dict,
    landlords: dict,
    collected_coins: set,
    facing: str = "right",
    height: int = 230,
) -> None:
    """Renders the walkable street. `x` is the character's real position
    (from st.session_state.street_x, moved by ◀/▶ buttons in app.py).
    Purely a renderer — takes plain data, writes nothing.
    """
    idx = min(round_number - 1, len(_SKY_STAGES) - 1)
    gradient, sky_icon, n_stars = _SKY_STAGES[idx]
    av = _avatar(avatar)
    flip = "scaleX(-1)" if facing == "left" else "scaleX(1)"

    stars_html = "".join(
        f"<div class='star' style='left:{7+i*17%94}%; top:{6+(i*13)%50}%; animation-delay:{i*0.35}s;'></div>"
        for i in range(n_stars)
    )

    doors_html = ""
    for label, dx in doors.items():
        near = abs(x - dx) <= KNOCK_RANGE
        ll = landlords[label]
        bubble = f"<div class='street-bubble'>👋 过来看看 {label} 号房！</div>" if near else ""
        ring = "door-near" if near else ""
        doors_html += f"""
        <div class="door-wrap {ring}" style="left:{dx}px;">
          <div class="street-npc">{ll['emoji']}</div>
          {bubble}
          <div class="door-frame">
            <div class="door-label">{label}</div>
          </div>
        </div>
        """

    coins_html = ""
    for i, cx in enumerate(COIN_X):
        if i in collected_coins:
            continue
        coins_html += f"<div class='coin' style='left:{cx}px;'>🪙</div>"

    html = f"""
    <style>
      .street{{position:relative;height:{height}px;border-radius:14px;overflow:hidden;border:2px solid #4a3b78;
        background:linear-gradient(180deg,{gradient}); transition:background 1s ease;}}
      .star{{position:absolute;width:2px;height:2px;background:#fff;border-radius:50%;opacity:.2;animation:twinkle 2.4s ease-in-out infinite;}}
      @keyframes twinkle{{0%,100%{{opacity:.15;}}50%{{opacity:.9;}}}}
      .ground{{position:absolute;left:0;right:0;bottom:0;height:40px;
        background:repeating-linear-gradient(90deg,#3a2c63 0 24px,#342456 24px 48px); border-top:3px solid #6fcf9770;}}
      .track{{position:absolute; left:0; right:0; bottom:40px; height:150px;}}
      .door-wrap{{position:absolute; bottom:0; width:60px; text-align:center; transition:filter .3s ease;}}
      .door-wrap.door-near .door-frame{{box-shadow:0 0 0 3px #FFD166, 0 0 16px rgba(255,209,102,.6);}}
      .door-frame{{width:44px;height:70px;margin:0 auto; background:linear-gradient(180deg,#4a3b78,#342456);
        border:2px solid #5b4a8a; border-radius:6px 6px 0 0; display:flex; align-items:flex-end; justify-content:center;}}
      .door-label{{font-family:'Press Start 2P',monospace; font-size:.6rem; color:var(--amber); margin-bottom:6px;}}
      .street-npc{{font-size:22px; animation:bob 1.4s ease-in-out infinite;}}
      .street-bubble{{position:absolute; top:-30px; left:50%; transform:translateX(-50%); white-space:nowrap;
        background:rgba(0,0,0,.55); color:#fff; font-size:.66rem; padding:3px 8px; border-radius:10px; animation:fadein .25s ease;}}
      .coin{{position:absolute; bottom:44px; font-size:18px; animation:coinspin 1.1s linear infinite, bob 1s ease-in-out infinite;}}
      @keyframes coinspin{{0%{{transform:rotateY(0);}}100%{{transform:rotateY(360deg);}}}}
      @keyframes bob{{0%,100%{{transform:translateY(0);}}50%{{transform:translateY(-4px);}}}}
      .char{{position:absolute; bottom:40px; width:26px; height:38px; transition:left .25s ease; transform:{flip};}}
      .char .head{{width:15px;height:15px;background:#FFE0B5;border-radius:50%;margin:0 auto;border:2px solid #3a2205; position:relative;}}
      .char .cap{{position:absolute; top:-7px; left:-2px; width:19px; height:9px; background:{av['cap']}; border-radius:10px 10px 0 0;}}
      .char .body{{width:20px;height:16px;background:{av['color']};border-radius:4px;margin:-2px auto 0;border:2px solid #3a2205;}}
      .char .legs{{display:flex; justify-content:center; gap:2px; margin-top:-2px;}}
      .char .legs div{{width:6px;height:9px;background:#3a2205;border-radius:2px; animation:walk .5s ease-in-out infinite;}}
      .char .legs div:nth-child(2){{animation-delay:.25s;}}
      @keyframes walk{{0%,100%{{transform:translateY(0);}}50%{{transform:translateY(2px);}}}}
      .cap-tag{{position:absolute; top:8px; left:12px; font-size:11px; color:#F4EFFF; background:rgba(0,0,0,.35); padding:3px 9px; border-radius:20px;}}
      .sky-icon{{position:absolute; top:8px; right:12px; font-size:18px;}}
    </style>
    <div class="street">
      <div class="cap-tag">STOP {round_number}/{total_rounds} · ◀ ▶ 走到门口敲门</div>
      <div class="sky-icon">{sky_icon}</div>
      {stars_html}
      <div class="track">
        {doors_html}
        {coins_html}
        <div class="char" style="left:{x}px;">
          <div class="cap"></div>
          <div class="head"></div>
          <div class="body"></div>
          <div class="legs"><div></div><div></div></div>
        </div>
      </div>
      <div class="ground"></div>
    </div>
    """
    components.html(html, height=height + 10)


def star_picker(key: str, label: str, scale: int = 7, icon: str = "★", default: int = 4) -> int:
    """Row of clickable icon buttons standing in for st.slider(1, scale).
    Returns the same 1..scale integer the original slider produced."""
    state_key = f"_stars_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = default
    st.caption(label)
    cols = st.columns(scale)
    for i in range(scale):
        active = (i + 1) <= st.session_state[state_key]
        if cols[i].button(icon, key=f"{key}_{i}", type="primary" if active else "secondary", use_container_width=True):
            st.session_state[state_key] = i + 1
            st.rerun()
    st.markdown(
        f"<div class='game-muted'>当前评分：{st.session_state[state_key]} / {scale}</div>",
        unsafe_allow_html=True,
    )
    return st.session_state[state_key]


def dialogue_box(speaker_emoji: str, speaker_name: str, text: str, page: int = 1, total_pages: int = 1) -> None:
    """RPG-style paged dialogue box. Purely a renderer; app.py owns the
    page counter in session_state and supplies the current page's text.
    """
    html = f"""
    <div class="dialogue-box">
      <div class="dialogue-head">
        <div class="dialogue-portrait">{speaker_emoji}</div>
        <div class="dialogue-name">{speaker_name}</div>
      </div>
      <div class="dialogue-text">{text}</div>
      <div class="dialogue-page">{page} / {total_pages}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def game_card(row: pd.Series, label: str, is_recommended: bool, group: str, explanation: str | None, type_labels: dict, landlord: Optional[dict] = None, locked: bool = False) -> None:
    highlight = is_recommended and group != "control"
    badge = "<span class='game-badge'>⭐ AI 推荐</span>" if highlight else ""
    score = f"<div class='game-muted'>推荐分数：{row['recommendation_score']:.1f}/100</div>" if highlight else ""
    landlord = landlord or landlord_for(1, label)
    landlord_tag = f"<div class='landlord-tag'>{landlord['emoji']} 房东：{landlord['name']}</div>"

    def shown(value, suffix="", digits=0):
        return "数据未提供" if pd.isna(value) else f"{value:.{digits}f}{suffix}"

    location = row.get("location_text") if pd.notna(row.get("location_text")) else row["district"]
    lock_note = "<div class='game-muted' style='color:var(--coral);'>🚶 走到门口才能敲门哦</div>" if locked else ""
    html = f"""
    <div class="game-card {'recommended' if highlight else ''} {'locked' if locked else ''}">
      <div class="pxl" style="font-size:.68rem;">房源 {label}</div>
      {badge}
      {landlord_tag}
      <h4 style="margin:6px 0 2px;">{row['title']}</h4>
      <div class="game-muted">{location} · {type_labels[row['rental_type']]}</div>
      <div class="game-price">¥{int(row['monthly_rent']):,}<small style="font-size:.9rem;">/月</small></div>
      {score}
      <p style="font-size:.85rem; line-height:1.7; margin-top:8px;">
        🚇 地铁距离：{shown(row['metro_distance_m'], ' 米')}<br>
        📐 面积：{shown(row['area_sqm'], '㎡')} · 卧室：{shown(row['bedrooms'], '间')}<br>
        🧭 朝向：{row.get('orientation') if pd.notna(row.get('orientation')) else '数据未提供'}<br>
        🕒 通勤：数据未提供<br>
        ✨ 装修/社区/安全：数据未提供<br>
        💳 押金/中介费/电梯：数据未提供
      </p>
      <p style="font-size:.82rem; color:#cfc4ea;">{row['short_description']}</p>
      {lock_note}
      <div class="game-muted" style="font-size:.72rem;">数据类型：租赁挂牌快照（非成交记录）</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Achievements — computed purely from data ALREADY collected in
# st.session_state.choices (the same rows written by save_choice).
# --------------------------------------------------------------------------

def compute_badges(choices: list[dict], preferences: Optional[dict]) -> list[dict]:
    if not choices:
        return []
    df = pd.DataFrame(choices)
    badges: list[dict] = []
    if (df["decision_time_seconds"] < 10).any():
        badges.append({"icon": "⚡", "title": "闪电决策", "desc": "10 秒内敲定过一套房"})
    if (df["satisfaction"] >= 6).all():
        badges.append({"icon": "😄", "title": "从不将就", "desc": "每一轮满意度都在 6 分以上"})
    if preferences and (df["chosen_rent"] <= preferences.get("budget_max", 1e9) * 0.7).mean() >= 0.5:
        badges.append({"icon": "🧮", "title": "精打细算", "desc": "过半选择低于预算的 70%"})
    if (df["recommendation_followed"] == True).mean() >= 0.8:  # noqa: E712
        badges.append({"icon": "🤖", "title": "信任 AI", "desc": "八成以上选择跟随了推荐"})
    if (df["recommendation_followed"] == True).mean() <= 0.2:  # noqa: E712
        badges.append({"icon": "🧭", "title": "自有主张", "desc": "很少直接采纳 AI 推荐"})
    if df["chosen_area"].mean() > 50:
        badges.append({"icon": "🛋️", "title": "宽敞党", "desc": "平均选房面积超过 50㎡"})
    if len(df) >= 6:
        badges.append({"icon": "🏁", "title": "全程通关", "desc": "走完了全部 6 站"})
    return badges


def badge_toast(new_badges: list[dict]) -> None:
    if not new_badges:
        return
    for b in new_badges:
        st.markdown(
            f"""<div style="background:linear-gradient(90deg,#3a2c63,#241a40); border:2px solid var(--amber);
              border-radius:12px; padding:10px 14px; margin-bottom:8px; animation:popin .35s ease;">
              🎉 <b>解锁成就：{b['icon']} {b['title']}</b> — {b['desc']}
            </div>""",
            unsafe_allow_html=True,
        )


def badge_shelf(badges: list[dict]) -> None:
    if not badges:
        st.caption("本次旅程还没有解锁成就。")
        return
    pills = "".join(
        f"""<div class="badge-pill"><div class="ic">{b['icon']}</div><div class="t">{b['title']}</div><div class="d">{b['desc']}</div></div>"""
        for b in badges
    )
    st.markdown(f"<div class='badge-shelf'>{pills}</div>", unsafe_allow_html=True)


def level_clear_banner(round_number: int, total_rounds: int, coins_earned: int) -> None:
    """'Level clear' interstitial shown right after confirming a choice,
    before walking into the next round. Pure flavor/pacing."""
    st.markdown(
        f"""<div class="clear-banner">
          <div class="pxl" style="font-size:1.1rem;">🚩 第 {round_number}/{total_rounds} 站 · 通关！</div>
          <div class="game-muted" style="margin-top:8px;">本站获得 🪙 +{coins_earned} 积分</div>
        </div>""",
        unsafe_allow_html=True,
    )


def identity_card(avatar_id: Optional[str], coins: int, badges: list[dict], group_label: str) -> None:
    av = _avatar(avatar_id)
    html = f"""
    <div style="display:flex; gap:16px; align-items:center; background:linear-gradient(135deg,#2f2354,#1c1240);
      border:2px solid var(--amber); border-radius:16px; padding:16px 20px;">
      <div style="font-size:2.6rem;">{av['emoji']}</div>
      <div>
        <div class="pxl" style="font-size:.8rem;">{av['name']} · 落脚通关证</div>
        <div class="game-muted" style="margin-top:4px;">体验模式：{group_label}</div>
        <div class="game-muted">累计积分：🪙 {coins} · 成就数：🏅 {len(badges)}</div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def confetti_burst(height: int = 220) -> None:
    html = f"""
    <canvas id="confetti-canvas" style="width:100%;display:block;"></canvas>
    <script>
    (function(){{
      const c = document.getElementById('confetti-canvas');
      const ctx = c.getContext('2d');
      const W = c.parentElement.clientWidth || 400, H = {height};
      c.width = W; c.height = H;
      const colors = ['#FFD166','#FF6B5C','#6FCF97','#B7A9E0'];
      const pieces = Array.from({{length: 70}}, () => ({{
        x: Math.random()*W, y: -20 - Math.random()*H,
        vy: 2+Math.random()*3, vx: -1+Math.random()*2,
        size: 4+Math.random()*4, color: colors[Math.floor(Math.random()*colors.length)],
        rot: Math.random()*360
      }}));
      let frame = 0;
      function tick(){{
        ctx.clearRect(0,0,W,H);
        pieces.forEach(p=>{{
          p.y += p.vy; p.x += p.vx; p.rot += 4;
          ctx.save(); ctx.translate(p.x,p.y); ctx.rotate(p.rot*Math.PI/180);
          ctx.fillStyle = p.color; ctx.fillRect(-p.size/2,-p.size/2,p.size,p.size);
          ctx.restore();
        }});
        frame++;
        if(frame < 90) requestAnimationFrame(tick);
      }}
      tick();
    }})();
    </script>
    """
    components.html(html, height=height)


def sound_ping(kind: str = "coin") -> None:
    """Best-effort tiny beep via the Web Audio API. Browsers often block
    autoplay audio inside iframes without a direct gesture, so this is
    decorative and silently no-ops if blocked."""
    freq = {"coin": 880, "badge": 660, "knock": 220, "step": 340}.get(kind, 880)
    html = f"""
    <script>
    try {{
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const o = ctx.createOscillator(); const g = ctx.createGain();
      o.type = 'square'; o.frequency.value = {freq};
      g.gain.setValueAtTime(0.05, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.15);
      o.connect(g); g.connect(ctx.destination);
      o.start(); o.stop(ctx.currentTime + 0.15);
    }} catch (e) {{}}
    </script>
    """
    components.html(html, height=0)
    