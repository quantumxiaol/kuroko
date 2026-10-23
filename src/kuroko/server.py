"""Kuroko bridge：本地 HTTP 服务，vvvv 轮询 /robot/pose 拿关节角。

启动：
    uv run python -m kuroko.server
    uv run python -m kuroko.chat          # 另一个终端里聊天

接口：
    GET  /health                      服务状态、有没有接 DeepSeek
    GET  /actions                     动作表
    GET  /robot/pose?d=2.3&st=calm    -> "j1,j2,...,j7" 七个浮点，vvvv 轮询这个
    GET  /robot/state                 当前动作/seq，给 HUD 或调试用
    POST /chat    {"text": "你好"}     -> 选动作 + 回复，然后开始播动作
    POST /chat    {"action": "wave"}   -> 直接播某个动作（调试用）
    POST /reset                        -> 回到蜷缩
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

from .actions import ACTIONS, BY_ID, FOLD, action_pose, format_pose
from .brain import Brain

load_dotenv()

STARTED_AT = time.monotonic()


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


class RobotState:
    """当前该摆什么姿态。动作是服务端插值的，vvvv 只负责跟随。"""

    def __init__(self, brain: Brain) -> None:
        self.brain = brain
        self._lock = threading.Lock()
        self.seq = 0
        self._action_id: str | None = None
        self._started = 0.0
        self.last_text = ""
        self.distance: float | None = None
        self.report_state = ""
        self.history: deque[tuple[str, str]] = deque(maxlen=8)

    def start(self, action_id: str, text: str = "") -> int:
        with self._lock:
            self.seq += 1
            self._action_id = action_id
            self._started = time.monotonic()
            self.last_text = text
            return self.seq

    def reset(self) -> None:
        with self._lock:
            self._action_id = None

    def snapshot(self) -> tuple[int, str, tuple[float, ...]]:
        with self._lock:
            seq, action_id, started = self.seq, self._action_id, self._started
        if action_id is None:
            return seq, "idle", FOLD
        action = BY_ID[action_id]
        t = time.monotonic() - started
        if t >= action.duration:
            return seq, "idle", FOLD
        return seq, action_id, action_pose(action, t)

    def remember(self, user: str, reply: str) -> None:
        with self._lock:
            self.history.append((user, reply))

    def chat(self, text: str, distance: float | None) -> dict:
        with self._lock:
            history = list(self.history)
        decision = self.brain.decide(text, distance=distance, history=history)
        seq = self.start(decision.action_id, text)
        self.remember(text, decision.say)
        log(f"你：{text}  ->  {decision.action_id} ({decision.source}) 说：{decision.say}")
        return {
            "ok": True,
            "reply": decision.say,
            "say": decision.say,
            "action": decision.action_id,
            "label": decision.action_label,
            "source": decision.source,
            "seq": seq,
            "pose": list(self.snapshot()[2]),
        }


def make_handler(state: RobotState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "KurokoBridge/0.1"
        # HTTP/1.0：每个请求独立连接。vvvv 轮询每次新开 TCP、响应一拿到就 RST，
        # 若用 HTTP/1.1 keep-alive，handler 傻等下一请求时会撞 ConnectionResetError 10054。
        protocol_version = "HTTP/1.0"

        # ---- 基础工具 ----

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            try:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                # 响应发完立即关连接，不给对端 RST keep-alive 等待的机会
                self.close_connection = True
            except (BrokenPipeError, ConnectionResetError):
                self.close_connection = True

        def _json(self, code: int, payload: dict | list) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(code, body, "application/json; charset=utf-8")

        def _text(self, code: int, text: str) -> None:
            self._send(code, text.encode("utf-8"), "text/plain; charset=utf-8")

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
                return data if isinstance(data, dict) else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}

        # ---- GET ----

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            if path == "/health":
                self._json(
                    200,
                    {
                        "ok": True,
                        "mode": state.brain.mode,
                        "actions": len(ACTIONS),
                        "seq": state.seq,
                        "uptime_s": round(time.monotonic() - STARTED_AT, 1),
                    },
                )
                return

            if path == "/actions":
                self._json(
                    200,
                    [
                        {
                            "id": a.id,
                            "label": a.label,
                            "description": a.description,
                            "duration": a.duration,
                        }
                        for a in ACTIONS
                    ],
                )
                return

            if path == "/robot/pose":
                if "d" in query:
                    try:
                        state.distance = float(query["d"][0])
                    except ValueError:
                        pass
                if "st" in query:
                    state.report_state = query["st"][0]
                _, _, joints = state.snapshot()
                self._text(200, format_pose(joints))
                return

            if path == "/robot/state":
                seq, action_id, joints = state.snapshot()
                self._json(
                    200,
                    {
                        "seq": seq,
                        "action": action_id,
                        "active": action_id != "idle",
                        "label": BY_ID[action_id].label if action_id in BY_ID else "待机",
                        "distance": state.distance,
                        "pose": list(joints),
                    },
                )
                return

            if path == "/":
                self._text(
                    200,
                    "Kuroko bridge\n"
                    "  GET  /robot/pose?d=2.3   当前 7 个关节角（vvvv 轮询）\n"
                    "  GET  /robot/state        当前动作/seq\n"
                    "  POST /chat               {\"text\":\"你好\"}\n"
                    "  GET  /actions            动作表\n"
                    "  GET  /health\n",
                )
                return

            self._json(404, {"ok": False, "error": "not found"})

        # ---- POST ----

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path

            if path == "/reset":
                state.reset()
                self._json(200, {"ok": True, "action": "idle"})
                return

            if path == "/chat":
                data = self._body()
                action_id = data.get("action")
                if action_id:
                    if action_id not in BY_ID:
                        self._json(400, {"ok": False, "error": f"unknown action {action_id}"})
                        return
                    action = BY_ID[action_id]
                    seq = state.start(action_id, "(direct)")
                    log(f"直接播放：{action_id}")
                    self._json(
                        200,
                        {
                            "ok": True,
                            "reply": action.say,
                            "say": action.say,
                            "action": action_id,
                            "label": action.label,
                            "source": "direct",
                            "seq": seq,
                            "pose": list(state.snapshot()[2]),
                        },
                    )
                    return

                text = str(data.get("text") or "").strip()
                if not text:
                    self._json(400, {"ok": False, "error": "text is required"})
                    return
                distance = data.get("distance")
                if distance is None:
                    distance = state.distance
                else:
                    try:
                        distance = float(distance)
                    except (TypeError, ValueError):
                        distance = None
                self._json(200, state.chat(text, distance))
                return

            self._json(404, {"ok": False, "error": "not found"})

        def log_message(self, fmt: str, *args) -> None:  # noqa: A003
            # 自己的日志已经够用，屏蔽 BaseHTTPRequestHandler 的默认逐请求输出
            return

    return Handler


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Kuroko dialogue bridge")
    parser.add_argument("--host", default=os.getenv("BRIDGE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("BRIDGE_PORT", "8765")))
    args = parser.parse_args(argv)

    brain = Brain()
    state = RobotState(brain)
    httpd = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    httpd.daemon_threads = True

    log(f"Kuroko bridge on http://{args.host}:{args.port}  (llm={brain.mode}, {len(ACTIONS)} actions)")
    if brain.mode == "offline":
        log("没有 DEEPSEEK_API_KEY：用关键词路由，先跑通链路；填 .env 后重启即接真模型")
    log("vvvv 轮询：GET /robot/pose   终端聊天：uv run python -m kuroko.chat")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("bye")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
