#!/usr/bin/env python3
"""服务器状态监控：每 5 分钟采集 CPU/内存/磁盘/负载/服务存活，生成状态页
用法：
    python3 monitor.py              # 采集一次，写入站点目录
    python3 monitor.py --demo       # 本地预览：生成演示数据到 ./_demo
    python3 monitor.py --outdir DIR # 指定输出目录
    python3 monitor.py --test-alert # 按配置发一封测试邮件
"""
import argparse
import json
import math
import os
import shutil
import smtplib
import socket
import ssl
import subprocess
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from html import escape

SITE_DIR = "/opt/1panel/apps/openresty/openresty/www/sites/47.115.150.227/index"
STATE_FILE = "/root/.monitor_state.json"
ALERT_CONF = "/root/.monitor_alert.env"
ALERT_COOLDOWN_H = 6  # 同类异常重复提醒间隔
HISTORY_LEN = 288  # 5 分钟一个点 ≈ 24 小时
HTTP_CHECKS = [
    ("本站首页", "http://127.0.0.1/"),
    ("AI 助手", "http://127.0.0.1:40247/"),
]
EXPECT_CONTAINERS = ("openresty", "lobe")  # 容器名包含这些关键字视为"应在运行"
THRESHOLDS = {"cpu": 85, "mem": 90, "disk": 85, "load_ratio": 1.5}
WEATHER_MAX_AGE_H = 30

CSS = """
 body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",system-ui,sans-serif;
      background:#f5f5f7;color:#1d1d1f;margin:0;padding:36px 16px;display:flex;justify-content:center}
 .box{background:#fff;border-radius:20px;max-width:880px;width:100%;padding:28px 30px;
      box-shadow:0 10px 30px rgba(0,0,0,.08)}
 h1{font-size:24px;margin:0}
 .badge{font-size:12px;padding:4px 10px;border-radius:999px;vertical-align:middle;margin-left:8px}
 .badge.ok{background:#e7f7ec;color:#147a3d}
 .badge.warn{background:#fff4e5;color:#9a5b00}
 .meta{color:#6e6e73;font-size:13px;margin:8px 0 0}
 .alert{margin-top:16px;background:#fff7ed;border:1px solid #ffe1b3;border-radius:12px;
        padding:12px 14px;font-size:13px}
 .alert b{color:#9a5b00}
 .alert ul{margin:8px 0 0 18px;padding:0}
 .alert li{margin:2px 0}
 .m{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:20px}
 .mc{background:#fafafa;border:1px solid #eee;border-radius:14px;padding:14px 16px}
 .mc .k{color:#6e6e73;font-size:12px}
 .mc .v{font-size:25px;font-weight:600;margin:6px 0 8px;letter-spacing:-.5px}
 .mc .s{color:#86868b;font-size:12px;margin-top:6px}
 .bar{height:6px;background:#ececf0;border-radius:3px;overflow:hidden}
 .bar i{display:block;height:100%;border-radius:3px}
 .charts{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px}
 .chart{background:#fafafa;border:1px solid #eee;border-radius:14px;padding:12px 14px}
 .chart .k{font-size:12px;color:#6e6e73}
 .chart svg{width:100%;height:56px;display:block;margin-top:8px}
 .nodata{color:#b0b0b5;font-size:12px;padding:16px 0;margin:0}
 .two{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}
 .sec{background:#fafafa;border:1px solid #eee;border-radius:14px;padding:14px 16px}
 .sec h2{font-size:14px;margin:0 0 8px;color:#1d1d1f}
 .sec .k{font-size:12px;color:#86868b;margin:10px 0 4px}
 .row{display:flex;align-items:center;gap:8px;font-size:13px;padding:6px 0;
      border-bottom:1px solid #f0f0f2}
 .row:last-child{border-bottom:0}
 .row .name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
 .row .val{color:#6e6e73;font-size:12px;white-space:nowrap}
 .dot{width:8px;height:8px;border-radius:50%;flex:0 0 8px}
 .green{background:#34c759}.red{background:#ff453a}
 table{width:100%;border-collapse:collapse;font-size:13px}
 th,td{text-align:left;padding:6px 4px;border-bottom:1px solid #f0f0f2}
 th{color:#6e6e73;font-weight:500;font-size:12px}
 td.n{text-align:right;font-variant-numeric:tabular-nums}
 footer{color:#6e6e73;font-size:12px;margin-top:22px;text-align:center}
 a{color:#0071e3;text-decoration:none}
 @media(max-width:640px){.charts{grid-template-columns:1fr}.two{grid-template-columns:1fr}}
"""


def read_text(path: str, default: str = "") -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return default


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return "0 B"


def human_uptime(sec: float) -> str:
    d, rest = divmod(int(sec), 86400)
    h, rest = divmod(rest, 3600)
    m = rest // 60
    if d:
        return f"{d} 天 {h} 小时"
    if h:
        return f"{h} 小时 {m} 分"
    return f"{m} 分钟"


def cpu_times():
    line = read_text("/proc/stat").split("\n", 1)[0].split()
    if not line or line[0] != "cpu":
        return None
    vals = [int(v) for v in line[1:8]]
    return sum(vals), vals[3] + vals[4]  # total, idle+iowait


def cpu_percent(interval: float = 0.3):
    first = cpu_times()
    if not first:
        return None
    time.sleep(interval)
    second = cpu_times()
    if not second:
        return None
    total, idle = second[0] - first[0], second[1] - first[1]
    return round(100 * (1 - idle / total), 1) if total > 0 else None


def memory():
    info = {}
    for line in read_text("/proc/meminfo").splitlines():
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts:
            info[key] = int(parts[0]) * 1024
    total, avail = info.get("MemTotal"), info.get("MemAvailable")
    if not total or avail is None:
        return None
    swap_total, swap_free = info.get("SwapTotal", 0), info.get("SwapFree", 0)
    return {
        "pct": round((total - avail) / total * 100, 1),
        "used": total - avail,
        "total": total,
        "swap_pct": round((swap_total - swap_free) / swap_total * 100, 1) if swap_total else None,
    }


def docker_containers():
    try:
        out = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=8,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [], f"Docker 不可用：{str(exc)[:80]}"
    rows = []
    for line in out.stdout.splitlines():
        name, _, status = line.partition("\t")
        if name.strip():
            rows.append({"name": name.strip(), "status": status.strip()})
    return rows, ""


def http_checks():
    rows = []
    for name, url in HTTP_CHECKS:
        start = time.monotonic()
        try:
            with urllib.request.urlopen(url, timeout=4) as resp:
                code = resp.status
        except urllib.error.HTTPError as exc:
            code = exc.code
        except Exception:
            code = 0
        rows.append({"name": name, "code": code, "ms": round((time.monotonic() - start) * 1000)})
    return rows


def weather_info():
    path = os.path.join(SITE_DIR, "weather.json")
    try:
        age_h = round((time.time() - os.stat(path).st_mtime) / 3600, 1)
    except OSError:
        return {"updated": "", "age_h": None, "error": "未找到 weather.json"}
    try:
        payload = json.loads(read_text(path, "{}"))
    except json.JSONDecodeError:
        payload = {}
    return {"updated": payload.get("updated", ""), "age_h": age_h, "error": payload.get("error", "")}


def top_processes(limit: int = 6):
    try:
        out = subprocess.run(
            ["ps", "-eo", "%cpu,%mem,comm", "--sort=-%cpu", "--no-headers"],
            capture_output=True, text=True, timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    rows = []
    for line in out.stdout.splitlines()[:limit]:
        parts = line.split(None, 2)
        if len(parts) == 3:
            rows.append({"cpu": parts[0], "mem": parts[1], "name": parts[2][:40]})
    return rows


def collect() -> dict:
    warnings = []
    cpu = cpu_percent()
    mem = memory()
    du = shutil.disk_usage(SITE_DIR if os.path.isdir(SITE_DIR) else "/")
    disk_pct = round(du.used / du.total * 100, 1)
    try:
        load = list(os.getloadavg())
    except (OSError, AttributeError):
        load = [0.0, 0.0, 0.0]
    cores = os.cpu_count() or 1
    up_sec = 0.0
    try:
        up_sec = float(read_text("/proc/uptime", "0").split()[0])
    except (ValueError, IndexError):
        pass
    containers, docker_err = docker_containers()
    checks = http_checks()
    weather = weather_info()
    top = top_processes()

    if cpu is not None and cpu >= THRESHOLDS["cpu"]:
        warnings.append(f"CPU 使用率 {cpu}% 偏高")
    if mem and mem["pct"] >= THRESHOLDS["mem"]:
        warnings.append(f"内存使用率 {mem['pct']}% 偏高")
    if disk_pct >= THRESHOLDS["disk"]:
        warnings.append(f"磁盘使用率 {disk_pct}% 偏高")
    if load[0] > cores * THRESHOLDS["load_ratio"]:
        warnings.append(f"1 分钟负载 {load[0]:.2f} 偏高（{cores} 核）")
    for check in checks:
        if not 200 <= check["code"] < 400:
            warnings.append(f"{check['name']}访问异常（{check['code'] or '超时'}）")
    if docker_err:
        warnings.append(docker_err)
    else:
        for expected in EXPECT_CONTAINERS:
            if not any(expected in c["name"].lower() for c in containers):
                warnings.append(f"未发现运行中的 {expected} 容器")
    if weather["age_h"] is None:
        warnings.append(weather["error"] or "天气数据缺失")
    elif weather["error"]:
        warnings.append(f"天气抓取失败：{weather['error'][:80]}")
    elif weather["age_h"] > WEATHER_MAX_AGE_H:
        warnings.append(f"天气数据已 {weather['age_h']} 小时未更新")

    return {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "host": socket.gethostname(),
        "uptime": human_uptime(up_sec) if up_sec else "—",
        "cpu": cpu,
        "mem": mem,
        "disk": {"pct": disk_pct, "used": du.used, "total": du.total},
        "load": load,
        "cores": cores,
        "containers": containers,
        "docker_err": docker_err,
        "http": checks,
        "weather": weather,
        "top": top,
        "warnings": warnings,
    }


def spark(vals: list, color: str) -> str:
    if not vals:
        return '<p class="nodata">暂无数据</p>'
    width, height, pad = 260, 64, 4
    n = len(vals)
    xs = [width / 2] if n == 1 else [pad + i * (width - 2 * pad) / (n - 1) for i in range(n)]
    ys = [height - pad - min(max(v, 0), 100) / 100 * (height - 2 * pad) for v in vals]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"{xs[0]:.1f},{height - pad} {pts} {xs[-1]:.1f},{height - pad}"
    return (
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
        f'<polygon points="{area}" fill="{color}" opacity="0.10"/>'
        f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linejoin="round"/></svg>'
    )


def bar(value, color: str) -> str:
    width = 0 if value is None else min(max(value, 0), 100)
    return f'<div class="bar"><i style="width:{width:.1f}%;background:{color}"></i></div>'


def render(snap: dict, hist: list) -> str:
    warnings = snap["warnings"]
    badge = (f'<span class="badge warn">⚠ {len(warnings)} 项注意</span>' if warnings
             else '<span class="badge ok">● 运行正常</span>')
    alert = ""
    if warnings:
        items = "".join(f"<li>{escape(w)}</li>" for w in warnings)
        alert = f'<div class="alert"><b>需要留意</b><ul>{items}</ul></div>'

    cpu, mem, disk, load = snap["cpu"], snap["mem"], snap["disk"], snap["load"]
    mem_sub = "—"
    if mem:
        mem_sub = f'{human_bytes(mem["used"])} / {human_bytes(mem["total"])}'
        if mem.get("swap_pct") is not None:
            mem_sub += f' · Swap {mem["swap_pct"]}%'
    cpu_hist = [h["cpu"] for h in hist if isinstance(h.get("cpu"), (int, float))]
    mem_hist = [h["mem"] for h in hist if isinstance(h.get("mem"), (int, float))]
    disk_hist = [h["disk"] for h in hist if isinstance(h.get("disk"), (int, float))]

    http_rows = "".join(
        f'<div class="row"><span class="dot {"green" if 200 <= c["code"] < 400 else "red"}"></span>'
        f'<span class="name">{escape(c["name"])}</span>'
        f'<span class="val">{c["code"] or "超时"} · {c["ms"]} ms</span></div>'
        for c in snap["http"]
    )
    container_rows = "".join(
        f'<div class="row"><span class="dot green"></span>'
        f'<span class="name">{escape(c["name"])}</span>'
        f'<span class="val">{escape(c["status"])}</span></div>'
        for c in snap["containers"]
    ) or '<p class="nodata">没有运行中的容器</p>'
    docker_note = f'<p class="k">{escape(snap["docker_err"])}</p>' if snap["docker_err"] else ""

    weather = snap["weather"]
    age = "—" if weather["age_h"] is None else f'{weather["age_h"]} 小时前'
    weather_extra = (f'<p class="k" style="color:#c00">抓取失败：{escape(weather["error"][:120])}</p>'
                     if weather["error"] else "")

    proc_rows = "".join(
        f'<tr><td>{escape(p["name"])}</td><td class="n">{escape(p["cpu"])}%</td>'
        f'<td class="n">{escape(p["mem"])}%</td></tr>'
        for p in snap["top"]
    ) or '<tr><td colspan="3" style="color:#b0b0b5">无法读取进程列表</td></tr>'

    cpu_text = "—" if cpu is None else f"{cpu:.1f}%"
    mem_text = "—" if not mem else f"{mem['pct']:.1f}%"
    cpu_bar = bar(cpu, "#0071e3")
    mem_bar = bar(None if not mem else mem['pct'], "#7c5cff")
    disk_bar = bar(disk['pct'], "#ff9f0a")
    cpu_chart = spark(cpu_hist, "#0071e3")
    mem_chart = spark(mem_hist, "#7c5cff")
    disk_chart = spark(disk_hist, "#ff9f0a")
    disk_text = f"{disk['pct']:.1f}%"
    host_text = escape(snap['host'])
    uptime_text = escape(snap['uptime'])
    time_text = escape(snap['time'])
    weather_updated = escape(weather['updated'] or "—")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>服务器状态</title>
<style>{CSS}</style></head><body>
<div class="box">
  <h1>服务器状态{badge}</h1>
  <p class="meta">主机 {host_text} · 已运行 {uptime_text} · 更新于 {time_text}</p>
  {alert}
  <div class="m">
    <div class="mc"><div class="k">CPU</div><div class="v">{cpu_text}</div>
      {cpu_bar}<div class="s">{snap['cores']} 核 · 0.3 秒采样</div></div>
    <div class="mc"><div class="k">内存</div><div class="v">{mem_text}</div>
      {mem_bar}<div class="s">{mem_sub}</div></div>
    <div class="mc"><div class="k">磁盘</div><div class="v">{disk_text}</div>
      {disk_bar}<div class="s">{human_bytes(disk['used'])} / {human_bytes(disk['total'])}</div></div>
    <div class="mc"><div class="k">负载</div><div class="v">{load[0]:.2f}</div>
      <div class="s">5 分钟 {load[1]:.2f} · 15 分钟 {load[2]:.2f}</div></div>
    <div class="mc"><div class="k">运行时长</div><div class="v" style="font-size:20px">{uptime_text}</div>
      <div class="s">开机至今</div></div>
  </div>
  <div class="charts">
    <div class="chart"><div class="k">CPU · 近 24 小时（{len(cpu_hist)} 点）</div>{cpu_chart}</div>
    <div class="chart"><div class="k">内存 · 近 24 小时（{len(mem_hist)} 点）</div>{mem_chart}</div>
    <div class="chart"><div class="k">磁盘 · 近 24 小时（{len(disk_hist)} 点）</div>{disk_chart}</div>
  </div>
  <div class="two">
    <div class="sec"><h2>服务</h2>
      <p class="k">端口探测</p>{http_rows}
      <p class="k">运行中的容器</p>{container_rows}{docker_note}
    </div>
    <div class="sec"><h2>定时任务</h2>
      <div class="row"><span class="name">天气数据更新</span><span class="val">{weather_updated}</span></div>
      <div class="row"><span class="name">距今</span><span class="val">{age}</span></div>
      {weather_extra}
    </div>
  </div>
  <div class="sec" style="margin-top:12px"><h2>占用最高的进程</h2>
    <table><tr><th>进程</th><th style="text-align:right">CPU</th><th style="text-align:right">内存</th></tr>
    {proc_rows}</table>
  </div>
  <footer>每 5 分钟自动采集 · 页面每 60 秒刷新 · <a href="/">← 返回首页</a></footer>
</div></body></html>
"""


def load_state() -> dict:
    try:
        data = json.loads(read_text(STATE_FILE, "{}"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def append_history(hist: list, snap: dict) -> list:
    entry = {"t": datetime.now().strftime("%m-%d %H:%M")}
    if snap["cpu"] is not None:
        entry["cpu"] = snap["cpu"]
    if snap["mem"]:
        entry["mem"] = snap["mem"]["pct"]
    entry["disk"] = snap["disk"]["pct"]
    hist.append(entry)
    del hist[:-HISTORY_LEN]
    return hist


def save_state(state: dict) -> None:
    try:
        write_atomic(STATE_FILE, json.dumps(state, ensure_ascii=False))
    except OSError:
        pass  # 状态保存失败不影响状态页


def load_alert_conf() -> dict:
    conf = {}
    for line in read_text(ALERT_CONF).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        conf[key.strip()] = value.strip().strip('"').strip("'")
    return conf


def send_email(subject: str, body: str) -> bool:
    conf = load_alert_conf()
    if not all(conf.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "ALERT_TO")):
        print(f"alert: 未配置 {ALERT_CONF}，跳过发信")
        return False
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = conf.get("ALERT_FROM") or conf["SMTP_USER"]
    msg["To"] = conf["ALERT_TO"]
    host = conf["SMTP_HOST"]
    port = int(conf.get("SMTP_PORT", "465"))
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=15, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            server.starttls(context=ssl.create_default_context())
        with server:
            server.login(conf["SMTP_USER"], conf["SMTP_PASS"])
            server.send_message(msg)
        print(f"alert: 已发送邮件 -> {conf['ALERT_TO']}")
        return True
    except Exception as exc:  # SMTP 失败不能影响状态页
        print(f"alert: 发送失败：{str(exc)[:120]}")
        print("trace: " + " | ".join(traceback.format_exc().strip().splitlines()[-3:]))
        return False


def maybe_alert(snap: dict, alert_state: dict) -> dict:
    """异常组合变化时发信；同类每 ALERT_COOLDOWN_H 小时最多一次；恢复时发一封。"""
    if not load_alert_conf():
        return alert_state
    warnings = snap["warnings"]
    now = time.time()
    fp = "|".join(warnings)
    prev_fp = alert_state.get("fp", "")
    last = float(alert_state.get("sent_at", 0))
    attempt = float(alert_state.get("attempt_at", 0))
    page = "http://47.115.150.227/status.html"

    if warnings:
        if fp != prev_fp or now - last >= ALERT_COOLDOWN_H * 3600:
            if now - attempt < 1800:  # 发信失败后 30 分钟内不重试
                return alert_state
            body = "\n".join(
                [f"主机：{snap['host']}", f"时间：{snap['time']}", "", "异常项："]
                + [f"- {w}" for w in warnings]
                + ["", f"状态页：{page}"]
            )
            if send_email(f"[服务器告警] {snap['host']} {len(warnings)} 项异常", body):
                return {"fp": fp, "sent_at": now}
            alert_state = dict(alert_state)
            alert_state["attempt_at"] = now
        return alert_state

    if prev_fp:
        body = "\n".join(
            [f"主机：{snap['host']}", f"时间：{snap['time']}", "", "所有检查项已恢复正常。",
             "", f"状态页：{page}"]
        )
        if send_email(f"[服务器恢复] {snap['host']} 运行正常", body):
            return {}
    return alert_state


def write_atomic(path: str, text: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o644)
    except OSError:
        pass


def demo_data():
    hist = []
    for i in range(48):
        hist.append({
            "cpu": round(18 + 9 * math.sin(i / 6), 1),
            "mem": round(52 + 6 * math.sin(i / 9), 1),
            "disk": round(41.5 + i / 200, 1),
        })
    snap = {
        "time": "2026-11-21 16:05",
        "host": "demo-server",
        "uptime": "3 天 4 小时",
        "cpu": 26.4,
        "mem": {"pct": 58.2, "used": 1_250_000_000, "total": 2_147_483_648, "swap_pct": 0.0},
        "disk": {"pct": 41.6, "used": 8_900_000_000, "total": 21_400_000_000},
        "load": [0.42, 0.55, 0.61],
        "cores": 2,
        "containers": [
            {"name": "1Panel-openresty-abc", "status": "Up 12 days"},
            {"name": "1Panel-lobe-chat-xyz", "status": "Up 12 days"},
        ],
        "docker_err": "",
        "http": [{"name": "本站首页", "code": 200, "ms": 3}, {"name": "AI 助手", "code": 200, "ms": 12}],
        "weather": {"updated": "2026-11-21 08:00", "age_h": 8.1, "error": ""},
        "top": [
            {"name": "docker", "cpu": "2.1", "mem": "0.8"},
            {"name": "python3", "cpu": "1.2", "mem": "0.6"},
            {"name": "openresty", "cpu": "0.4", "mem": "0.3"},
        ],
        "warnings": [],
    }
    return snap, hist


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="生成本地演示数据")
    parser.add_argument("--outdir", default="", help="输出目录")
    parser.add_argument("--test-alert", action="store_true", help="按配置发送测试邮件")
    args = parser.parse_args()

    if args.test_alert:
        body = "\n".join([
            "这是一封测试邮件。",
            f"主机：{socket.gethostname()}",
            f"时间：{datetime.now():%Y-%m-%d %H:%M}",
        ])
        return 0 if send_email("[测试] 服务器监控邮件通知", body) else 1

    outdir = args.outdir or (os.path.join(os.getcwd(), "_demo") if args.demo else SITE_DIR)
    os.makedirs(outdir, exist_ok=True)

    if args.demo:
        snap, hist = demo_data()
    else:
        snap = collect()
        state = load_state()
        hist = state.get("history", [])
        if not isinstance(hist, list):
            hist = []
        hist = append_history(hist, snap)
        state["history"] = hist
        state["alert"] = maybe_alert(snap, state.get("alert", {}))
        save_state(state)

    write_atomic(os.path.join(outdir, "status.html"), render(snap, hist))
    write_atomic(os.path.join(outdir, "status.json"),
                 json.dumps(snap, ensure_ascii=False, indent=2))

    print(f"ok: {outdir}/status.html | warnings: {len(snap['warnings'])}")
    for warn in snap["warnings"]:
        print(f"  - {warn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
