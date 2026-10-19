"""Repair dependency declarations of a .vl file that was saved outside its package.

vvvv help patches inside a nuget package reference their library document with a
RELATIVE DocumentDependency (e.g. VL.PRC's help uses "../VL.PRC.vl", Bunraku's
"../../VL.Bunraku.vl"). Once the patch is saved anywhere else, that path no longer
resolves and vvvv shows the "missing dependency" dialog on open.

The fix: drop the relative DocumentDependency and rely on the NugetDependency
instead — the nuget package ships the very same document, so every node reference
still resolves, on any machine that has the pack installed.

Usage:
    uv run python scripts/fix_vl_dependencies.py "path/to/YourPatch.vl"
    uv run python scripts/fix_vl_dependencies.py "path/to/YourPatch.vl" --dry-run

Known document -> nuget mapping:
    VL.PRC.vl     -> VL.PRC (any installed version)
    VL.Bunraku.vl -> VL.Bunraku (any installed version)
"""

import argparse
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDS_PY = ROOT / ".agent/skills/vvvv-fileformat/scripts/vl-patch-manipulator/src/vl_patch_manipulator/ids.py"

spec = importlib.util.spec_from_file_location("vl_ids", IDS_PY)
vl_ids = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vl_ids)

DOC_TO_NUGET = {
    "VL.PRC.vl": "VL.PRC",
    "VL.Bunraku.vl": "VL.Bunraku",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path: Path = args.file.resolve()
    if not path.exists():
        print(f"file not found: {path}")
        return 1

    text = path.read_text(encoding="utf-8-sig")
    dir_ = path.parent
    changes: list[str] = []

    def doc_dep_repl(match: re.Match) -> str:
        tag = match.group(0)
        location = match.group("location")
        loc_path = Path(location.replace("/", "\\"))
        resolved = loc_path if loc_path.is_absolute() else (dir_ / location)
        doc_name = Path(location).name
        nuget = DOC_TO_NUGET.get(doc_name)
        # A path that points into a nuget package folder is machine-local:
        # replace it with the nuget reference so the file opens anywhere.
        in_nuget_cache = bool(re.search(r"[\\/]\.nuget[\\/]packages[\\/]", str(resolved), re.I))
        if nuget is not None and (in_nuget_cache or not resolved.exists()):
            version = None
            m = re.search(rf"[\\/]\.nuget[\\/]packages[\\/][^\\/]+[\\/]([^\\/]+)[\\/]", str(resolved), re.I)
            if m and in_nuget_cache:
                version = m.group(1)
            changes.append(f"REMOVE DocumentDependency {location} (rely on nuget {nuget}"
                           + (f" {version}" if version else "") + ")")
            if version:
                nuget_versions[nuget] = version
            return ""
        if resolved.exists():
            return tag  # relative path still resolves outside any package -> keep
        changes.append(f"KEPT unresolved DocumentDependency (no known nuget for {doc_name}): {location}")
        return tag

    nuget_versions: dict[str, str] = {}

    text = re.sub(r'<DocumentDependency[^>]*Location="(?P<location>[^"]+)"[^>]*/>', doc_dep_repl, text)

    # ensure the nuget dependencies exist
    for doc_name, nuget in DOC_TO_NUGET.items():
        if not any(nuget in c for c in changes if "REMOVE" in c and nuget in c):
            continue
        if re.search(rf'<NugetDependency[^>]*Location="{re.escape(nuget)}"', text):
            changes.append(f"NugetDependency {nuget} already present")
        else:
            version = nuget_versions.get(nuget)
            ver = f' Version="{version}"' if version else ""
            dep = f'  <NugetDependency Id="{vl_ids.new_vl_id()}" Location="{nuget}"{ver} />\n'
            # insert right after the opening <Document ...> line
            text = re.sub(r'(<Document[^>]*>\n)', r"\1" + dep, text, count=1)
            changes.append(f"ADD NugetDependency {nuget}" + (f" {version}" if version else ""))

    if not changes:
        print("nothing to fix: all dependencies resolve from this location")
        return 0

    for c in changes:
        print(" ", c)
    if args.dry_run:
        print("dry run, file not modified")
        return 0

    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"fixed: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
