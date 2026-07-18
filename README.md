# RentChoice AI

RentChoice AI 是《人工智能与经管前沿》课程期末项目：参与者匿名填写偏好、完成六轮租房三选一，系统以透明公式计算推荐，并随机比较“仅信息”“推荐分数”“推荐+解释”三种体验。当前房源来自用户提供的房天下上海租赁挂牌 CSV 快照；项目不进行实时爬取，数据不是二手房成交记录，也不提供真实租房建议。

## 已实现功能

- 知情同意、随机匿名 participant_id、参与者级固定分组
- 29,006 条上海租赁挂牌快照，其中通过基础质量检查的记录进入实验抽样
- 八维 0–100 确定性推荐、平衡解释、无 API Key 回退
- 六轮随机顺序三选一、反应时间、满意度、信心、WTP 和代理福利损失
- 结束问卷、个人摘要、密码管理台、图表和三表 CSV 下载
- Supabase 优先、本地 UTF-8 CSV 自动回退、按唯一键防重复

## 文件结构

```text
app.py                      参与者网站入口
pages/1_Admin_Dashboard.py  密码保护管理台
data/listings.csv           模拟房源
src/                        推荐、实验、存储、解释、统计模块
scripts/smoke_test.py       离线自检
docs/                       系统设计、研究设计、变量字典
```

## 零基础本地运行

1. 安装 Python 3.11。Windows/macOS 可从 [Python 官网](https://www.python.org/downloads/) 下载；Windows 安装时勾选 “Add Python to PATH”。
2. 打开终端：Windows 搜索 PowerShell；macOS 打开“终端”。使用 `cd` 进入本项目目录。例如 macOS：

   ```bash
   cd /你的路径/rentchoice-ai
   ```

3. 创建独立环境（只需一次）：

   ```bash
   python3 -m venv .venv
   ```

4. 激活环境。macOS/Linux：

   ```bash
   source .venv/bin/activate
   ```

   Windows PowerShell：

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

5. 安装依赖：

   ```bash
   python -m pip install -r requirements.txt
   ```

6. 运行检查和网站：

   ```bash
   python scripts/smoke_test.py
   streamlit run app.py
   ```

   浏览器通常自动打开 `http://localhost:8501`。停止网站时回终端按 `Ctrl+C`。未配置 Supabase 会显示“本地演示模式”；每轮选择写入 `data/local_results.csv`，参与者和问卷分别写入对应的本地 CSV。

## 配置环境变量与 LLM

复制 `.env.example` 为 `.env`（不要上传 `.env`），填写需要的值。基础演示不需要任何密钥。LLM 默认关闭，规则解释仍完整可用；保持 `ENABLE_LLM=false` 即可关闭。若启用 OpenAI 或 DeepSeek 等 OpenAI-compatible 服务，填写 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`，并设置 `ENABLE_LLM=true`。API 失败自动回退规则解释。

## Supabase：从创建到建表

1. 注册 Supabase，点击 New project，保存数据库密码并等待项目建立。
2. 左侧打开 SQL Editor，点击 New query，粘贴下方完整 SQL 并 Run。
3. 打开 Project Settings → API，复制 Project URL 和 `anon` key（课程演示可用；公开研究应配置严格 RLS 或仅服务端写入）。
4. 本地写入 `.env`：`SUPABASE_URL=...`、`SUPABASE_KEY=...`。重启 Streamlit。

```sql
create table if not exists participants (
 participant_id text primary key, created_at timestamptz default now(), treatment_group text not null,
 budget_max integer, ideal_rent integer, max_commute integer, destination_district text, min_area integer, rental_type_preference text,
 importance_rent integer, importance_commute integer, importance_location integer, importance_area integer, importance_metro integer,
 importance_decoration integer, importance_community integer, importance_safety integer,
 prior_rental_experience boolean, initial_ai_trust integer, participant_status text, consent boolean
);
create table if not exists choices (
 participant_id text references participants(participant_id), round_number integer, treatment_group text,
 option_a_id text, option_b_id text, option_c_id text, recommended_listing_id text, chosen_listing_id text,
 recommendation_followed boolean, chosen_rent integer, chosen_commute integer, chosen_area numeric,
 willingness_to_pay integer, satisfaction integer, choice_confidence integer, decision_time_seconds numeric,
 chosen_location_match numeric, chosen_utility numeric, best_available_utility numeric, welfare_loss numeric, created_at timestamptz default now(),
 primary key (participant_id, round_number)
);
create table if not exists post_survey (
 participant_id text primary key references participants(participant_id), perceived_helpfulness integer,
 final_ai_trust integer, perceived_accuracy integer, willingness_to_use_again integer,
 comments varchar(200), created_at timestamptz default now()
);
alter table participants enable row level security;
alter table choices enable row level security;
alter table post_survey enable row level security;
create policy "anon insert participants" on participants for insert to anon with check (consent = true);
create policy "anon update participants" on participants for update to anon using (true) with check (consent = true);
create policy "anon insert choices" on choices for insert to anon with check (round_number between 1 and 6);
create policy "anon update choices" on choices for update to anon using (true) with check (round_number between 1 and 6);
create policy "anon insert survey" on post_survey for insert to anon with check (char_length(coalesce(comments,'')) <= 200);
create policy "anon update survey" on post_survey for update to anon using (true) with check (char_length(coalesce(comments,'')) <= 200);
```

旧数据库升级到位置匹配版时，在 SQL Editor 额外运行：

```sql
alter table participants add column if not exists destination_district text;
alter table participants add column if not exists importance_location integer;
alter table choices add column if not exists chosen_location_match numeric;
```

注意：管理台需要读取数据。最简单的课堂演示可在 Supabase 为三表增加 `select` policy，但这会让持有 anon key 的客户端能读取匿名原始数据。更安全的方式是使用只在 Streamlit Secrets 中保存的 service-role key，并绝不提交 GitHub。正式研究应由教师/伦理审查决定访问策略。

## GitHub 与 Streamlit Community Cloud（零基础）

1. 注册 GitHub，右上角 `+` → New repository，命名 `rentchoice-ai`，选择 Private 或 Public，不要勾选自动创建 README。
2. 项目终端依次运行（把账号和仓库名改成自己的）：

   ```bash
   git init
   git add .
   git commit -m "Initial RentChoice AI project"
   git branch -M main
   git remote add origin https://github.com/你的账号/rentchoice-ai.git
   git push -u origin main
   ```

3. 登录 [Streamlit Community Cloud](https://share.streamlit.io/)，点击 Create app，选择仓库、`main` 分支和 `app.py`，然后 Deploy。
4. App settings → Secrets，使用 TOML 格式填写（不要加到代码仓库）：

   ```toml
   SUPABASE_URL="https://xxxx.supabase.co"
   SUPABASE_KEY="你的密钥"
   ADMIN_PASSWORD="一个强密码"
   ENABLE_LLM="false"
   ```

5. 保存后重启应用。把参与者链接发给同学即可。Community Cloud 的本地文件可能在重启后丢失，且多实例写 CSV 不可靠，所以多人正式收集必须配置 Supabase。

## 数据下载与管理台

左侧页面导航进入 `Admin Dashboard`，输入 `ADMIN_PASSWORD`。未配置时本地默认密码是 `rentchoice-demo`，仅供本机演示，公开部署前必须修改。管理台可分别下载 participants、choices、post_survey CSV；文件用 UTF-8 BOM，可直接在中文 Excel 打开。参与者页面不显示密码。

## 修改实验

- 重新导入同结构真实 CSV：`python scripts/import_real_listings.py "源文件.csv" --output data/listings.csv`。脚本不会修改源文件，会保留原始文本、解析明确数值并标记异常记录；之后运行 smoke test。
- 手工修改房源：用 Excel/表格软件编辑 `data/listings.csv`，必须保留全部列、至少 36 行、唯一 `listing_id`，并另存为 UTF-8 CSV；运行 smoke test 验证。
- 修改轮数：调整 `src/experiment.py` 的 `TOTAL_ROUNDS`，同步修改 Supabase `choices` policy、说明文字和测试。确保房源池足够。
- 修改公式：只改 `src/recommender.py`，同时更新 `docs/system_design.md`，保证输出仍为 0–100。

## 常见错误

- `streamlit: command not found`：确认已激活 `.venv`，再运行 `python -m streamlit run app.py`。
- `ModuleNotFoundError`：运行 `python -m pip install -r requirements.txt`。
- Supabase 保存失败后出现本地 CSV：检查 URL/key、表名、SQL 和 RLS policy；系统会安全回退。
- 部署后数据消失：本地模式不是云端数据库，请配置 Supabase。
- 页面显示房源字段缺失：还原 CSV 表头并运行 smoke test。
- Git 上传密钥：立即在服务商后台撤销密钥，生成新密钥；确认 `.env` 与 `.streamlit/secrets.toml` 在 `.gitignore`。

## 局限与伦理

数据为第三方租赁挂牌快照，未验证真实性、时效性或可租状态，且缺少通勤、装修、社区、安全、电梯、押金和中介费；偏好和福利均为声明式代理。项目组公开分发数据或网站前，应确认数据取得方式、再利用授权和原平台条款。推荐公式无法涵盖噪音、合同风险、歧视、真实供给等因素。平台不应替代现实决策。正式研究需伦理审批、预注册、最小化收集、访问控制、保留期限、撤回机制和充分样本；不得把探索性结果包装为已证实结论。
