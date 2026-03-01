# OpenSentinel MVP 技术方案

## 1. 架构图（文本）

```text
[FastAPI API]
   |  create/update tracker, manual run, query reports
   v
[PostgreSQL] <---- [Celery Worker] <---- [Celery Beat]
   ^                     |                    |
   |                     |                    +-- 定时分发 active tracker
   |                     v
   |               [Source Adapters]
   |                - RSS
   |                - Webpage
   |                     |
   |                     v
   |               [Normalization + Dedup + Evaluation]
   |                     |
   |                     v
   +------------- [Report + Delivery]
                         |
                         v
                   [WeCom Webhook]

[Redis] 作为 Celery broker/result backend
```

## 2. MVP 模块说明

- `api/`: Tracker CRUD、暂停/恢复、手动执行、报告查询。
- `workers/`: 周期调度与执行管线。
- `services/`: 采集、归一化、去重、评估、报告、投递。
- `adapters/`: RSS、网页抽取、企业微信、LLM provider（当前 mock）。
- `models/`: tracker/raw_item/report 核心表。

## 3. 数据流

1. 用户创建 tracker（含 source_profile、alert_rules、delivery_channels）。
2. Beat 定时触发 `dispatch_active_trackers`。
3. Worker 对每个 tracker 执行：采集 -> 归一化 -> 去重 -> 状态评估 -> 报告生成 -> 企业微信推送。
4. 结果写入 report 历史，供 API 查询。

## 4. 数据表设计（MVP）

- `tracker_tasks`: 任务定义、调度字段、告警规则、状态。
- `raw_items`: 每次采集后的标准化条目。
- `reports`: 实时报告与推送结果。

## 5. 调度设计

- Beat 全局按 `BEAT_SCAN_INTERVAL_MINUTES` 分发 active tracker。
- 每个 tracker 的 `schedule` 字段已保留，第二阶段将支持按任务级 cron 动态调度。

## 6. LLM 调用点

- 当前 `report_service` 中调用 `llm_provider.extract_facts_mock`。
- 第二阶段替换为真实 provider + JSON schema 结构化输出。

## 7. 推送流程

- 生成 markdown 报告。
- 调用 WeCom webhook 发送 markdown 消息。
- 写入 delivered 状态，避免重复发送（第二阶段补充强幂等策略）。

## 8. MVP 边界

已包含：
- tracker 管理
- RSS/网页采集
- 基础去重（URL + hash）
- 基础状态机评估
- markdown 报告生成
- 企业微信推送
- 历史报告查询
- Docker Compose 部署

暂不包含（第二阶段）：
- 多租户与权限
- 复杂事件聚类
- 多路新闻 API
- 向量检索增强
- 动态任务级调度

## 9. 风险点

- 网站反爬/限流可能导致网页采集失败。
- RSS 质量不一致导致噪声偏高。
- 单机 Celery 模式下高并发可扩展性有限。
- 当前幂等仅为基础版本，需加强 dedupe_key 与规则控制。
