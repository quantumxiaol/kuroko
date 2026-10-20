"""Rework MimosaFinal.vl camera logic — v2, cycle-free.

Problems fixed:
1. CYCLE: distance was routed out of MimosaMove and back into its input.
   Now the vision chain (RealSense, probes, Damper, renderer windows) lives back
   in the Application canvas; MimosaMove receives a pure "distance in" input pin.
   The shy/dance camera switch runs fully at Application level:
       Damper.Position -> <=(threshold 1.4m) -> Switch(near 2m / far 10m)
           -> MimosaMove.camera distance
       Switch.Output -> Changed -> OrbitCamera.Reset   (auto-bang on every flip;
           the manual Reset pad stays as fallback)
2. Orphan Skia windows: vision chain is no longer inside the MimosaMove process.

Run:  uv run --with lxml python scripts/fix_final_camera2.py
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

FILE = ROOT / "test_vl_code" / "MimosaFinal.vl"

MM_UPDATE_PATCH = "QZOzsnvywKfLiVuOVOEjr1"
MM_INSTANCE = "J30HaKF2TXPOuUVCMmpVsP"
MAPCLAMP_INPUT = "TRmuAbgJsJMQBPpgHR8mDY"
MM_CAMDIST_INPUT = "Pa7dwtAzsiVOJHreXiEVff"
ORBIT_RESET = "EUFGBVS0gG1O5wAZ4U3ysZ"
LE_INPUT = "CiWw3ttgSlgPTRt4wpd3Tt"
SWITCH_OUTPUT = "GEpnehTRxMSNGsGIvGFqM8"
PAD_NEAR = "Su64pxl9JbNNFBwWWaVibV"
PAD_FAR = "UP6x2aDmfY8QS4XNaEM7nw"

GRAFT_Y = 1846  # vision content in MimosaMove was offset by this much at merge


def find_by_id(root, eid):
    for el in root.iter():
        if el.get("Id") == eid:
            return el
    return None


def main() -> int:
    parser = etree.XMLParser(remove_blank_text=False)
    doc = etree.parse(str(FILE), parser)
    root = doc.getroot()

    app_inner = None
    for node in root.iter("Node"):
        if node.get("Name") == "Application":
            app_inner = node.find("Patch")
            break
    app_canvas = app_inner.find("Canvas")

    mm_inner = find_by_id(root, MM_UPDATE_PATCH).getparent()  # MimosaMove def inner patch
    mm_canvas = mm_inner.find("Canvas")

    # --- 1. move grafted vision content back to the Application canvas ---
    grafted_ids = set()
    to_move = []
    for el in list(mm_canvas):
        b = el.get("Bounds")
        if b:
            try:
                y = float(b.split(",")[1])
            except (ValueError, IndexError):
                y = 0
            if y >= GRAFT_Y:
                to_move.append(el)
                for sub in el.iter():
                    if sub.get("Id"):
                        grafted_ids.add(sub.get("Id"))
                if el.get("Id"):
                    grafted_ids.add(el.get("Id"))
    for el in to_move:
        mm_canvas.remove(el)
        app_canvas.append(el)

    # links inside mm whose BOTH endpoints are grafted -> move to app patch
    moved_links = 0
    for l in list(mm_inner.findall("Link")):
        ids = l.get("Ids", "").split(",")
        if all(i in grafted_ids for i in ids):
            mm_inner.remove(l)
            app_inner.append(l)
            moved_links += 1
    print(f"moved {len(to_move)} elements + {moved_links} links back to Application canvas")

    # vision damper Position pin: find among moved nodes (the Damper in the graft)
    vis_damper_pos = None
    for el in to_move:
        ref = el.find("{property}NodeReference")
        if ref is not None and 'Name="Damper"' in etree.tostring(ref, encoding="unicode"):
            for pin in el.findall("Pin"):
                if pin.get("Name") == "Position" and pin.get("Kind") == "OutputPin":
                    vis_damper_pos = pin.get("Id")
    if not vis_damper_pos:
        print("ERROR: moved vision Damper not found")
        return 1

    # --- 2. remove the cycle path: distance out pins + their links ---
    for pin_name in ("distance out",):
        for el in root.iter("Pin"):
            if el.get("Name") == pin_name:
                pid = el.get("Id")
                el.getparent().remove(el)
                print(f"removed '{pin_name}' pin {pid[:8]}")
                for parent in root.iter():
                    if parent.tag == "Patch":
                        for l in list(parent.findall("Link")):
                            if pid in l.get("Ids", "").split(","):
                                parent.remove(l)
                                print(f"  removed link {l.get('Id')} touching it")

    # delete any link feeding <=.Input (leftover from the cycle path)
    for l in list(app_inner.findall("Link")):
        ids = l.get("Ids", "").split(",")
        if ids[-1] == LE_INPUT:
            app_inner.remove(l)
            print(f"deleted link {l.get('Id')} into <=.Input")

    # --- 3. new input pin "distance in" on MimosaMove (def + instance) ---
    upd = find_by_id(root, MM_UPDATE_PATCH)
    dist_in_def = vl_ids.new_vl_id()
    upd.append(etree.Element("Pin", Id=dist_in_def, Name="distance in", Kind="InputPin"))
    inst = find_by_id(root, MM_INSTANCE)
    dist_in_inst = vl_ids.new_vl_id()
    inst.append(etree.Element("Pin", Id=dist_in_inst, Name="distance in", Kind="InputPin"))
    # inside: distance in -> MapClamp.Input
    mm_inner.append(etree.Element("Link", Id=vl_ids.new_vl_id(),
                                  Ids=f"{dist_in_def},{MAPCLAMP_INPUT}"))
    print("added 'distance in' pin (def+instance) and wired to MapClamp.Input")

    # --- 4. Application-level wiring ---
    add = lambda s, d: app_inner.append(etree.Element("Link", Id=vl_ids.new_vl_id(), Ids=f"{s},{d}"))
    add(vis_damper_pos, LE_INPUT)               # measured distance -> <=
    add(vis_damper_pos, dist_in_inst)           # measured distance -> MimosaMove.distance in
    print("wired vision Damper.Position -> <=.Input and -> MimosaMove.distance in")

    # --- 5. Changed node: auto-bang OrbitCamera.Reset when the switch flips ---
    ch = etree.SubElement(app_canvas, "Node", Bounds="1665,650,57,19", Id=vl_ids.new_vl_id())
    ref = etree.SubElement(ch, "{property}NodeReference")
    ref.set("LastCategoryFullName", "Control")
    ref.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="Changed")
    ch_ctx = vl_ids.new_vl_id()
    etree.SubElement(ch, "Pin", Id=ch_ctx, Name="Node Context", Kind="InputPin", IsHidden="true")
    ch_coc = vl_ids.new_vl_id()
    etree.SubElement(ch, "Pin", Id=ch_coc, Name="Changed On Create", Kind="InputPin", IsHidden="true")
    ch_val = vl_ids.new_vl_id()
    etree.SubElement(ch, "Pin", Id=ch_val, Name="Value", Kind="InputPin")
    ch_res = vl_ids.new_vl_id()
    etree.SubElement(ch, "Pin", Id=ch_res, Name="Result", Kind="OutputPin")
    ch_un = vl_ids.new_vl_id()
    etree.SubElement(ch, "Pin", Id=ch_un, Name="Unchanged", Kind="OutputPin")
    add(SWITCH_OUTPUT, ch_val)
    add(ch_res, ORBIT_RESET)
    print("added Changed node -> OrbitCamera.Reset (auto-bang on camera flip)")

    # --- 6. camera distances: near 2 m / far 10 m ---
    for pid, val, label in [(PAD_NEAR, "2", "near"), (PAD_FAR, "10", "far")]:
        pad = find_by_id(root, pid)
        pad.set("Value", val)
        pad.set("Comment", f"camera {label} view (m)")
    print("camera near=2m, far=10m")

    FILE.write_bytes(etree.tostring(doc, xml_declaration=True, encoding="UTF-8"))
    print(f"wrote {FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
