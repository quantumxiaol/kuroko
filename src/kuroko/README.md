# kuroko — 对话到机械臂的本地服务

`src/kuroko/` 是 `kuroko` 包（和 `src/prc_client/` 平级）。文字链路：

```bash
# 终端 A：起服务（二选一）
uv run python -m kuroko.server
uv run kuroko-bridge

# 终端 B：聊天（二选一）
uv run python -m kuroko.chat --pose
uv run kuroko-chat --pose
```

`.env` 里填 `DEEPSEEK_API_KEY` 后重启服务就走真模型；没有 key 时用关键词路由，
链路照样能跑通（`llm=offline`）。

## 局域网测试（vvvv 在另一台 Windows 上）

```bash
uv run kuroko-bridge --host 0.0.0.0      # 默认只绑 127.0.0.1
ipconfig getifaddr en0                    # 拿本机 IP，比如 10.20.247.184
```

Windows 上用 `http://10.20.247.184:8765/robot/pose`。macOS 第一次会弹防火墙允许提示。
正式布展时把服务挪到 Windows 本机跑，URL 再换回 `127.0.0.1`。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/robot/pose?d=<米>` | 返回 `j1,...,j7` 七个浮点，vvvv 每 0.2 s 拉一次 |
| GET | `/robot/state` | 当前动作、seq、距离，给 HUD/调试 |
| POST | `/chat` | `{"text":"..."}` 聊天；`{"action":"wave"}` 直接播 |
| GET | `/actions` | 动作表 |
| POST | `/reset` | 回到蜷缩 |
| GET | `/health` | 服务状态、llm=deepseek/offline |

返回值是服务端按关键帧插值的**当前**姿态，所以动作序列、速度、缓动都在 Python 里改，
vvvv 不用为每个新动作改 patch。

## 动作

见 `src/kuroko/actions.py`。全部是 `mimosa2.vl` 里已验证的 fold 姿态
`(-1, -110, 90, 20, 30, 40, 0)` 加小偏移，共 10 个：`shy_fold / peek /
dance_sway / dance_bounce / bow / reach / point_mushroom / retreat / shiver / wave`。
`AMPLITUDE` 是全局幅度开关；改动作只改这个文件。

## 下一步

- `/asr`：接收 wav，调 MiMo ASR
- `/tts`：MiMo TTS，服务端直接播放
- `GET /`：一个按住说话的网页（push-to-talk），比 VAD 稳
