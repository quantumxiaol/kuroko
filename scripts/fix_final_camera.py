"""Fix the orbit-camera binary switch in vlsrc/MimosaFinal.vl.

Problem: the `<=` node compared two CONSTANTS (1 <= 0.96), so the camera
distance was pinned at the far value forever.

Fix (binary switch, as chosen):
- Expose the measured depth distance out of the MimosaMove process as a new
  "distance out" output pin (definition + instance).
- `<=` now compares (real distance) <= (threshold pad, 1.4 m).
- Its result drives the Switch condition DIRECTLY (NOT removed from the chain;
  the "robot is happy" display pad keeps its feed).
- Switch values swapped so: distance <= 1.4 -> far view (1.75), else -> near view (1.0).

Run:  uv run --with lxml python scripts/fix_final_camera.py
"""

import importlib.util
import sys
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
IDS_PY = ROOT / ".agent/skills/vvvv-fileformat/scripts/vl-patch-manipulator/src/vl_patch_manipulator/ids.py"

spec = importlib.util.spec_from_file_location("vl_ids", IDS_PY)
vl_ids = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vl_ids)

FILE = ROOT / "vlsrc" / "MimosaFinal.vl"

# element ids (from MimosaFinal.vl)
MM_UPDATE_PATCH = "QZOzsnvywKfLiVuOVOEjr1"      # MimosaMove definition Update fragment
MM_INSTANCE = "J30HaKF2TXPOuUVCMmpVsP"          # MimosaMove instance node
VISION_DAMPER_POS = "UgFbknm42h2QcqjUoCJYkg"    # grafted vision Damper Position pin
LE_INPUT = "CiWw3ttgSlgPTRt4wpd3Tt"             # <= Input
LE_INPUT2 = "HmcvuqSa1FtM0ttvQuDCxv"            # <= Input 2 (threshold pad feeds it)
LE_RESULT = "BT8nnC310HAPXBWcbt2Teu"            # <= Result
SWITCH_CONDITION = "EM9iwA04gV2OSm5dsxHAM5"
SWITCH_INPUT = "JXio3Vfe1FfLJDydKDliR0"
SWITCH_INPUT2 = "K5hSN623CO2L1i8MqAfjnA"
PAD_FAR = "UP6x2aDmfY8QS4XNaEM7nw"              # 1.75
PAD_NEAR = "Su64pxl9JbNNFBwWWaVibV"             # 1.0
PAD_THRESHOLD = "CfHcmqBbVGJM6UhS4eByEk"        # currently 0.96 -> becomes 1.4

DELETE_LINKS = [
    "CGIoANaGk5cNoiVa7e8ZXL",  # const pad -> <=.Input
    "KOdQpFM5mljMfZ5CG0FdHr",  # NOT.Output -> Switch.Condition
    "PHkbP3gemZtL0HyF7nnOJm",  # 1.75 -> Switch.Input
    "R2pXNfK8cVaQJSPVmj9pGj",  # 1.0  -> Switch.Input 2
]

ADD_LINKS_APP = [
    # (source, sink) — in the Application inner patch
    (LE_RESULT, SWITCH_CONDITION),      # shy flag drives the switch directly
    (PAD_FAR, SWITCH_INPUT2),           # True (shy) -> far view
    (PAD_NEAR, SWITCH_INPUT),           # False (dance) -> near view
]


def find_by_id(root, eid):
    for el in root.iter():
        if el.get("Id") == eid:
            return el
    return None


def main() -> int:
    parser = etree.XMLParser(remove_blank_text=False)
    doc = etree.parse(str(FILE), parser)
    root = doc.getroot()

    # the Application inner patch (contains the switch / <= / NOT nodes)
    app_inner = None
    for node in root.iter("Node"):
        if node.get("Name") == "Application":
            app_inner = node.find("Patch")
            break
    if app_inner is None:
        print("ERROR: Application patch not found")
        return 1

    # 1. delete stale links
    for parent in root.iter():
        if parent.tag in ("Patch",):
            for l in list(parent.findall("Link")):
                if l.get("Id") in DELETE_LINKS:
                    parent.remove(l)
                    print(f"deleted link {l.get('Id')}")

    # 2. add "distance out" output pin to the MimosaMove definition's Update fragment
    upd = find_by_id(root, MM_UPDATE_PATCH)
    if upd is None:
        print("ERROR: MimosaMove Update fragment not found")
        return 1
    dist_out_def = vl_ids.new_vl_id()
    upd.append(etree.Element("Pin", Id=dist_out_def, Name="distance out", Kind="OutputPin"))

    inst = find_by_id(root, MM_INSTANCE)
    if inst is None:
        print("ERROR: MimosaMove instance node not found")
        return 1
    dist_out_inst = vl_ids.new_vl_id()
    inst.append(etree.Element("Pin", Id=dist_out_inst, Name="distance out", Kind="OutputPin"))
    print("added 'distance out' pin to MimosaMove definition and instance")

    # 3. inside MimosaMove: vision damper -> distance out
    mm_inner = upd.getparent()  # definition inner patch
    mm_inner.append(etree.Element("Link", Id=vl_ids.new_vl_id(),
                                  Ids=f"{VISION_DAMPER_POS},{dist_out_def}"))
    print("wired vision Damper.Position -> MimosaMove.distance out (internal)")

    # 4. Application-level links
    app_inner.append(etree.Element("Link", Id=vl_ids.new_vl_id(),
                                   Ids=f"{dist_out_inst},{LE_INPUT}"))
    print("wired MimosaMove.distance out -> <=.Input")
    for src, dst in ADD_LINKS_APP:
        app_inner.append(etree.Element("Link", Id=vl_ids.new_vl_id(), Ids=f"{src},{dst}"))
        print(f"added link {src[:8]} -> {dst[:8]}")

    # 5. threshold pad: 0.96 -> 1.4 (meters)
    thr = find_by_id(root, PAD_THRESHOLD)
    if thr is not None:
        thr.set("Value", "1.4")
        thr.set("Comment", "camera shy threshold (m)")
        print("threshold pad set to 1.4 m")

    FILE.write_bytes(etree.tostring(doc, xml_declaration=True, encoding="UTF-8"))
    print(f"wrote {FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
