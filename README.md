# Kuroko

含羞草机器人互动装置：有人靠近时，机械臂害羞地蜷缩、微微发抖；没人时，它在草地上对着蘑菇自娱自乐地跳舞。

A shy robot installation: when someone approaches, the arm folds into itself and trembles; when alone, it dances among the mushrooms on the lawn.

基于 vvvv gamma + VL.Bunraku（机器人实时运动学/仿真/渲染）+ Intel RealSense D435i（深度感知），面向 KUKA 机械臂（仿真：KR13 / LBR iiwa；真机走 PRC Server）。

## 目录结构

```
vlsrc/          vvvv patch（按演进顺序，越往后越完整）
scripts/        生成/修复/合并这些 patch 的 Python 脚本 + PRC 工具链
assert/         模型与贴图（顶点色蘑菇 glb、草地/天空盒 png）
proto/          PRC gRPC API 定义（来自 PRC.Integrations）
src/prc_client/ 生成的 Python gRPC 客户端
third_party/    VL.Bunraku submodule
third_service/  PRC Server（闭源，gitignored，安装见 docs/prc-server.md）
docs/           安装与环境文档
```

## vlsrc/ 里的 patch

| 文件 | 内容 |
|---|---|
| `TCPRotate.vl` | 起点：阈值 IOBox 驱动单台机械臂绕 TCP 旋转 |
| `MimosaVision_MediaPipe.vl` | 视觉 v1：MediaPipe 姿态检测 → 躯干高度反推距离 |
| `MimosaVision_Depth.vl` | 视觉 v2：D435i 深度图探针排 → 最近距离（无识别环节，推荐） |
| `ShroomViewer.vl` | 最小模型查看器：顶点色蘑菇（FileModel → 顶点色 ShaderFX → PBRMaterial） |
| `ShroomScene.vl` | 场景实验：3 个蘑菇 + 圆柱地面 + 灯光 |
| `MimosaFinal.vl` | 完整单体：深度感知 → 害羞/跳舞行为 + 自动运镜 |
| `MimosaGarden.vl` | **最终版**：上面的全部 + 草地/天空盒/蘑菇场景 |

## 运行环境

- vvvv gamma 8.0（安装见 [docs/INSTALL.md](./docs/INSTALL.md)）
- vvvv packs：`VL.Bunraku` 1.0.3、`VL.PRC` 1.0.0-rc1、`VL.MediaPipe` 0.11.0-alpha、`VL.Devices.RealSense` 1.11.0（+ 其依赖 `VL.Skia3d`）、`VL.CEF.Stride`
  - 装不上时可用 `uv run python scripts/stage_nuget.py <包名> <版本>` 直接塞进 nuget 缓存
- Intel RealSense D435i（USB 3 口）
- Python 侧（PRC gRPC 客户端等）：`uv sync`

## 开发约定

- `.vl` 文件由 `scripts/` 里的生成器产出/修复，手工在 vvvv 里调整后 Ctrl+S 落盘
- `*.pc` 是 vvvv 编译缓存，不进 git
- vvvv gamma **没有** beta 时代的自动 Spread 运算，集合要显式处理
- 顶点色模型渲染需要 `vlsrc/shaders/VertexColor_ShaderFX.sdsl`（patch 旁 `shaders/` 目录约定），首次加入需重启 vvvv

skills 来自 [vvvv-skills](https://github.com/tebjan/vvvv-skills)
