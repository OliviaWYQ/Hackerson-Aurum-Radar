# Aurum Radar 后端架构设计文档


## 1. 概述

**Aurum Radar** 是一个面向珠宝海外市场的战略情报 Agent：定时抓取全球公开信息，抽取为结构化市场事件，判断机会与风险，生成每日战略简报与部门行动建议，并通过看板呈现。

后端职责：

```text
采集公开信息 → 清洗去重 → 抽取结构化事件 → 评分研判
→ 生成每日简报 → 生成部门行动建议 → 通过 JSON API 提供给前端
```

MVP 范围：

```text
市场：Singapore / Thailand / Japan
数据源：新闻搜索 / RSS、竞品官网、平台公告、法规公告、金价汇率、高端商场活动
不接入企业内部数据，只用公开信息
```

---

## 2. 设计原则

| 原则 | 含义 |
|---|---|
| 简洁高效 | 单体 FastAPI 应用 + 单库 PostgreSQL + 对象存储 OSS。MVP 不引入 Redis、消息队列、微服务、OpenSearch |
| 前后端分离 | 后端只产出 JSON API，前端是纯静态资源；Nginx 单入口同源，免 CORS |
| 云资源一致性 | 本地与云端**同一套** RDS / OSS / DashScope，只差 `.env` 与运行位置 |
| 来源可追溯 | 每个事件关联 `raw_document` 与 `source_url`，结论可回溯到原文 |
| 不过度工程化 | mock / seed 数据仅用于初始化、无网络 fallback、测试；**不作为主链路** |
| Agent 流水线化 | 采集→简报拆成独立、幂等、可单独运行的阶段，由调度器串联 |

**严禁**：SQLite、本地文件存储、MockLLM 作为主运行分支；不在代码里判断"本地/云端"或写死内外网地址（一律由 `.env` 决定）。

---

## 3. 技术栈

```text
语言运行时   Python 3.11+
Web 框架     FastAPI（ASGI）+ Uvicorn
ORM / 迁移   SQLAlchemy 2.x + Alembic
配置         pydantic-settings
调度         APScheduler
HTTP / 抓取  httpx、BeautifulSoup4
LLM          openai SDK（DashScope OpenAI 兼容接口）
对象存储     oss2
数据库驱动   psycopg2-binary
日志         loguru
部署         Docker + Docker Compose + Nginx
```

云服务：阿里云 RDS PostgreSQL、阿里云 OSS、百炼 DashScope。具体已开通资源见 **附录 A**。

---

## 4. 系统架构

### 4.1 部署拓扑

```text
                       浏览器（React SPA 看板）
                              │  HTTP，/api/* 每 30–60s 轮询
                              ▼
        ┌──────────────── ECS · Nginx :80 ────────────────┐
        │   /        → 前端静态资源（HTML / JSX / CSS）     │
        │   /api/*   → 反向代理到 Uvicorn :8000             │
        └───────────────────────┬──────────────────────────┘
                                 ▼
          ┌─────────── 后端进程（同一镜像，三种角色）──────────┐
          │  web        Uvicorn + FastAPI，提供 REST API       │
          │  scheduler  APScheduler，按 cron 触发 Agent 流水线  │
          │  worker     执行 Agent 各阶段（采集/抽取/简报…）    │
          └───────┬───────────────┬───────────────┬──────────┘
                  ▼               ▼               ▼
        RDS PostgreSQL        阿里云 OSS       百炼 DashScope
        （结构化数据）        （原文/快照/导出）（LLM 抽取/简报/行动）
```

### 4.2 组件职责

| 组件 | 职责 |
|---|---|
| Nginx | 单入口；托管前端静态文件；`/api/*` 反代到后端；可选 SSE 透传 |
| FastAPI (web) | 暴露 JSON API，只读 RDS 返回数据；手动触发任务入口 |
| Scheduler | 按计划触发 Agent 流水线；MVP 用 APScheduler，受 `SCHEDULER_ENABLED` 控制 |
| Worker | 实际执行 Agent 各阶段；与 web 共用代码与镜像 |
| RDS PostgreSQL | 唯一业务库：原始文档元数据、事件、研判、简报、行动、任务记录 |
| OSS | 大文件：网页快照、PDF、截图、导出文件。Bucket 私有，前端经签名 URL 访问 |
| DashScope | 事件抽取、简报生成、行动建议生成、向量化（全部 API 调用，本机不部署模型） |

> MVP 阶段 web / scheduler / worker 可以是同一容器内的不同启动命令；数据量上来后再拆。

---

## 5. 环境设计（一致性）

`local / dev / prod` 只代表**运行位置与配置差异**，不代表技术栈差异。

| 环境 | 运行位置 | RDS 地址 | OSS Endpoint | 调度 |
|---|---|---|---|---|
| local | 本地电脑 | RDS 公网地址 | OSS 公网 Endpoint | `SCHEDULER_ENABLED=false`，手动触发 |
| dev | ECS 测试 | RDS 内网地址 | OSS 内网 Endpoint | 可开启 |
| prod | ECS 正式 | RDS 内网地址 | OSS 内网 Endpoint | `SCHEDULER_ENABLED=true` |

要求：

```text
本地开发 = 本地跑代码 + 连云端 RDS / OSS / DashScope
云端部署 = ECS 跑代码 + 连同一套 RDS / OSS / DashScope
切换环境只改 .env，永不改代码
```

---

## 6. 前后端分离 API 设计（核心）

### 6.1 设计约定

```text
前缀        所有接口以 /api 开头（API_PREFIX）
风格        REST，资源化，标准 HTTP 状态码
数据格式    请求 / 响应均为 JSON（UTF-8）
分页        列表接口支持 ?page=1&size=20，返回 { items, total, page, size }
筛选        通过 query 参数（market / source_category / env_factor / priority / department …）
错误        非 2xx 返回 { "error": { "code": "...", "message": "..." } }
时间        ISO 8601 字符串（UTC）
鉴权        MVP 不做鉴权（内部 Demo）；预留 Header 注入位
```

前端与后端唯一耦合点就是这份契约。前端不含任何业务数据，挂载时 `fetch('/api/...')` 取数。

### 6.2 接口清单（映射到 4 个前端页面）

| 接口 | 方法 | 对应页面 / 用途 |
|---|---|---|
| `/api/health` | GET | 健康检查（DB / OSS / DashScope 连通性） |
| `/api/dashboard/summary` | GET | 概览页：核心指标卡片（重点事件数、高风险数、高机会市场、待处理行动） |
| `/api/overview` | GET | 概览页：世界地图各国机会 / 风险节点 |
| `/api/markets/{market}` | GET | 概览页：选中国家的国家级摘要（综合指数、亮点） |
| `/api/markets/{market}/districts` | GET | 地图洞察页：国家内部商圈节点 |
| `/api/markets/{market}/council` | GET | 战略情报智囊团决策报告（多专家分析 + 上中下三策，见 §17） |
| `/api/districts/{district_id}` | GET | 地图洞察页：商圈详情与建议动作 |
| `/api/events` | GET | 情报中心：事件列表，支持 `market / source_category / env_factor / signal_direction / priority / intensity` 筛选 + 分页 |
| `/api/events/{event_id}` | GET | 情报中心：事件详情 + 来源引用 |
| `/api/brief/latest` | GET | 每日战略简报（最新一期） |
| `/api/briefs/{brief_date}` | GET | 指定日期简报 |
| `/api/actions` | GET | 行动建议看板，支持 `department / priority / market` 筛选 |
| `/api/actions/{action_id}` | GET | 行动清单详情 |
| `/api/jobs/status` | GET | 定时任务 / 流水线状态（前端轮询用） |
| `/api/jobs/run` | POST | 手动触发 Agent 流水线（MVP 的「手动触发抓取」按钮） |

### 6.3 关键响应结构（示例）

`GET /api/overview`：

```json
{
  "as_of": "2026-05-21T08:00:00Z",
  "markets": [
    { "market": "Singapore", "region": "Southeast Asia", "tier": 1,
      "opportunity_score": 82, "risk_score": 35, "headline": "高端礼赠需求增强" },
    { "market": "Thailand", "region": "Southeast Asia", "tier": 1,
      "opportunity_score": 76, "risk_score": 41, "headline": "旅游零售恢复" }
  ]
}
```

`GET /api/events?market=Thailand&page=1&size=20`：

```json
{
  "items": [
    { "event_id": 101, "market": "Thailand",
      "source_category": "channel",
      "env_factors": [
        { "factor_id": "F7", "factor_name": "channel_power_shift", "is_primary": true,
          "evidence": "Siam Paragon 周末客流同比 +28%，高端珠宝专区延时营业" }
      ],
      "conduction_chain": { "chain_id": "C", "chain_name": "文化-偏好-结构链",
        "node_position": "渠道格局", "lag_estimate": "短期(周级)" },
      "signal_direction": "positive", "intensity": 3,
      "impact_scope": ["brand", "retailer", "category_gold", "market_TH"],
      "title": "Siam Paragon 高端珠宝活动热度上升",
      "key_claim": "Siam Paragon 周末客流同比 +28%，珠宝专柜参与延时营业活动",
      "downstream_implications": ["华人游客婚庆采购转移到曼谷高端商场", "本地零售商对节假日促销响应加快"],
      "priority": "P1", "confidence": 0.82,
      "opportunity_score": 78, "risk_score": 40,
      "source_url": "https://...", "published_at": "2026-05-20T09:30:00Z" }
  ],
  "total": 28, "page": 1, "size": 20
}
```

`POST /api/jobs/run`：

```json
// 请求
{ "markets": ["Singapore", "Thailand", "Japan"],
  "source_types": ["news", "competitor", "regulation"],
  "stages": ["ingest", "extract", "score", "forecast", "brief", "action"] }
// 响应
{ "job_run_id": 55, "status": "running", "started_at": "2026-05-21T10:00:00Z" }
```

### 6.4 实时数据策略

数据更新节奏：爬虫每 6 小时、每日简报 08:00 —— 本质不是秒级流。「实时」指**前端始终展示库内最新状态并自动刷新**。

```text
MVP：前端轮询。挂载拉一次全量，之后每 30–60s 轮询，刷新地图 / 事件流 / 行动看板。
     点「手动触发」后轮询 GET /api/jobs/status 直到完成再刷新。
增强：任务进度条 / 新情报弹窗 → 对该处单独加 SSE（FastAPI/ASGI 原生支持，Nginx 关缓冲透传）。
     双向通信场景本项目没有，不用 WebSocket。
```

---

## 7. Agent 工作流

### 7.1 流水线总览

Agent 是一条**分阶段、幂等、可单独运行**的流水线，由调度器按 cron 串联，也可经 `POST /api/jobs/run` 手动触发任意子集。

```text
[1 采集] → [2 清洗去重] → [3 抽取] → [4 评分] → [5 研判] → [6 简报] → [7 行动·智囊团 §17]
   每个阶段都向 job_runs 写入运行记录（开始/结束/影响行数/错误）
```

### 7.2 各阶段定义

| 阶段 | 输入 | 处理 | 输出 → 落库 |
|---|---|---|---|
| 1 采集 Ingest | 市场、关键词、Provider 配置 | 各 Provider 抓取公开信息，统一为 `RawDocumentCreate` | 内存对象列表 |
| 2 清洗去重 Clean | `RawDocumentCreate[]` | 正文清洗、语言识别、`content_hash` 去重、关键词相关性初筛 | `raw_documents` + 原文存 OSS（`oss_path`） |
| 3 抽取 Extract | 新增 `raw_documents` | 规则预分类候选 `source_category`（可被 LLM 覆盖）→ DashScope **双坐标轴抽取**：信息来源轴 + **底层环境影响因子**（F1–F7）+ 传导链路 + 信号方向 / 烈度 / 影响范围 / 实体 / 关键事实 / 下游推断 → JSON Schema 校验 | `intelligence_events` |
| 4 评分 Score | `intelligence_events` | **以 Stage 3 输出为输入的规则化打分**：`intensity × confidence` → 基础分；`signal_direction × impact_scope` → 机会/风险分；`conduction_chain.lag_estimate` → 时效权重；`intensity ≥ 4` 自动入预警；LLM 仅在歧义时辅助裁定 | 更新 `intelligence_events` 的 `opportunity_score / risk_score / priority` |
| 5 研判 Forecast | 按市场聚合的当日事件 | 按 `env_factors[primary] + conduction_chain` 聚类 → `entities` 汇总实体关系 → DashScope 生成国家级综合研判（机会 / 风险 / 需关注） | `market_snapshots` |
| 6 简报 Brief | 当日事件 + 市场研判 | 以 `key_claim + downstream_implications` 为摘要素材 → DashScope 生成每日战略简报（执行摘要 + 跨市场对比 + 重点事件） | `daily_briefs` |
| 7 行动 Action | 当日事件 + 市场研判 | 战略情报智囊团（§17）：情报适配为 intelligence_batch（透传 env_factors / conduction_chain / signal_direction / impact_scope 等完整作用机制）→ 5 位专家并行分析 → 总参谋综合 → 决策报告（上中下三策）→ 派生行动 | `council_reports` + `action_items` |

### 7.3 抽取阶段细节（双坐标轴 + 底层影响因子）

> 完整 prompt / 字段规则 / 边界情况见 [backend/preclassify_extract.md](preclassify_extract.md)。本节只描述与整体架构耦合的部分。

**设计动机**：把"信息从哪里来"（渠道/场景）与"信息怎么作用于市场"（作用机制）解耦。LLM 决策（Stage 5/6/7）不再只看渠道分类，而是基于底层作用机制聚类与推理。简单的来源标签太粗：一条"金价上涨"和一条"婚庆下滑"都可能被打成 `pricing` 或 `social`，但前者走价格传导链，后者走文化偏好链，对品牌的可执行含义完全不同。

```text
规则预分类 + 双坐标轴 LLM 抽取：
raw_document → keyword 初筛 → 候选 source_category（人工初判，pre_label，LLM 可覆盖）
            → 调 DashScope 抽取（来源轴 + 环境因子轴 + 传导链路 + 实体 + 含义）
            → 校验 JSON schema → 入库 intelligence_events
```

**第一坐标轴 · source_category**（信息从哪个渠道/场景产生）：

```text
competition    竞争情报：对手动作、市占变化、并购、人事
product        产品动态：新品、技术、定价、SKU 调整
social_media   社媒舆情：消费者声量、KOL、话题热度、情绪
regulation     法规政策：监管文件、标准、税务、合规要求
channel        渠道变化：零售格局、电商规则、物流、终端
macro          宏观数据：金价、汇率、利率、GDP、PMI
supply_chain   供应链：矿产、加工、物流、产能
```

**第二坐标轴 · env_factors**（底层环境影响因子，1–3 个，按主次排序；`is_primary: true` 只能一个）：

```text
F1 supply_constraint     供给约束    上游 → 原料成本 → 品牌毛利
F2 structure_disruption  结构重塑    横向 → 市场份额再分配 → 竞争壁垒重建
F3 demand_shift          需求迁移    需求侧 → 品类结构 → 定价权归属
F4 regulatory_friction   制度摩擦    外部制度 → 合规成本 → 供应链重组
F5 price_conduction      价格传导    宏观变量 → 原料/进出口成本 → 终端定价
F6 narrative_pressure    叙事压力    认知层 → 溢价能力 → 消费者信任
F7 channel_power_shift   渠道博弈    中间层结构 → 利润分配 → 品牌触达效率
```

**传导链路 · conduction_chain**（A–E，无法归类时为 null，不强行套）：

```text
A 地缘-供给-成本链   地缘事件 → 产区/制裁 → 原料供给 → 品牌成本 → 终端价格
B 货币-消费-需求链   利率/汇率 → 消费信心 → 可选消费 → 品类需求 → 品牌销量
C 文化-偏好-结构链   代际迁移 → 审美偏好 → 品类重构 → 渠道格局 → 份额再分配
D 制度-合规-成本链   政策发布 → 合规要求 → 运营成本 → 产品定价 → 竞争格局
E 技术-替代-颠覆链   Lab 技术 → 成本下降 → 替代加速 → 天然材质溢价压缩 → 份额转移
```

**信号属性**（每条事件必填，缺失填 null 而非省略）：

```text
signal_direction  positive / negative / mixed / neutral   对珠宝终端市场的方向
intensity         1–5                                     1 微弱 → 5 可能引发结构变化
impact_scope      raw_material / brand / retailer / consumer
                  / category_natdiamond / category_labdiamond
                  / category_gold / category_gemstone
                  / market_CN / market_US / market_IN / market_GLOBAL …
entities          { brands, materials, markets, regulators, locations }
key_claim         纯事实陈述（≤50 字，不含"可能/或许"等不确定词）
downstream_implications  1–3 条推断，按概率从高到低
confidence        0.0–1.0 浮点（替代旧 high/medium/low 三档）
ambiguity_flags   multi_factor_conflict / scope_unclear / timing_uncertain
                  / source_unverified / entity_ambiguous
priority          P0 / P1 / P2（由 Stage 4 评分阶段产出，不在抽取阶段产生）
```

**与下游约定**（与 [preclassify_extract.md](preclassify_extract.md) 末尾接口约定一致）：

```text
Stage 4 评分      intensity × confidence → 基础分
                  signal_direction × impact_scope → 机会/风险分
                  conduction_chain.lag_estimate → 时效权重
Stage 5 研判      env_factors[primary] + conduction_chain → 聚类分析
                  entities → 实体关系图更新
Stage 6 简报      key_claim + downstream_implications → 摘要素材
                  intensity ≥ 4 → 进入预警队列
Stage 7 智囊团    完整 JSON + signal_direction + impact_scope → 角色化建议
```

LLM 输出约束：严格 JSON（`response_format=json_object`，不带 markdown 包裹）、`temperature 0.2–0.4`、失败重试、失败记日志、不吞异常；置信度规则与歧义标记见 [preclassify_extract.md](preclassify_extract.md)。

### 7.4 触发方式与可追溯性

```text
定时   APScheduler，新闻每 6h、简报每日 08:00（cron 见 §13）
手动   POST /api/jobs/run，可指定 markets / source_types / stages
记录   每个阶段每次运行写 job_runs：status / params / started_at / finished_at
       / rows_affected / error_message
追溯   event → raw_document → source_url / oss_path；brief / action → event_id
```

---

## 8. 数据模型

PostgreSQL，SQLAlchemy 2.x 定义，Alembic 迁移。核心 7 张流水线表 + 1 张种子表。

```text
raw_documents       原始文档元数据（原文存 OSS）
intelligence_events 结构化市场事件（Agent 核心产物）
market_snapshots    国家级每日研判（机会/风险分 + 综合判断）
daily_briefs        每日战略简报
council_reports     智囊团完整决策报告（上中下三策 + 部门行动源数据）
action_items        部门行动建议（由智囊团决策报告派生，见 §17）
job_runs            Agent 各阶段运行记录
districts            商圈种子数据（地图洞察页用，不参与流水线）
```

**raw_documents**

```text
id, source_type, source_name, market, region, title, summary, url,
published_at, fetched_at, language, raw_content, clean_content,
content_hash(唯一,去重), oss_path, credibility_level(S/A/B/C),
created_at, updated_at
```

**intelligence_events**

```text
-- 基础字段
id, market, region, title, summary, business_impact,
source_url, raw_document_id(FK), created_at, updated_at

-- Stage 3 抽取产出：第一坐标轴（信息来源）
source_category    competition / product / social_media / regulation
                   / channel / macro / supply_chain

-- Stage 3 抽取产出：第二坐标轴（底层环境影响因子 + 传导链路）
env_factors        jsonb  [{factor_id, factor_name, is_primary, evidence}]
conduction_chain   jsonb  {chain_id, chain_name, node_position, lag_estimate}

-- Stage 3 抽取产出：信号属性
signal_direction   positive / negative / mixed / neutral
intensity          smallint 1-5
impact_scope       jsonb  品类/角色/市场标签数组
entities           jsonb  {brands, materials, markets, regulators, locations}
key_claim          text   纯事实陈述 ≤50 字
downstream_implications  jsonb  1-3 条推断
ambiguity_flags    jsonb  歧义标记数组
confidence         numeric(3,2)  0.00-1.00（替代旧 high/medium/low）

-- Stage 4 评分产出
priority           P0 / P1 / P2
opportunity_score  0-100
risk_score         0-100
```

> 旧 `event_type / impact_type` 字段被替换：`event_type → source_category`（来源轴），`impact_type` 的语义拆解到 `signal_direction`（方向）与 `impact_scope`（影响范围）。confidence 从枚举变为浮点。

**market_snapshots**

```text
id, market, region, snapshot_date, opportunity_score, risk_score,
overall_judgement, key_opportunities(jsonb), key_risks(jsonb),
watch_items(jsonb), event_count, created_at
```

**daily_briefs**

```text
id, brief_date(唯一), markets(jsonb), executive_summary,
opportunities(jsonb), risks(jsonb), watch_items(jsonb),
recommended_actions(jsonb), source_count, event_count,
created_at, updated_at
```

**council_reports**

```text
id, market, report_date, report(jsonb),
extra(jsonb), created_at
```

**action_items**

```text
id, market, department, priority(P0/P1/P2), action_title, action_detail,
reason, deadline, expected_output, success_metric,
status(pending/in_progress/done/ignored), event_id(FK),
created_at, updated_at
```

**job_runs**

```text
id, job_name, stage, trigger_type(scheduled/manual), status(running/success/failed),
params_json, started_at, finished_at, rows_affected, error_message, created_at
```

**districts**（种子数据：乌节路、滨海湾…，含门店数量、商圈画像）

```text
id, market, name, store_count, heat_level, profile(jsonb), created_at
```

关系：`intelligence_events.raw_document_id → raw_documents.id`；`action_items.event_id → intelligence_events.id`。
索引：`raw_documents.content_hash` 唯一；`intelligence_events(market, source_category, priority, created_at)` 主筛选索引；`intelligence_events` 在 `env_factors / impact_scope` 上建 **GIN** 索引以支持按因子/范围查询；`daily_briefs.brief_date` 唯一。
扩展：需要语义检索时 `CREATE EXTENSION vector;`，给文本表加 `embedding vector` 列（MVP 可不做）。

---

## 9. 代码结构与模块

```text
backend/
├── app/
│   ├── main.py                  # FastAPI 入口，挂载路由、中间件、生命周期
│   ├── api/                     # 路由层（仅做请求/响应，不写业务）
│   │   ├── routes_health.py
│   │   ├── routes_dashboard.py  # overview / summary / markets / districts
│   │   ├── routes_events.py
│   │   ├── routes_brief.py
│   │   ├── routes_actions.py
│   │   └── routes_jobs.py
│   ├── core/
│   │   ├── config.py            # pydantic-settings，读 .env
│   │   ├── logging.py           # loguru
│   │   └── errors.py            # 统一异常 → { error: {...} }
│   ├── database/
│   │   ├── session.py           # Engine / Session
│   │   ├── base.py
│   │   └── init_db.py           # 建表 / 灌种子数据
│   ├── models/                  # SQLAlchemy 模型（§8 七张表）
│   ├── schemas/                 # Pydantic 请求/响应模型
│   ├── services/                # 业务层 = Agent 各阶段
│   │   ├── ingestion/           # 阶段1-2：Provider + 清洗去重
│   │   ├── extraction/          # 阶段3：规则预分类 + LLM 抽取
│   │   ├── scoring/             # 阶段4：评分
│   │   ├── forecast/            # 阶段5：市场研判
│   │   ├── brief/               # 阶段6：简报生成
│   │   ├── council/             # 阶段7「行动」：战略情报智囊团（见 §17）
│   │   ├── storage/             # OSSStorageProvider
│   │   └── llm/                 # DashScopeLLMProvider
│   ├── scheduler/
│   │   ├── scheduler.py         # APScheduler 实例与启停
│   │   └── jobs.py              # job 定义，串联 services
│   └── utils/
├── alembic/                     # 迁移脚本
├── scripts/                     # 初始化 / 灌数据 / 手动跑流水线
├── tests/
├── docker/
│   ├── nginx.conf
│   └── gunicorn_conf.py
├── Dockerfile
├── docker-compose.yml           # 云端：nginx + backend + scheduler + worker
├── docker-compose.local.yml     # 本地：仅 backend
├── requirements.txt
├── .env.example
└── README.md
```

分层原则：`api` 只做协议转换 → `services` 写业务 → `models/database` 管持久化。`services` 各子目录一一对应 Agent 阶段，可独立调用与测试。

---

## 10. 数据采集 Provider 设计

统一 Provider 模式，所有 Provider 输出统一的 `RawDocumentCreate`，互不耦合，可逐个增减。

| Provider | 实现 | 监控对象 |
|---|---|---|
| NewsProvider | NewsAPIProvider / SerpAPIProvider / RSSProvider | 新闻、市场变化、竞品动态、消费趋势 |
| CompetitorProvider | SimpleWebPageProvider（+ Firecrawl placeholder） | Cartier、Tiffany、Van Cleef & Arpels、Pandora、周生生、六福 |
| PlatformPolicyProvider | 公告页抓取 | TikTok Shop / Shopee / Lazada 卖家中心公告（只抓公告，不抓商品） |
| RegulationProvider | 公告页抓取 | Singapore Customs、Enterprise Singapore、Japan METI、Thailand FDA |
| MarketDataProvider | API | GoldAPI（金价）、ExchangeRate API（汇率） |
| MallEventProvider | 活动页抓取 | Marina Bay Sands、Siam Paragon、ION Orchard |

约定：Provider 只负责"取回原始内容 + 基本元数据"，清洗、去重、相关性判断统一在阶段 2 处理。无法抓取的源（如社媒）MVP 用 seed 数据，但仅作展示补充，不进主链路。

---

## 11. 存储设计

**结构化数据进 RDS，大文件 / 原文 / 网页快照进 OSS。**

`OSSStorageProvider` 接口：

```python
class OSSStorageProvider:
    def save_text(self, path: str, content: str) -> str: ...      # 返回 oss_path
    def save_bytes(self, path: str, content: bytes) -> str: ...
    def get_signed_url(self, path: str, expires: int = 3600) -> str: ...
```

路径规则：

```text
raw_html/{market}/{yyyy-mm-dd}/{hash}.html
pdf/{market}/{yyyy-mm-dd}/{hash}.pdf
screenshots/{market}/{yyyy-mm-dd}/{hash}.png
exports/{yyyy-mm-dd}/{filename}
```

要求：Bucket 私有；前端访问文件一律由后端 `get_signed_url` 生成临时链接；不返回永久公开链接。Endpoint 由 `.env` 决定（本地公网 / 云端内网）。

---

## 12. LLM 集成（DashScope）

走百炼 DashScope 的 **OpenAI 兼容接口**（`openai` SDK，只改 `base_url`）。

`DashScopeLLMProvider` 接口：

```python
class DashScopeLLMProvider:
    def extract_event(self, document) -> dict: ...        # 阶段3
    def forecast_market(self, market, events) -> dict: ...# 阶段5
    def generate_brief(self, events, snapshots) -> dict: ...# 阶段6
    def chat_json(self, system, user) -> dict: ...        # 阶段7 智囊团各专家与总参谋复用
```

模型分级（成本控制）：

```text
规则预分类 / 轻量标签   qwen-flash
事件抽取 / 研判 / 简报 / 行动   qwen-plus
复杂推理（可选）        qwen-max
向量化（可选）          text-embedding-v3
```

事件抽取输出契约（JSON Schema 校验，详细字段规则见 [preclassify_extract.md](preclassify_extract.md)）：

```json
{
  "source_category": "competition",
  "env_factors": [
    { "factor_id": "F2", "factor_name": "structure_disruption",
      "is_primary": true, "evidence": "三大品牌停购天然钻，不可逆模式切换" },
    { "factor_id": "F6", "factor_name": "narrative_pressure",
      "is_primary": false, "evidence": "CEO 强调 ESG 风险" }
  ],
  "conduction_chain": {
    "chain_id": "E", "chain_name": "技术-替代-颠覆链",
    "node_position": "天然材质溢价压缩", "lag_estimate": "中期(月级)"
  },
  "signal_direction": "mixed", "intensity": 5,
  "impact_scope": ["brand", "category_natdiamond", "category_labdiamond", "market_GLOBAL"],
  "entities": {
    "brands": ["Signet Jewelers"], "materials": ["天然钻石", "Lab Diamond"],
    "markets": ["US", "GLOBAL"], "regulators": [], "locations": []
  },
  "key_claim": "Signet 旗下三品牌 2026 年底前停购天然钻，全面切换 Lab Diamond",
  "downstream_implications": [
    "全球天然钻批发需求进一步萎缩",
    "Lab Diamond 在美国婚戒市场渗透率加速突破 50%"
  ],
  "confidence": 0.95,
  "ambiguity_flags": []
}
```

`market / region / title / summary` 由 adapter 从 `raw_documents` 元数据或抽取上下文补齐，不强制 LLM 重复输出。`priority / opportunity_score / risk_score` 由 Stage 4 评分阶段产出，不在抽取契约内。

要求：输出尽量 JSON、`temperature 0.2–0.4`、失败重试 + 退避、记录 token 与错误日志、不吞异常；注意 QPS / 每分钟 token 配额，批处理控制并发。多模态（分析门店 / 社媒图片）按需用原生 `dashscope` SDK，图片传 OSS 签名 URL。

---

## 13. 调度设计

APScheduler，受 `SCHEDULER_ENABLED` 控制（local 默认关、prod 默认开）。

| Job | 频率（cron） | 说明 |
|---|---|---|
| `fetch_public_sources_job` | 每 6 小时 | 阶段 1–2：采集 + 清洗去重 |
| `extract_events_job` | 每 6 小时（采集后） | 阶段 3–4：抽取 + 评分 |
| `daily_pipeline_job` | 每日 07:00 | 阶段 5–7：研判 + 简报 + 行动，08:00 前出当日简报 |

要求：每个 job 每个阶段写 `job_runs`（成功记 `rows_affected`，失败记 `error_message`）；所有 job 支持经 `POST /api/jobs/run` 手动触发；阶段幂等，可重跑。MVP 不引入 Celery / 消息队列，APScheduler + `job_runs` 表足够。

---

## 14. 前端整合方案

### 14.1 前端现状

`frontend/Aurum-Radar/` 是纯静态 React SPA：React 18 + Babel Standalone 从 CDN 加载，浏览器端实时编译 `.jsx`，无构建步骤、无 Node 运行时。页面文件：`overview.jsx / map-insight.jsx / intel.jsx / actions.jsx / shell.jsx / app.jsx`，入口 `Aurum Radar.html`。当前数据写死在 `.jsx` 里（mock）。

### 14.2 整合步骤（后续把静态页面整合出来）

```text
1. 入口 Aurum Radar.html 重命名为 index.html（带空格的文件名在 Nginx/URL 里别扭）
2. frontend 目录纳入部署：Nginx 挂载为静态根目录（见 §15 nginx.conf）
3. 各页面把写死的 mock 数据替换为挂载时 fetch('/api/...')，按 §6.2 契约取数
4. 顶部筛选器（时间/地区/品类）作为 query 参数透传给各接口
5. 同源部署（Nginx 单入口），不需要 CORS
6. 文件类资源（PDF/截图）用后端返回的签名 URL 展示
```

### 14.3 页面 → 接口映射

| 前端页面 | 调用接口 |
|---|---|
| `overview.jsx` 概览 | `GET /api/dashboard/summary`、`GET /api/overview`、`GET /api/markets/{market}`、`GET /api/brief/latest` |
| `map-insight.jsx` 地图洞察 | `GET /api/markets/{market}/districts`、`GET /api/districts/{id}` |
| `intel.jsx` 情报中心 | `GET /api/events`（带筛选 + 分页）、`GET /api/events/{id}` |
| `actions.jsx` 行动建议 | `GET /api/actions`（按部门筛选）、`GET /api/actions/{id}` |
| `shell.jsx` 顶栏/触发 | `GET /api/jobs/status`、`POST /api/jobs/run` |

> 可选演进：MVP 后若需要更强工程化，可把 build-less SPA 迁到 Vite 构建产物，部署方式不变（仍是 Nginx 托管静态文件 + 反代）。MVP 不要求。

---

## 15. 部署

### 15.1 Nginx（单入口）

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;       # 前端静态文件
    index index.html;

    location /api/ {                  # 反代到 Uvicorn(FastAPI)
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /api/stream {            # SSE（如启用）：关闭缓冲
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }
    location / { try_files $uri $uri/ /index.html; }  # SPA 兜底
}
```

### 15.2 Docker Compose

```text
docker-compose.local.yml   只起 backend（连云端 RDS 公网 / OSS 公网）
docker-compose.yml         起 nginx + backend + scheduler + worker（连内网）
```

```yaml
# docker-compose.yml（云端）
services:
  nginx:
    image: nginx
    ports: ["80:80"]
    volumes:
      - ./frontend:/usr/share/nginx/html:ro
      - ./docker/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on: [backend]
  backend:
    image: aurum-radar-backend
    command: gunicorn -k uvicorn.workers.UvicornWorker app.main:app -b 0.0.0.0:8000
    env_file: [.env]
  scheduler:
    image: aurum-radar-backend
    command: python -m app.scheduler.scheduler
    env_file: [.env]
  worker:
    image: aurum-radar-backend
    command: python -m app.scheduler.jobs        # 或 worker 入口
    env_file: [.env]
```

后端三个服务共用同一镜像，靠 `command` 区分角色。FastAPI 用 Uvicorn worker；生产由 Gunicorn 管理。
本地开发：本地只跑 backend，直连云端 RDS 公网地址 + OSS 公网 Endpoint + DashScope；`SCHEDULER_ENABLED=false`，靠 `POST /api/jobs/run` 手动触发。

---

## 16. 实施优先级与验收标准

### 16.1 优先级

```text
P0  配置系统、数据库连接、模型、API 骨架，本地可连云资源跑通
P1  OSSStorageProvider、DashScopeLLMProvider、Provider 框架
P2  Agent 流水线：采集 / 抽取 / 评分 / 研判 / 简报 / 行动
P3  APScheduler、job_runs、Docker Compose、Nginx、前端联调
P4  真实数据源增强、向量检索、SSE
```

### 16.2 验收标准

```text
1. 本地运行 FastAPI 可连接阿里云 RDS PostgreSQL
2. 本地可把 raw_html 写入 OSS，并能生成签名 URL
3. 本地可调用 DashScope 抽取结构化事件
4. POST /api/jobs/run 可手动触发 Agent 流水线
5. GET /api/events / brief/latest / actions / overview 返回真实库内数据
6. 前端 4 个页面能从 /api/* 取数渲染（不再依赖 mock）
7. ECS 部署只改 .env 不改代码，使用 RDS / OSS 内网地址
8. 每次流水线运行在 job_runs 留有可追溯记录
```

---

## 17. 战略情报智囊团（阶段 7「行动」算法升级）

> 本节整合 `skills/jewelry_intelligence_council/` 的智囊团设计，替代原「战略沙盘推演」。
> 智囊团 skill 文件随本次改造迁入 `backend/`，成为后端阶段 7 的正式实现依据。

### 17.1 定位

§7 主流水线的**阶段 7「行动」目前太泛**——当前实现是「高优先级事件 → LLM + 部门模板 → 部门任务」，产出常沦为「市场部做营销 / 法务部看合规」这类正确但无信息量的建议。原「战略沙盘推演」（6 步 + 兵法策略库 + 14 变量）虽更结构化，但实测结论质量仍不满意，故整体替换为智囊团方案。

战略情报智囊团是**对阶段 7 的算法层面升级**，不是独立 Agent、不另起流程：**在同一条主流水线里**，把「行动」这一步从「一个模型一次出建议」改成「**多位领域专家并行分析 → 总参谋综合裁定**」——

```text
旧 阶段7：高优先级事件 ──────────────────────────────► 部门行动（太泛）
新 阶段7：当日 intelligence_events
          → 适配为 intelligence_batch
          → 5 位专家并行分析（互不看彼此输出）
          → 总参谋交叉验证 / 裁定分歧 / 拆解部门
          → 决策报告（上中下三策 + 部门行动）
```

每条行动都能回溯「哪些情报 → 哪些专家判断 → 哪一策 → 所以这个动作」，从泛泛建议变成可解释、可比较、可验证的战略决策。

为什么是专家智囊团而不是单一 LLM 总结：

| 维度 | 单一 LLM 总结 | 专家智囊团 |
|---|---|---|
| 视角 | 一个 prompt 兼顾所有维度，互相稀释 | 每位专家只深挖一个维度 |
| 偏差 | 易被最显眼情报锚定 | 专家并行、互不看输出，减少锚定 |
| 分歧 | 内部矛盾被和稀泥抹平 | 分歧显式保留在 `expert_disagreements` |
| 证据 | 结论与证据易脱钩 | 每个判断强制绑定情报 `id` |
| 可执行 | 常停在「需关注 XX」 | 总参谋强制拆到部门 + 市场 + 品类 + 渠道 + 动作 |

设计原则（与 §2 一致）：

- **不让单个模型从情报直接跳到建议**——拆成「多专家并行 → 总参谋综合」两段，每段可单独检查、单独重跑。
- **强制证据绑定**：没有 `evidence_ids` 的判断不进任何输出；证据不足必须降置信度。
- **专家是结构化知识**，每位独立成 skill 文件，不散落在一个大 prompt 里（与 taxonomy 同思路）。
- 复用现有能力：`DashScopeLLM`（§12）、按市场聚合（§7 forecast）、JSONB 重表（§8）。不新增基础设施、不接新库、不另起独立项目。

### 17.2 在 Agent 流程中的位置

智囊团是**主流水线阶段 7 的内部算法**，随每日 `daily_pipeline_job`（§13）运行，不是旁路、不是独立 Agent：

```text
§7 主流水线：
[1采集][2清洗][3抽取][4评分][5研判][6简报] ─► [7 行动 = 战略情报智囊团]

阶段 7 内部（按市场逐个运行）：
intelligence_events + market_snapshot
  → 输入适配：聚合为 intelligence_batch（§17.5）
  → 5 位专家并行分析（§17.3）
  → 总参谋综合 → 决策报告（§17.6）
  → council_reports 保存完整报告
  → 从 department_actions 派生 action_items（落库）
```

术语对齐：智囊团 skill 文档里的「market signals / 清洗后的市场情报」即本项目的 `intelligence_events`，**不另设 signals 概念**；所有 `evidence_ids` 一律指向 `intelligence_events.id`（适配时转字符串，见 §17.5）。

### 17.3 智囊团组成

执行模式 `parallel_then_synthesis`：5 位分析专家并行，总参谋串行综合。

| 角色 | id | 职责 | 类型 |
|---|---|---|---|
| 产品营销战略专家 | product_marketing_strategist | 品类机会 / 金钻珍珠彩宝趋势 / 价格带 / 节日营销 / 社媒打法 / 新品方向 | 专家 |
| 竞品战略专家 | competitor_strategy_analyst | 国际与本地品牌动作 / 门店扩张 / 定价 / 联名代言 / 渠道变化 | 专家 |
| 消费者洞察专家 | consumer_insight_analyst | 婚庆 / 悦己 / 年轻客群 / 高净值 / 宗教文化偏好 / 社媒情绪 | 专家 |
| 风险合规专家 | risk_compliance_analyst | 金价波动 / 汇率 / 关税 / 广告合规 / 文化禁忌 / 地缘监管 | 专家 |
| **兵法谋士** | military_strategist | 融合孙子兵法 + 毛选 + 12 条策略库，匹配计策、给上中下三策思路（§17.4） | 专家 |
| 总参谋（首席战略官） | chief_strategy_officer | 综合 5 份专家输出 → 交叉验证 / 裁定分歧 / 拆解部门 → 决策报告 | 综合 |

```text
intelligence_batch
        ├──▶ 产品营销战略专家 ─┐
        ├──▶ 竞品战略专家     ─┤
        ├──▶ 消费者洞察专家   ─┼──▶ 总参谋 ──▶ 决策报告
        ├──▶ 风险合规专家     ─┤
        └──▶ 兵法谋士         ─┘
```

5 位专家不得看到彼此输出（避免锚定）；每位严格按自己的 skill 文件七段结构（Role / Scope / Input / Analysis Framework / Output Contract / Rules / Questions for Other Experts）工作。

### 17.4 兵法谋士与谋略知识库

兵法谋士（`military_strategist`）是智囊团里**唯一带外部知识库的专家**，融合三套**全部以 skill 文件形态**收录的谋略知识（「都用 skill」，不写成 Python 常量）：

| 知识源 | 形态 | 内容 | 在分析中的角色 |
|---|---|---|---|
| 孙子兵法 skill | `knowledge/sunzi-strategy/`（vendored） | `SKILL.md` + 13 条原则库 + 商业 / 组织 / 反模式等场景参考 | 通用谋略透镜：先胜后战 / 避实击虚 / 知彼知己 / 致人而不致于人 |
| 毛选 skill | `knowledge/maoxuan/`（vendored） | `SKILL.md` + 7 个心智模型 + 10 条决策启发式 | 通用谋略透镜：矛盾分析法 / 农村包围城市 / 纸老虎论 / 统一战线 |
| 12 条兵法策略库 | `knowledge/strategy_library.json` | 珠宝海外市场专属计策（原 `library.py` 迁移而来） | 行业落地 playbook：把通用谋略落到珠宝出海的具体打法 |

12 条策略（沿用谋士叙事，是 demo 差异化亮点）：

```text
轻骑探路  借港登岸  避实击虚  文化定锚  小金引玉  华圈破冰
先声后店  高地占位  婚庆结盟  可退可进  避钻攻金  节庆爆点
```

`strategy_library.json` 每条策略字段（去掉旧版对 14 变量与规则匹配器的依赖）：

```text
strategy_id / strategy_name   策略标识与中文名
classical_source              对应兵法 / 三十六计意象（谋士叙事）
business_meaning              商业含义
fit_scenario / avoid_scenario 适配 / 规避场景（自然语言描述，供 LLM 匹配）
recommended_actions / expected_benefits / key_risks
validation_metrics / example_use_case
```

兵法谋士的工作方式（写在 `experts/military_strategist.md`，统一七段结构）：

1. **判局**——用孙子「定战场 / 敌我 / 虚实 / 势」与毛选「主要矛盾 / 一分为二」判读 `intelligence_batch`。
2. **匹配计策**——把局势 LLM 匹配到 12 条策略库，给计策组合；**不得编造库里不存在的 `strategy_id`**。
3. **输出**——按 Output Contract 输出结构化 JSON：匹配计策、`classical_source` 叙事、为何适配（绑定 `evidence_ids`）、上中下三策思路；供总参谋构造 `strategic_options` 时引用。

**关键约束**：孙子 / 毛选原 skill 面向对话（孙子六段式、毛选第一人称「同志」角色扮演）。兵法谋士**只取其分析框架当透镜，不做角色扮演、不用第一人称**，输出严格是智囊团 JSON 契约，并与其他专家一样强制 `evidence_ids` 绑定。

**vendoring 说明**：孙子（`calmlim/sunzi-strategy-skill`）、毛选（`leezythu/maoxuan-skill`，MIT）按快照 vendoring 进 `knowledge/`，保留各自 README / LICENSE 作署名；毛选的可选外挂知识库 `MaoZeDongAnthology` **不**随附——其 `SKILL.md` 内置 7 模型已自包含，足够分析用。

### 17.5 输入适配：intelligence_events → intelligence_batch

智囊团一次调用接收一个 `intelligence_batch`（同一 market、同一时间窗）。阶段 7 用一个轻量 adapter 把 `intelligence_events` 聚合成符合 `input_schema.json` 的批次：

| intelligence_batch 字段 | 来源 |
|---|---|
| `batch_meta.market / region / time_window` | 市场参数 + 当日日期窗 |
| `items[].id` | `intelligence_events.id`（证据链依赖，转字符串） |
| `items[].market / region / source_url` | 同名字段 |
| `items[].source_type / source_name / published_at / raw_excerpt` | 关联 `raw_documents`（FK） |
| `items[].category` | 由 `source_category` 直接映射（7 值枚举一一对应） |
| `items[].event_summary` | `key_claim`（无则回退到 `summary`） |
| `items[].sentiment` | 由 `signal_direction` 推导（positive/negative/mixed/neutral） |
| `items[].impact_area` | 由 `impact_scope` 推导（品类/角色/市场维度） |
| `items[].confidence` | `confidence`（已是 0-1 浮点，直接透传） |
| `items[].tags` | `env_factors[].factor_name` + `conduction_chain.chain_id` + 标题关键词 |
| `items[].env_factors` ⭐ | 直接透传 Stage 3 抽取的因子数组（专家据此聚类作用机制） |
| `items[].conduction_chain` ⭐ | 直接透传链路（兵法谋士据此判局，匹配计策） |
| `items[].intensity` ⭐ | 直接透传 1-5 烈度（总参谋按 ≥4 触发关键信号） |
| `items[].entities` ⭐ | 直接透传实体（竞品专家 / 消费者洞察专家做实体关联） |
| `items[].downstream_implications` ⭐ | 直接透传推断（作为专家分析的下游起点） |
| `items[].ambiguity_flags` ⭐ | 直接透传歧义标记（专家据此降低置信度或要求补证） |

⭐ 标记的字段是本次 Stage 3 升级新增的底层影响因子层，**直接透传**而非二次映射，让专家与总参谋读到完整作用机制而不是只有渠道分类。

`market_snapshot`（§7 forecast 产物）作为批次背景输入，帮助专家理解市场整体机会 / 风险水位；与 §7 forecast 不冲突——snapshot 是粗粒度判断，智囊团是细粒度专家分工。

### 17.6 输出契约：决策报告

总参谋产出**单个 JSON 决策报告**，结构见 `output_schema.json`，核心字段：

```text
council_summary          面向管理层的整体结论（3-5 句，必须给方向）
key_signals              3-6 个核心信号 + 解读 + evidence_ids
opportunities / risks    机会 / 风险，每条绑定证据、品类、置信度
watch_items              证据不足、暂不定性的观察项
strategic_options        上策 / 中策 / 下策（各含前提 / 代价 / 预期）
department_actions       5 个团队的行动清单（产品 / 营销 / 渠道 / 管理层 / 风险）
evidence_chain           证据链：每条情报 id 在哪些结论中被引用
expert_disagreements     专家分歧如实保留 + 总参谋裁定
confidence               整体置信度（level / score / rationale）
next_observation_points  下一轮采集应盯防的方向
```

### 17.7 持久化策略

**决策报告整体落库**到 `council_reports`，便于前端快速读取上 / 中 / 下三策与完整证据链，避免页面请求时重复触发约 6 次 LLM 调用。

同时，从 `department_actions` 派生 `action_items`（沿用 §8 已有表）：

- 每条 `department_action` → 一条 `action_items`，`department` = 该团队名。
- `department_actions` 是产品 / 营销 / 渠道 / 管理层 / 风险 5 个固定团队**段**，但**段可为空**——某团队没有被任何行动命中就不产生 `action_items` 行，**不做「每个部门凑一条」的填充**（区别于按部门模板逐部门出任务的旧做法）。
- 每条 `action_items` 在 `extra` 里带 `evidence_ids` 与所属 `strategic_option`，保留「行动 → 结论 → 证据情报」回溯。

`council_reports` 采用 one row per market/run_date/run 的追加模式；`GET /api/council/latest` 和 `GET /api/markets/{market}/council` 读取最新一行。

### 17.8 专家 Skill 与 Prompt

智囊团 skill 是 **markdown（角色定义）+ JSON（schema / 知识 / 样例）**，不含运行框架，由后端 §17.10 的编排代码加载执行。

- 每位专家一个 `experts/*.md`，统一七段结构。
- `prompts/council_orchestrator.md`：编排（并行 → 综合）。
- `prompts/synthesis_prompt.md`：总参谋综合指令。
- `council.yaml`：专家清单 / 执行模式 / 置信度政策 / 证据政策 / 领域铁律。
- 兵法谋士额外注入 §17.4 的三套谋略知识源（孙子 / 毛选 / 12 条策略库）。

所有 prompt 按 §12 JSON 输出约束（`response_format=json_object`、temperature 0.2-0.4、失败重试）。共 6 次 LLM 调用 / 市场（5 专家 + 1 综合）。

领域铁律（所有专家与总参谋共同遵守）：

- 不允许泛泛而谈，每个判断必须可回溯到具体情报 `id`。
- 证据不足（单一来源 / 未验证社媒 / 单时间点）→ 置信度不得高于 medium。
- **不把黄金价格上涨简单等同于利好**——必须区分投资金条 / 饰品金 / 婚庆金 / 悦己消费。
- 行动建议必须具体到部门、市场、品类、渠道、动作。
- 区分情报 `sentiment`（来源情绪）与对我方业务的 `impact`（影响方向）。
- 保留专家分歧，不和稀泥。

### 17.9 API

沿用 §6 REST 风格：

```text
GET /api/council/latest             读取最新智囊团完整决策报告
GET /api/markets/{market}/council   读取某市场最新智囊团完整决策报告
```

接口只读 `council_reports`，不在请求链路中运行智囊团；若没有报告则返回 404，提示先运行阶段 7 或 `python -m scripts.run_council`。

### 17.10 代码结构

智囊团 skill 文件随本次改造**迁入 `backend/`**，与编排代码同处一个 `council` 子包，阶段 7 实现取代旧的 `services/strategy/`（沙盘）与 `services/action/`（旧部门模板生成器）：

```text
backend/app/services/council/
├── __init__.py
├── skills/                          # 迁入的智囊团 skill（原 skills/jewelry_intelligence_council/）
│   └── jewelry_intelligence_council/
│       ├── council.yaml
│       ├── input_schema.json / output_schema.json
│       ├── experts/                 # 5 位专家 + 总参谋 的 .md
│       ├── knowledge/
│       │   ├── strategy_library.json    # §17.4：12 条兵法策略库（原 library.py 迁移）
│       │   ├── sunzi-strategy/          # vendored：孙子兵法 skill（SKILL.md + references）
│       │   └── maoxuan/                 # vendored：毛选 skill（SKILL.md + references）
│       ├── prompts/                 # council_orchestrator / synthesis_prompt
│       └── examples/                # sample_intelligence / sample_council_output
├── loader.py        # 读 council.yaml / 专家 .md / 策略库
├── adapter.py       # §17.5：intelligence_events → intelligence_batch
├── orchestrator.py  # 阶段7 编排器：5 专家并行 → 总参谋综合 → 决策报告
└── actions.py       # §17.7：decision report → 派生 action_items 落库
```

`services/strategy/` 与 `services/action/` 随之删除；`pipeline.py` 阶段 7 改调 `council.orchestrator`。

### 17.11 前端

按 §14 现状，不重做 UI、不大改页面结构：把市场详情页原「行动建议 / 沙盘推演」区域替换为决策报告——总体结论 `council_summary` → 关键信号 → 机会 / 风险 / 观察项 → 上中下三策 → 部门行动清单 →（可折叠）证据链 / 专家分歧 / 置信度。

### 17.12 实施建议

```text
- 它是阶段 7 的算法升级，随每日 daily_pipeline_job 运行（§13），不在 6h 高频
  cron；单市场约 6 次 LLM 调用，成本可控。
- MVP 聚焦单一市场做深（现有 data_probe 快照为 Singapore），跑通
  「情报 → 适配 → 5 专家 → 总参谋 → 决策报告 → 部门行动」一条链。
- 它是 demo 的差异化亮点（呼应赛题「更前瞻 / 创新的 Agent 设计」）：多专家
  并行 + 总参谋裁定 + 兵法谋士（融合孙子兵法 / 毛选），把阶段 7 从泛泛建议
  升级为可解释、可比较、可验证的战略决策。
- 依赖主流水线先产出 intelligence_events —— 实施顺序排在主流水线落库之后。
- 落地 兵法谋士 需：vendoring 孙子 / 毛选 skill 进 knowledge/、迁移
  library.py 为 strategy_library.json、写 military_strategist.md，并同步
  council.yaml 专家清单、council_orchestrator 阶段一清单、
  chief_strategy_officer 的 Input 段与 synthesis_prompt。
```

---

## 附录 A：已开通的云资源与连接信息

```text
地域            阿里云 新加坡 ap-southeast-1（ECS / RDS / OSS 全部同地域同 VPC）

ECS             2 vCPU / 4 GiB（ecs.e-c1m2.large），Ubuntu 22.04 LTS，x86
                系统盘 ESSD Entry 40GB；公网带宽 按量峰值 5 Mbps；按量付费
                安全组入方向：22(限本人IP) / 80 / 443；8000 不对外，走 Nginx 反代

RDS PostgreSQL  实例 pgm-t4nrl3s1kv94f574，PostgreSQL 17，基础系列单节点，2核2G
                内网地址 pgm-t4nrl3s1kv94f574.pgsql.singapore.rds.aliyuncs.com
                内网 IP 172.17.57.139，端口 5432
                白名单加 ECS 内网 IP（172.17.x.x 段）；本机调试临时加公网 IP
                数据库 aurum_radar；连接用域名不用 IP

OSS             Bucket aurum-radar-demo，标准存储，私有 ACL
                内网 Endpoint oss-ap-southeast-1-internal.aliyuncs.com（ECS 用）
                公网 Endpoint oss-ap-southeast-1.aliyuncs.com（本机调试用）

DashScope       新加坡国际站，OpenAI 兼容接口
                base_url 
                模型 qwen-flash / qwen-plus / qwen-max、text-embedding-v3
```

---

## 附录 B：`.env` 配置参考

```env
APP_ENV=local                       # local / dev / prod
APP_NAME=Aurum Radar
APP_DEBUG=true
API_PREFIX=/api

# 数据库（local 用 RDS 公网地址，prod 用内网地址）
DATABASE_URL=

# OSS（local 用公网 Endpoint，prod 用内网 Endpoint）
OSS_ACCESS_KEY_ID=
OSS_ACCESS_KEY_SECRET=
OSS_BUCKET=
OSS_ENDPOINT=

# DashScope
DASHSCOPE_API_KEY=
DASHSCOPE_BASE_URL=
DASHSCOPE_MODEL_EXTRACT=qwen-plus
DASHSCOPE_MODEL_SUMMARY=qwen-plus
DASHSCOPE_MODEL_ACTION=qwen-plus

# 数据源（按需）
NEWS_API_KEY=
SERPAPI_API_KEY=
GOLD_API_KEY=
EXCHANGE_RATE_API_KEY=

# 调度（local 关，prod 开）
SCHEDULER_ENABLED=false
```

约定：代码只读 `DATABASE_URL` / `OSS_ENDPOINT` / `DASHSCOPE_BASE_URL`，不在代码里判断本地还是云端，不写死内外网地址 —— 环境差异全部由 `.env` 承担。
