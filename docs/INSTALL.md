# 环境

## 安装gamma-launcher

https://github.com/Mord3rca/gamma-launcher

```cmd
winget find gammalauncher
名称          ID                       版本  源
----------------------------------------------------
GammaLauncher sebescudie.GammaLauncher 5.4.2 winget

winget install sebescudie.GammaLauncher
已找到 GammaLauncher [sebescudie.GammaLauncher] 版本 5.4.2
此应用程序由其所有者授权给你。
Microsoft 对第三方程序包概不负责，也不向第三方程序包授予任何许可证。
此包需要以下依赖项：
  - 程序包
      Microsoft.DotNet.DesktopRuntime.6
      Microsoft.VCRedist.2015+.x64
正在下载 https://github.com/sebescudie/GammaLauncher/releases/download/5.4.2/gammalauncher_5.4.2_win-x64_installer.exe
  ██████████████████████████████  14.6 MB / 14.6 MB
已成功验证安装程序哈希
正在启动程序包安装...
安装程序将请求以管理员身份运行。期待提示。
已成功安装
注意: Have a delightful patching day

```

启动

```
dir "%LOCALAPPDATA%\Programs" /s /b | findstr /i GammaLauncher
```

## 安装vvvv 8.0-01184

在gamma-launcher中选择安装