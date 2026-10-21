"""Create test_vl_code/MimosaGarden.vl = MimosaFinal.vl + ScaredyShroom.vl scene content.

- Floor: the Plane is replaced by the shroom Cylinder (top radius enlarged to 4 m),
  textured with grass_tile.png (no transparent margins -> no black borders).
- Mushrooms: the whole shroom chain (Repeat x3 + vertex-color material) is grafted in,
  wrapped in an entity Group with a Translation pad so they sit beside the robots.
- The shroom PointLight is kept (scene mood light).
- The shroom Background/SceneWindow/RootScene/SkyboxLight are NOT grafted (the Bunraku
  cave sky stays).

Run:  uv run --with lxml python scripts/gen_garden.py
"""

import copy
import importlib.util
import sys
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
IDS_PY = ROOT / ".agent/skills/vvvv-fileformat/scripts/vl-patch-manipulator/src/vl_patch_manipulator/ids.py"

spec = importlib.util.spec_from_file_location("vl_ids", IDS_PY)
vl_ids = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vl_ids)

BASE = ROOT / "test_vl_code" / "MimosaFinal.vl"
SHROOM = ROOT / "test_vl_code" / "ScaredyShroom.vl"
OUT = ROOT / "test_vl_code" / "MimosaGarden.vl"
P = "{property}"

# MimosaFinal floor pieces to remove (added by add_grass_texture.py): Plane, TextureMaterial,
# FileTexture(grass), grass texture pad — identified by NodeReference/comment, not bounds
GROUP_CHILD2 = "PqPX1mP4HMbMPza6nylHsC"   # floor slot in the scene entity group
GROUP_CHILD4 = "UM1ZCN5f6ikMmqZbGpwvf0"   # free slot

SHROOM_OFFSET = (-2.2, 0, 0.6)  # mushrooms beside robot 1, not blocking
CYL_RADIUS = "4"                # enlarged top


def nid() -> str:
    return vl_ids.new_vl_id()


def remap_tree(el, idmap):
    for node in el.iter():
        i = node.get("Id")
        if i is not None:
            node.set("Id", idmap.setdefault(i, nid()))
        ids = node.get("Ids")
        if ids is not None:
            node.set("Ids", ",".join(idmap.setdefault(p, nid()) for p in ids.split(",")))
        if node.tag == "Fragment" and node.get("Patch"):
            node.set("Patch", idmap.setdefault(node.get("Patch"), nid()))


def offset_bounds(el, dx, dy):
    for node in el.iter():
        b = node.get("Bounds")
        if not b:
            continue
        parts = b.split(",")
        try:
            x = float(parts[0]) + dx
            y = float(parts[1]) + dy
            parts[0] = str(int(x)) if x == int(x) else str(x)
            parts[1] = str(int(y)) if y == int(y) else str(y)
            node.set("Bounds", ",".join(parts))
        except (ValueError, IndexError):
            pass


def entity_group(bounds: str) -> tuple[etree._Element, str, str, str]:
    """Returns (node, Transformation pin id, Child pin id, Output pin id)."""
    g = etree.Element("Node", Bounds=bounds, Id=nid())
    ref = etree.SubElement(g, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride")
    ref.set("LastDependency", "VL.Stride.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    cat = etree.SubElement(ref, "CategoryReference", Kind="Category", Name="Stride")
    cat.set("NeedsToBeDirectParent", "true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="Group")
    etree.SubElement(g, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    tr = nid()
    etree.SubElement(g, "Pin", Id=tr, Name="Transformation", Kind="InputPin")
    child = nid()
    etree.SubElement(g, "Pin", Id=child, Name="Child", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Child 2", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Child 3", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Child 4", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Name", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Enabled", Kind="InputPin")
    out = nid()
    etree.SubElement(g, "Pin", Id=out, Name="Output", Kind="OutputPin")
    return g, tr, child, out


def translate_node(bounds: str) -> tuple[etree._Element, str, str, str]:
    """Returns (node, Input pin, Translation pin, Output pin)."""
    t = etree.Element("Node", Bounds=bounds, Id=nid())
    ref = etree.SubElement(t, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "3D.Transform")
    ref.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    cat = etree.SubElement(ref, "CategoryReference", Kind="Category", Name="Transform")
    cat.set("NeedsToBeDirectParent", "true")
    outer = etree.SubElement(cat, f"{P}OuterCategoryReference", Kind="Category", Name="3D")
    outer.set("NeedsToBeDirectParent", "true")
    etree.SubElement(ref, "Choice", Kind="OperationCallFlag", Name="Translate")
    i = nid()
    etree.SubElement(t, "Pin", Id=i, Name="Input", Kind="InputPin")
    tr = nid()
    etree.SubElement(t, "Pin", Id=tr, Name="Translation", Kind="InputPin")
    o = nid()
    etree.SubElement(t, "Pin", Id=o, Name="Output", Kind="OutputPin")
    return t, i, tr, o


def vec3_pad(name: str, comment: str, bounds: str, value: tuple) -> etree._Element:
    pad = etree.Element("Pad", Id=nid(), Comment=comment, Bounds=bounds,
                        ShowValueBox="true", isIOBox="true",
                        Value=f"{value[0]}, {value[1]}, {value[2]}")
    ann = etree.SubElement(pad, f"{P}TypeAnnotation")
    ann.set("LastCategoryFullName", "3D")
    ann.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ann, "Choice", Kind="TypeFlag", Name="Vector3")
    return pad


def texture_material(bounds: str) -> tuple[etree._Element, str, str]:
    """TextureMaterial -> (node, Texture pin, Output pin)."""
    tm = etree.Element("Node", Bounds=bounds, Id=nid())
    ref = etree.SubElement(tm, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride.Materials")
    ref.set("LastDependency", "VL.Stride.Rendering.ShaderFX.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    etree.SubElement(ref, "CategoryReference", Kind="Category", Name="Materials")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="TextureMaterial")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    tex = nid()
    etree.SubElement(tm, "Pin", Id=tex, Name="Texture", Kind="InputPin")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Fallback Color", Kind="InputPin")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Texcoord Index", Kind="InputPin")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Filtering", Kind="InputPin")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Address Mode U", Kind="InputPin", DefaultValue="Wrap")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Address Mode V", Kind="InputPin", DefaultValue="Wrap")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Scale", Kind="InputPin", DefaultValue="4, 4")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Offset", Kind="InputPin")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Transparency", Kind="InputPin")
    etree.SubElement(tm, "Pin", Id=nid(), Name="Cull Mode", Kind="InputPin")
    out = nid()
    etree.SubElement(tm, "Pin", Id=out, Name="Output", Kind="OutputPin")
    return tm, tex, out


def file_texture(bounds: str, relpath: str) -> tuple[etree._Element, str, str]:
    """FileTexture -> (node, Path pin, Texture pin)."""
    ft = etree.Element("Node", Bounds=bounds, Id=nid())
    ref = etree.SubElement(ft, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride.Assets")
    ref.set("LastDependency", "VL.Stride.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="FileTexture")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    path = nid()
    pin = etree.SubElement(ft, "Pin", Id=path, Name="Path", Kind="InputPin")
    pin.set("DefaultValue", relpath)
    etree.SubElement(ft, "Pin", Id=nid(), Name="Generate Mipmaps", Kind="InputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Is sRGB", Kind="InputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Premultiply Alpha", Kind="InputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Compress", Kind="InputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Alpha Format", Kind="InputPin")
    etree.SubElement(ft, "Pin", Id=nid(), Name="Reload", Kind="InputPin")
    tex = nid()
    etree.SubElement(ft, "Pin", Id=tex, Name="Texture", Kind="OutputPin")
    return ft, path, tex


def main() -> int:
    parser = etree.XMLParser(remove_blank_text=False)
    base = etree.parse(str(BASE), parser)
    shroom = etree.parse(str(SHROOM), parser)
    broot = base.getroot()
    sroot = shroom.getroot()

    app_inner = None
    for node in broot.iter("Node"):
        if node.get("Name") == "Application":
            app_inner = node.find("Patch")
            break
    app_canvas = app_inner.find("Canvas")
    add = lambda s, d: app_inner.append(etree.Element("Link", Id=nid(), Ids=f"{s},{d}"))

    # ============ 1. remove the Disc floor from MimosaFinal ============
    # (green Disc + its PBRMaterial + color pad + the 1cm-lift Translate + its pad)
    removed = set()
    for el in list(app_canvas):
        ref = el.find(f"{P}NodeReference")
        xml = etree.tostring(ref, encoding="unicode") if ref is not None else ""
        if el.tag == "Node" and ('Name="Disc"' in xml or 'Name="PBRMaterial"' in xml
                                 or 'Name="Translate"' in xml):
            for sub in el.iter():
                if sub.get("Id"):
                    removed.add(sub.get("Id"))
            app_canvas.remove(el)
        elif el.tag == "Pad" and el.get("Comment") in ("Grass color", "floor lift (m)"):
            if el.get("Id"):
                removed.add(el.get("Id"))
            app_canvas.remove(el)
    for l in list(app_inner.findall("Link")):
        ids = l.get("Ids", "").split(",")
        if any(i in removed for i in ids):
            app_inner.remove(l)
    print(f"removed disc floor ({len(removed)} ids)")

    # ============ 2. graft shroom content ============
    s_canvas = None
    for node in sroot.iter("Node"):
        if node.get("Name") == "Application":
            s_inner = node.find("Patch")
            s_canvas = s_inner.find("Canvas")
            s_links_parent = s_inner
            break

    # elements to graft, by id (mushroom chain + cylinder + lights)
    GRAFT_IDS = [
        "ICgMvIa9SGZMSoqVyI5RS5",  # Repeat region (incl. FileModel/ModelEntity/TransformSRT/UniformScale inside)
        "UWtkpnRwFiAO5YwxTIFupt",  # Group (Spectral) collecting mushrooms
        "K4mkqbRCnSxONlpvFnBfcL",  # Iteration Count pad
        "GikP5rRYArrMTp1CyeIYd5",  # positions spread pad
        "QnzZOggtUu4Pq7pk6y7Sv8",  # scales spread pad
        "M1wnfPRbiuHNiJQqwVTuba",  # VertexColor shader node
        "MC4Nj42my6HLCGkwPF7ikG",  # PBRMaterial (Metallic)
        "AFwfqqxVKMKOL56rJ1enhO",  # Cylinder
        "SYCUbn6z8SZOf5CXrQctY9",  # Translate (cylinder)
        "KYmdLGGYir2MZYaYWc21ef",  # Height pad
        "TLZFz6BNH3qOKwkcF4mfH8",  # Base Radius pad
        "UVOE6aRTWuTO8ehuRfwNYY",  # Tessellation pad
        "VP0eiFWeWCrMyVq10mkgUd",  # Translation pad
        "VjhGvotxi8wNbnoi9xbHdd",  # model path pad (inside Repeat's patch! NOT grafted here)
    ]
    # note: the path pad lives inside the Repeat region's inner patch — it comes along
    # with the Repeat node automatically; do not graft it separately.

    idmap: dict[str, str] = {}
    grafted: list[etree._Element] = []
    for el in list(s_canvas):
        if el.get("Id") in GRAFT_IDS:
            el_copy = copy.deepcopy(el)
            remap_tree(el_copy, idmap)
            offset_bounds(el_copy, 3200, 1550)
            grafted.append(el_copy)
            app_canvas.append(el_copy)
            s_canvas.remove(el)

    # links of the shroom inner patch that belong fully to grafted content
    for l in list(s_links_parent.findall("Link")):
        ids = l.get("Ids", "").split(",")
        if all(i in idmap for i in ids):
            lc = copy.deepcopy(l)
            remap_tree(lc, idmap)
            app_inner.append(lc)
            s_links_parent.remove(l)
    print(f"grafted {len(grafted)} elements + links")

    # helper: find pin id in grafted content by (node name marker, pin name)
    def grafted_pin(marker: str, pin_name: str) -> str:
        for el in grafted:
            for node in el.iter("Node"):
                ref = node.find(f"{P}NodeReference")
                if ref is not None and marker in etree.tostring(ref, encoding="unicode"):
                    for p in node.findall("Pin"):
                        if p.get("Name") == pin_name:
                            return p.get("Id")
        raise RuntimeError(f"pin {pin_name} of {marker} not found in graft")

    # ============ 3. floor = shroom cylinder, enlarged + grass textured ============
    cyl_mat = grafted_pin('Name="Cylinder"', "Material")
    cyl_entity = grafted_pin('Name="Cylinder"', "Entity")
    # enlarge top: Base Radius pad value
    for el in grafted:
        if el.tag == "Pad" and el.get("Comment") == "Base Radius":
            el.set("Value", CYL_RADIUS)
    ft, ft_path, ft_tex = file_texture("2600,1550", "..\\assert\\grass_tile.png")
    app_canvas.append(ft)
    tm, tm_tex, tm_out = texture_material("2820,1600")
    app_canvas.append(tm)
    add(ft_tex, tm_tex)
    add(tm_out, cyl_mat)          # grass material -> cylinder
    add(cyl_entity, GROUP_CHILD2) # cylinder -> scene floor slot
    print("floor: shroom cylinder, r=4m, grass texture")

    # ============ 4. mushrooms offset beside the robots ============
    shroom_group_out = grafted_pin('Name="Group (Spectral)"', "Output")
    off_grp, off_tr, off_child, off_out = entity_group("3050,2050")
    app_canvas.append(off_grp)
    tr, tr_in, tr_trans, tr_out = translate_node("3050,1950")
    app_canvas.append(tr)
    app_canvas.append(vec3_pad("pad_shroom_off", "mushroom offset (m)", "2820,1950", SHROOM_OFFSET))
    add(shroom_group_out, off_child)
    add(tr_out, off_tr)
    add(off_out, GROUP_CHILD4)
    print("mushrooms grafted with offset", SHROOM_OFFSET)

    # ============ 5. done ============
    # the shroom PointLight is intentionally NOT grafted (the Bunraku scene has its
    # own lighting); neither are its skybox Background, SceneWindow, RootScene, SkyboxLight.

    OUT.write_bytes(etree.tostring(base, xml_declaration=True, encoding="UTF-8"))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
