"""对话 → 动作：DeepSeek function call，没 key 时退化成关键词路由。

生产环境里 LLM 只负责"选哪个动作 + 说哪句话"，永远不产生关节角；
关节角由 bridge.actions 里的固定动作表给出。
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass

from dotenv import load_dotenv

from .actions import ACTIONS, BY_ID, catalog_text

load_dotenv()

MAX_SAY = 18  # 汉字数上限，TTS 一句话别太长

SYSTEM_PROMPT = """\
你是 Kuroko，一台立在草地上、两米外的机械臂装置。你像含羞草，也像胆小菇：
怕生、容易缩起来，但其实很好奇，喜欢有人陪。
对方刚对你说了一句话，你要选一个动作回应，并同时说一句话。

规则：
1. 只能通过 perform_action 工具回应。
2. action 必须从下面的动作表里选一个，不要发明新的。
3. say 是你说出口的一句话，口语、短，不超过 18 个汉字；不要解释，不要提 AI、模型、工具。
4. 对方靠得近、吓你、让你害羞 → shy_fold / retreat / shiver。
5. 对方打招呼、道谢、道别 → wave / bow / peek。
6. 对方让你表演、夸你 → dance_sway / dance_bounce。
7. 对方提到蘑菇、旁边的东西 → point_mushroom。
8. 对方想靠近、想摸你 → reach（但当前距离小于 1.2 米时改用 shy_fold）。

动作表：
{catalog}
"""


@dataclass
class Decision:
    action_id: str
    say: str
    source: str  # deepseek | offline | offline-fallback

    @property
    def action_label(self) -> str:
        return BY_ID[self.action_id].label


def _tool(strict: bool) -> dict:
    function = {
        "name": "perform_action",
        "description": "让机械臂做一个动作，并同时说一句话。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [a.id for a in ACTIONS],
                    "description": "动作 id，必须来自动作表。",
                },
                "say": {
                    "type": "string",
                    "description": f"同时说出口的一句话，不超过 {MAX_SAY} 个汉字。",
                },
                "intensity": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "动作幅度，默认 0.8。",
                },
            },
            "required": ["action", "say", "intensity"],
        },
    }
    if strict:
        function["strict"] = True
        function["parameters"]["additionalProperties"] = False
    return {"type": "function", "function": function}


def _clip_say(text: str) -> str:
    text = " ".join(str(text).split())
    return text[:MAX_SAY]


class Brain:
    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.strict = os.getenv("DEEPSEEK_STRICT", "0") == "1"
        self.base_url = f"{base}/beta" if self.strict else base
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
        self._client = None

    @property
    def mode(self) -> str:
        return "deepseek" if self.api_key else "offline"

    def decide(
        self,
        text: str,
        distance: float | None = None,
        state: str | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> Decision:
        if not self.api_key:
            return self._offline(text)
        try:
            return self._deepseek(text, distance, state, history or [])
        except Exception as exc:  # noqa: BLE001 - 任何网络/解析问题都要能降级
            print(f"[brain] deepseek failed ({exc!r}) -> offline", flush=True)
            decision = self._offline(text)
            decision.source = "offline-fallback"
            return decision

    # ---- DeepSeek ----

    def _client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=10.0)
        return self._client

    def _deepseek(
        self,
        text: str,
        distance: float | None,
        state: str | None,
        history: list[tuple[str, str]],
    ) -> Decision:
        system = SYSTEM_PROMPT.format(catalog=catalog_text())
        lines = [f"对方说：「{text}」"]
        if distance is not None:
            lines.append(f"当前距离：{distance:.2f} 米")
        if state:
            lines.append(f"装置状态：{state}")
        if history:
            recent = "；".join(f"对方：{u} / 你：{a}" for u, a in history[-3:])
            lines.append(f"最近对话：{recent}")

        response = self._client().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": "\n".join(lines)},
            ],
            tools=[_tool(self.strict)],
            tool_choice={"type": "function", "function": {"name": "perform_action"}},
            temperature=0.9,
            max_tokens=200,
            extra_body={"thinking": {"type": "disabled"}},
        )

        message = response.choices[0].message
        if message.tool_calls:
            raw = message.tool_calls[0].function.arguments
            data = json.loads(raw)
            action_id = data.get("action")
            if action_id not in BY_ID:
                raise ValueError(f"unknown action {action_id!r}")
            say = _clip_say(data.get("say") or BY_ID[action_id].say)
            return Decision(action_id=action_id, say=say, source="deepseek")

        # 模型没调工具：用它的话 + 本地路由的动作兜底
        decision = self._offline(text)
        if message.content:
            decision.say = _clip_say(message.content)
        decision.source = "offline-fallback"
        return decision

    # ---- 没有 key 时的关键词路由 ----

    def _offline(self, text: str) -> Decision:
        table = (
            ("dance_bounce", ("蹦", "弹", "兴奋", "high", "跳高")),
            ("dance_sway", ("跳舞", "跳", "表演", "来一个", "节目", "摇")),
            ("shy_fold", ("害羞", "别过来", "不要", "怕", "吓", "躲开", "讨厌")),
            ("shiver", ("冷", "抖", "害怕", "瑟瑟")),
            ("retreat", ("远点", "退", "走开", "别碰")),
            ("reach", ("握手", "摸", "靠近", "过来", "抱")),
            ("point_mushroom", ("蘑菇", "那边", "旁边", "看")),
            ("bow", ("谢谢", "再见", "拜拜", "鞠躬", "辛苦")),
            ("peek", ("偷看", "藏", "躲", "还在")),
            ("wave", ("你好", "嗨", "hello", "hi", "早上好", "晚上好")),
        )
        low = text.lower()
        for action_id, words in table:
            if any(w in low for w in words):
                action = BY_ID[action_id]
                return Decision(action_id=action_id, say=action.say, source="offline")

        action = random.choice([BY_ID["peek"], BY_ID["wave"], BY_ID["dance_sway"]])
        return Decision(action_id=action.id, say=action.say, source="offline")
