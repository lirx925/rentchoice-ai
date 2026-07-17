"""Password-protected aggregate dashboard for course researchers."""
import os
from io import BytesIO
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from src.analytics import group_summary
from src.storage import load_all_results, storage_mode

load_dotenv()
try:
    for _key in ["SUPABASE_URL","SUPABASE_KEY","ADMIN_PASSWORD"]:
        if _key in st.secrets and _key not in os.environ: os.environ[_key]=str(st.secrets[_key])
except FileNotFoundError:
    pass
st.set_page_config(page_title="RentChoice AI 管理台",page_icon="📊",layout="wide")
st.title("📊 RentChoice AI 管理员仪表盘")
password=os.getenv("ADMIN_PASSWORD") or "rentchoice-demo"
if not os.getenv("ADMIN_PASSWORD"): st.warning("当前使用本地演示默认密码 rentchoice-demo。公开部署前必须配置 ADMIN_PASSWORD。")
if not st.session_state.get("admin_ok"):
    entered=st.text_input("管理员密码",type="password")
    if st.button("登录"):
        if entered==password: st.session_state.admin_ok=True; st.rerun()
        else: st.error("密码错误。")
    st.stop()

st.caption(f"当前数据源：{storage_mode()}模式")
if st.button("刷新数据"): st.rerun()
data=load_all_results(); participants,choices,surveys=data["participants"],data["choices"],data["post_survey"]
c1,c2,c3=st.columns(3); c1.metric("参与人数",participants["participant_id"].nunique() if not participants.empty else 0); c2.metric("已完成轮次",len(choices)); c3.metric("完成问卷",len(surveys))
if choices.empty:
    st.info("暂无选择数据。完成至少一轮体验后即可查看统计。"); st.stop()
summary=group_summary(choices); st.subheader("分组结果"); st.dataframe(summary,use_container_width=True,hide_index=True)
st.plotly_chart(px.bar(summary,x="treatment_group",y="participants",title="各组参与人数"),use_container_width=True)
round_completion=choices.groupby("round_number")["participant_id"].nunique().reset_index(name="completed_participants")
st.plotly_chart(px.line(round_completion,x="round_number",y="completed_participants",markers=True,title="每轮完成人数"),use_container_width=True)
if not participants.empty and not surveys.empty and "initial_ai_trust" in participants:
    trust=participants[["participant_id","treatment_group","initial_ai_trust"]].merge(surveys[["participant_id","final_ai_trust"]],on="participant_id")
    trust["trust_change"]=trust["final_ai_trust"]-trust["initial_ai_trust"]
    st.subheader("AI 信任前后变化"); st.dataframe(trust.groupby("treatment_group",as_index=False)[["initial_ai_trust","final_ai_trust","trust_change"]].mean(),hide_index=True,use_container_width=True)
st.subheader("匿名数据预览"); table=st.selectbox("数据表",list(data)); st.dataframe(data[table].head(200),use_container_width=True)
for name,df in data.items(): st.download_button(f"下载 {name}.csv",df.to_csv(index=False).encode("utf-8-sig"),f"rentchoice_{name}.csv","text/csv")
