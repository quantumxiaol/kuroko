"""终端聊天客户端：每敲一句话，服务端选动作、机械臂跟着动。

    uv run python -m kuroko.chat
    uv run python -m kuroko.chat --pose     # 顺便打印当前关节角
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()


def _post(url: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8").strip()


def _action_ids(base: str) -> set[str]:
    try:
        return {a["id"] for a in json.loads(_get(f"{base}/actions"))}
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, TypeError):
        return set()


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Kuroko terminal chat")
    parser.add_argument(
        "--url", default="http://127.0.0.1:8765", help="bridge 地址，默认 http://127.0.0.1:8765"
    )
    parser.add_argument("--pose", action="store_true", help="每轮后打印 vvvv 会收到的姿态包")
    args = parser.parse_args(argv)
    base = args.url.rstrip("/")

    try:
        health = json.loads(_get(f"{base}/health"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"连不上 bridge（{base}）：{exc}", file=sys.stderr)
        print("先在另一个终端跑：uv run python -m kuroko.server", file=sys.stderr)
        return 1

    action_ids = _action_ids(base)
    print(f"Kuroko bridge 已连接（llm={health['mode']}，{health['actions']} 个动作）")
    print(f"动作：{', '.join(sorted(action_ids))}")
    print("输入一句话回车发送；直接敲动作名可以跳过模型直接播；Ctrl-D 退出。\n")

    while True:
        try:
            line = input("你 > ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break
        if not line:
            continue

        payload = {"action": line} if line in action_ids else {"text": line}
        try:
            result = _post(f"{base}/chat", payload)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            print(f"[{exc.code}] {detail}", file=sys.stderr)
            continue
        except urllib.error.URLError as exc:
            print(f"请求失败：{exc}", file=sys.stderr)
            continue

        print(f"它  > {result['reply']}")
        print(
            f"      [{result['action']}] {result['label']}  "
            f"({result['source']}, seq={result['seq']})"
        )
        if args.pose:
            try:
                time.sleep(0.6)  # 动作刚起步时还是蜷缩姿态，等一下再看
                print(f"      pose {_get(f'{base}/robot/pose')}")
            except urllib.error.URLError:
                pass
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
