#!/usr/bin/env python3
"""农业总控看板后端桥接：把网页的每条消息转发到对应 Hermes Bot 的 Bot Chat，并返回回复。

用法:
  python3 bridge.py            # 默认 127.0.0.1:8790
  python3 bridge.py --port 9000

API:
  GET  /api/bots                     -> bot 列表与状态
  POST /api/chat  {bot, message}     -> 发给指定 bot，SSE 流式返回该 bot 的回复
"""
import json
import os
import shlex
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

_BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_BASE, "bots.json")


def load_config():
    """从 bots.json 读取公司抬头与 bot 列表；文件缺失时用内置兜底。"""
    default = {
        "company": "沽渌农业自动化管理总控台",
        "company_en": "GULU AGRI · AUTOMATION COMMAND",
        "hero_title": "让每一寸农田，被看见、被理解、被调度。",
        "bots": [
            {"id": "agri-xiaoshou", "name": "农业销售部", "dept": "农业销售部",
             "role": "市场开拓 · 客户跟进 · 订单转化", "state": "在线",
             "task": "梳理本周高意向客户，生成首轮回访建议", "progress": 72,
             "kpi1": "今日跟进客户", "value1": "12 位", "kpi2": "订单转化", "value2": "3 单",
             "image": "assets/agri-sales-bot.png",
             "welcome": "您好，我是农业销售部智能助手。我可以协助市场开拓、客户跟进与订单转化。"},
            {"id": "agri-shengchan", "name": "农业生产部", "dept": "农业生产部",
             "role": "种植排产 · 农事执行 · 产量跟踪", "state": "工作中",
             "task": "监测秋季叶菜批次长势，更新明日农事排产", "progress": 58,
             "kpi1": "今日排产", "value1": "8 亩", "kpi2": "农事执行", "value2": "6 项",
             "image": "assets/agri-production-bot.png",
             "welcome": "您好，我是农业生产部智能助手。我可以协助种植排产、农事执行和产量跟踪。"},
        ],
    }
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        for key in default:
            cfg.setdefault(key, default[key])
        return cfg
    except Exception:
        return default


def bot_index():
    cfg = load_config()
    return {b["id"]: b for b in cfg.get("bots", [])}


LOCK = threading.Lock()


def bot_chat(profile: str, message: str) -> str:
    """调用 hermes -p <profile> chat，向该 bot 的常驻 'Bot Chat' 发消息，取纯文本回复。"""
    # 通过 stdin 传消息避免 shell 转义问题
    cmd = [
        "hermes", "-p", profile, "chat",
        "-Q", "-q", message,
        "-c", "Bot Chat", "--create-if-missing",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, cwd="/Users/Zhuanz",
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        # 提取回复：取两个 ╰/╭ 框内文本或 '链路OK' 行之后的纯文本
        text = _extract_reply(out)
        return text or out[-2000:]
    except subprocess.TimeoutExpired:
        return "(bot 响应超时，请重试)"
    except Exception as e:
        return f"(调用出错: {e})"


def _extract_reply(out: str) -> str:
    import re
    # 优先：Hermes 的框线回复格式：╭─...╮ \n 内容 \n ╰─...╯
    m = re.search(r"╭[^\n]*\n(.*?)\n╰", out, re.S)
    if m:
        return m.group(1).strip()
    # -Q 模式：回复后跟 "↻ Resumed session ..." / session 尾注 → 截断
    for tail_marker in ["↻ Resumed session", "\nsession_id:", "Resume this session"]:
        i = out.find(tail_marker)
        if i > 0:
            out = out[:i]
    # 去掉 tirith 警告行
    lines = [ln for ln in out.splitlines() if "tirith" not in ln.lower() and not ln.strip().startswith("⚠")]
    return "\n".join(lines).strip()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 静默
        pass

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/bots":
            cfg = load_config()
            self._json(200, cfg)
        elif path.startswith("/assets/"):
            # 静态资源（Codex 生成的图片）
            import os
            rel = path.lstrip("/")
            fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)
            if os.path.isfile(fpath):
                ctype = "image/png" if fpath.endswith(".png") else "application/octet-stream"
                with open(fpath, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(body)
            else:
                self._json(404, {"error": "asset not found"})
        elif path == "/" or path == "/index.html":
            try:
                with open("/tmp/agri-dashboard/index.html", encoding="utf-8") as f:
                    html = f.read().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            except FileNotFoundError:
                self._json(500, {"error": "index.html not found"})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/chat":
            try:
                n = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                self._json(400, {"error": "bad json"})
                return
            bot = payload.get("bot", "")
            msg = (payload.get("message") or "").strip()
            bots = bot_index()
            if bot not in bots:
                self._json(404, {"error": "unknown bot: " + bot})
                return
            if not msg:
                self._json(400, {"error": "empty message"})
                return
            reply = bot_chat(bot, msg)
            self._json(200, {"bot": bot, "reply": reply})
        else:
            self._json(404, {"error": "not found"})


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    cfg = load_config()
    bots = cfg.get("bots", [])
    print(f"{cfg.get('company','农业总控看板')} 后端已启动: http://{args.host}:{args.port}")
    print("Bots:", ", ".join(f"{b.get('name')}({b.get('id')})" for b in bots))
    print("编辑同目录 bots.json 可增删/改名要连接的 bot；改后重启本服务即可。")
    srv.serve_forever()


if __name__ == "__main__":
    main()
