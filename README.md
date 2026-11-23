# 个人服务器实验站

> 当前进度与待办见 [`进度存档.md`](进度存档.md)。

一台 2 核 2G 的阿里云 ECS（Ubuntu），用 1Panel 做的静态站点 + Docker 应用 + 每日定时任务。

- 首页：`http://47.115.150.227`
- AI 助手：LobeChat（Docker，端口 40247）
- 博客：Typecho（Docker + MariaDB，端口 40300）

## 技术栈

| 层 | 用的东西 |
|---|---|
| 云 | 阿里云 ECS、安全组、CDT 流量 |
| 系统 | Ubuntu、systemd |
| 面板 | 1Panel（文件、应用商店、计划任务） |
| Web | OpenResty（静态站点） |
| 容器 | Docker / Docker Compose |
| 脚本 | Python 3（标准库，无第三方依赖） |

## 文件说明

- `index.html`：站点首页，标题下通过 `fetch('/weather.json')` 显示一行天气
- `daily.py`：抓取公开天气接口，生成 `daily.html`（详情页）与 `weather.json`（首页数据）
- `monitor.py`：采集 CPU/内存/磁盘/负载/容器与端口存活，生成 `status.html`（状态页）与 `status.json`

## 功能

1. 静态站点（80 端口，OpenResty 提供）
2. LobeChat 网页 AI 助手（Docker 部署，访问密码保护）
3. 每日 8:00 定时任务：生成天气页面与数据
4. 每 5 分钟监控采集：`/status.html` 显示资源占用、服务存活与 24 小时趋势
5. 每日 3:00 / 3:10 / 3:20 备份站点、LobeChat、Typecho（MariaDB 另行备份）到本地磁盘，保留 7 份
6. 邮件告警：异常时发邮件，同类 6 小时内最多一封；恢复正常后发一封恢复通知
7. Typecho 博客（Docker + MariaDB，端口 40300），后台 `/admin/`
8. SSH 密钥登录 + fail2ban 防爆破；1GB swap 兜底内存

## 部署步骤（简版）

1. 阿里云 ECS（Ubuntu 22.04），安全组入方向放行 22 / 80 / 40130（面板）/ 40247 / 40300
2. 安装 1Panel，浏览器登录面板（地址与安全入口用 `1pctl user-info` 查看）
3. 1Panel → 应用商店 → 安装 OpenResty；网站 → 创建静态网站，主域名填服务器 IP
4. 把 `index.html` 上传到站点根目录（`.../www/sites/<IP>/index/`）
5. 把 `daily.py` 上传到 `/root`，运行 `python3 daily.py 城市名` 验证
6. 1Panel → 计划任务 → 每天 8:00 执行 `cd /root && python3 daily.py 城市名`
7. 把 `monitor.py` 上传到 `/root`，运行 `python3 monitor.py` 验证，再建计划任务每 5 分钟执行 `cd /root && python3 monitor.py`
8. 1Panel → 计划任务 → 备份网站：选站点 `47.115.150.227`，每天 03:00，备份到本地磁盘，保留 7 份
9. 1Panel → 计划任务 → 备份应用：选 LobeChat，每天 03:10，保留 7 份（没有「备份应用」就用「备份目录」备份 `/opt/1panel/apps/lobe-chat`）
10. 在 `/root/.monitor_alert.env` 填 SMTP 配置（见告警说明），执行 `python3 monitor.py --test-alert` 验证收信
11. 应用商店装 Typecho：先装 MariaDB 实例（3306 不对公网开放），Typecho 端口 `40300`、管理员密码自设；安全组放行 40300
12. 本机生成 SSH 密钥，把公钥写入 `/root/.ssh/authorized_keys`，验证密钥登录成功后安装 fail2ban
13. 增加 1GB swap（`/swapfile`），写入 `/etc/fstab`，`vm.swappiness=10`

## 监控说明

- 每 5 分钟采一次：CPU、内存（含 Swap）、磁盘、负载、运行时长、Docker 容器、80/40247/40300 端口探测、天气数据新鲜度
- 阈值：CPU 85% / 内存 90% / 磁盘 85% / 1 分钟负载 > 核心数 × 1.5 / 天气数据 30 小时未更新，触发即在页面顶部列出
- 历史只留最近 288 个点（约 24 小时），存在 `/root/.monitor_state.json`，页面内嵌 SVG 趋势图
- 全走本机 `/proc` 与回环探测，不产生公网流量；页面公网可见，只展示资源数字和容器名，不含路径、密钥与进程参数
- 容器名按包含 `openresty` / `lobe` / `typecho` / `mariadb` 判断，端口按 80 / 40247 / 40300 探测；换端口或改容器名时改 `monitor.py` 顶部常量
- 本地预览：`python3 monitor.py --demo`，输出到 `_demo/status.html`

## 告警说明（邮件）

1. QQ 邮箱网页 → 设置 → 账号 → 开启 POP3/SMTP 服务 → 获取**授权码**（授权码不是 QQ 密码）
2. 服务器上创建 `/root/.monitor_alert.env`（权限 600）：

```
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=你的QQ邮箱@qq.com
SMTP_PASS=授权码
ALERT_TO=接收邮箱（可填同一个QQ邮箱）
```

3. 测试：`cd /root && python3 monitor.py --test-alert`，收到邮件即成功
4. 规则：异常组合变化立即发信；同一组异常每 6 小时最多提醒一次；恢复后发一封恢复邮件；发信失败 30 分钟内不重试
5. 未配置该文件时脚本照常生成状态页，只是不发信；配置文件不进仓库
6. 收不到先查垃圾箱、再确认 465 端口出站正常

## 备份说明

- 备份存放：1Panel 本地磁盘（默认 `/opt/1panel/backup`），每类保留 7 份
- 覆盖范围：站点目录（页面、天气 JSON、状态数据）+ LobeChat 应用目录（含 `.env` 里的 API key）+ Typecho 应用与 MariaDB（03:20，保留 7 份），备份文件不要外传
- 恢复：网站 / 应用 → 备份列表 → 恢复；恢复前先手动备份一次当前状态
- 局限：本地备份只能防误删、误改，防不了服务器磁盘损坏。每月用 FinalShell 把 `/opt/1panel/backup` 里的最新备份下载一份到电脑
- 1Panel 面板自身配置不在备份范围，面板坏了重装后用本 README 重建即可

## 安全说明

- SSH：ed25519 密钥登录，私钥只放本机（`~/.ssh/server_ecs_ed25519`），公钥写入服务器 `/root/.ssh/authorized_keys`
- 密码登录暂时保留：1Panel 自带的「终端」依赖它；等不再用面板终端后可关闭
- fail2ban：sshd jail 默认策略，多次失败自动封 IP；查看 `fail2ban-client status sshd`，解封 `fail2ban-client set sshd unbanip <IP>`
- 公网端口：22 / 80 / 40130（面板）/ 40247 / 40300；数据库 3306 只在 1Panel 内网，不对外
- 敏感文件：`/root/.monitor_alert.env`（600）、SSH 私钥、Typecho 后台密码，均不进仓库

## 系统与 swap

- 物理内存 2G（实际约 1.7GiB），2026-11 增加 1GB `/swapfile` 兜底，`vm.swappiness=10`
- 查看：`free -h`、`swapon --show`
- 移除：`swapoff /swapfile`，删掉 `/etc/fstab` 里的 `/swapfile` 行，再 `rm /swapfile`
- 监控页显示的是物理内存占用，不含 swap

## 运维速查

```bash
fail2ban-client status sshd          # 防爆破状态
docker ps                            # 容器
python3 /root/monitor.py --test-alert # 测试邮件
free -h                              # 内存与 swap
```

## 踩坑记录

- **Docker 镜像拉取超时**：默认加速源不稳定；改为手动从 `docker.1panel.live` 拉取后 `docker tag` 成 1Panel 期望的镜像名，重建即成功
- **公网 IP 记错一位**（115 vs 116），导致 22/端口全部超时——先用 SSH 能连的地址为准
- **1Panel 安全入口**：只开 IP:端口会提示“暂时无法访问”，完整地址需 `1pctl user-info`
- **host 网络模式**：容器端口不经 Docker 映射，安全组要直接放行
- **应用模板镜像 tag 不存在**：如 MariaDB `11.8.9`、Typecho 镜像，先从 `docker.1panel.live` 拉可用版本，再 `docker tag` 成模板要求的名字，安装时取消「拉取镜像」即可绕过
- **Typecho 只绑 127.0.0.1**：安装时高级设置的「端口外部访问」没生效会导致公网 502；重装时确认勾选，或改 `.env` 的 `HOST_IP=0.0.0.0` 后重建

## 说明

仓库不含任何密码、密钥或访问口令。
