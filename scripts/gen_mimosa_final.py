"""Merge MimosaVisioni.vl (depth distance chain) into mimosa2.vl (robot behaviour)
to produce vlsrc/MimosaFinal.vl.

- Grafts all vision nodes/pads/links into the mimosa2 Application canvas with fresh
  VL ids, positioned below the existing content.
- Replaces the simulated distance IOBox link into MapClamp.Input with the real
  depth-derived distance (the vision Damper output). The simulated IOBox stays,
  disconnected, as a debug backup.
- Adds the VL.Devices.RealSense (1.11.0) and VL.Skia nuget dependencies.

Run:  uv run --with lxml python scripts/gen_mimosa_final.py
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

BASE = ROOT / "vlsrc" / "mimosa2.vl"
VISION = ROOT / "vlsrc" / "MimosaVisioni.vl"
OUT = ROOT / "vlsrc" / "MimosaFinal.vl"

# in mimosa2.vl: simulated distance pad and its link into MapClamp.Input
SIM_PAD = "IrFdQXZODvTPMSVgcJrNqq"
SIM_LINK = "DO704rA3kPuOfMAWbrQhQV"
MAPCLAMP_INPUT = "TRmuAbgJsJMQBPpgHR8mDY"

P = "{property}"  # p: namespace for property elements; Id/Bounds are plain attributes


def fresh_ids() -> dict[str, str]:
    return {}


def remap_tree(el: etree._Element, idmap: dict[str, str]) -> None:
    """Assign fresh ids to every Id attribute and rewrite Link Ids references."""
    for node in el.iter():
        i = node.get("Id")
        if i is not None:
            node.set("Id", idmap.setdefault(i, vl_ids.new_vl_id()))
        ids = node.get("Ids")
        if ids is not None:
            parts = [idmap.setdefault(p, vl_ids.new_vl_id()) for p in ids.split(",")]
            node.set("Ids", ",".join(parts))


def offset_bounds(el: etree._Element, dx: float, dy: float) -> None:
    for node in el.iter():
        b = node.get("Bounds")
        if b:
            parts = b.split(",")
            try:
                parts[0] = str(float(parts[0]) + dx).rstrip("0").rstrip(".") if "." in parts[0] else str(int(parts[0]) + int(dx))
                parts[1] = str(float(parts[1]) + dy).rstrip("0").rstrip(".") if "." in parts[1] else str(int(parts[1]) + int(dy))
                node.set("Bounds", ",".join(p if p else "0" for p in parts))
            except (ValueError, IndexError):
                pass


def main() -> int:
    parser = etree.XMLParser(remove_blank_text=False)
    base = etree.parse(str(BASE), parser)
    vision = etree.parse(str(VISION), parser)

    base_root = base.getroot()
    vis_root = vision.getroot()

    # --- dependencies ---
    existing = {d.get("Location") for d in base_root.iter("NugetDependency")}
    for loc, ver in [("VL.Devices.RealSense", "1.11.0"), ("VL.Skia", None)]:
        if loc not in existing:
            dep = etree.Element("NugetDependency", Id=vl_ids.new_vl_id(), Location=loc)
            if ver:
                dep.set("Version", ver)
            base_root.append(dep)
            print(f"added dependency {loc} {ver or ''}")

    # --- locate application canvases ---
    def app_parts(root):
        for node in root.iter("Node"):
            if node.get("Name") == "Application":
                inner = node.find("Patch")
                canvas = inner.find("Canvas")
                return inner, canvas
        raise RuntimeError("Application node not found")

    # --- locate the MimosaMove process patch (the MapClamp and the simulated
    # distance pad live INSIDE that local process, not in the Application canvas) ---
    sim_link_el = None
    for l in base_root.iter("Link"):
        if l.get("Id") == SIM_LINK:
            sim_link_el = l
            break
    if sim_link_el is None:
        print("ERROR: simulated-distance link not found in mimosa2.vl")
        return 1
    mm_inner = sim_link_el.getparent()          # inner Patch of the MimosaMove definition
    mm_canvas = mm_inner.find("Canvas")
    print(f"target process patch found (canvas {mm_canvas.get('CanvasType')})")

    vis_inner, vis_canvas = app_parts(vis_root)

    # --- collect vision content ---
    vis_nodes = list(vis_canvas)  # Nodes, Pads, Overlays inside the group canvas
    vis_links = [l for l in vis_inner.findall("Link")]

    # find the vision Damper's Position output pin BEFORE remapping (mimosa2 has its
    # own Damper node — wiring to that one would create a feedback loop)
    vis_damper_pos_old = None
    for node in vis_canvas.iter("Node"):
        ref = node.find(f"{P}NodeReference")
        if ref is not None and 'Name="Damper"' in etree.tostring(ref, encoding="unicode"):
            for pin in node.findall("Pin"):
                if pin.get("Name") == "Position" and pin.get("Kind") == "OutputPin":
                    vis_damper_pos_old = pin.get("Id")
    if not vis_damper_pos_old:
        print("ERROR: vision Damper Position pin not found in source")
        return 1

    # fresh ids for the whole graft
    idmap: dict[str, str] = {}
    graft = vis_nodes + vis_links
    for el in graft:
        remap_tree(el, idmap)
    damper_pos_new = idmap[vis_damper_pos_old]

    # offset below existing MimosaMove content
    max_y = 0.0
    for el in mm_canvas.iter():
        b = el.get("Bounds")
        if b:
            try:
                max_y = max(max_y, float(b.split(",")[1]))
            except (ValueError, IndexError):
                pass
    dy = max_y + 200
    for el in graft:
        offset_bounds(el, 0, dy)
    print(f"grafting {len(vis_nodes)} nodes/pads + {len(vis_links)} links into MimosaMove, offset y +{dy:.0f}")

    # detach from vision doc, attach to the MimosaMove patch
    for el in vis_nodes:
        vis_canvas.remove(el)
        mm_canvas.append(el)
    for el in vis_links:
        vis_inner.remove(el)
        mm_inner.append(el)

    # --- rewire: simulated pad -> real distance ---
    mm_inner.remove(sim_link_el)
    print("removed simulated-distance link into MapClamp.Input")
    new_link = etree.Element("Link", Id=vl_ids.new_vl_id(), Ids=f"{damper_pos_new},{MAPCLAMP_INPUT}")
    mm_inner.append(new_link)
    print("wired vision Damper.Position -> MapClamp.Input")

    # mark the simulated pad as backup
    for pad in mm_canvas.iter("Pad"):
        if pad.get("Id") == SIM_PAD:
            pad.set("Comment", "Camera distance (m) [simulated, backup - not connected]")

    OUT.write_bytes(etree.tostring(base, xml_declaration=True, encoding="UTF-8"))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
