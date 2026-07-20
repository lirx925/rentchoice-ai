"""RentChoice AI participant-facing Streamlit application.

The presentation follows a scene-by-scene interactive-explainer rhythm:
a cover, a short introduction, preferences, six focused choices, and a
closing reflection. Experiment assignment, scoring, outcomes, and storage
remain unchanged.
"""
from __future__ import annotations
import time, uuid
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.analytics import participant_summary
from src.data_loader import eligible_listings, load_listings
from src.experiment import TOTAL_ROUNDS, assign_treatment, build_choice_sets, welfare_metrics
from src.explanations import optional_llm_explanation
from src.recommender import score_listings
from src.storage import load_participant_progress, save_choice, save_participant, save_post_survey, storage_mode
from src.game_ui import (
    inject_game_css, quest_log, title_scene, journey_map, scene_heading, progress_dots,
    character_creator, game_topbar, day_route, day_summary_card, character_identity_card,
    star_picker, game_card, confetti_burst, ROUND_STORY, landlord_for,
    hud_bar, dialogue_box, compute_badges, badge_toast, badge_shelf,
    level_clear_banner, identity_card, sound_ping, community_hero, property_detail, nest_room,
    interactive_journey_map,
)

load_dotenv()
try:
    for _key in ["SUPABASE_URL","SUPABASE_KEY","OPENAI_API_KEY","OPENAI_BASE_URL","OPENAI_MODEL","ADMIN_PASSWORD","EXPERIMENT_SEED","ENABLE_LLM"]:
        if _key in st.secrets and _key not in __import__("os").environ:
            __import__("os").environ[_key] = str(st.secrets[_key])
except FileNotFoundError:
    pass
st.set_page_config(page_title="租房小岛", page_icon="🏝️", layout="wide", initial_sidebar_state="collapsed")
inject_game_css()

TYPE_LABELS = {"shared":"合租", "studio":"独立单间", "whole":"整租"}
GROUP_LABELS = {"control":"信息浏览模式", "score_only":"智能评分模式", "explained":"解释型推荐模式"}
QUEST_STEPS = ["① 行前准备", "② 沿街找房 ×6", "③ 结束问卷"]
COINS_PER_ROUND = 15
COINS_QUICK_BONUS = 5   # awarded when a decision took under 15s — flavor only
COIN_PICKUP_VALUE = 5   # flavor coins picked up while walking the street


def init_state() -> None:
    """Initialize all workflow state in one place."""
    defaults = {
        "stage": "cover", "participant_id": None, "treatment_group": None,
        "preferences": None, "preference_draft": {}, "choice_sets": None, "round_number": 1,
        "round_started_at": None, "choices": [], "survey_done": False,
        "choice_stage": "pick", "picked_label": None,
        # cosmetic game-layer state — never written to the saved dataset
        "avatar": None, "avatar_hair": "short", "avatar_hair_color": "brown", "avatar_outfit": "tee", "avatar_bottom": "shorts",
        "avatar_accessory": "bag", "player_name": "小岛新住民",
        "coins": 0, "badges_earned": [], "pending_toast": [],
        "sound_on": False, "dialogue_page": 1, "clear_coins_earned": 0,
        "stage_history": [], "favorites": [], "viewed_homes": [], "contacted_landlords": [],
        "lifestyle": "平衡生活", "home_wishes": [], "nest_theme": "ocean", "free_area": 1,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def restore_reconnected_session() -> None:
    """Rehydrate a new Streamlit session from the durable participant URL."""
    if st.session_state.participant_id:
        return
    participant_id = str(st.query_params.get("participant", "")).strip()
    try:
        uuid.UUID(participant_id)
    except (ValueError, AttributeError):
        return
    try:
        progress = load_participant_progress(participant_id)
    except Exception:
        # A transient backend failure must not put the app into a reconnect loop.
        # Keep the participant URL intact so the next rerun can retry restoration.
        return
    if not progress:
        return
    participant = progress["participant"]
    preference_keys = {
        "budget_max", "ideal_rent", "destination_district", "min_area",
        "rental_type_preference", "importance_rent", "importance_location",
        "importance_area", "importance_metro", "prior_rental_experience",
        "initial_ai_trust", "participant_status",
    }
    preferences = {key: participant[key] for key in preference_keys if key in participant and not pd.isna(participant[key])}
    required_preferences = {
        "budget_max", "ideal_rent", "destination_district", "min_area",
        "rental_type_preference", "importance_rent", "importance_location",
        "importance_area", "importance_metro",
    }
    if not required_preferences.issubset(preferences) or not participant.get("treatment_group"):
        return
    # Older persisted rows did not include this UI-only switch.
    preferences["metro_priority"] = True
    choices = progress["choices"]
    completed_rounds = {
        int(row["round_number"])
        for row in choices
        if 1 <= int(row["round_number"]) <= TOTAL_ROUNDS
    }
    next_round = next((day for day in range(1, TOTAL_ROUNDS + 1) if day not in completed_rounds), TOTAL_ROUNDS + 1)
    st.session_state.participant_id = participant_id
    st.session_state.treatment_group = str(participant["treatment_group"])
    st.session_state.preferences = preferences
    st.session_state.preference_draft = {key: preferences[key] for key in (
        "budget_max", "ideal_rent", "destination_district", "min_area",
        "rental_type_preference", "metro_priority",
    ) if key in preferences}
    st.session_state.choice_sets = build_choice_sets(listings_data(), participant_id)
    st.session_state.choices = choices
    st.session_state.round_number = next_round
    st.session_state.round_started_at = time.time()
    st.session_state.choice_stage = "pick"
    st.session_state.coins = len(choices) * COINS_PER_ROUND
    st.session_state.badges_earned = compute_badges(choices, preferences)
    st.session_state.survey_done = progress["survey_done"]
    st.session_state.stage = "results" if progress["survey_done"] else "survey" if next_round > TOTAL_ROUNDS else "journey"
    st.session_state.pending_toast = []


@st.cache_data
def listings_data() -> pd.DataFrame:
    return eligible_listings(load_listings())


def go(stage: str) -> None:
    current = st.session_state.get("stage")
    if current and current != stage:
        st.session_state.stage_history.append(current)
    st.session_state.stage = stage
    st.rerun()


def render_back_button() -> None:
    if st.session_state.stage == "cover" or not st.session_state.stage_history:
        return
    with st.container(key="back_nav"):
        if st.button("← 返回", key="global_back", use_container_width=True):
            st.session_state.stage = st.session_state.stage_history.pop()
            st.rerun()


def top_progress(label: str, value: float) -> None:
    st.caption(f"匿名参与 · {storage_mode()}模式 · {label}")
    st.progress(value)


def _show_pending_toast() -> None:
    if st.session_state.pending_toast:
        badge_toast(st.session_state.pending_toast)
        if st.session_state.sound_on:
            sound_ping("badge")
        st.session_state.pending_toast = []


def cover_page() -> None:
    title_scene()
    with st.container(key="cover_action"):
        if st.button("开始游戏", type="primary", use_container_width=True):
            go("intro")
        if st.button("继续游戏", use_container_width=True, disabled=st.session_state.participant_id is None):
            go("journey" if st.session_state.preferences else "welcome")
    with st.container(key="cover_settings"):
        if st.button("⚙ 设置", use_container_width=True): go("settings")


def intro_page() -> None:
    with st.container(key="intro_page"):
        progress_dots(0, 12)
        scene_heading(
            "来自租房小岛的邀请函",
            "在岛上生活六天",
            "每天认识一个社区、查看三套房源。没有标准答案，只有越来越清晰的生活偏好。",
        )
        st.markdown("<div style='max-width:720px;margin:20px auto 28px;text-align:center;line-height:2;color:#806b52'>探索小岛 → 认识社区 → 体验房子 → 发现偏好 → 建立属于自己的小窝。<br><small>房源使用租赁挂牌数据快照（非成交记录），仅用于匿名研究体验。</small></div>", unsafe_allow_html=True)
        if st.button("创建我的岛民角色 →", type="primary", use_container_width=True):
            go("welcome")


def welcome() -> None:
    progress_dots(1, 12)
    scene_heading("创建你的角色", "设计你的小岛形象", "选择发型、发色、服装和下装。")
    character_creator()
    st.info("房源来自上海租赁挂牌数据快照，并非实时房源或成交记录；本体验不构成真实租房建议。")
    st.caption("约 8–12 分钟 · 不收集真实姓名、电话、邮箱或精确住址 · 可随时关闭退出")
    st.session_state.sound_on = st.toggle("🔊 开启轻量音效（可选，浏览器可能会拦截自动播放）", value=st.session_state.sound_on)
    consent = st.checkbox("我已阅读以上说明，同意匿名记录我的选择数据")
    if st.button("创建完成，开始租房之旅 →", type="primary", disabled=not consent, use_container_width=True):
        st.session_state.participant_id = str(uuid.uuid4())
        st.session_state.treatment_group = assign_treatment(st.session_state.participant_id)
        st.query_params["participant"] = st.session_state.participant_id
        go("preferences_basic")


def preferences_basic_page() -> None:
    progress_dots(2, 12)
    scene_heading("第一幕 · 你的地图", "先画出房子的边界", "预算、地点和空间——先告诉我们哪些是不能退让的条件。")
    draft = st.session_state.preference_draft
    with st.form("preferences_basic_form"):
        c1,c2 = st.columns(2)
        budget_max = c1.number_input("💰 每月最高预算（元）", 500, 100000, int(draft.get("budget_max", 7000)), 100)
        ideal_rent = c2.number_input("💵 最理想月租（元）", 500, 80000, int(draft.get("ideal_rent", 5500)), 100)
        destination_district = c1.selectbox(
            "📍 主要目的地区域（不需要填写精确地址）",
            [
                "暂不确定/不限", "浦东", "黄浦", "徐汇", "长宁",
                "静安", "普陀", "虹口", "杨浦", "闵行",
                "宝山", "嘉定", "金山", "松江", "青浦",
                "奉贤", "崇明"
            ],
        )
        min_area = c2.slider("📐 最低可接受面积（㎡）", 5, 300, 35)
        rental_pref_label = st.radio("🏠 租赁类型偏好", ["接受合租", "仅接受单间或整租", "无明显偏好"], horizontal=True)
        metro_priority = st.toggle("🚉 我重视地铁便利", value=True)
        submitted = st.form_submit_button("下一步：哪些更重要？ →", type="primary", use_container_width=True)
    if submitted:
        if ideal_rent > budget_max:
            st.error("最理想月租不能高于最高预算，请调整后重试。")
            return
        mapping = {"接受合租":"accept_shared", "仅接受单间或整租":"no_shared", "无明显偏好":"no_preference"}
        st.session_state.preference_draft = {
            "budget_max": budget_max, "ideal_rent": ideal_rent,
            "destination_district": destination_district, "min_area": min_area,
            "rental_type_preference": mapping[rental_pref_label], "metro_priority": metro_priority,
        }
        go("preferences_detail")


def preferences_detail_page() -> None:
    progress_dots(3, 12)
    scene_heading("第一幕 · 你的地图", "再排一次优先顺序", "同样的房源，不同的人会看见不同的答案。拖动滑块，表达你真正的取舍。")
    with st.form("preferences_detail_form"):
        st.markdown("##### 你向往怎样的岛屿生活？")
        lifestyle = st.radio("生活方式", ["安静生活", "热闹生活", "平衡生活"], horizontal=True, index=2)
        home_wishes = st.multiselect("房屋偏好（可多选）", ["大空间", "小而温馨", "阳光充足", "有厨房", "有阳台", "可以养宠物"], default=["阳光充足", "有厨房"])
        st.markdown("##### 各因素重要性（1=不重要，5=非常重要）")
        cols = st.columns(4)
        fields = [("租金","importance_rent"),("目的地区域匹配","importance_location"),("面积","importance_area"),("地铁距离","importance_metro")]
        vals = {key: cols[i%4].slider(label,1,5,4 if i<3 else 3,key=key) for i,(label,key) in enumerate(fields)}
        prior = st.radio("是否有租房经历？", ["是", "否"], horizontal=True)
        trust = st.slider("🤝 对 AI 推荐的初始信任程度", 1, 7, 4)
        status = st.selectbox("当前身份", ["本科生", "研究生", "实习生", "已工作", "其他"])
        submitted = st.form_submit_button("背好包，出发 →", type="primary", use_container_width=True)
    if submitted:
        st.session_state.lifestyle = lifestyle
        st.session_state.home_wishes = home_wishes
        prefs = {**st.session_state.preference_draft, **vals, "prior_rental_experience":prior=="是", "initial_ai_trust":trust, "participant_status":status}
        st.session_state.preferences = prefs
        st.session_state.choice_sets = build_choice_sets(listings_data(), st.session_state.participant_id)
        try:
            save_participant({"participant_id":st.session_state.participant_id,"treatment_group":st.session_state.treatment_group,**{k:v for k,v in prefs.items() if k!="metro_priority"},"consent":True})
        except Exception as exc:
            st.error(f"偏好暂时无法保存：{exc}"); return
        st.session_state.round_started_at = time.time()
        st.session_state.choice_stage = "pick"
        go("journey")


def _scored_options(r: int):
    ids = st.session_state.choice_sets[r-1]
    options = listings_data()[listings_data().listing_id.isin(ids)].set_index("listing_id").loc[ids].reset_index()
    scored = score_listings(options, st.session_state.preferences)
    best_idx = scored["recommendation_score"].idxmax()
    recommended_id = str(scored.loc[best_idx, "listing_id"])
    explanation = None
    if st.session_state.treatment_group == "explained":
        exp_key = f"_explanation_{r}"
        if exp_key not in st.session_state:
            st.session_state[exp_key] = optional_llm_explanation(
                scored.loc[best_idx], scored.drop(best_idx), st.session_state.preferences
            )
        explanation = st.session_state[exp_key]
    return scored, recommended_id, explanation


def journey_page() -> None:
    r = int(st.session_state.round_number)
    if r > TOTAL_ROUNDS:
        go("survey")
        return
    selected_day = st.query_params.get("map_day")
    if selected_day and str(selected_day) == str(r):
        del st.query_params["map_day"]
        st.session_state.round_started_at = time.time()
        st.session_state.choice_stage = "pick"
        go("choice")
        return
    progress_dots(r + 2, 12)
    interactive_journey_map(r)


def choice_page() -> None:
    r = int(st.session_state.round_number)
    if r > TOTAL_ROUNDS:
        go("survey"); return

    scored, recommended_id, explanation = _scored_options(r)
    labels = ["A", "B", "C"]
    stage = st.session_state.choice_stage
    landlords = {lab: landlord_for(r, lab) for lab in labels}

    game_topbar(r, TOTAL_ROUNDS, st.session_state.coins, st.session_state.player_name, st.session_state.avatar_accessory)
    progress_dots(r + 3, 12)
    _show_pending_toast()

    if stage == "clear":
        completed = next((x for x in st.session_state.choices if x["round_number"] == r), {})
        completed = {**completed, "chosen_listing_id": st.session_state.picked_label or "—"}
        scene_heading(f"☀️ 第 {r} 天结束", "今天也找到了一处可能的家", "回顾今天的选择与收获，准备继续探索小岛。")
        day_summary_card(r, completed, st.session_state.clear_coins_earned)
        badge_toast(st.session_state.pending_toast)
        st.session_state.pending_toast = []
        if st.button("结束今天，返回旅程地图 →", type="primary", use_container_width=True):
            st.session_state.round_number = r + 1
            st.session_state.round_started_at = time.time()
            st.session_state.choice_stage = "pick"
            st.session_state.picked_label = None
            st.session_state.dialogue_page = 1
            go("free_explore" if r == TOTAL_ROUNDS else "journey")
        return

    title, story = ROUND_STORY.get(r, (f"第 {r} 站", "新一批房源出现了——"))
    st.markdown(f"<div style='text-align:center;margin:4px 0 15px'><h3 style='font-size:1.45rem;margin:0'>选择今天的房源</h3><span class='game-muted'>{story}</span></div>", unsafe_allow_html=True)

    if stage == "pick":
        st.markdown("<div class='scene-copy'>仔细比较，然后凭第一判断选择一扇门。</div>", unsafe_allow_html=True)
        cols = st.columns(3)
        for i, (_, row) in enumerate(scored.iterrows()):
            label = labels[i]
            with cols[i]:
                game_card(row, label, row["listing_id"] == recommended_id, st.session_state.treatment_group, explanation, TYPE_LABELS, landlord=landlords[label], round_number=r)
                if st.button(f"查看房源 {label}", key=f"pick_{r}_{label}", type="primary", use_container_width=True):
                    st.session_state.picked_label = label
                    st.session_state.choice_stage = "detail"
                    st.session_state.dialogue_page = 1
                    listing_id = str(row["listing_id"])
                    if listing_id not in st.session_state.viewed_homes:
                        st.session_state.viewed_homes.append(listing_id)
                    if st.session_state.sound_on:
                        sound_ping("knock")
                    st.rerun()
        return

    # Stages after choosing a card: detail first, then a separate rating page.
    idx = labels.index(st.session_state.picked_label)
    chosen_row = scored.iloc[idx]
    landlord = landlords[st.session_state.picked_label]

    listing_id = str(chosen_row.listing_id)
    if stage == "detail":
        st.markdown("<h3 style='text-align:center;font-size:1.45rem;margin:0 0 14px'>房源详情</h3>", unsafe_allow_html=True)
        property_detail(chosen_row, st.session_state.picked_label, r, TYPE_LABELS, landlord)
        actions = st.columns([1, 1, 1.35, 1.35])
        is_favorite = listing_id in st.session_state.favorites
        if actions[0].button("← 返回", key=f"drop_{r}", use_container_width=True):
            st.session_state.choice_stage = "pick"; st.session_state.picked_label = None; st.rerun()
        if actions[1].button("💛 已收藏" if is_favorite else "♡ 收藏", key=f"fav_{r}", use_container_width=True):
            if is_favorite: st.session_state.favorites.remove(listing_id)
            else: st.session_state.favorites.append(listing_id)
            st.rerun()
        if actions[2].button("联系房东", key=f"contact_{r}", use_container_width=True):
            if listing_id not in st.session_state.contacted_landlords: st.session_state.contacted_landlords.append(listing_id)
            st.toast(f"已给{landlord['name']}留言。", icon="💬")
        if actions[3].button("选择它 →", key=f"choose_{r}", type="primary", use_container_width=True):
            st.session_state.choice_stage = "rate"; st.rerun()
        return

    st.markdown(f"<div class='island-panel' style='max-width:680px;margin:20px auto'><div class='scene-number'>房源 {st.session_state.picked_label} · ¥{int(chosen_row.monthly_rent):,}/月</div><h3 style='text-align:center;font-size:1.55rem'>记录你的真实感受</h3>", unsafe_allow_html=True)
    rating_col = st.container()
    with rating_col:
        satisfaction = star_picker(f"sat_{r}", "对这次选择的满意度", scale=7, icon="★", default=4)
        confidence = star_picker(f"conf_{r}", "选择信心", scale=7, icon="⚡", default=4)
        wtp_limit = max(30000, int(chosen_row.monthly_rent * 1.5))
        wtp = st.number_input("最高月租支付意愿（元）", 1000, wtp_limit, 3000, 100, key=f"wtp_{r}")
        c1, c2 = st.columns([1, 2])
        with c1:
            if st.button("← 换一套", key=f"back_{r}", use_container_width=True):
                st.session_state.choice_stage = "detail"
                st.rerun()
        with c2:
            confirm = st.button("确认选择 →", key=f"confirm_{r}", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if confirm:
        chosen_u, best_u, loss = welfare_metrics(scored, str(chosen_row.listing_id))
        elapsed = round(max(0.0, time.time() - float(st.session_state.round_started_at or time.time())), 2)
        row = {
            "participant_id": st.session_state.participant_id,
            "round_number": r,
            "treatment_group": st.session_state.treatment_group,
            "option_a_id": str(scored.iloc[0].listing_id),
            "option_b_id": str(scored.iloc[1].listing_id),
            "option_c_id": str(scored.iloc[2].listing_id),
            "recommended_listing_id": recommended_id,
            "chosen_listing_id": str(chosen_row.listing_id),
            "recommendation_followed": str(chosen_row.listing_id) == recommended_id,
            "chosen_rent": int(chosen_row.monthly_rent),
            "chosen_commute": None,
            "chosen_area": float(chosen_row.area_sqm),
            "chosen_location_match": None if pd.isna(chosen_row.location_fit) else float(chosen_row.location_fit),
            "willingness_to_pay": int(wtp),  
            "satisfaction": int(satisfaction),
            "choice_confidence": int(confidence),
            "decision_time_seconds": elapsed,
            "chosen_utility": chosen_u,
            "best_available_utility": best_u,
            "welfare_loss": loss,
        }
        try:
            save_choice(row)
        except Exception as exc:
            st.error(f"本轮数据保存失败，请重试：{exc}")
            return
        existing = [x for x in st.session_state.choices if x["round_number"] != r]
        st.session_state.choices = existing + [row]

        # --- cosmetic game-layer bookkeeping (never touches saved schema) ---
        earned = COINS_PER_ROUND + (COINS_QUICK_BONUS if elapsed < 15 else 0)
        st.session_state.coins += earned
        st.session_state.clear_coins_earned = earned
        new_badges = compute_badges(st.session_state.choices, st.session_state.preferences)
        just_unlocked = [b for b in new_badges if b["title"] not in {x["title"] for x in st.session_state.badges_earned}]
        st.session_state.badges_earned = new_badges
        st.session_state.pending_toast = just_unlocked
        if st.session_state.sound_on:
            sound_ping("coin")

        st.session_state.pop(f"_stars_sat_{r}", None)
        st.session_state.pop(f"_stars_conf_{r}", None)
        st.session_state.choice_stage = "clear"
        st.rerun()


def _current_streak() -> int:
    """Cosmetic-only: consecutive most-recent rounds with satisfaction >= 5."""
    streak = 0
    for row in reversed(st.session_state.choices):
        if row.get("satisfaction", 0) >= 5:
            streak += 1
        else:
            break
    return streak


def render_bottom_navigation(active: str) -> None:
    """Persistent, clickable navigation for the island-life layer."""
    with st.container(key="bottom_nav_buttons"):
        cols = st.columns(5)
        targets = [("🏝 地图", "journey"), ("🏠 小窝", "nest"), ("🔍 记录", "records"), ("⭐ 收藏", "favorites"), ("⚙ 设置", "settings")]
        for col, (label, target) in zip(cols, targets):
            if col.button(label, key=f"nav_{active}_{target}", use_container_width=True):
                if target == "journey" and not st.session_state.preferences:
                    target = "intro"
                go(target)


def free_explore_page() -> None:
    game_topbar(TOTAL_ROUNDS, TOTAL_ROUNDS, st.session_state.coins, st.session_state.player_name, st.session_state.avatar_accessory)
    day_route(TOTAL_ROUNDS, TOTAL_ROUNDS)
    scene_heading("第 6 天 · 自由探索", "小岛现在完全向你开放", "六轮看房已经完成。回访喜欢的社区、整理收藏，再完成最后的探索任务。")
    areas = [(day, ROUND_STORY[day][0]) for day in range(1, TOTAL_ROUNDS + 1)]
    cols = st.columns(len(areas))
    for col, (day, name) in zip(cols, areas):
        if col.button(name, key=f"free_{day}", type="primary" if st.session_state.free_area == day else "secondary", use_container_width=True):
            st.session_state.free_area = day; st.rerun()
    day, name = next((area for area in areas if area[0] == st.session_state.free_area), areas[0])
    community_hero(day, name, "自由回访：这里不会新增实验选择，可以安心查看与回忆。")
    c1, c2, c3 = st.columns(3)
    c1.metric("看过的房子", len(st.session_state.viewed_homes))
    c2.metric("收藏房源", len(st.session_state.favorites))
    c3.metric("联系过的房东", len(st.session_state.contacted_landlords))
    st.markdown(f"<div class='story-box'>今日任务：✓ 完成六日看房　{'✓' if st.session_state.favorites else '○'} 收藏喜欢的房子　✓ 回访一个社区</div>", unsafe_allow_html=True)
    if st.button("完成自由探索，生成旅程报告 →", type="primary", use_container_width=True): go("survey")
    render_bottom_navigation("map")


def nest_page() -> None:
    scene_heading("我的小窝", "把房间布置成喜欢的样子", "家具切换只改变你的游戏房间，不影响实验推荐结果。")
    themes = [("ocean","🌊 海风原木"),("green","🌿 绿野植物"),("journal","📔 暖阳手账")]
    cols = st.columns(3)
    for col, (key, label) in zip(cols, themes):
        if col.button(label, key=f"theme_{key}", type="primary" if st.session_state.nest_theme == key else "secondary", use_container_width=True):
            st.session_state.nest_theme = key; st.rerun()
    nest_room(st.session_state.nest_theme)
    left, right = st.columns(2)
    with left:
        st.markdown("#### ⭐ 收藏展示")
        st.write(f"你已经收藏了 {len(st.session_state.favorites)} 套房源。")
        if st.session_state.favorites: st.caption(" · ".join(st.session_state.favorites[:6]))
    with right:
        st.markdown("#### 📔 旅行日记")
        st.write(f"已经走过 {len(st.session_state.choices)}/6 天，看过 {len(st.session_state.viewed_homes)} 套房子。")
        st.caption(f"目前向往：{st.session_state.lifestyle}；喜欢：{'、'.join(st.session_state.home_wishes) or '等待发现'}")
    render_bottom_navigation("nest")


def records_page() -> None:
    scene_heading("看房记录", "六日旅程手账", "看过的房子、满意度和生活评价都留在这里。")
    if not st.session_state.choices:
        st.info("还没有完成的看房记录。先去小岛地图开始第一天吧。")
    for row in sorted(st.session_state.choices, key=lambda x: x["round_number"]):
        st.markdown(f"<div class='record-card'><b>第 {row['round_number']} 天 · {ROUND_STORY[row['round_number']][0]}</b><br>房源 {row['chosen_listing_id']}　¥{int(row['chosen_rent']):,}/月　{float(row['chosen_area']):.0f}㎡<br><small>满意度 {'★' * min(5, round(row['satisfaction']/1.4))}　选择信心 {row['choice_confidence']}/7</small></div>", unsafe_allow_html=True)
    render_bottom_navigation("records")


def favorites_page() -> None:
    scene_heading("我的收藏", "把心动的小窝放在一起", "收藏不会自动成为最终选择，你可以随时添加或移除。")
    if not st.session_state.favorites:
        st.info("收藏夹还是空的。在房源详情页点击“♡ 收藏”即可加入。")
    else:
        df = listings_data().set_index("listing_id")
        for listing_id in list(st.session_state.favorites):
            if listing_id not in df.index: continue
            row = df.loc[listing_id]
            c1, c2 = st.columns([4,1])
            c1.markdown(f"<div class='record-card'><b>{row['title']}</b><br>{row['district']} · ¥{int(row['monthly_rent']):,}/月 · {float(row['area_sqm']):.0f}㎡</div>", unsafe_allow_html=True)
            if c2.button("移除", key=f"remove_{listing_id}", use_container_width=True):
                st.session_state.favorites.remove(listing_id); st.rerun()
    render_bottom_navigation("favorites")


def settings_page() -> None:
    scene_heading("设置", "让小岛更适合你", "这些设置只影响当前浏览器会话。")
    with st.container():
        st.session_state.sound_on = st.toggle("🔊 轻量音效", value=st.session_state.sound_on)
        st.toggle("🌊 首页动态效果", value=True, disabled=True, help="水面、岛屿与按钮动效已开启")
        st.caption("房源数据：租赁挂牌快照（非实时、非成交记录）｜不收集真实姓名、电话、邮箱或精确住址。")
    if st.session_state.preferences: render_bottom_navigation("settings")
    elif st.button("返回首页", use_container_width=True): go("cover")


def survey_page() -> None:
    game_topbar(TOTAL_ROUNDS, TOTAL_ROUNDS, st.session_state.coins, st.session_state.player_name, st.session_state.avatar_accessory)
    progress_dots(10, 12)
    hud_bar(st.session_state.coins, _current_streak(), len(st.session_state.badges_earned))
    _show_pending_toast()
    scene_heading("终幕 · 回望", "最后几道问题", "旅程快结束了。聊聊这一路的体验，就真正“落脚”了。")
    control = st.session_state.treatment_group == "control"
    with st.form("post_survey"):
        helpful = st.slider("房源排序是否有帮助" if control else "AI 推荐是否有帮助",1,7,4)
        final_trust = st.slider("对网站推荐机制的最终信任程度" if control else "对 AI 推荐的最终信任程度",1,7,4)
        accuracy = st.slider("房源信息是否有助于准确选择" if control else "推荐是否准确",1,7,4)
        reuse = st.slider("是否愿意再次使用此类租房推荐工具",1,7,4)
        comments = st.text_area("可选意见（最多200字）",max_chars=200)
        done = st.form_submit_button("提交并查看个人结果",type="primary",use_container_width=True)
    if done:
        row={"participant_id":st.session_state.participant_id,"perceived_helpfulness":helpful,"final_ai_trust":final_trust,"perceived_accuracy":accuracy,"willingness_to_use_again":reuse,"comments":comments}
        try: save_post_survey(row)
        except Exception as exc: st.error(f"问卷保存失败：{exc}"); return
        st.session_state.survey_done=True; go("results")


def results_page() -> None:
    game_topbar(TOTAL_ROUNDS, TOTAL_ROUNDS, st.session_state.coins, st.session_state.player_name, st.session_state.avatar_accessory)
    progress_dots(11, 12)
    confetti_burst()
    if st.session_state.sound_on:
        sound_ping("badge")
    st.markdown("<div class='pxl' style='font-size:1.3rem;'>🏁 到站了：落脚成功</div>", unsafe_allow_html=True)
    st.title("感谢参与！")
    choices=pd.DataFrame(st.session_state.choices)
    if choices.empty: st.warning("当前会话没有可汇总的选择记录。"); return
    summary=participant_summary(choices)

    character_identity_card(
        st.session_state.avatar_hair, st.session_state.avatar_outfit,
        st.session_state.avatar_accessory, st.session_state.player_name,
        st.session_state.coins, st.session_state.badges_earned,
        GROUP_LABELS[st.session_state.treatment_group], st.session_state.avatar_hair_color,
    )
    st.markdown("##### 本次解锁的成就")
    badge_shelf(st.session_state.badges_earned)

    st.markdown("---")
    c1,c2,c3=st.columns(3); c1.metric("平均决策时间",f"{summary['avg_time']:.1f} 秒"); c2.metric("平均满意度",f"{summary['avg_satisfaction']:.1f}/7"); c3.metric("选择算法最高分房源",f"{summary['follow_rate']:.0%}")
    st.write("匿名编号：",st.session_state.participant_id); st.write("体验模式：",GROUP_LABELS[st.session_state.treatment_group])
    names={"importance_rent":"租金","importance_location":"目的地区域匹配","importance_area":"面积","importance_metro":"地铁距离"}
    top=sorted(names,key=lambda k:st.session_state.preferences[k],reverse=True)[:3]
    st.success(f"你最重视的三个属性是：{'、'.join(names[k] for k in top)}。以上结果仅根据本次声明偏好和模拟选择计算，不代表真实市场中的最优选择。")
    if st.button("重新开始（不会覆盖已保存记录）"):
        if "participant" in st.query_params:
            del st.query_params["participant"]
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()


init_state()
restore_reconnected_session()
render_back_button()
try:
    {"cover":cover_page,"intro":intro_page,"welcome":welcome,
     "preferences_basic":preferences_basic_page,"preferences_detail":preferences_detail_page,
     "journey":journey_page,"choice":choice_page,
     "free_explore":free_explore_page,"nest":nest_page,"records":records_page,
     "favorites":favorites_page,"settings":settings_page,
     "survey":survey_page,"results":results_page}.get(st.session_state.stage,cover_page)()
except Exception as exc:
    st.error(f"页面遇到异常：{exc}")
    st.info("请刷新页面重试；已成功提交的数据不会因刷新而被覆盖。")
