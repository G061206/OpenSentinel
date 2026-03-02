# OpenSentinel

OpenSentinel 是一个面向长期运行场景的事件跟踪系统。用户创建跟踪任务后，系统会持续采集公开信源、去重、评估事件等级、生成报告，并推送到企业微信群机器人。

当前代码状态：**MVP 可运行 + 管理后台面板化重构完成**。

## 当前能力（与代码一致）

- Tracker 管理：创建、查询、编辑、暂停、恢复、删除、手动触发
- 采集：RSS + 网页正文抽取（`source_profile.web_urls` + 任务绑定 RSS 源）
- 去重：URL + 稳定哈希
- 评估：`NORMAL/WATCH/ELEVATED/CRISIS/CONFIRMED`
- 报告：Markdown + 结构化 payload 入库
- LLM Provider：`mock/openrouter/bailian/...`（失败自动回退 mock）
- 投递：企业微信群 webhook，支持 `text` / `markdown`
- 调度：Celery Beat 扫描 active 任务 + 按任务 `schedule` 判定是否到期
- 幂等：执行分布式锁 + 报告证据指纹去重
- 管理后台：`/admin` 单页壳 + 独立面板（任务、Provider、RSS、日志）

## 重要现状说明

- LLM 目前用于**事实抽取与报告 payload**，尚未参与最终状态机判定。
- 事件等级当前主要按“新增证据数量阈值”升级，尚未做问题相关性过滤。
- 数据库迁移目前采用 `create_all + 启动兼容补列`，尚未引入 Alembic。

## 技术栈

- Python 3.11+
- FastAPI
- SQLModel / SQLAlchemy
- PostgreSQL
- Redis
- Celery + Celery Beat
- httpx / feedparser / trafilatura
- Jinja2 + HTMX
- Docker Compose

## 项目结构

```text
app/
  api/
  adapters/
  core/
  models/
  schemas/
  services/
  templates/
  workers/
tests/
scripts/
deploy/
Dockerfile
docker-compose.yml
.env.example
TECHNICAL_PLAN.md
```

## 快速开始

### 1) 准备配置

```bash
cp .env.example .env
```

至少确认：

- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `WECOM_WEBHOOK_URL`（要推送时必填）

### 2) 启动

```bash
docker compose up -d --build
```

### 3) 验证

- `GET /healthz`
- `GET /admin`

## 管理后台（新）

入口：`/admin`

面板路由：

- `/admin/panels/trackers`
- `/admin/panels/tracker-form`
- `/admin/panels/providers`
- `/admin/panels/rss-sources`
- `/admin/panels/tracker-logs/{id}`

后台可配置：

- 任务级 `wecom_webhook_url`
- Provider 级 `api_key/model/base_url`
- 任务绑定 Provider 与 RSS 源

## API 概览

Tracker:

- `POST /api/v1/trackers`
- `GET /api/v1/trackers`
- `GET /api/v1/trackers/{id}`
- `PATCH /api/v1/trackers/{id}`
- `POST /api/v1/trackers/{id}/pause`
- `POST /api/v1/trackers/{id}/resume`
- `POST /api/v1/trackers/{id}/run`
- `DELETE /api/v1/trackers/{id}`

Report:

- `GET /api/v1/reports`
- `GET /api/v1/reports?tracker_id={id}`

## 测试

如本地无 Postgres 驱动，可先用 sqlite 环境变量执行：

```bash
DATABASE_URL="sqlite:///./test_temp.db" python -m pytest -q
```

## 部署

远程部署文档见：`deploy/REMOTE_DEPLOY_GUIDE.md`

## 下一步建议

- 增加“问题相关性过滤”后再进入评估（避免无关新闻推高等级）
- 状态机融合规则 + LLM 复核，而不是仅看条目数
- 引入 Alembic 迁移体系

---

详细技术状态见 `TECHNICAL_PLAN.md`。
