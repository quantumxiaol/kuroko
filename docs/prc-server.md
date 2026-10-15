# PRC Server（third_service/prc-server）

Parametric Robot Control 服务器：机器人仿真、运动学、碰撞检查、程序生成，对外暴露 gRPC API 和 web UI（默认 `https://127.0.0.1:5001`，同一端口）。

**闭源软件**（Johannes Braumann / Robots in Architecture），不进 git，`third_service/` 已在 `.gitignore` 中。

## 依赖

- .NET 10 运行时（`Microsoft.AspNetCore.App`）：https://dotnet.microsoft.com/download/dotnet/10.0
- 跨平台：Windows / macOS / Linux 均可运行

## 来源（三选一）

### 1. 本机 nuget 缓存（最快）

安装过 VL.PRC 的机器上直接复制：

```powershell
robocopy "$env:USERPROFILE\.nuget\packages\prc.server.bundle\1.749.0\tools\server" "third_service\prc-server" /E
```

### 2. nuget.org 直接下载（可 wget，无需登录）

`.nupkg` 就是 zip，下载后解压取 `tools/server`：

```bash
curl -fLO https://www.nuget.org/api/v2/package/PRC.Server.Bundle/1.749.0
unzip -o PRC.Server.Bundle.1.749.0 -d prc-bundle-tmp   # 或 mv 成 .zip 后用资源管理器解压
cp -r prc-bundle-tmp/tools/server third_service/prc-server
```

### 3. 官方安装包（需要 portal 账号）

https://portal.robotsinarchitecture.org/download

## 版本

当前固定为 **1.749.0**。gRPC 客户端（`proto/` 里的 proto 文件、`PRC.GRPC` nuget）必须和服务器版本匹配，升级时要一起升。

## 授权

启动后在 web UI 的 **SYSTEM** 页登录 portal 账号激活 license。license 与本机其他 PRC Server 安装共享。

- Community（免费）：仿真 + 免费驱动；外链轴和在线驱动不可用
- Regular Membership：全部功能（本机当前状态）

## 启动

```cmd
scripts\start-prc-server.cmd
```

支持 `PRC_SERVER_HOME` 环境变量指向其他安装位置。

## 证书

浏览器首次访问有证书警告。消除方法：把 `Certificates/PRCRootCertificate.crt` 导入 Windows"受信任的根证书颁发机构"。gRPC 客户端用 `Certificates/PRCRootCertificate.pem` 作为 root CA 即可正常验证（服务器证书 SAN 含 `127.0.0.1`）。
