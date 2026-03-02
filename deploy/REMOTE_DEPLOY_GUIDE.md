# OpenSentinel 远程部署指南（Ubuntu VPS）

本文用于在一台全新 Ubuntu VPS 上部署 OpenSentinel（单机 Docker Compose）。

## 1. 部署目标

- 一台 VPS 跑完整服务：`api + worker + beat + postgres + redis`
- 支持后台任务持续执行（Celery Worker/Beat）
- 支持后续增量更新与回滚

## 2. 服务器建议配置

- OS：Ubuntu 22.04 / 24.04
- CPU：2 vCPU+
- 内存：4 GB+（最低 2 GB，可跑但余量较小）
- 磁盘：30 GB+（建议 SSD）
- 网络：开放 `22`（SSH），`8000`（临时直连）

## 3. 首次初始化服务器

```bash
sudo apt update && sudo apt -y upgrade
sudo timedatectl set-timezone Asia/Shanghai
```

建议创建普通用户并禁用 root 直登（可选但推荐）。

## 4. 安装 Docker / Compose

```bash
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

执行后重新登录一次，再确认：

```bash
docker --version
docker compose version
```

## 5. 拉取项目与配置环境变量

```bash
git clone https://github.com/G061206/OpenSentinel.git
cd OpenSentinel
cp .env.example .env
```

编辑 `.env`（至少改这些）：

- `DATABASE_URL`（默认 compose 内网可直接用）
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `WECOM_WEBHOOK_URL`（如需企业微信推送）
- `OPENROUTER_API_KEY` / `BAILIAN_API_KEY`（如用真实 LLM）

> 提示：`.env` 不要提交到 Git 仓库。

## 6. 启动服务

```bash
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
```

期望看到服务：

- `opensentinel-api`
- `opensentinel-worker`
- `opensentinel-beat`
- `opensentinel-postgres`
- `opensentinel-redis`

## 7. 验证部署

```bash
curl http://127.0.0.1:8000/healthz
```

预期返回：

```json
{"ok": true}
```

打开页面：

- 管理台：`http://<VPS_IP>:8000/admin`

查看日志：

```bash
docker compose logs -f api worker beat
```

## 8. 常用运维命令

重启：

```bash
docker compose restart
```

停止：

```bash
docker compose down
```

更新代码并发布：

```bash
git pull
docker compose up -d --build
```

## 9. 数据持久化与备份

当前 PostgreSQL 使用命名卷 `pg_data` 持久化。

数据库导出备份：

```bash
docker exec -t opensentinel-postgres pg_dump -U opensentinel -d opensentinel > backup_$(date +%F).sql
```

数据库恢复：

```bash
cat backup_xxx.sql | docker exec -i opensentinel-postgres psql -U opensentinel -d opensentinel
```

## 10. 生产安全建议

- 不要长期暴露 `8000` 到公网，建议前置 Nginx/Caddy 做 HTTPS
- 使用 UFW 仅开放必要端口：`22/80/443`
- 为 SSH 配置密钥登录，关闭密码登录
- 定期轮换 API Key（LLM、Webhook）
- 定期备份数据库并异地存储

## 11. 故障排查

### 11.1 访问 `admin` 报 500

先看 API 日志：

```bash
docker compose logs --tail=200 api
```

若是旧库字段缺失，重启容器触发启动兼容逻辑后再验证：

```bash
docker compose up -d --build
```

### 11.2 Redis 端口冲突（6379 被占用）

本项目 compose 已使用容器内暴露，不再强占宿主机 `6379`。若你自行改过 `ports`，删除映射后重启即可。

### 11.3 容器反复退出

```bash
docker compose ps -a
docker compose logs --tail=200 api worker beat
```

重点检查：

- `.env` 是否缺关键配置
- `DATABASE_URL`/`REDIS_URL` 是否写错
- VPS 内存是否不足（可用 `free -h` 查看）

## 12. 建议的下一步

- 增加 `Caddy/Nginx + HTTPS`（域名访问）
- 配置 `systemd` 或云厂商重启策略，确保主机重启后自动恢复
- 增加可观测性（错误告警、任务积压监控、磁盘告警）
