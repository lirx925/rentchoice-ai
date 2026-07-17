"""RentChoice AI participant-facing Streamlit application."""
from __future__ import annotations
import time, uuid
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.analytics import participant_summary
from src.data_loader import load_listings
from src.experiment import TOTAL_ROUNDS, assign_treatment, build_choice_sets, welfare_metrics
from src.explanations import optional_llm_explanation
from src.recommender import score_listings
from src.storage import save_choice, save_participant, save_post_survey, storage_mode

load_dotenv()
try:
    for _key in ["SUPABASE_URL","SUPABASE_KEY","OPENAI_API_KEY","OPENAI_BASE_URL","OPENAI_MODEL","ADMIN_PASSWORD","EXPERIMENT_SEED","ENABLE_LLM"]:
        if _key in st.secrets and _key not in __import__("os").environ:
            __import__("os").environ[_key] = str(st.secrets[_key])
except FileNotFoundError:
    pass
st.set_page_config(page_title="RentChoice AI", page_icon="🏠", layout="wide", initial_sidebar_state="collapsed")

TYPE_LABELS = {"shared":"合租", "studio":"独立单间", "whole":"整租"}
GROUP_LABELS = {"control":"信息浏览模式", "score_only":"智能评分模式", "explained":"解释型推荐模式"}

st.markdown("""<style>
.block-container{max-width:1100px;padding-top:2rem}.rent-card{border:1px solid #dfe5ec;border-radius:14px;padding:16px;background:#fff;min-height:390px}.tag{display:inline-block;background:#eaf2ff;color:#2457a6;padding:4px 9px;border-radius:99px;font-size:.82rem}.muted{color:#667085}.stButton>button{border-radius:9px} @media(max-width:700px){.block-container{padding:1rem}.rent-card{min-height:auto}}
</style>""", unsafe_allow_html=True)

def init_state() -> None:
    """Initialize all workflow state in one place."""
    defaults = {"stage":"welcome", "participant_id":None, "treatment_group":None, "preferences":None, "choice_sets":None, "round_number":1, "round_started_at":None, "choices":[], "survey_done":False}
    for key, value in defaults.items(): st.session_state.setdefault(key, value)

@st.cache_data
def listings_data() -> pd.DataFrame:
    return load_listings()

def go(stage: str) -> None:
    st.session_state.stage = stage
    st.rerun()

def top_progress(label: str, value: float) -> None:
    st.caption(f"匿名参与 · {storage_mode()}模式 · {label}")
    st.progress(value)

def welcome() -> None:
    st.title("🏠 RentChoice AI")
    st.subheader("面向大学生的可解释租房推荐与住房选择研究平台")
    st.info("这是《人工智能与经管前沿》课程项目和研究原型。所有房源均为模拟数据，不构成真实租房、投资或消费建议。")
    st.markdown("""
本体验约需 8–12 分钟。系统不会收集姓名、电话、邮箱、身份证、学校全称或精确住址。你的偏好、选择与反应时间将使用随机匿名编号保存，仅用于课程展示和潜在学术研究设计。你可以随时关闭页面退出。

你将先设置租房偏好，再完成 6 轮三选一任务，最后填写简短问卷。不同参与者看到的信息形式可能不同，这是随机研究设计的一部分。
""")
    consent = st.checkbox("我已阅读以上说明，同意匿名记录我的选择数据")
    if st.button("我同意并开始", type="primary", disabled=not consent, use_container_width=True):
        st.session_state.participant_id = str(uuid.uuid4())
        st.session_state.treatment_group = assign_treatment(st.session_state.participant_id)
        go("preferences")

def preferences_page() -> None:
    top_progress("设置租房偏好", .08)
    st.title("你的租房偏好")
    st.caption("请按真实想法回答；不需要填写任何身份识别信息。")
    # Form/widget keys must not collide with workflow data stored in session_state.
    with st.form("preferences_form"):
        c1,c2 = st.columns(2)
        budget_max = c1.number_input("每月最高预算（元）", 1800, 8000, 3500, 100)
        ideal_rent = c2.number_input("最理想月租（元）", 1500, 7000, 2800, 100)
        max_commute = c1.slider("最大可接受通勤时间（分钟）", 10, 90, 45)
        min_area = c2.slider("最低可接受面积（㎡）", 10, 60, 22)
        rental_pref_label = st.radio("租赁类型偏好", ["接受合租", "仅接受单间或整租", "无明显偏好"], horizontal=True)
        metro_priority = st.toggle("我重视地铁便利", value=True)
        st.markdown("##### 各因素重要性（1=不重要，5=非常重要）")
        cols = st.columns(4)
        fields = [("租金","importance_rent"),("通勤时间","importance_commute"),("面积","importance_area"),("地铁距离","importance_metro"),("装修","importance_decoration"),("社区环境","importance_community"),("安全","importance_safety")]
        vals = {key: cols[i%4].slider(label,1,5,4 if i<3 else 3,key=key) for i,(label,key) in enumerate(fields)}
        prior = st.radio("是否有租房经历？", ["是", "否"], horizontal=True)
        trust = st.slider("对 AI 推荐的初始信任程度", 1, 7, 4)
        status = st.selectbox("当前身份", ["本科生", "研究生", "实习生", "已工作", "其他"])
        submitted = st.form_submit_button("保存偏好并进入选择任务", type="primary", use_container_width=True)
    if submitted:
        if ideal_rent > budget_max:
            st.error("最理想月租不能高于最高预算，请调整后重试。")
            return
        mapping = {"接受合租":"accept_shared", "仅接受单间或整租":"no_shared", "无明显偏好":"no_preference"}
        prefs = {"budget_max":budget_max,"ideal_rent":ideal_rent,"max_commute":max_commute,"min_area":min_area,"rental_type_preference":mapping[rental_pref_label],"metro_priority":metro_priority,**vals,"prior_rental_experience":prior=="是","initial_ai_trust":trust,"participant_status":status}
        st.session_state.preferences = prefs
        st.session_state.choice_sets = build_choice_sets(listings_data(), st.session_state.participant_id)
        try:
            save_participant({"participant_id":st.session_state.participant_id,"treatment_group":st.session_state.treatment_group,**{k:v for k,v in prefs.items() if k!="metro_priority"},"consent":True})
        except Exception as exc:
            st.error(f"偏好暂时无法保存：{exc}"); return
        st.session_state.round_started_at = time.time(); go("choice")

def card(row: pd.Series, label: str, is_recommended: bool, group: str, explanation: str | None) -> None:
    badge = "<span class='tag'>RentChoice AI 推荐</span>" if is_recommended and group != "control" else ""
    score = f"<b>推荐分数：{row['recommendation_score']:.1f}/100</b><br>" if is_recommended and group != "control" else ""
    detail = f"<div style='margin-top:10px;color:#344054'>{explanation}</div>" if explanation and is_recommended and group == "explained" else ""
    fee = "无" if float(row["agency_fee"]) == 0 else f"{int(row['agency_fee'])}元"
    st.markdown(f"""<div class='rent-card'><h3>房源 {label}</h3>{badge}<h4>{row['title']}</h4><div class='muted'>{row['district']} · {TYPE_LABELS[row['rental_type']]}</div><h2>¥{int(row['monthly_rent']):,}<small>/月</small></h2>{score}<p>🚇 通勤 {int(row['commute_minutes'])} 分钟 · 地铁 {int(row['metro_distance_m'])} 米<br>📐 {int(row['area_sqm'])}㎡ · {int(row['bedrooms'])} 间卧室 · {'有' if row['has_elevator'] else '无'}电梯<br>✨ 装修 {row['decoration_score']}/5 · 社区 {row['community_score']}/5 · 安全 {row['safety_score']}/5<br>💳 押金 {int(row['deposit_months'])} 个月 · 中介费 {fee}</p><p>{row['short_description']}</p>{detail}</div>""", unsafe_allow_html=True)

def choice_page() -> None:
    r = int(st.session_state.round_number)
    if r > TOTAL_ROUNDS: go("survey"); return
    top_progress(f"第 {r}/{TOTAL_ROUNDS} 轮", .1 + .65*(r-1)/TOTAL_ROUNDS)
    st.title(f"第 {r} 轮：选择最愿意租的房源")
    ids = st.session_state.choice_sets[r-1]
    options = listings_data()[listings_data().listing_id.isin(ids)].set_index("listing_id").loc[ids].reset_index()
    scored = score_listings(options, st.session_state.preferences)
    best_idx = scored["recommendation_score"].idxmax(); recommended_id = str(scored.loc[best_idx,"listing_id"])
    explanation = optional_llm_explanation(scored.loc[best_idx], scored.drop(best_idx), st.session_state.preferences) if st.session_state.treatment_group == "explained" else None
    labels = ["A","B","C"]
    cols = st.columns(3)
    for i,(_,row) in enumerate(scored.iterrows()):
        with cols[i]: card(row, labels[i], row["listing_id"]==recommended_id, st.session_state.treatment_group, explanation)
    with st.form(f"choice_{r}"):
        selected_label = st.radio("我最愿意租", labels, index=None, horizontal=True)
        satisfaction = st.slider("对这次选择的满意度",1,7,4)
        confidence = st.slider("选择信心",1,7,4)
        wtp = st.number_input("对所选房源的最高月租支付意愿（元）",1000,10000,3000,100)
        submitted = st.form_submit_button("提交本轮选择", type="primary", use_container_width=True)
    if submitted:
        if selected_label is None: st.error("请先选择房源 A、B 或 C。"); return
        idx = labels.index(selected_label); chosen = scored.iloc[idx]
        chosen_u,best_u,loss = welfare_metrics(scored,str(chosen.listing_id))
        elapsed = round(max(0.0,time.time()-float(st.session_state.round_started_at or time.time())),2)
        row = {"participant_id":st.session_state.participant_id,"round_number":r,"treatment_group":st.session_state.treatment_group,"option_a_id":str(scored.iloc[0].listing_id),"option_b_id":str(scored.iloc[1].listing_id),"option_c_id":str(scored.iloc[2].listing_id),"recommended_listing_id":recommended_id,"chosen_listing_id":str(chosen.listing_id),"recommendation_followed":str(chosen.listing_id)==recommended_id,"chosen_rent":int(chosen.monthly_rent),"chosen_commute":int(chosen.commute_minutes),"chosen_area":float(chosen.area_sqm),"willingness_to_pay":int(wtp),"satisfaction":int(satisfaction),"choice_confidence":int(confidence),"decision_time_seconds":elapsed,"chosen_utility":chosen_u,"best_available_utility":best_u,"welfare_loss":loss}
        try: save_choice(row)
        except Exception as exc: st.error(f"本轮数据保存失败，请重试：{exc}"); return
        existing = [x for x in st.session_state.choices if x["round_number"] != r]
        st.session_state.choices = existing + [row]
        st.session_state.round_number = r+1
        st.session_state.round_started_at = time.time()
        go("survey" if r == TOTAL_ROUNDS else "choice")

def survey_page() -> None:
    top_progress("结束问卷", .82); st.title("最后几道问题")
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
    top_progress("已完成",1.0); st.title("感谢参与！")
    choices=pd.DataFrame(st.session_state.choices)
    if choices.empty: st.warning("当前会话没有可汇总的选择记录。"); return
    summary=participant_summary(choices)
    c1,c2,c3=st.columns(3); c1.metric("平均决策时间",f"{summary['avg_time']:.1f} 秒"); c2.metric("平均满意度",f"{summary['avg_satisfaction']:.1f}/7"); c3.metric("选择算法最高分房源",f"{summary['follow_rate']:.0%}")
    st.write("匿名编号：",st.session_state.participant_id); st.write("体验模式：",GROUP_LABELS[st.session_state.treatment_group])
    names={"importance_rent":"租金","importance_commute":"通勤","importance_area":"面积","importance_metro":"地铁距离","importance_decoration":"装修","importance_community":"社区环境","importance_safety":"安全"}
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
