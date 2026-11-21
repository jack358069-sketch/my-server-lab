# 个人服务器实验站

一台 2 核 2G 的阿里云 ECS（Ubuntu），用 1Panel 做的静态站点 + Docker 应用 + 每日定时任务。

- 首页：`http://47.115.150.227`
- AI 助手：LobeChat（Docker，端口 40247）

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

## 功能

1. 静态站点（80 端口，OpenResty 提供）
2. LobeChat 网页 AI 助手（Docker 部署，访问密码保护）
3. 每日 8:00 定时任务：生成天气页面与数据

## 部署步骤（简版）

1. 阿里云 ECS（Ubuntu 22.04），安全组入方向放行 22 / 80 / 40247
2. 安装 1Panel，浏览器登录面板（地址与安全入口用 `1pctl user-info` 查看）
3. 1Panel → 应用商店 → 安装 OpenResty；网站 → 创建静态网站，主域名填服务器 IP
4. 把 `index.html` 上传到站点根目录（`.../www/sites/<IP>/index/`）
5. 把 `daily.py` 上传到 `/root`，运行 `python3 daily.py 城市名` 验证
6. 1Panel → 计划任务 → 每天 8:00 执行 `cd /root && python3 daily.py 城市名`

## 踩坑记录

- **Docker 镜像拉取超时**：默认加速源不稳定；改为手动从 `docker.1panel.live` 拉取后 `docker tag` 成 1Panel 期望的镜像名，重建即成功
- **公网 IP 记错一位**（115 vs 116），导致 22/端口全部超时——先用 SSH 能连的地址为准
- **1Panel 安全入口**：只开 IP:端口会提示“暂时无法访问”，完整地址需 `1pctl user-info`
- **host 网络模式**：容器端口不经 Docker 映射，安全组要直接放行

## 说明

仓库不含任何密码、密钥或访问口令。
