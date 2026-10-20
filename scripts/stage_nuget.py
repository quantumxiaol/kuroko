"""Pre-stage nuget packages into the global cache (~/.nuget/packages) for vvvv.

vvvv resolves NugetDependency from the global nuget cache folder layout:
    <id-lowercase>/<version>/  containing: extracted nupkg files, <id>.nuspec,
    <id>.<version>.nupkg, <id>.<version>.nupkg.sha512, .nupkg.metadata

Usage: uv run python scripts/stage_nuget.py VL.Devices.RealSense 1.11.0 [more pairs...]
"""

import base64
import hashlib
import json
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

CACHE = Path.home() / ".nuget" / "packages"


def stage(package_id: str, version: str) -> None:
    pid = package_id.lower()
    dest = CACHE / pid / version
    if (dest / ".nupkg.metadata").exists():
        print(f"already staged: {package_id} {version}")
        return
    url = f"https://www.nuget.org/api/v2/package/{package_id}/{version}"
    print(f"downloading {url}")
    tmp = Path(tempfile.mkdtemp())
    nupkg = tmp / "pkg.nupkg"
    urllib.request.urlretrieve(url, nupkg)
    data = nupkg.read_bytes()
    sha512 = base64.b64encode(hashlib.sha512(data).digest()).decode()

    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(nupkg) as z:
        z.extractall(dest)
    (dest / f"{pid}.{version}.nupkg").write_bytes(data)
    (dest / f"{pid}.{version}.nupkg.sha512").write_text(sha512)
    (dest / ".nupkg.metadata").write_text(json.dumps({
        "version": 2,
        "contentHash": sha512,
        "source": "https://api.nuget.org/v3/index.json",
    }))
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"staged: {dest}")


def main() -> int:
    args = sys.argv[1:]
    if len(args) % 2 or not args:
        print("usage: stage_nuget.py <PackageId> <Version> [<PackageId> <Version>...]")
        return 1
    for i in range(0, len(args), 2):
        stage(args[i], args[i + 1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
