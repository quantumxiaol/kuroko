"""Tune MimosaGarden.vl: floor height bake, bigger disc, mushroom heights, skybox,
and a Dispose fragment so closing the document closes the render window.

Run:  uv run --with lxml python scripts/garden_tune.py
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

FILE = ROOT / "test_vl_code" / "MimosaGarden.vl"
P = "{property}"

CYL_TRANSLATION = (0, 0.01, 0)     # bake the live-tuned floor height
CYL_RADIUS = "6"                   # bigger disc
SHROOM_Y_LIFT = 0.22               # floor raised by ~0.22 -> mushrooms sit on top

SCENEWINDOW_CHILD = "REjpQ5HcpTdMs6JVCbPgKK"


def nid() -> str:
    return vl_ids.new_vl_id()


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
    add = lambda s, d: app_inner.append(etree.Element("Link", Id=nid(), Ids=f"{s},{d}"))

    # --- 1. bake floor height + enlarge disc ---
    for pad in app_canvas.iter("Pad"):
        if pad.get("Comment") == "Translation":
            pad.set("Value", f"{CYL_TRANSLATION[0]}, {CYL_TRANSLATION[1]}, {CYL_TRANSLATION[2]}")
            print("floor Translation baked to", CYL_TRANSLATION)
        elif pad.get("Comment") == "Base Radius":
            pad.set("Value", CYL_RADIUS)
            print("floor radius ->", CYL_RADIUS)

    # --- 2. mushrooms: raise onto the new floor level ---
    for pad in app_canvas.iter("Pad"):
        val = pad.find(f"{P}Value")
        if val is not None and len(val.findall("Item")) == 3:
            items = val.findall("Item")
            first = items[0].text or ""
            if "-1.22" in first or "1.17" in (items[1].text or ""):
                for it in items:
                    parts = [float(x.strip()) for x in it.text.split(",")]
                    parts[1] = round(parts[1] + SHROOM_Y_LIFT, 2)
                    it.text = ", ".join(str(p) for p in parts)
                    print("mushroom position ->", it.text)

    # --- 3. skybox background: FileTexture -> Background -> outer group ---
    # FileTexture
    ft = etree.Element("Node", Bounds="3300,2400,105,19", Id=nid())
    ref = etree.SubElement(ft, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride.Assets")
    ref.set("LastDependency", "VL.Stride.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="FileTexture")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    ft_path = nid()
    pin = etree.SubElement(ft, "Pin", Id=ft_path, Name="Path", Kind="InputPin")
    pin.set("DefaultValue", "..\\assert\\skybox.png")
    for nm in ("Generate Mipmaps", "Premultiply Alpha", "Compress", "Alpha Format", "Reload"):
        etree.SubElement(ft, "Pin", Id=nid(), Name=nm, Kind="InputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Is sRGB", Kind="InputPin", IsHidden="true")
    ft_tex = nid()
    etree.SubElement(ft, "Pin", Id=ft_tex, Name="Texture", Kind="OutputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Is Loading", Kind="OutputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Already Loaded", Kind="OutputPin")
    app_canvas.append(ft)

    # Background (skybox)
    bg = etree.Element("Node", Bounds="3300,2500,145,19", Id=nid())
    ref = etree.SubElement(bg, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride.Models")
    ref.set("LastDependency", "VL.Stride.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    cat = etree.SubElement(ref, "CategoryReference", Kind="Category", Name="Models")
    cat.set("NeedsToBeDirectParent", "true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="Background")
    etree.SubElement(bg, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    etree.SubElement(bg, "Pin", Id=nid(), Name="Transformation", Kind="InputPin")
    bg_tex = nid()
    etree.SubElement(bg, "Pin", Id=bg_tex, Name="Texture", Kind="InputPin")
    etree.SubElement(bg, "Pin", Id=nid(), Name="Intensity", Kind="InputPin")
    etree.SubElement(bg, "Pin", Id=nid(), Name="Is 2D", Kind="InputPin")
    etree.SubElement(bg, "Pin", Id=nid(), Name="Component", Kind="InputPin")
    etree.SubElement(bg, "Pin", Id=nid(), Name="Children", Kind="InputPin")
    etree.SubElement(bg, "Pin", Id=nid(), Name="Name", Kind="InputPin")
    etree.SubElement(bg, "Pin", Id=nid(), Name="Enabled", Kind="InputPin")
    etree.SubElement(bg, "Pin", Id=nid(), Name="Output", Kind="OutputPin", IsHidden="true")
    bg_entity = nid()
    etree.SubElement(bg, "Pin", Id=bg_entity, Name="Entity", Kind="OutputPin")
    app_canvas.append(bg)

    # outer group: [existing scene group output] + [background] -> SceneWindow.Child
    child_link = None
    for l in app_inner.findall("Link"):
        if l.get("Ids", "").endswith("," + SCENEWINDOW_CHILD):
            child_link = l
            break
    if child_link is None:
        print("ERROR: scene-window child link not found")
        return 1
    scene_group_out = child_link.get("Ids").split(",")[0]
    app_inner.remove(child_link)

    g = etree.Element("Node", Bounds="3300,2650,125,19", Id=nid())
    ref = etree.SubElement(g, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride")
    ref.set("LastDependency", "VL.Stride.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    cat = etree.SubElement(ref, "CategoryReference", Kind="Category", Name="Stride")
    cat.set("NeedsToBeDirectParent", "true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="Group")
    etree.SubElement(g, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    etree.SubElement(g, "Pin", Id=nid(), Name="Transformation", Kind="InputPin")
    g_in1 = nid()
    etree.SubElement(g, "Pin", Id=g_in1, Name="Child", Kind="InputPin")
    g_in2 = nid()
    etree.SubElement(g, "Pin", Id=g_in2, Name="Child 2", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Child 3", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Child 4", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Name", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Enabled", Kind="InputPin")
    g_out = nid()
    etree.SubElement(g, "Pin", Id=g_out, Name="Output", Kind="OutputPin")
    app_canvas.append(g)

    add(ft_tex, bg_tex)
    add(bg_entity, g_in2)
    add(scene_group_out, g_in1)
    add(g_out, SCENEWINDOW_CHILD)
    print("skybox background grafted")

    # --- 4. Dispose fragment on the Application process (close window with document) ---
    proc_def = None
    for pd in app_inner.iter("ProcessDefinition"):
        proc_def = pd
        break
    if proc_def is not None and not any(f.get("Patch", "").startswith("dispose") for f in proc_def):
        existing = {f.get("Patch") for f in proc_def.findall("Fragment")}
        if not any(p.get("Name") == "Dispose" for p in app_inner.findall("Patch")):
            disp = etree.Element("Patch", Id=nid(), Name="Dispose")
            app_inner.append(disp)
            frag = etree.Element("Fragment", Id=nid(), Enabled="true")
            frag.set("Patch", disp.get("Id"))
            proc_def.append(frag)
            print("added Dispose fragment to Application (windows should close with the document)")
        else:
            print("Dispose patch already exists")

    FILE.write_bytes(etree.tostring(doc, xml_declaration=True, encoding="UTF-8"))
    print(f"wrote {FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
