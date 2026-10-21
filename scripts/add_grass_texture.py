"""Swap the flat-green Disc floor for a textured grass Plane in MimosaFinal.vl.

    FileTexture (../assert/grass.png) -> TextureMaterial (Scale 8x8 tiling)
        -> Plane (20x20 m, UpY) -> entity Group Child 2
    (the old green PBRMaterial + Disc are removed; the 1cm lift Translate stays)

Run:  uv run --with lxml python scripts/add_grass_texture.py
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
P = "{property}"

GROUP_CHILD2 = "PqPX1mP4HMbMPza6nylHsC"  # entity Group Child 2 (currently the Disc)

# nodes/pads added by add_grass_floor.py, identified by their Bounds
OLD_BOUNDS = {"2080,1160", "1900,1260", "2300,1210", "1900,1150"}  # PBRMaterial, Translate, Disc, grass pad


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

    # --- remove old floor (PBRMaterial, Disc, grass pad) but KEEP the Translate ---
    # identify by content, not Bounds (nodes may have been moved in the editor)
    def kind_of(el):
        ref = el.find(f"{P}NodeReference")
        return etree.tostring(ref, encoding="unicode") if ref is not None else ""

    removed_ids = set()
    for el in list(app_canvas):
        if el.tag == "Node" and ('Name="PBRMaterial"' in kind_of(el) or 'Name="Disc"' in kind_of(el)):
            for sub in el.iter():
                if sub.get("Id"):
                    removed_ids.add(sub.get("Id"))
            app_canvas.remove(el)
        elif el.tag == "Pad" and el.get("Comment") == "Grass color":
            if el.get("Id"):
                removed_ids.add(el.get("Id"))
            app_canvas.remove(el)
    for l in list(app_inner.findall("Link")):
        ids = l.get("Ids", "").split(",")
        if any(i in removed_ids for i in ids):
            app_inner.remove(l)
    print(f"removed old floor nodes ({len(removed_ids)} ids) and their links")

    # Translate stays: find by its OperationCallFlag
    tr_out = None
    for el in app_canvas.iter("Node"):
        if 'OperationCallFlag" Name="Translate"' in kind_of(el):
            for p in el.findall("Pin"):
                if p.get("Name") == "Output":
                    tr_out = p.get("Id")
    if not tr_out:
        print("ERROR: Translate node not found")
        return 1

    # --- FileTexture ---
    ft = etree.Element("Node", Bounds="2080,1160,125,19", Id=nid())
    ref = etree.SubElement(ft, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride.Assets")
    ref.set("LastDependency", "VL.Stride.Assets.Windows.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="FileTexture")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    ft_path = nid()
    etree.SubElement(ft, "Pin", Id=ft_path, Name="Path", Kind="InputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Generate Mipmaps", Kind="InputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Is sRGB", Kind="InputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Premultiply Alpha", Kind="InputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Compress", Kind="InputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Alpha Format", Kind="InputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Reload", Kind="InputPin")
    ft_tex = nid()
    etree.SubElement(ft, "Pin", Id=ft_tex, Name="Texture", Kind="OutputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Is Loading", Kind="OutputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Already Loaded", Kind="OutputPin")
    app_canvas.append(ft)

    ftpath_pad = nid()
    pp = etree.Element("Pad", Id=ftpath_pad, Comment="grass texture", Bounds="1830,1160,56,15",
                       ShowValueBox="true", isIOBox="true", Value="..\\assert\\grass.png")
    ann = etree.SubElement(pp, f"{P}TypeAnnotation")
    ann.set("LastCategoryFullName", "IO")
    ann.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ann, "Choice", Kind="TypeFlag", Name="Path")
    app_canvas.append(pp)

    # --- TextureMaterial ---
    tm = etree.Element("Node", Bounds="2300,1160,185,19", Id=nid())
    ref = etree.SubElement(tm, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride.Materials")
    ref.set("LastDependency", "VL.Stride.Rendering.ShaderFX.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    cat = etree.SubElement(ref, "CategoryReference", Kind="Category", Name="Materials")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="TextureMaterial")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    tm_tex = nid()
    etree.SubElement(tm, "Pin", Id=tm_tex, Name="Texture", Kind="InputPin")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Fallback Color", Kind="InputPin")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Texcoord Index", Kind="InputPin")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Filtering", Kind="InputPin")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Address Mode U", Kind="InputPin", DefaultValue="Wrap")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Address Mode V", Kind="InputPin", DefaultValue="Wrap")
    tm_scale = nid()
    etree.SubElement(tm, "Pin", Id=tm_scale, Name="Scale", Kind="InputPin", DefaultValue="8, 8")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Offset", Kind="InputPin")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Transparency", Kind="InputPin")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Cull Mode", Kind="InputPin")
    tm_out = nid()
    etree.SubElement(tm, "Pin", Id=tm_out, Name="Output", Kind="OutputPin")
    app_canvas.append(tm)

    # --- Plane (the grass floor) ---
    pl = etree.Element("Node", Bounds="2560,1210,185,19", Id=nid())
    ref = etree.SubElement(pl, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride.Models")
    ref.set("LastDependency", "VL.Stride.Engine.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="Plane")
    etree.SubElement(pl, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    pl_tr = nid()
    etree.SubElement(pl, "Pin", Id=pl_tr, Name="Transformation", Kind="InputPin")
    etree.SubElement(pl, "Pin", Id=nid(), Name="Size", Kind="InputPin", DefaultValue="20, 20")
    etree.SubElement(pl, "Pin", Id=nid(), Name="Tessellation", Kind="InputPin")
    etree.SubElement(pl, "Pin", Id=nid(), Name="Normal", Kind="InputPin", DefaultValue="UpY")
    etree.SubElement(pl, "Pin", Id=nid(), Name="Generate Back Face", Kind="InputPin")
    pl_mat = nid()
    etree.SubElement(pl, "Pin", Id=pl_mat, Name="Material", Kind="InputPin")
    etree.SubElement(pl, "Pin", Id=nid(), Name="Is Shadow Caster", Kind="InputPin")
    etree.SubElement(pl, "Pin", Id=nid(), Name="Components", Kind="InputPin")
    etree.SubElement(pl, "Pin", Id=nid(), Name="Children", Kind="InputPin")
    etree.SubElement(pl, "Pin", Id=nid(), Name="Name", Kind="InputPin")
    etree.SubElement(pl, "Pin", Id=nid(), Name="Enabled", Kind="InputPin")
    etree.SubElement(pl, "Pin", Id=nid(), Name="Output", Kind="OutputPin", IsHidden="true")
    pl_entity = nid()
    etree.SubElement(pl, "Pin", Id=pl_entity, Name="Entity", Kind="OutputPin")
    app_canvas.append(pl)

    # --- wiring ---
    add = lambda s, d: app_inner.append(etree.Element("Link", Id=nid(), Ids=f"{s},{d}"))
    add(ftpath_pad, ft_path)        # png path -> FileTexture
    add(ft_tex, tm_tex)             # texture -> TextureMaterial
    add(tm_out, pl_mat)             # material -> Plane
    add(tr_out, pl_tr)              # 1cm lift -> Plane
    add(pl_entity, GROUP_CHILD2)    # plane -> scene group
    print("wired textured grass plane")

    FILE.write_bytes(etree.tostring(doc, xml_declaration=True, encoding="UTF-8"))
    print(f"wrote {FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
