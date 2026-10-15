@echo off
setlocal

rem PRC_SERVER_HOME can point to another PRC Server installation
if "%PRC_SERVER_HOME%"=="" set "PRC_SERVER_HOME=%~dp0..\third_service\prc-server"

if not exist "%PRC_SERVER_HOME%\PRC.Server.dll" (
    echo [start-prc-server] PRC.Server.dll not found in "%PRC_SERVER_HOME%"
    echo [start-prc-server] Copy it from %%USERPROFILE%%\.nuget\packages\prc.server.bundle\^<version^>\tools\server
    echo [start-prc-server] or download from https://portal.robotsinarchitecture.org/download
    exit /b 1
)

rem ASP.NET resolves wwwroot/appsettings relative to the working directory
cd /d "%PRC_SERVER_HOME%"
echo [start-prc-server] Starting PRC Server from %CD% ...
echo [start-prc-server] Web UI: https://127.0.0.1:5001 ^(gRPC on the same port^)
dotnet PRC.Server.dll %*
