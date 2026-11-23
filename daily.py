#!/usr/bin/env python3
"""每天生成天气页面与 JSON 数据：抓取公开天气接口 -> 写入网站目录
用法：
    python3 daily.py             # 按服务器出口 IP 自动定位城市
    python3 daily.py Shenzhen    # 指定城市（英文名）
"""
import ipaddress
import json
import os
import socket
import sys
import urllib.parse
import urllib.request
from contextlib import closing
from datetime import datetime
from html import escape
from pathlib import Path

SITE_DIR = "/opt/1panel/apps/openresty/openresty/www/sites/47.115.150.227/index"
API = "https://wttr.in"


def write_site_file(name: str, text: str) -> None:
    """只允许写站点目录下的白名单文件：目录固定，文件名来自白名单。"""
    if name not in ("daily.html", "weather.json"):
        raise ValueError(f"不允许写入的文件: {name}")
    path = os.path.normpath(os.path.join(SITE_DIR, name))
    if not path.startswith(os.path.normpath(SITE_DIR) + os.sep):
        raise ValueError(f"输出路径越界: {path}")
    Path(path).write_text(text, encoding="utf-8")


def safe_get(url: str, timeout: int = 15) -> bytes:
    """只允许 http/https；请求前解析 host，拒绝环回/私网/保留地址。"""
    parts = urllib.parse.urlparse(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError("只允许 http/https")
    host = parts.hostname or ""
    if not host:
        raise ValueError("URL 缺少 host")
    for info in socket.getaddrinfo(host, None):
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            raise ValueError(f"拒绝访问内网地址: {ip}")
    with closing(urllib.request.urlopen(url, timeout=timeout)) as resp:
        return resp.read()


def render(city: str, current: dict, days: list, updated: str, error: str = "") -> str:
    temp = current.get("temp_C", "?")
    desc = current.get("weatherDesc", [{}])[0].get("value", "")
    humidity = current.get("humidity", "?")
    wind = current.get("windspeedKmph", "?")
    rows = "".join(
        f"<tr><td>{escape(d['date'])}</td><td>{escape(d['maxtempC'])}° / "
        f"{escape(d['mintempC'])}°</td><td>{escape(d['hourly'][4]['weatherDesc'][0]['value'])}</td></tr>"
        for d in days
    )
    note = f"<p class='err'>抓取失败：{escape(error)}</p>" if error else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>每日天气 · {escape(city or '自动')}</title>
<style>
 body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",system-ui,sans-serif;
      background:#f5f5f7;color:#1d1d1f;margin:0;padding:40px 16px;display:flex;justify-content:center}}
 .box{{background:#fff;border-radius:20px;max-width:560px;width:100%;padding:32px;box-shadow:0 10px 30px rgba(0,0,0,.08)}}
 h1{{font-size:26px;margin:0 0 6px}}
 .meta{{color:#6e6e73;font-size:13px}}
 .now{{display:flex;align-items:center;gap:18px;margin:26px 0}}
 .temp{{font-size:56px;font-weight:200;line-height:1}}
 .desc{{color:#6e6e73}}
 table{{width:100%;border-collapse:collapse;margin-top:8px}}
 th,td{{text-align:left;padding:10px 6px;border-bottom:1px solid #eee;font-size:14px}}
 th{{color:#6e6e73;font-weight:500}}
 a{{color:#0071e3;text-decoration:none;font-size:14px}}
 .err{{color:#c00;font-size:13px;background:#fff2f0;padding:10px 12px;border-radius:10px}}
</style></head><body>
<div class="box">
  <h1>今日天气</h1>
  <p class="meta">{escape(city or '按出口 IP 自动定位')} · 更新于 {escape(updated)}</p>
  {note}
  <div class="now">
    <div class="temp">{escape(str(temp))}°</div>
    <div><div>{escape(desc)}</div>
      <div class="desc">湿度 {escape(str(humidity))}% · 风速 {escape(str(wind))} km/h</div></div>
  </div>
  <h3 style="font-size:16px;margin:0 0 4px">未来两天</h3>
  <table><tr><th>日期</th><th>温度</th><th>天气</th></tr>{rows}</table>
  <p style="margin-top:22px"><a href="/">← 返回首页</a></p>
</div></body></html>
"""


def main() -> int:
    city = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    url = f"{API}/{urllib.parse.quote(city)}?format=j1" if city else f"{API}/?format=j1"
    updated = datetime.now().strftime("%Y-%m-%d %H:%M")
    current, days, error = {}, [], ""
    try:
        raw = safe_get(url)
        data = json.loads(raw)
        current = data["current_condition"][0]
        days = data["weather"][:2]
    except Exception as exc:  # 网络失败也要产出页面，避免站点 404
        error = str(exc)[:200]

    write_site_file("daily.html", render(city, current, days, updated, error))

    payload = {
        "city": city,
        "temp": current.get("temp_C", ""),
        "desc": current.get("weatherDesc", [{}])[0].get("value", ""),
        "humidity": current.get("humidity", ""),
        "wind": current.get("windspeedKmph", ""),
        "updated": updated,
        "error": error,
    }
    write_site_file("weather.json", json.dumps(payload, ensure_ascii=False))

    print(f"ok: {SITE_DIR}/daily.html / {SITE_DIR}/weather.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
