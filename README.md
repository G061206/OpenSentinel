# OpenSentinel

OpenSentinel 是一个面向长期运行场景的事件跟踪系统：
用户创建跟踪任务后，系统会按计划持续采集公开信源、去重、评估事件等级、生成报告，并推送到企业微信群机器人。

当前仓库已完成 **MVP 第二批**（可运行主链路 + 任务级调度判断 + 幂等推送 + 轻量管理后台）。

## 核心能力

- Tracker 管理：创建、查询、编辑、暂停、恢复、删除、手动触发
- 信源采集：RSS + 网页正文抽取
- 内容处理：归一化 + URL/哈希去重
- 事件评估：`NORMAL/WATCH/ELEVATED/CRISIS/CONFIRMED`
- 报告输出：Markdown 报告 + 结构化 payload 入库
- LLM 提供商：支持 `openrouter`、`bailian` 真实调用（失败自动回退 mock）
- 通知推送：企业微信群 webhook
- 推送格式：`text`（默认，普通微信更友好）/ `markdown`
- 后台调度：Celery Worker + Celery Beat
- 运维友好：Docker Compose 单机部署（Ubuntu VPS 优先）

## 技术栈

- Python 3.11+
- FastAPI
- SQLModel / SQLAlchemy
- PostgreSQL
- Redis
- Celery + Celery Beat
- httpx / feedparser / trafilatura
- Jinja2 + HTMX（轻量后台）
- Docker Compose

## 项目结构

```text
app/
  api/          # HTTP API 与管理后台路由
  adapters/     # 外部适配器（RSS、网页、LLM、企业微信）
  core/         # 配置、日志、数据库
  models/       # ORM 模型
  schemas/      # Pydantic 模型
  services/     # 业务服务层
  workers/      # Celery 任务与调度
tests/          # 测试用例
scripts/        # 辅助脚本
deploy/         # 部署补充说明
Dockerfile
docker-compose.yml
.env.example
TECHNICAL_PLAN.md
```

## 快速开始（本地）

### 1) 准备配置

Linux/macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

请至少检查以下配置：

- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `WECOM_WEBHOOK_URL`（需要推送时配置）
- `WECOM_MESSAGE_FORMAT`（默认 `text`）

### 2) 启动服务

```bash
docker compose up --build
```

启动后默认包含 5 个容器：

- `api`
- `worker`
- `beat`
- `postgres`
- `redis`

### 3) 验证服务

- 健康检查：`GET /healthz`
- 管理后台：`GET /admin`

## 常用 API

### Tracker

- `POST /api/v1/trackers`：创建任务
- `GET /api/v1/trackers`：任务列表
- `GET /api/v1/trackers/{id}`：任务详情
- `PATCH /api/v1/trackers/{id}`：更新任务
- `POST /api/v1/trackers/{id}/pause`：暂停
- `POST /api/v1/trackers/{id}/resume`：恢复
- `POST /api/v1/trackers/{id}/run`：手动触发
- `DELETE /api/v1/trackers/{id}`：删除

### Report

- `GET /api/v1/reports`
- `GET /api/v1/reports?tracker_id={id}`

## 管理后台

访问 `GET /admin` 后可直接进行：

- 创建任务
- 暂停 / 恢复
- 立即执行
- 删除任务
- 进入 `/admin/config` 配置 LLM Provider 与全局 RSS 源
- 打开 `/admin/trackers/{id}/logs` 查看任务执行日志
  - 支持配置 `LLM API Key` 与 `LLM Model`

采用 HTMX 局部刷新，适合 VPS 场景下的轻量运维管理。

## 调度与幂等说明（已实现）

- 支持任务级调度表达式：
  - Cron：`*/15 * * * *`
  - 英文简写：`every 15 minutes`、`daily 09:00`
  - 中文简写：`每天 9 点`
- 分发时根据 `schedule + last_run_at` 判定是否到期
- 单任务分布式锁防并发重复执行
- 报告按证据指纹幂等，避免重复推送
- 当“无新增证据且状态不变”时，跳过重复告警

## LLM Provider 配置

在 `GET /admin/config` 中选择 Provider 并保存：

- `openrouter`：使用 OpenRouter 的 OpenAI 兼容接口
- `bailian`：使用阿里百炼 DashScope 兼容接口

你可以在页面填写：

- `LLM API Key`
- `LLM Model`（例如 OpenRouter 的 `openai/gpt-4o-mini`，或百炼的 `qwen-plus`）

环境变量默认值见 `.env.example`：

- `OPENROUTER_BASE_URL`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `OPENROUTER_APP_URL`
- `BAILIAN_BASE_URL`
- `BAILIAN_API_KEY`
- `BAILIAN_MODEL`
- `LLM_TIMEOUT_SECONDS`

## 数据库初始化

当前为 MVP 模式：API 启动时自动 `create_all`。

也可手动执行：

```bash
python -m scripts.init_db
```

## 测试

```bash
python -m pytest -q
```

## Ubuntu VPS 部署

1. 安装 Docker 与 Docker Compose 插件
2. 拉取代码并创建 `.env`
3. 执行：

```bash
docker compose up -d --build
```

4. 查看日志：

```bash
docker compose logs -f api worker beat
```

5. 访问：

- `http://<VPS_IP>:8000/healthz`
- `http://<VPS_IP>:8000/admin`

## 已完成与下一步

已完成：

- MVP 主链路可运行
- 第二批调度与幂等能力
- 轻量后台管理页面

下一步建议：

- Alembic 数据库迁移体系
- 报告查询分页与筛选
- 更完善的告警规则（来源可信度、时间窗统计）
- 真实 LLM Provider（严格 JSON Schema 输出）

---

详细设计见 `TECHNICAL_PLAN.md`。
