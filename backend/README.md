# Aurum Radar Backend

FastAPI + Uvicorn 后端，提供 JSON API 供前端调用。

技术栈：FastAPI · Uvicorn · SQLAlchemy 2.x · PostgreSQL · APScheduler · DashScope

---

## 本地运行

> ⚠️ **请务必使用项目虚拟环境运行，不要用 Homebrew/系统 Python**。否则会缺少 `stevedore`、`apscheduler` 等依赖，出现 `ModuleNotFoundError`。

### 1. 安装依赖

项目使用 [uv](https://github.com/astral-sh/uv) 管理依赖（`uv.lock` 已锁定版本），推荐方式：

```bash
cd backend
uv sync                    # 创建 .venv 并按 uv.lock 安装所有依赖
source .venv/bin/activate  # 激活虚拟环境（后续命令都在该环境下运行）
```

如果未安装 uv，可用传统方式：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

打开 `.env`，至少填写以下字段才能启动：

| 字段 | 说明 |
|------|------|
| `DATABASE_URL` | RDS PostgreSQL 公网地址，格式：`postgresql+psycopg2://USER:PASSWORD@HOST:5432/aurum_radar` |
| `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` | 阿里云 OSS 密钥 |
| `DASHSCOPE_API_KEY` | 百炼 DashScope API Key |
| `DATA_PROBE_OUTPUT_DIR` | data_probe 输出目录，默认 `../data_probe/output/normalized` |

其余字段有默认值，可按需修改。`SCHEDULER_ENABLED` 本地默认 `false`，不会自动触发定时任务。

### 3. 启动服务

确保已 `source .venv/bin/activate`（或用 `uv run` 前缀）：

```bash
uvicorn app.main:app --reload --port 8000
# 或：uv run uvicorn app.main:app --reload --port 8000
```

服务启动后：

- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/health`（会真正连接 RDS，返回 `{"status": "ok", "db": "connected"}`）

### 4. 数据库迁移（如需）

```bash
alembic upgrade head                              # 应用所有迁移
alembic revision --autogenerate -m "描述信息"     # 基于 ORM 变更生成新迁移
```

---

## 常用脚本

所有脚本都需要在已激活的 `.venv` 中运行（或前缀 `uv run`）。

### 摄取 data_probe 爬取数据 → RDS

```bash
python -m scripts.ingest_crawl_data                  # 摄取今天的数据
python -m scripts.ingest_crawl_data --date 2026-05-23
python -m scripts.ingest_crawl_data --all            # 摄取目录下全部文件
python -m scripts.ingest_crawl_data --dry-run        # 不写库，仅打印
```

### 跑 Stage 3–6 + Council + Evaluation（基于 RDS 内已有 raw_documents）

```bash
python -m scripts.run_council
# 可选参数：
#   --market Singapore       仅跑指定市场
#   --since 30d              仅取最近 N 天的文档
#   --until 2026-05-22       截止日期
#   --limit 50               限制文档数
#   --no-evaluation          跳过评估阶段
```

### 通过 API 手动触发整条流水线

```bash
curl -X POST http://localhost:8000/api/jobs/run \
  -H "Content-Type: application/json" \
  -d '{"markets": ["Singapore"], "stages": ["ingest", "extract"]}'
```

---

## 常见问题排查

| 报错 | 原因 | 处理 |
|------|------|------|
| `ModuleNotFoundError: No module named 'stevedore'`（或 `apscheduler`、`oss2` 等） | 用了系统 Python（`/opt/homebrew/...`）而非 `.venv` | `source .venv/bin/activate` 后重跑；或先 `uv sync` |
| `/api/health` 返回 `db: disconnected` | `.env` 中 `DATABASE_URL` 不可达 | 检查 RDS 白名单与公网地址 |
| 启动时 DashScope 报错 | `DASHSCOPE_API_KEY` 未配置或失效 | 重新到百炼控制台生成 Key |
| `SCHEDULER_ENABLED=true` 后定时任务未触发 | APScheduler 仅在主进程启用，`--reload` 模式下会重复创建 | 本地保持 `false`，用 `POST /api/jobs/run` 手动触发 |

---

## 项目结构

```
backend/
├── .env.example          # 环境变量模板
├── requirements.txt      # Python 依赖
└── app/
    ├── main.py           # FastAPI 入口，挂载路由与异常处理
    ├── core/
    │   └── config.py     # 读取 .env 的全局配置（pydantic-settings）
    ├── database/
    │   └── session.py    # 数据库 Engine / Session / get_db 依赖
    └── api/
        ├── routes_health.py     # GET /api/health
        ├── routes_dashboard.py  # GET /api/overview, /api/markets/{market} 等
        ├── routes_events.py     # GET /api/events, /api/events/{id}
        ├── routes_brief.py      # GET /api/brief/latest, /api/briefs/{date}
        ├── routes_actions.py    # GET /api/actions, /api/actions/{id}
        └── routes_jobs.py       # GET /api/jobs/status, POST /api/jobs/run
```

---

## API 接口

| 接口 | 方法 | 状态 | 说明 |
|------|------|------|------|
| `/api/health` | GET | 已实现 | 健康检查，验证 DB 连通性 |
| `/api/dashboard/summary` | GET | 待实现 | 概览页核心指标 |
| `/api/overview` | GET | 待实现 | 世界地图各市场节点 |
| `/api/markets/{market}` | GET | 待实现 | 国家级摘要 |
| `/api/markets/{market}/districts` | GET | 待实现 | 商圈节点列表 |
| `/api/districts/{district_id}` | GET | 待实现 | 商圈详情 |
| `/api/events` | GET | 待实现 | 情报事件列表（支持筛选 + 分页） |
| `/api/events/{event_id}` | GET | 待实现 | 事件详情 |
| `/api/brief/latest` | GET | 待实现 | 最新每日战略简报 |
| `/api/briefs/{brief_date}` | GET | 待实现 | 指定日期简报 |
| `/api/actions` | GET | 待实现 | 行动建议看板 |
| `/api/actions/{action_id}` | GET | 待实现 | 行动详情 |
| `/api/jobs/status` | GET | 待实现 | 流水线运行状态 |
| `/api/jobs/run` | POST | 待实现 | 手动触发 Agent 流水线 |

完整接口契约见 [architecture.md](./architecture.md) 第 6 节。

---

## 详细架构

见 [architecture.md](./architecture.md)。
