"""动作库：7 轴关节角，全部相对 mimosa2.vl 里已验证的 fold 姿态做小偏移。

vlsrc/mimosa2.vl 的 MimosaMove 就是这套关节空间：
    Fold A1..A7 = -1, -110, 90, 20, 30, 40, 0 (deg)
    openness 0 = 蜷缩，1 = 跳舞（fold + 正弦）
所以新动作不另起坐标系，只在 fold 上加减几度到几十度，保证仿真里不出现
奇怪的姿态，也方便视觉上直接对比"确实换了动作"。

每个动作是一串关键帧 (秒, 7 关节角)，服务端按时间插值成连续姿态，
vvvv 只要每 0.1~0.2 秒来取一次当前姿态即可。
"""

from __future__ import annotations

from dataclasses import dataclass

# mimosa2.vl / MimosaGarden.vl 里的 Fold A1..A7
FOLD: tuple[float, ...] = (-1.0, -110.0, 90.0, 20.0, 30.0, 40.0, 0.0)

# 所有动作幅度总开关：1.0 = 原样，0.5 = 偏移减半（仿真里觉得动作太大就调这个）
AMPLITUDE = 1.0


def pose(*delta: float) -> tuple[float, ...]:
    """fold 姿态 + 每轴偏移（度），偏移受 AMPLITUDE 缩放。"""
    return tuple(round(f + d * AMPLITUDE, 2) for f, d in zip(FOLD, delta))


# 几个基础姿态，动作都在它们之间走
PEEK = pose(0, 30, -18, -4, -10, 6, 0)  # 探出去偷看
OPEN = pose(10, 45, -52, 6, -12, 0, 20)  # 展开，跳舞
OPEN2 = pose(-6, 36, -36, -6, -20, 12, -20)  # 展开的另一侧
BOW = pose(0, 55, -24, 0, 10, 0, 0)  # 前倾鞠躬
REACH = pose(0, 64, -60, -12, 20, 8, 0)  # 伸向对方
POINT = pose(0, 40, -34, 8, 42, -12, 32)  # 指向一侧
RETREAT = pose(0, -14, 14, 0, 20, 8, 0)  # 往后缩
WAVE_UP = pose(0, 34, -30, 0, 4, 0, 38)  # 抬起末端
WAVE_DOWN = pose(0, 34, -30, 0, 4, 0, -38)  # 末端摆到另一侧


def _shiver_keys() -> tuple[tuple[float, tuple[float, ...]], ...]:
    """原地高频小抖：A2/A4/A6 反相，1.44 秒六个来回。"""
    keys: list[tuple[float, tuple[float, ...]]] = [(0.0, FOLD)]
    for i in range(6):
        s = 1 if i % 2 == 0 else -1
        keys.append((round(0.12 + i * 0.24, 2), pose(0, 2.5 * s, 0, -2.0 * s, 0, 5.0 * s, 0)))
    keys.append((1.8, FOLD))
    return tuple(keys)


@dataclass(frozen=True)
class Action:
    id: str
    label: str
    description: str
    keys: tuple[tuple[float, tuple[float, ...]], ...]
    say: str

    @property
    def duration(self) -> float:
        return self.keys[-1][0]


ACTIONS: tuple[Action, ...] = (
    Action(
        id="shy_fold",
        label="害羞蜷缩",
        description="整个缩起来，末端轻轻发抖。人靠得太近、被吓到、被说害羞时用。",
        keys=((0.0, FOLD), (0.5, pose(0, 4, 2, 0, 6, 6, 0)), (1.4, FOLD)),
        say="呜……别靠这么近……",
    ),
    Action(
        id="peek",
        label="探头偷看",
        description="从蜷缩里慢慢探出一点，偷偷看对方，又缩回去。",
        keys=((0.0, FOLD), (0.9, PEEK), (2.4, PEEK), (3.2, FOLD)),
        say="……你还在吗？",
    ),
    Action(
        id="dance_sway",
        label="摇摆跳舞",
        description="大幅左右摇摆地跳舞，最像原来 patch 里的 dance 状态。",
        keys=((0.0, FOLD), (0.6, OPEN), (1.6, OPEN2), (2.6, OPEN), (3.6, FOLD)),
        say="你看我跳得怎么样～",
    ),
    Action(
        id="dance_bounce",
        label="上下蹦跳",
        description="更快、更小的上下弹跳，显得兴奋。",
        keys=(
            (0.0, FOLD),
            (0.35, OPEN),
            (0.75, FOLD),
            (1.15, OPEN),
            (1.55, FOLD),
            (1.95, OPEN),
            (2.35, FOLD),
        ),
        say="嘿！嘿！",
    ),
    Action(
        id="bow",
        label="鞠躬",
        description="向前倾身鞠躬，用来道谢、打招呼、说再见。",
        keys=((0.0, FOLD), (0.8, BOW), (1.8, BOW), (2.6, FOLD)),
        say="谢谢你来看我。",
    ),
    Action(
        id="reach",
        label="伸手",
        description="把末端伸向对方，像要握手、讨摸。人太近时不要用。",
        keys=((0.0, FOLD), (0.9, REACH), (2.6, REACH), (3.4, FOLD)),
        say="要……要握手吗？",
    ),
    Action(
        id="point_mushroom",
        label="指蘑菇",
        description="转向一侧，指向草地上的蘑菇，像在介绍自己的朋友。",
        keys=((0.0, FOLD), (0.8, POINT), (2.6, POINT), (3.4, FOLD)),
        say="那边有朵蘑菇。",
    ),
    Action(
        id="retreat",
        label="后退缩",
        description="往后缩、躲远一点，比 shy_fold 更明显的退让。",
        keys=((0.0, FOLD), (0.6, RETREAT), (2.0, RETREAT), (2.8, FOLD)),
        say="我、我退后一点……",
    ),
    Action(
        id="shiver",
        label="发抖",
        description="原地快速发抖，冷、害怕、被吓到的时候用。",
        keys=_shiver_keys(),
        say="（抖）……",
    ),
    Action(
        id="wave",
        label="挥手",
        description="抬起末端左右挥手，打招呼、道别。",
        keys=(
            (0.0, FOLD),
            (0.45, WAVE_UP),
            (0.72, WAVE_DOWN),
            (0.99, WAVE_UP),
            (1.26, WAVE_DOWN),
            (1.53, WAVE_UP),
            (1.95, pose(0, 30, -26, 0, 2, 0, 4)),
            (2.4, FOLD),
        ),
        say="你好呀。",
    ),
)

BY_ID: dict[str, Action] = {a.id: a for a in ACTIONS}


def _ease(u: float) -> float:
    """smoothstep，让关键帧之间不是生硬的匀速。"""
    return u * u * (3.0 - 2.0 * u)


def action_pose(action: Action, t: float) -> tuple[float, ...]:
    """动作在第 t 秒的姿态（线性 + ease 插值）。"""
    keys = action.keys
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = _ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            return tuple(round(a + (b - a) * u, 2) for a, b in zip(p0, p1))
    return keys[-1][1]


def format_pose(joints: tuple[float, ...]) -> str:
    return ",".join(f"{j:.2f}" for j in joints)


def catalog_text() -> str:
    """给 LLM 看的动作表。"""
    return "\n".join(f"- {a.id}（{a.label}）：{a.description}" for a in ACTIONS)


if __name__ == "__main__":  # uv run python -m kuroko.actions
    print(f"{'id':<16}{'label':<10}{'dur':>5}  pose@mid")
    for action in ACTIONS:
        mid = action_pose(action, action.duration / 2)
        print(f"{action.id:<16}{action.label:<10}{action.duration:>5.2f}  {format_pose(mid)}")
