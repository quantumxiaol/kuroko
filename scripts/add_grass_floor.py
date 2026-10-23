"""Add a green grass floor disc to MimosaFinal.vl (and revert the all-green cave).

CaveColour turned out to color the WHOLE cave backdrop model (BG4e.glb) — reverting it.
The grass floor is our own Disc entity grouped with the robot scene:

    VisualizePRCRobot ─┐
                       Group(Stride.Rendering) ─→ BunrakuSceneWindow.Child
    green PBRMaterial → Disc (UpY, r=2.5m) ─┘     (sky stays the original cave gradient)

Run:  uv run --with lxml python scripts/add_grass_floor.py
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
P = "{property}"

SCENEWINDOW_CHILD = "REjpQ5HcpTdMs6JVCbPgKK"
ROBOT_TO_CHILD_LINK = "Pk5YwEaW71POhSny4nUSOf"
CAVE_COLOUR_PIN = "OAmtkv2IZApM4GZ8wGkN5t"


def find_by_id(root, eid):
    for el in root.iter():
        if el.get("Id") == eid:
            return el
    return None


def nid() -> str:
    return vl_ids.new_vl_id()


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

    # --- 1. revert the cave colour: drop my green pad + link ---
    cave_link = None
    for l in app_inner.findall("Link"):
        if l.get("Ids", "").endswith("," + CAVE_COLOUR_PIN):
            cave_link = l
            break
    if cave_link is not None:
        pad_id = cave_link.get("Ids").split(",")[0]
        app_inner.remove(cave_link)
        pad = find_by_id(root, pad_id)
        if pad is not None:
            pad.getparent().remove(pad)
        print("reverted CaveColour (back to default gray cave)")

    # --- 2. grass color pad ---
    grass_pad = nid()
    pad = etree.Element("Pad", Id=grass_pad, Comment="Grass color", Bounds="1900,1150,60,30",
                        ShowValueBox="true", isIOBox="true", Value="0.13, 0.42, 0.16, 1")
    ann = etree.SubElement(pad, f"{P}TypeAnnotation")
    ann.set("LastCategoryFullName", "Color")
    ann.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ann, "Choice", Kind="TypeFlag", Name="RGBA")
    app_canvas.append(pad)

    # --- 3. PBRMaterial (green) ---
    mat = nid()
    m = etree.Element("Node", Bounds="2080,1160,85,19", Id=mat)
    ref = etree.SubElement(m, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride.Materials")
    ref.set("LastDependency", "VL.Stride.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="PBRMaterial")
    etree.SubElement(m, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    mat_color = nid()
    etree.SubElement(m, "Pin", Id=mat_color, Name="Color", Kind="InputPin")
    etree.SubElement(m, "Pin", Id=nid(), Name="Metalness", Kind="InputPin")
    etree.SubElement(m, "Pin", Id=nid(), Name="Roughness", Kind="InputPin", DefaultValue="0.9")
    etree.SubElement(m, "Pin", Id=nid(), Name="Transparency", Kind="InputPin")
    etree.SubElement(m, "Pin", Id=nid(), Name="Cull Mode", Kind="InputPin")
    etree.SubElement(m, "Pin", Id=nid(), Name="State Output", Kind="OutputPin", IsHidden="true")
    mat_out = nid()
    etree.SubElement(m, "Pin", Id=mat_out, Name="Output", Kind="OutputPin")
    app_canvas.append(m)

    # --- 4. Translate (slight lift to avoid z-fighting the cave floor) ---
    tr = nid()
    t = etree.Element("Node", Bounds="2080,1260,76,19", Id=tr)
    ref = etree.SubElement(t, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "3D.Transform")
    ref.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    cat = etree.SubElement(ref, "CategoryReference", Kind="Category", Name="Transform")
    cat.set("NeedsToBeDirectParent", "true")
    outer = etree.SubElement(cat, f"{P}OuterCategoryReference", Kind="Category", Name="3D")
    outer.set("NeedsToBeDirectParent", "true")
    etree.SubElement(ref, "Choice", Kind="OperationCallFlag", Name="Translate")
    etree.SubElement(t, "Pin", Id=nid(), Name="Input", Kind="InputPin")
    tr_trans = nid()
    etree.SubElement(t, "Pin", Id=tr_trans, Name="Translation", Kind="InputPin")
    tr_out = nid()
    etree.SubElement(t, "Pin", Id=tr_out, Name="Output", Kind="OutputPin")
    app_canvas.append(t)

    lift_pad = nid()
    lp = etree.Element("Pad", Id=lift_pad, Comment="floor lift (m)", Bounds="1900,1260,52,15",
                       ShowValueBox="true", isIOBox="true", Value="0, 0.01, 0")
    ann = etree.SubElement(lp, f"{P}TypeAnnotation")
    ann.set("LastCategoryFullName", "3D")
    ann.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ann, "Choice", Kind="TypeFlag", Name="Vector3")
    app_canvas.append(lp)

    # --- 5. Disc (the grass floor) ---
    disc = nid()
    d = etree.Element("Node", Bounds="2300,1210,265,19", Id=disc)
    ref = etree.SubElement(d, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride.Models")
    ref.set("LastDependency", "VL.Stride.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="Disc")
    etree.SubElement(d, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    disc_tr = nid()
    etree.SubElement(d, "Pin", Id=disc_tr, Name="Transformation", Kind="InputPin")
    etree.SubElement(d, "Pin", Id=nid(), Name="Outer Radius", Kind="InputPin", DefaultValue="10")
    etree.SubElement(d, "Pin", Id=nid(), Name="Inner Radius", Kind="InputPin")
    etree.SubElement(d, "Pin", Id=nid(), Name="From Angle", Kind="InputPin")
    etree.SubElement(d, "Pin", Id=nid(), Name="To Angle", Kind="InputPin")
    etree.SubElement(d, "Pin", Id=nid(), Name="Tessellation", Kind="InputPin", DefaultValue="71")
    etree.SubElement(d, "Pin", Id=nid(), Name="Normal", Kind="InputPin", DefaultValue="UpY")
    etree.SubElement(d, "Pin", Id=nid(), Name="Generate Back Face", Kind="InputPin")
    disc_mat = nid()
    etree.SubElement(d, "Pin", Id=disc_mat, Name="Material", Kind="InputPin")
    etree.SubElement(d, "Pin", Id=nid(), Name="Is Shadow Caster", Kind="InputPin")
    etree.SubElement(d, "Pin", Id=nid(), Name="Components", Kind="InputPin")
    etree.SubElement(d, "Pin", Id=nid(), Name="Children", Kind="InputPin")
    etree.SubElement(d, "Pin", Id=nid(), Name="Name", Kind="InputPin")
    etree.SubElement(d, "Pin", Id=nid(), Name="Enabled", Kind="InputPin")
    etree.SubElement(d, "Pin", Id=nid(), Name="Output", Kind="OutputPin", IsHidden="true")
    disc_entity = nid()
    etree.SubElement(d, "Pin", Id=disc_entity, Name="Entity", Kind="OutputPin")
    app_canvas.append(d)

    # --- 6. Group (robot + floor) ---
    grp = nid()
    g = etree.Element("Node", Bounds="2600,1210,125,19", Id=grp)
    ref = etree.SubElement(g, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride.Rendering")
    ref.set("LastDependency", "VL.Stride.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    cat = etree.SubElement(ref, "CategoryReference", Kind="Category", Name="Rendering")
    cat.set("NeedsToBeDirectParent", "true")
    outer = etree.SubElement(cat, f"{P}OuterCategoryReference", Kind="Category", Name="Stride")
    outer.set("NeedsToBeDirectParent", "true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="Group")
    etree.SubElement(g, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    grp_in1 = nid()
    etree.SubElement(g, "Pin", Id=grp_in1, Name="Input", Kind="InputPin")
    grp_in2 = nid()
    etree.SubElement(g, "Pin", Id=grp_in2, Name="Input 2", Kind="InputPin")
    grp_out = nid()
    etree.SubElement(g, "Pin", Id=grp_out, Name="Output", Kind="OutputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Input 3", Kind="InputPin")
    app_canvas.append(g)

    # --- 7. rewire ---
    old_link = find_by_id(root, ROBOT_TO_CHILD_LINK)
    robot_out = old_link.get("Ids").split(",")[0]
    old_link.getparent().remove(old_link)

    add = lambda s, d2: app_inner.append(etree.Element("Link", Id=nid(), Ids=f"{s},{d2}"))
    add(grass_pad, mat_color)       # grass color -> material
    add(mat_out, disc_mat)          # material -> disc
    add(lift_pad, tr_trans)         # lift -> translate
    add(tr_out, disc_tr)            # translate -> disc
    add(disc_entity, grp_in2)       # disc -> group
    add(robot_out, grp_in1)         # robot -> group
    add(grp_out, SCENEWINDOW_CHILD) # group -> scene window
    print("wired: robot + grass disc -> Group -> BunrakuSceneWindow.Child")

    FILE.write_bytes(etree.tostring(doc, xml_declaration=True, encoding="UTF-8"))
    print(f"wrote {FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
