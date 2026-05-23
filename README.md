# Hackerson-Aurum-Radar · 全球市场战略情报 Agent

Aurum Radar 是面向高级珠宝品牌海外市场战略决策的 AI 情报系统。在**不接入任何企业内部数据**的前提下，从 9 个海外市场（JP / KR / SG / TH / MY / VN / ID / PH / US）的新闻、社媒、官方法规、市场行情、电商平台公告等公开渠道主动采集信号，经多阶段 Agent 流水线沉淀为结构化情报事件，**每天产出可解释、可追溯、可执行**的战略简报与部门行动建议。

系统不是单次 LLM 总结，而是一条分阶段、幂等、全链路可追溯的流水线：

```
data_probe 9 市场采集 → 清洗去重 → 双坐标轴抽取（来源 × 作用机制）
→ 规则化评分 → 国家级研判 → 每日简报 → 战略情报议会（5 专家并行 + 首席战略官综合，输出上中下三策）
→ 部门行动建议 → 关联分析 + Ask Agent 追问
```

每一条结论都能回溯到具体情报 `id` → `raw_document` → `source_url`，避免泛泛而谈。前端以世界地图为入口，可视化呈现各市场机会 / 风险判断、情报事件流、行动建议看板，并通过右滑 Ask Agent 抽屉支持对当日判断的多轮追问与跨事件关联分析。

---

## 项目说明

仓库为单体多模块结构，各目录独立可运行：

| 目录 | 说明 |
|------|------|
| `backend/` | FastAPI 服务，承载 7 阶段情报流水线与 JSON API |
| `frontend/` | Vite + React + TypeScript 单页应用，战略情报看板 |
| `data_probe/` | 数据采集探针，输出 JSONL 至 `output/normalized/`（独立 venv） |

### 7 阶段流水线（后端核心）

```
Ingest → Clean → Extract → Score → Forecast → Brief → Council
 采集    清洗    抽取     打分     预测       简报     议会（合成行动）
```

第 7 阶段「珠宝情报议会」并联运行 5 位专家（产品营销 / 竞品战略 / 消费者洞察 / 风险合规 / 兵法谋士），再由首席战略官汇总输出 `council_reports` 与 `action_items`。详见 [backend/architecture.md](backend/architecture.md)。

### 前端页面

- **概览** Overview — 世界地图 + 国家判断面板 + 每日战略简报抽屉
- **情报中心** Intel — 情报事件流与详情
- **行动建议** Actions — 部门行动清单与详情
- **Agent Chat** — 右滑抽屉，针对当日判断进行追问

---

## Agent 设计方案

Agent 不是单点 LLM 调用，而是一条**分阶段、幂等、可单独触发**的流水线。每个阶段独立可重跑，全链路向 `job_runs` 写运行记录，结论可逐条回溯到原文。

### 阶段分工

| # | 阶段 | 模型/方式 | 落库 |
|---|------|----------|------|
| 1 | **Ingest** 采集 | Provider 框架（News / Competitor / Platform / Regulation / MarketData / MallEvent） | 内存 |
| 2 | **Clean** 清洗去重 | `content_hash` 去重 + 关键词初筛 | `raw_documents` + OSS 快照 |
| 3 | **Extract** 双坐标轴抽取 | `qwen-plus` + JSON Schema 校验 | 内存（Stage 4 落库） |
| 4 | **Score** 评分 | 规则化打分（LLM 仅在歧义时辅助） | `intelligence_events` |
| 5 | **Forecast** 国家级研判 | `qwen-plus` 聚类分析 | `market_snapshots` |
| 6 | **Brief** 每日简报 | `qwen-plus` 长文本生成 | `daily_briefs` |
| 7 | **Council** 战略情报议会 | 5 专家并行 + 总参谋综合（`qwen-plus`/`qwen-max`） | `council_reports` + `action_items` |

### 第 7 阶段：战略情报议会

```
intelligence_batch
   ├── 产品营销战略专家  ─┐
   ├── 竞品战略专家      ─┤
   ├── 消费者洞察专家    ─┼─▶ 首席战略官 ─▶ 决策报告（上/中/下三策 + 部门行动）
   ├── 风险合规专家      ─┤
   └── 兵法谋士          ─┘
```

5 位专家**并行、互不见彼此输出**（避免锚定），首席战略官串行综合、裁定分歧、拆解部门。一次市场调用约 6 次 LLM。

### 关键技术点

- **模型分级**：`qwen-flash`（轻量分类）/ `qwen-plus`（抽取/简报/行动，默认）/ `qwen-max`（议会综合）
- **环境一致性**：local / dev / prod 共用同一套 RDS + OSS + DashScope，差异全部由 `.env` 承担，代码不写 `if APP_ENV == ...`
- **可追溯性**：`event → raw_document → source_url / oss_path`；`brief / action → event_id`
- **手动触发**：`POST /api/jobs/run` 可指定 `markets` / `source_types` / `stages` 子集重跑

---

## 创新点

> 按数据流转顺序排列：**数据采集 → 结构化抽取 → 质量约束 → 议会决策 → 议会输出 → 横向分析 → 用户对话 → 横向架构能力**

### 1. data_probe · 数据源验证层（采集起点）

`data_probe/` 是独立的**数据源验证与采集层**，硬边界："不接 FastAPI、不写业务库、不用 Playwright"。验证通过的源才迁移到 `backend/services/ingestion/`——把"哪些源头能稳定生产化"作为可追溯的研究问题，而不是事后再返工。

- **9 市场 × 18 字段统一 schema**（JP/KR/SG/TH/MY/VN/ID/PH/US），`hl/gl/ceid` 参数化，与旧 SG 11 字段 JSON 双 schema 并存
- **failed placeholder 即信息**：百度指数需 JS+登录态、Lazada JS 渲染、DDG 沙盒 IP 被封——失败原因显式登记 `registry_only`，为下一步路径（申请 API / 采购数据）提供决策依据
- **去重 key 与 backend 对齐**：`dedupe_key()` ↔ `_compute_content_hash()` 实现一致，跨模块共享 `content_hash` 唯一约束，重复摄取自动幂等
- **HTTP 双栈 + 凭据降级**：requests→urllib 自动 fallback（兼容 LibreSSL + 代理）；PRAW 缺凭据降级公开 JSON；Tavily 24h 文件缓存零重复消耗
- **`evidence_level` ≠ `confidence`**：来源类型（official/media/social）与排序强度独立打分，下游可分别用于硬判断与早期信号

### 2. 双坐标轴抽取（信息来源 × 环境因子 + 传导链路）

把"信息从哪里来"与"信息如何作用于市场"解耦。第三阶段 LLM 同时输出两个独立坐标轴：

- **第一轴 · source_category**（来源渠道）：competition / product / social_media / regulation / channel / macro / supply_chain
- **第二轴 · env_factors**（底层作用机制，F1–F7）：supply_constraint / structure_disruption / demand_shift / regulatory_friction / price_conduction / narrative_pressure / channel_power_shift
- **传导链路 · conduction_chain**（A–E）：地缘-供给-成本 / 货币-消费-需求 / 文化-偏好-结构 / 制度-合规-成本 / 技术-替代-颠覆

下游聚类、研判、议会推理基于**作用机制**而非渠道分类——避免"金价上涨"和"婚庆下滑"被错误归并为同一类。

### 3. 强制证据链 + 置信度约束 + Evaluation 后置校验（贯穿 Stage 3–7）

领域铁律由所有专家与首席战略官共同遵守，从抽取阶段就开始执行，**末端再由独立 Evaluation Agent 复核打分**——单凭 prompt 自律不够，必须出闭环。

**前置约束**（写在专家与议会 prompt 里）：

- 任何判断**必须**可回溯到具体情报 `id`，没有 `evidence_ids` 不进任何输出
- 证据不足（单一来源 / 未验证社媒 / 单时间点）→ 置信度不得高于 medium
- **不把黄金价格上涨简单等同于利好**——必须区分投资金条 / 饰品金 / 婚庆金 / 悦己消费
- 区分情报 `sentiment`（来源情绪）与对我方业务的 `impact`（影响方向）
- `confidence` 由旧三档枚举升级为 `0.0–1.0` 浮点 + `ambiguity_flags` 数组（multi_factor_conflict / scope_unclear / timing_uncertain / source_unverified / entity_ambiguous）

**后置校验**（`services/evaluation/`，每轮议会跑完自动触发，加权产出 0–100 质量分）：

| 层 | 实现 | 校验内容 |
|----|------|---------|
| **规则校验**（无 LLM） | `checks.py` | `citation_completeness`（事件 source_url 覆盖率）/ `traceability_rate`（事件 → raw_document FK 比例）/ `credibility_distribution`（S/A/B/C/unknown 分布）/ `credibility_risk_flags`（P0 或 risk≥60 却仅 C/unknown 来源支撑）/ `score_range_flags`（分数越界） |
| **逐事件证据 grounding**（qwen-flash） | `critic.critique_event` | 拉对应 `raw_document` 节选 → 判 `business_impact` 是否能从原文推出 → verdict ∈ {grounded, overstated, unsupported} + `credibility_ok` 是否匹配来源 |
| **议会逻辑复审**（qwen-max） | `critic.critique_council` | 整体逻辑链是否自洽：council_summary 有没有泛泛而谈？opportunities / risks 是否都绑了 evidence_ids？上中下三策是否层次清晰且与摘要一致？department_actions 是否具体可执行？confidence 与证据强度是否匹配？→ logic_verdict ∈ {sound, minor_issues, flawed} |

**加权综合分**（`_overall_score`）：

```
0.20 × citation_completeness
+ 0.15 × traceability_rate
+ 0.35 × grounding_pass_rate       ← LLM 逐事件 grounding 通过率
+ 0.30 × credibility_match_rate    ← LLM 判 confidence 与来源可信度是否匹配
− 0.25 × credibility_penalty       ← 高影响事件 × 低可信来源的占比
```

凡是 verdict 为 `overstated/unsupported` 或 `credibility_ok=false` 的事件自动进 `human_review_list`，对接 PRD §16.1 人工复核流程——**让"不可信但被采纳"的结论成为可观测、可干预的指标**，而不是事后拍脑袋。

### 4. 五专家议会取代单 LLM 总结（Stage 7 核心）

| 维度 | 单一 LLM 总结 | 专家议会 |
|------|--------------|---------|
| 视角 | 一个 prompt 兼顾所有维度，互相稀释 | 每位专家只深挖一个维度 |
| 偏差 | 易被最显眼情报锚定 | 并行 + 互不可见，减少锚定 |
| 分歧 | 内部矛盾被和稀泥抹平 | 显式保留在 `expert_disagreements` |
| 证据 | 结论与证据易脱钩 | 强制每个判断绑定情报 `id` |
| 可执行 | 常停在「需关注 XX」 | 强制拆到部门 + 市场 + 品类 + 渠道 + 动作 |

### 5. 兵法谋士 · 三套谋略知识库融合

议会内置**兵法谋士**专家，融合三套全部以 skill 文件形态收录的谋略知识：

- **孙子兵法 skill**（vendored）— 13 条原则 / 商业 / 组织 / 反模式参考，作为通用谋略透镜
- **毛选 skill**（vendored，MIT）— 7 个心智模型 + 10 条决策启发式，提供矛盾分析法等框架
- **12 条珠宝出海策略库**（`strategy_library.json`）— 轻骑探路 / 借港登岸 / 避实击虚 / 文化定锚 / 小金引玉 / 华圈破冰 / 先声后店 / 高地占位 / 婚庆结盟 / 可退可进 / 避钻攻金 / 节庆爆点

谋士输出"判局 → 匹配计策 → 上中下三策思路"，并强制只能引用库内 `strategy_id`，不可编造。

### 6. 上中下三策决策结构（议会最终产出）

议会输出不是单一建议，而是 `strategic_options` 三策：每策包含**前提 / 代价 / 预期收益**，搭配机会 / 风险 / 观察项与五个部门行动清单（产品 / 营销 / 渠道 / 管理层 / 风险）。部门段**允许为空**，没有命中就不凑数。

### 7. 情报关联分析 Skill（横向分析能力）

议会回答"由情报推结论"，关联分析 skill 回答**"这些事合在一起意味着什么"**——与议会并列注册、可独立调用。核心差异化在于**反 LLM 过度自信**的硬约束：

- **强制前置校验**：事件数 ≥ 3 / 时间窗口 ≤ 90 天 / 必有 `env_factors` 与 `impact_scope` / ≥ 2 对共享字段，任一不通过直接 `ANALYSIS_REJECTED`，不在劣质输入上强行出结论
- **量化判定树**取代主观打分：候选对筛选 → 机制验证（相关 ≠ 因果）→ 共因排查 → 强度定级 → 置信度计算，每步阈值可查
- **传导时滞参考表**：F1–F7 每个因子配具体天数（价格 1–7 天、需求迁移 60–365 天），超出自动降级
- **链路置信度递减**：`chain.confidence = MIN(边) × 0.9`，越长越保守；必填 `alternative_explanation` 共因假设
- **置信度只能向下调整**（GC-5）+ **品类分化不得平均**（GC-4）+ **无 evidence_ids 不写结论**（GC-1）

### 8. Ask Agent · Chip 上下文 + 双 Agent 流式追问（用户对话终点）

前端右滑 `AgentChatDrawer` + 后端 `POST /api/agents/stream`（SSE）组合，把"针对今日判断追问"做成一个**上下文可拼装、路由确定性、可流式回放**的对话能力——而不是简单接一个 LLM Chat：

- **双 Agent + 确定性路由**：`general_chat`（追问简报/判断）与 `correlation_analysis`（≥3 个事件的因果链分析）按 `query.type` 字段直接 dispatch，**不靠 LLM 判断意图**；缺 type 或不存在直接 400
- **Chip 注入上下文**：5 个 chip（今日简报 / 市场判断 / 高优先级事件 / 部门行动 / 关联分析）一选即前端 fetch 对应接口，格式化为纯文本块 prepend 到用户 prompt 中——LLM 拿到的是真实结构化数据，不是凭空脑补
- **OpenAI 协议 SSE**：标准 `data: {chunk}\n\n` + `[DONE]`，每个 chunk 注入 `session_id`，前端 `streamAgent` 异步生成器逐 token 渲染，兼容任意 OpenAI 兼容生态
- **前后端双校验 + chip 联动**：关联分析在前端先用正则提取 `#数字` 校验 ≥3，后端 `_extract_event_ids` 再校验一次；选「关联分析」chip 自动联动「高优先级事件」chip，保证后端能 `_fetch_events_batch` 拿到真实事件
- **Skill 复用 + 输出格式覆盖**：关联分析 Agent 直接读 `intelligence-correlation-analysis/SKILL.md` 作 system prompt，末尾追加"纯文本输出覆盖"指令——同一 skill 同时支撑批处理 JSON 与对话纯文本两种输出，不复制提示词

### 9. Skill 化知识架构（横向架构能力）

专家、谋略库、知识源均以 markdown + JSON 的 **skill** 形式组织，不散落在大 prompt 里也不写成 Python 常量。新增专家或更换知识库只需替换文件，不动编排代码。Skills 通过 `pyproject.toml` 的 `aurum_radar.skills` entry point 注册，由 `stevedore` 自动发现。

### 10. 全链路可追溯 + 可手动重跑（横向工程能力）

- 每个阶段每次运行写 `job_runs`（status / params / rows_affected / error_message）
- 阶段幂等：`raw_documents.content_hash` 唯一约束保证重复采集不重复入库
- 任意子集可经 `POST /api/jobs/run` 指定 `stages` 重跑——debug 不必从头再来

---

## 依赖环境

### 后端
- Python **>= 3.9**（推荐 3.11）
- PostgreSQL（建议直接使用阿里云 RDS）
- 阿里云 OSS（可选，MVP 阶段未启用写入）
- 百炼 DashScope API Key（调用 `qwen-flash` / `qwen-plus` / `qwen-max`）
- 包管理：[uv](https://github.com/astral-sh/uv)（推荐）或 `pip`
- 主要库：FastAPI 0.115 · Uvicorn 0.32 · SQLAlchemy 2.0 · Alembic 1.14 · psycopg2 · APScheduler 3.10 · OpenAI SDK 1.55 · loguru · oss2 · stevedore

### 前端
- Node.js **>= 18**（推荐 20+）
- npm（或兼容的 pnpm / yarn）
- 主要库：React 18 · TypeScript 5.6 · Vite 6 · Tailwind CSS 3.4

---

## 安装步骤

```bash
git clone https://github.com/<your-org>/Aurum-Radar.git
cd Aurum-Radar
```

### 1. 后端

```bash
cd backend

# 推荐：使用 uv 按 uv.lock 同步依赖
uv sync
source .venv/bin/activate

# 或：传统方式
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

配置环境变量：

```bash
cp .env.example .env
```

至少填写以下字段：

| 字段 | 说明 |
|------|------|
| `DATABASE_URL` | `postgresql+psycopg2://USER:PASSWORD@HOST:5432/aurum_radar` |
| `DASHSCOPE_API_KEY` | 百炼 DashScope Key |
| `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` | 阿里云 OSS 密钥（可选） |
| `DATA_PROBE_OUTPUT_DIR` | data_probe 输出目录，默认 `../data_probe/output/normalized` |

> ⚠️ 务必在项目 `.venv` 内运行，避免使用 Homebrew/系统 Python，否则会缺少 `stevedore`、`apscheduler` 等依赖。

应用数据库迁移（如需）：

```bash
alembic upgrade head
```

### 2. 前端

```bash
cd frontend
npm install
```

前端开发模式下，`/api/*` 请求会通过 `vite.config.ts` 代理到 `http://localhost:8000`。

---

## 使用方法

### 启动后端 API

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health（返回 `{"status":"ok","db":"connected"}`）

### 启动前端

```bash
cd frontend
npm run dev        # http://localhost:5173
npm run build      # 生产构建（tsc -b && vite build）
npm run preview    # 本地预览生产产物
```

### 运行流水线

```bash
# 摄取 data_probe 爬取数据到 RDS
python -m scripts.ingest_crawl_data                     # 摄取今天
python -m scripts.ingest_crawl_data --date 2026-05-23
python -m scripts.ingest_crawl_data --all
python -m scripts.ingest_crawl_data --dry-run

# 基于 RDS 已有 raw_documents 跑 Stage 3-6 + Council + Evaluation
python -m scripts.run_council
#   --market Singapore        仅跑指定市场
#   --since 30d               最近 N 天
#   --until 2026-05-22        截止日期
#   --limit 50                文档数量上限
#   --no-evaluation           跳过评估
```

### 通过 API 手动触发流水线

```bash
curl -X POST http://localhost:8000/api/jobs/run \
  -H "Content-Type: application/json" \
  -d '{"markets": ["Singapore"], "stages": ["ingest", "extract"]}'
```

`SCHEDULER_ENABLED` 本地默认 `false`，定时任务不会自动触发；需要时使用上述 API 或脚本入口手动触发。

---

## 常见问题

| 报错 | 处理 |
|------|------|
| `ModuleNotFoundError: stevedore` / `apscheduler` / `oss2` | 未激活 `.venv`，执行 `source backend/.venv/bin/activate` 或 `uv sync` |
| `/api/health` 返回 `db: disconnected` | 检查 `.env` 的 `DATABASE_URL` 与 RDS 白名单 |
| DashScope 启动报错 | 确认 `DASHSCOPE_API_KEY` 已正确配置 |
| 前端接口 404 / 跨域 | 确认后端已在 8000 端口运行，`vite.config.ts` 代理生效 |

---

## 子模块文档

- 后端详细说明：[backend/README.md](backend/README.md)
- 前端详细说明：[frontend/README.md](frontend/README.md)
- 架构与接口契约：[backend/architecture.md](backend/architecture.md)

