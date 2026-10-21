"""Add a second, synchronized robot arm to MimosaFinal.vl.

Design: the PRC server hosts one robot per client id — robot 2 is a second
KUKA_KR13R9003 (KRL) with Client Id "Bob", fed the SAME task as robot 1
(perfectly synchronized joint-space motion). The visual offset comes from an
entity Group with a Translation, so the two arms never overlap visually:

    KUKA_KR13R9003 #2 (Bob) -> RobotAssembly #2 <-[same Task source]
        -> VisualizePRCRobot #2 -> GroupB(Transform = +1.5m X) -> mainGroup.Child 3

Run:  uv run --with lxml python scripts/add_second_robot.py
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

ROBOT1 = "CCZ69X3RgSeMt0DSYZgCqc"        # KUKA_KR13R9003 (KRL)
ASSEMBLY1 = "I1lvc3r7PbFMtVQNuejxYL"     # RobotAssembly (PRC)
VIS1 = "PdikRUrHJDyLZOPibHTVfF"          # VisualizePRCRobot
MAIN_GROUP_CHILD3 = "RJfOjOXbQWeLG9dzhsi6uI"  # my entity group's free Child 3

OFFSET = (1.5, 0, 0)  # metres to the side


def nid() -> str:
    return vl_ids.new_vl_id()


def find_by_id(root, eid):
    for el in root.iter():
        if el.get("Id") == eid:
            return el
    return None


def clone_with_fresh_ids(el, idmap):
    """Deep-copy an element, assigning fresh ids to every Id and remapping Ids refs."""
    import copy
    new = copy.deepcopy(el)
    for node in new.iter():
        i = node.get("Id")
        if i is not None:
            node.set("Id", idmap.setdefault(i, nid()))
        ids = node.get("Ids")
        if ids is not None:
            node.set("Ids", ",".join(idmap.setdefault(p, nid()) for p in ids.split(",")))
    return new


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

    # find the task source feeding RobotAssembly1.Task
    a1 = find_by_id(root, ASSEMBLY1)
    a1_task_pin = next(p.get("Id") for p in a1.findall("Pin") if p.get("Name") == "Task")
    task_link = None
    for l in app_inner.findall("Link"):
        if l.get("Ids", "").endswith("," + a1_task_pin):
            task_link = l
            break
    if task_link is None:
        print("ERROR: RobotAssembly1.Task link not found")
        return 1
    task_source = task_link.get("Ids").split(",")[0]
    print(f"task source pin: {task_source[:8]} (will feed both assemblies)")

    idmap: dict[str, str] = {}

    # --- robot 2 ---
    robot1 = find_by_id(root, ROBOT1)
    robot2 = clone_with_fresh_ids(robot1, idmap)
    robot2.set("Bounds", "1666,1450,100,19")
    r2_out = r2_clientid = None
    for p in robot2.findall("Pin"):
        if p.get("Name") == "Output":
            r2_out = p.get("Id")
        if p.get("Name") == "Client Id":
            r2_clientid = p.get("Id")
    app_canvas.append(robot2)

    bob_pad = nid()
    pad = etree.Element("Pad", Id=bob_pad, Comment="Client Id", Bounds="1830,1400,35,15",
                        ShowValueBox="true", isIOBox="true", Value="Bob")
    ann = etree.SubElement(pad, f"{P}TypeAnnotation")
    ann.set("LastCategoryFullName", "Primitive")
    ann.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ann, "Choice", Kind="TypeFlag", Name="String")
    app_canvas.append(pad)

    # --- assembly 2 ---
    assembly2 = clone_with_fresh_ids(find_by_id(root, ASSEMBLY1), idmap)
    assembly2.set("Bounds", "1665,1560,87,19")
    a2_in = a2_task = a2_state = None
    for p in assembly2.findall("Pin"):
        nm = p.get("Name")
        if nm == "Input":
            a2_in = p.get("Id")
        elif nm == "Task":
            a2_task = p.get("Id")
        elif nm == "RobotState":
            a2_state = p.get("Id")
    app_canvas.append(assembly2)

    # --- visualizer 2 ---
    vis2 = clone_with_fresh_ids(find_by_id(root, VIS1), idmap)
    vis2.set("Bounds", "1666,1680,101,19")
    v2_in = v2_out = None
    for p in vis2.findall("Pin"):
        if p.get("Name") == "Input":
            v2_in = p.get("Id")
        elif p.get("Name") == "Output":
            v2_out = p.get("Id")
    app_canvas.append(vis2)

    # --- offset group B ---
    grp_b = nid()
    g = etree.Element("Node", Bounds="1900,1680,125,19", Id=grp_b)
    ref = etree.SubElement(g, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "Stride")
    ref.set("LastDependency", "VL.Stride.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    cat = etree.SubElement(ref, "CategoryReference", Kind="Category", Name="Stride")
    cat.set("NeedsToBeDirectParent", "true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="Group")
    etree.SubElement(g, "Pin", Id=nid(), Name="Node Context", Kind="InputPin", IsHidden="true")
    gb_tr = nid()
    etree.SubElement(g, "Pin", Id=gb_tr, Name="Transformation", Kind="InputPin")
    gb_child = nid()
    etree.SubElement(g, "Pin", Id=gb_child, Name="Child", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Child 2", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Child 3", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Child 4", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Name", Kind="InputPin")
    etree.SubElement(g, "Pin", Id=nid(), Name="Enabled", Kind="InputPin")
    gb_out = nid()
    etree.SubElement(g, "Pin", Id=gb_out, Name="Output", Kind="OutputPin")
    app_canvas.append(g)

    # --- translate (offset) ---
    t = etree.Element("Node", Bounds="1900,1580,76,19", Id=nid())
    ref = etree.SubElement(t, f"{P}NodeReference")
    ref.set("LastCategoryFullName", "3D.Transform")
    ref.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    cat2 = etree.SubElement(ref, "CategoryReference", Kind="Category", Name="Transform")
    cat2.set("NeedsToBeDirectParent", "true")
    outer = etree.SubElement(cat2, f"{P}OuterCategoryReference", Kind="Category", Name="3D")
    outer.set("NeedsToBeDirectParent", "true")
    etree.SubElement(ref, "Choice", Kind="OperationCallFlag", Name="Translate")
    etree.SubElement(t, "Pin", Id=nid(), Name="Input", Kind="InputPin")
    tr_trans = nid()
    etree.SubElement(t, "Pin", Id=tr_trans, Name="Translation", Kind="InputPin")
    tr_out = nid()
    etree.SubElement(t, "Pin", Id=tr_out, Name="Output", Kind="OutputPin")
    app_canvas.append(t)

    off_pad = nid()
    op = etree.Element("Pad", Id=off_pad, Comment="robot 2 offset (m)", Bounds="1665,1580,56,15",
                       ShowValueBox="true", isIOBox="true",
                       Value=f"{OFFSET[0]}, {OFFSET[1]}, {OFFSET[2]}")
    ann2 = etree.SubElement(op, f"{P}TypeAnnotation")
    ann2.set("LastCategoryFullName", "3D")
    ann2.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ann2, "Choice", Kind="TypeFlag", Name="Vector3")
    app_canvas.append(op)

    # --- wiring ---
    add = lambda s, d: app_inner.append(etree.Element("Link", Id=nid(), Ids=f"{s},{d}"))
    add(bob_pad, r2_clientid)          # Client Id "Bob"
    add(r2_out, a2_in)                 # robot2 -> assembly2.Input
    add(task_source, a2_task)          # SAME task -> assembly2.Task (synchronized)
    add(a2_state, v2_in)               # assembly2.RobotState -> visualizer2
    add(v2_out, gb_child)              # visualizer2 -> offset group
    add(off_pad, tr_trans)             # offset pad -> translate
    add(tr_out, gb_tr)                 # translate -> group transform
    add(gb_out, MAIN_GROUP_CHILD3)     # offset group -> main group Child 3
    print("wired robot 2 chain (Bob) with +1.5m X offset")

    FILE.write_bytes(etree.tostring(doc, xml_declaration=True, encoding="UTF-8"))
    print(f"wrote {FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
