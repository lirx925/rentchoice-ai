"""RentChoice AI participant-facing Streamlit application.

Game-ified presentation layer (v4 - Mario-style street): the participant
now actually WALKS a little sprite left/right along a street with ◀ / ▶
buttons, has to reach a door before it will let them knock, picks up
coins on the way, and gets a paged RPG-style dialogue box from each
landlord — on top of the existing avatar / coin / achievement / level-
clear systems, all rendered by src/game_ui.py.

Movement, coins and dialogue paging are driven by real
st.session_state — not just decoration — but they are entirely separate
from the experiment data. Treatment assignment, choice-set construction,
recommendation scoring, explanations, welfare metrics, and storage are
imported and used exactly as in the original app, so saved data keeps
the same schema described in docs/variable_dictionary.md.
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
from src.storage import save_choice, save_participant, save_post_survey, storage_mode
from src.game_ui import (
    inject_game_css, quest_log, intro_skyline, avatar_picker, interactive_street,
    star_picker, game_card, confetti_burst, ROUND_STORY, landlord_for,
    hud_bar, dialogue_box, compute_badges, badge_toast, badge_shelf,
    level_clear_banner, identity_card, sound_ping,
    DOOR_X, COIN_X, STREET_WIDTH, MOVE_STEP, RUN_STEP, KNOCK_RANGE, COIN_RANGE,
)

load_dotenv()
try:
    for _key in ["SUPABASE_URL","SUPABASE_KEY","OPENAI_API_KEY","OPENAI_BASE_URL","OPENAI_MODEL","ADMIN_PASSWORD","EXPERIMENT_SEED","ENABLE_LLM"]:
        if _key in st.secrets and _key not in __import__("os").environ:
            __import__("os").environ[_key] = str(st.secrets[_key])
except FileNotFoundError:
    pass
st.set_page_config(page_title="落脚 · RentChoice AI", page_icon="🏮", layout="wide", initial_sidebar_state="collapsed")
inject_game_css()

TYPE_LABELS = {"shared":"合租", "studio":"独立单间", "whole":"整租"}
GROUP_LABELS = {"control":"信息浏览模式", "score_only":"智能评分模式", "explained":"解释型推荐模式"}
QUEST_STEPS = ["① 行前准备", "② 沿街找房 ×6", "③ 结束问卷"]
COINS_PER_ROUND = 15
COINS_QUICK_BONUS = 5   # awarded when a decision took under 15s — flavor only
COIN_PICKUP_VALUE = 5   # flavor coins picked up while walking the street
STREET_START_X = 10


def init_state() -> None:
    """Initialize all workflow state in one place."""
    defaults = {
        "stage": "welcome", "participant_id": None, "treatment_group": None,
        "preferences": None, "choice_sets": None, "round_number": 1,
        "round_started_at": None, "choices": [], "survey_done": False,
        "choice_stage": "pick", "picked_label": None,
        # cosmetic game-layer state — never written to the saved dataset
        "avatar": None, "coins": 0, "badges_earned": [], "pending_toast": [],
        "sound_on": False, "street_x": STREET_START_X, "facing": "right",
        "collected_coins": set(), "dialogue_page": 1, "clear_coins_earned": 0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


@st.cache_data
def listings_data() -> pd.DataFrame:
    return eligible_listings(load_listings())


def go(stage: str) -> None:
    st.session_state.stage = stage
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


def _move_character(delta: int) -> None:
    """Real movement handler: updates position, flips facing, and
    auto-collects any coin the character walks over. Cosmetic bookkeeping
    only — never touches the saved experiment rows."""
    new_x = max(0, min(STREET_WIDTH, st.session_state.street_x + delta))
    st.session_state.facing = "right" if delta >= 0 else "left"
    for i, cx in enumerate(COIN_X):
        if i in st.session_state.collected_coins:
            continue
        if abs(new_x - cx) <= COIN_RANGE:
            st.session_state.collected_coins.add(i)
            st.session_state.coins += COIN_PICKUP_VALUE
            st.toast(f"🪙 捡到一枚金币 +{COIN_PICKUP_VALUE}", icon="🪙")
            if st.session_state.sound_on:
                sound_ping("coin")
    st.session_state.street_x = new_x
    if st.session_state.sound_on:
        sound_ping("step")
    st.rerun()


def welcome() -> None:
    intro_skyline()
    st.markdown("<div class='pxl' style='font-size:1.8rem;margin-top:14px;'>落脚</div>", unsafe_allow_html=True)
    st.subheader("面向大学生的可解释租房推荐与住房选择研究平台")
    quest_log(QUEST_STEPS, current=0)
    st.info("这是《人工智能与经管前沿》课程项目和研究原型。房源来自用户提供的上海租赁挂牌数据快照，并非实时房源或成交记录，不构成真实租房、投资或消费建议。")
    st.markdown("""
本体验约需 8–12 分钟。原始数据共 29,006 条，系统仅从通过基础质量检查的记录中抽取实验选项。数据快照可能过时，平台未验证挂牌真实性或可租状态。系统不会收集姓名、电话、邮箱、身份证、学校全称或精确住址。你的偏好、选择与反应时间将使用随机匿名编号保存，仅用于课程展示和潜在学术研究设计。你可以随时关闭页面退出。

你将先设置租房偏好，再走上街头完成 6 轮找房任务，最后填写简短问卷。走到门口才能敲门看房——不同参与者看到的信息形式可能不同，这是随机研究设计的一部分。
""")
    avatar_picker("avatar")
    st.session_state.sound_on = st.toggle("🔊 开启轻量音效（可选，浏览器可能会拦截自动播放）", value=st.session_state.sound_on)
    consent = st.checkbox("我已阅读以上说明，同意匿名记录我的选择数据")
    if st.button("我同意，进入数码世界 →", type="primary", disabled=not consent, use_container_width=True):
        st.session_state.participant_id = str(uuid.uuid4())
        st.session_state.treatment_group = assign_treatment(st.session_state.participant_id)
        go("preferences")


def preferences_page() -> None:
    top_progress("行前准备", .08)
    quest_log(QUEST_STEPS, current=0)
    st.markdown("<div class='story-box'><b class='pxl' style='font-size:.75rem;'>行前准备</b><br>"
                 "你刚拿到这座城市的 offer，接下来要找一个未来一年的落脚点。先告诉「落脚」你在意什么——"
                 "这些偏好会陪你走完整趟旅程，也会决定路上遇到的向导会怎么给你指路。</div>", unsafe_allow_html=True)
    st.title("你的租房偏好")
    st.caption("请按真实想法回答；不需要填写任何身份识别信息。")
    with st.form("preferences_form"):
        c1,c2 = st.columns(2)
        budget_max = c1.number_input("💰 每月最高预算（元）", 500, 100000, 7000, 100)
        ideal_rent = c2.number_input("💵 最理想月租（元）", 500, 80000, 5500, 100)
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
        st.markdown("##### 各因素重要性（1=不重要，5=非常重要）")
        cols = st.columns(4)
        fields = [("租金","importance_rent"),("目的地区域匹配","importance_location"),("面积","importance_area"),("地铁距离","importance_metro")]
        vals = {key: cols[i%4].slider(label,1,5,4 if i<3 else 3,key=key) for i,(label,key) in enumerate(fields)}
        prior = st.radio("是否有租房经历？", ["是", "否"], horizontal=True)
        trust = st.slider("🤝 对 AI 推荐的初始信任程度", 1, 7, 4)
        status = st.selectbox("当前身份", ["本科生", "研究生", "实习生", "已工作", "其他"])
        submitted = st.form_submit_button("背好包，出发 →", type="primary", use_container_width=True)
    if submitted:
        if ideal_rent > budget_max:
            st.error("最理想月租不能高于最高预算，请调整后重试。")
            return
        mapping = {"接受合租":"accept_shared", "仅接受单间或整租":"no_shared", "无明显偏好":"no_preference"}
        prefs = {"budget_max":budget_max,"ideal_rent":ideal_rent,"destination_district":destination_district,"min_area":min_area,"rental_type_preference":mapping[rental_pref_label],"metro_priority":metro_priority,**vals,"prior_rental_experience":prior=="是","initial_ai_trust":trust,"participant_status":status}
        st.session_state.preferences = prefs
        st.session_state.choice_sets = build_choice_sets(listings_data(), st.session_state.participant_id)
        try:
            save_participant({"participant_id":st.session_state.participant_id,"treatment_group":st.session_state.treatment_group,**{k:v for k,v in prefs.items() if k!="metro_priority"},"consent":True})
        except Exception as exc:
            st.error(f"偏好暂时无法保存：{exc}"); return
        st.session_state.round_started_at = time.time()
        st.session_state.choice_stage = "pick"
        go("choice")


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


def choice_page() -> None:
    r = int(st.session_state.round_number)
    if r > TOTAL_ROUNDS:
        go("survey"); return

    scored, recommended_id, explanation = _scored_options(r)
    labels = ["A", "B", "C"]
    stage = st.session_state.choice_stage
    landlords = {lab: landlord_for(r, lab) for lab in labels}

    top_progress(f"第 {r}/{TOTAL_ROUNDS} 站", .1 + .65*(r-1)/TOTAL_ROUNDS)
    quest_log(QUEST_STEPS, current=1)
    hud_bar(st.session_state.coins, _current_streak(), len(st.session_state.badges_earned))
    _show_pending_toast()

    title, story = ROUND_STORY.get(r, (f"第 {r} 站", "新一批房源出现了——"))
    st.markdown(f"<div class='story-box'><b class='pxl' style='font-size:.75rem;'>{title}</b><br>{story}</div>", unsafe_allow_html=True)

    if stage == "clear":
        level_clear_banner(r, TOTAL_ROUNDS, st.session_state.clear_coins_earned)
        badge_toast(st.session_state.pending_toast)
        st.session_state.pending_toast = []
        if st.button("继续前进 →", type="primary", use_container_width=True):
            st.session_state.round_number = r + 1
            st.session_state.round_started_at = time.time()
            st.session_state.choice_stage = "pick"
            st.session_state.picked_label = None
            st.session_state.street_x = STREET_START_X
            st.session_state.facing = "right"
            st.session_state.collected_coins = set()
            st.session_state.dialogue_page = 1
            go("survey" if r == TOTAL_ROUNDS else "choice")
        return

    if stage == "pick":
        interactive_street(r, TOTAL_ROUNDS, st.session_state.street_x, st.session_state.avatar, DOOR_X, landlords, st.session_state.collected_coins, facing=st.session_state.facing)
        mc1, mc2, mc3, mc4 = st.columns(4)
        if mc1.button("◀◀ 快退", use_container_width=True):
            _move_character(-RUN_STEP)
        if mc2.button("◀ 走", use_container_width=True):
            _move_character(-MOVE_STEP)
        if mc3.button("走 ▶", use_container_width=True):
            _move_character(MOVE_STEP)
        if mc4.button("快进 ▶▶", use_container_width=True):
            _move_character(RUN_STEP)

        st.subheader("这一站，你会敲开哪一扇门？")
        cols = st.columns(3)
        for i, (_, row) in enumerate(scored.iterrows()):
            label = labels[i]
            near = abs(st.session_state.street_x - DOOR_X[label]) <= KNOCK_RANGE
            with cols[i]:
                game_card(row, label, row["listing_id"] == recommended_id, st.session_state.treatment_group, explanation, TYPE_LABELS, landlord=landlords[label], locked=not near)
                dist = abs(st.session_state.street_x - DOOR_X[label])
                btn_label = f"敲门 · {label} →" if near else f"🚶 还差 {dist}px 走近点"
                if st.button(btn_label, key=f"pick_{r}_{label}", type="primary" if near else "secondary", use_container_width=True, disabled=not near):
                    st.session_state.picked_label = label
                    st.session_state.choice_stage = "rate"
                    st.session_state.dialogue_page = 1
                    if st.session_state.sound_on:
                        sound_ping("knock")
                    st.rerun()
        return

    # stage == "rate"
    idx = labels.index(st.session_state.picked_label)
    chosen_row = scored.iloc[idx]
    landlord = landlords[st.session_state.picked_label]

    ai_line = explanation if (explanation and chosen_row["listing_id"] == recommended_id and st.session_state.treatment_group == "explained") else None
    pages = [landlord["line"]] + ([ai_line] if ai_line else [])
    page = min(st.session_state.dialogue_page, len(pages))
    speaker = landlord["name"] if page == 1 else "AI 顾问"
    speaker_emoji = landlord["emoji"] if page == 1 else "🏮"

    st.subheader(f"你敲开了房源 {st.session_state.picked_label} 的门")
    dialogue_box(speaker_emoji, speaker, pages[page - 1], page, len(pages))
    if page < len(pages):
        if st.button("▶ 继续", key=f"dlg_next_{r}"):
            st.session_state.dialogue_page += 1
            st.rerun()

    game_card(chosen_row, st.session_state.picked_label, chosen_row["listing_id"] == recommended_id, st.session_state.treatment_group, None, TYPE_LABELS, landlord=landlord)

    satisfaction = star_picker(f"sat_{r}", "对这次选择的满意度", scale=7, icon="★", default=4)
    confidence = star_picker(f"conf_{r}", "选择信心", scale=7, icon="⚡", default=4)
    wtp_limit = max(30000, int(chosen_row.monthly_rent * 1.5))
    wtp = st.number_input("对所选房源的最高月租支付意愿（元）", 1000, wtp_limit, 3000, 100, key=f"wtp_{r}")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("← 换一套", key=f"back_{r}", use_container_width=True):
            st.session_state.choice_stage = "pick"
            st.rerun()
    with c2:
        confirm = st.button("确认选择，继续前进 →", key=f"confirm_{r}", type="primary", use_container_width=True)

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


def survey_page() -> None:
    top_progress("结束问卷", .82)
    quest_log(QUEST_STEPS, current=2)
    hud_bar(st.session_state.coins, _current_streak(), len(st.session_state.badges_earned))
    _show_pending_toast()
    st.markdown("<div class='story-box'><b class='pxl' style='font-size:.75rem;'>最后一站</b><br>"
                 "旅程快结束了，聊聊这一路的体验，就真正「落脚」了。</div>", unsafe_allow_html=True)
    st.title("最后几道问题")
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
    top_progress("已完成",1.0)
    confetti_burst()
    if st.session_state.sound_on:
        sound_ping("badge")
    st.markdown("<div class='pxl' style='font-size:1.3rem;'>🏁 到站了：落脚成功</div>", unsafe_allow_html=True)
    st.title("感谢参与！")
    choices=pd.DataFrame(st.session_state.choices)
    if choices.empty: st.warning("当前会话没有可汇总的选择记录。"); return
    summary=participant_summary(choices)

    identity_card(st.session_state.avatar, st.session_state.coins, st.session_state.badges_earned, GROUP_LABELS[st.session_state.treatment_group])
    st.markdown("##### 本次解锁的成就")
    badge_shelf(st.session_state.badges_earned)

    st.markdown("---")
    c1,c2,c3=st.columns(3); c1.metric("平均决策时间",f"{summary['avg_time']:.1f} 秒"); c2.metric("平均满意度",f"{summary['avg_satisfaction']:.1f}/7"); c3.metric("选择算法最高分房源",f"{summary['follow_rate']:.0%}")
    st.write("匿名编号：",st.session_state.participant_id); st.write("体验模式：",GROUP_LABELS[st.session_state.treatment_group])
    names={"importance_rent":"租金","importance_location":"目的地区域匹配","importance_area":"面积","importance_metro":"地铁距离"}
    top=sorted(names,key=lambda k:st.session_state.preferences[k],reverse=True)[:3]
    st.success(f"你最重视的三个属性是：{'、'.join(names[k] for k in top)}。以上结果仅根据本次声明偏好和模拟选择计算，不代表真实市场中的最优选择。")
    if st.button("重新开始（不会覆盖已保存记录）"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()


init_state()
try:
    {"welcome":welcome,"preferences":preferences_page,"choice":choice_page,"survey":survey_page,"results":results_page}.get(st.session_state.stage,welcome)()
except Exception as exc:
    st.error(f"页面遇到异常：{exc}")
    st.info("请刷新页面重试；已成功提交的数据不会因刷新而被覆盖。")
