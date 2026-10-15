#!/usr/bin/env bash
# Start the PRC Server (gRPC + web UI on https://127.0.0.1:5001).
# Override the installation location with PRC_SERVER_HOME.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRC_SERVER_HOME="${PRC_SERVER_HOME:-$SCRIPT_DIR/../third_service/prc-server}"

if [ ! -f "$PRC_SERVER_HOME/PRC.Server.dll" ]; then
    echo "[start-prc-server] PRC.Server.dll not found in $PRC_SERVER_HOME" >&2
    echo "[start-prc-server] Copy it from ~/.nuget/packages/prc.server.bundle/<version>/tools/server" >&2
    echo "[start-prc-server] or download from https://portal.robotsinarchitecture.org/download" >&2
    exit 1
fi

# ASP.NET resolves wwwroot/appsettings relative to the working directory
cd "$PRC_SERVER_HOME"
echo "[start-prc-server] Starting PRC Server from $PWD ..."
echo "[start-prc-server] Web UI: https://127.0.0.1:5001 (gRPC on the same port)"
exec dotnet PRC.Server.dll "$@"
