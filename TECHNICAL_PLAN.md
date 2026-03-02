# OpenSentinel 技术方案（As-Is，对齐当前代码）

## 1. 架构图（文本）

```text
[FastAPI API + Admin UI]
   |  Tracker API / Reports API / Admin Panels(HTMX)
   v
[PostgreSQL] <---- [Celery Worker] <---- [Celery Beat]
   ^                     |                    |
   |                     |                    +-- 扫描 active tracker 并按 schedule 分发
   |                     v
   |               [Run Pipeline]
   |               collect -> normalize -> dedup -> evaluate -> report -> deliver
   |                     |                                     |
   |                     |                                     +-- WeCom Webhook
   |                     +-- RSS / Webpage / LLM adapters
   |
[Redis] 作为 Celery broker/result backend + tracker 执行锁
```

## 2. 模块状态

- `api/`
  - `trackers.py`: Tracker CRUD + run/pause/resume
  - `reports.py`: 报告查询
  - `admin.py`: `/admin` 壳页 + 独立面板（任务/Provider/RSS/日志）
- `workers/`
  - `dispatch_active_trackers`: 扫描并按 `schedule` 分发
  - `run_tracker_once`: 单任务执行 + 分布式锁 + 运行日志
- `services/`
  - `ingestion/normalization/dedup/evaluation/report/delivery/tracker_run`
  - `llm_provider_service`、`rss_source_service` 已接入
- `adapters/`
  - RSS、网页抓取、企业微信 webhook
  - LLM provider（mock/openrouter/bailian，失败回退）

## 3. 数据流（当前实现）

1. 用户在 API 或 Admin 创建/编辑 Tracker，可绑定 Provider 与 RSS 源。
2. Beat 周期执行 `dispatch_active_trackers`，按 `ScheduleService.should_dispatch` 判定是否到期。
3. Worker 执行 `run_tracker_once`：
   - 读取 Provider 与 RSS 绑定
   - 采集 -> 归一化 -> 去重
   - 按阈值评估等级
   - 生成报告并投递
   - 写入 Report 与 TrackerRunLog
4. API 与 Admin 查询数据库渲染结果。

## 4. 数据库表（当前）

- `tracker_tasks`: 任务主表（含 `llm_provider_id`）
- `raw_items`: 标准化证据
- `reports`: 报告与投递状态（含 dedupe_key）
- `tracker_run_logs`: 每次执行日志
- `llm_providers`: Provider 配置
- `rss_sources`: RSS 源配置
- `tracker_rss_links`: 任务与 RSS 多对多
- `system_configs`: 旧配置表（保留，兼容迁移来源）

## 5. 调度与幂等（当前）

- 支持 `cron` / `every N minutes|hours` / `daily HH:MM` / `每天X点`
- `dispatch_active_trackers` 按 `schedule + last_run_at` 判断到期
- Redis 分布式锁避免同一 tracker 并发执行
- Report 使用证据指纹 `dedupe_key` 防重复推送
- 无新增且状态不变时跳过告警

## 6. LLM 调用点（当前）

- `ReportService.build_alert_report` 中调用 `extract_facts`
- provider 支持：`openrouter`、`bailian`、`mock`
- 失败自动降级为 mock payload

当前限制：

- LLM 尚未参与最终状态机决策
- 相关性过滤尚未接入（会导致无关新闻进入评估与报告 Top5）

## 7. 管理后台（当前）

- 主入口：`/admin`
- 面板：
  - `/admin/panels/trackers`
  - `/admin/panels/tracker-form`
  - `/admin/panels/providers`
  - `/admin/panels/rss-sources`
  - `/admin/panels/tracker-logs/{id}`
- 特性：
  - 任务可绑定 Provider + 多个 RSS 源
  - Provider 支持默认切换
  - RSS 支持单条/批量导入

## 8. 部署状态

- Docker Compose 单机部署可用（Ubuntu VPS 优先）
- 已处理 Redis 6379 宿主端口冲突（容器内 expose）
- 已增加启动期数据库兼容补列（旧库可启动）

注意：

- 首次冷启动存在 API 早于 Postgres ready 的时序风险，建议下一步补 `healthcheck + depends_on: service_healthy + restart`。

## 9. 测试状态

- 现有测试覆盖：admin 页面、tracker API、run idempotency、delivery、dedup
- 当前回归命令：

```bash
DATABASE_URL="sqlite:///./test_temp.db" python -m pytest -q
```

## 10. 后续优先级（建议）

1. 引入“问题相关性过滤”后再评估等级
2. 状态机融合规则 + LLM 复核（不再仅按数量阈值）
3. Alembic 迁移体系替代 `create_all`
4. Compose 健康检查与重启策略完善
