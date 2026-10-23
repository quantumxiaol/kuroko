"""Generate vlsrc/MimosaTalk.vl — Mimosa.vl + a polling bridge to the local Python service.

What it does:
- copies vlsrc/Mimosa.vl (the simple, single-Application patch)
- adds a NuGet dependency on VL.SimpleHTTP 1.3.1
- disconnects the local shy/dance pose (Cons.Result -> AxisTarget.AxisValues)
- adds: LFO(0.2s) -> Request (Async) GET localhost:8765/robot/pose
         -> Split (String) "," -> TryParse -> AxisTarget.AxisValues

The local distance/pose nodes stay in place, just unconnected, so switching back is
one link. The Python bridge interpolates the action keyframes and serves the current
7 joint angles; vvvv only follows them.

Run:  uv run --with lxml python scripts/gen_mimosa_talk.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
IDS_PY = (
    ROOT
    / ".agent/skills/vvvv-fileformat/scripts/vl-patch-manipulator/src/vl_patch_manipulator/ids.py"
)

spec = importlib.util.spec_from_file_location("vl_ids", IDS_PY)
vl_ids = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vl_ids)

BASE = ROOT / "vlsrc" / "Mimosa.vl"
OUT = ROOT / "vlsrc" / "MimosaTalk.vl"

P = "{property}"

# in Mimosa.vl: Cons.Result -> AxisTarget.AxisValues
LOCAL_POSE_LINK = "OeeXaIPpvktNgKf1rzisVO"
AXIS_TARGET_VALUES = "U6qYrrRZRmkOM5IhePg0J6"

BRIDGE_URL = "http://127.0.0.1:8765/robot/pose"


def new_id() -> str:
    return vl_ids.new_vl_id()


def pin(parent: etree._Element, name: str, kind: str, default: str | None = None,
        hidden: bool = False) -> str:
    attrs = {"Id": new_id(), "Name": name, "Kind": kind}
    if default is not None:
        attrs["DefaultValue"] = default
    if hidden:
        attrs["IsHidden"] = "true"
    el = etree.SubElement(parent, "Pin", **attrs)
    return el.get("Id")


def request_async(bounds: str) -> tuple[etree._Element, dict[str, str]]:
    """Verbatim shape of VL.SimpleHTTP's Request (Async) as used in its help patches."""
    node = etree.Element("Node", Bounds=bounds, Id=new_id())
    ref = etree.SubElement(node, P + "NodeReference")
    ref.set("LastCategoryFullName", "IO.HTTP")
    ref.set("LastDependency", "VL.SimpleHTTP.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="Request (Async)")
    pins: dict[str, str] = {}
    for name, kind, hidden in (
        ("Node Context", "InputPin", True),
        ("URL", "InputPin", False),
        ("Headers", "InputPin", False),
        ("Body", "InputPin", False),
        ("Method", "InputPin", False),
        ("Timeout", "InputPin", False),
        ("Refresh", "InputPin", False),
        ("Content", "OutputPin", False),
        ("Raw Bytes", "OutputPin", True),
        ("Status Code", "OutputPin", False),
        ("Status Description", "OutputPin", False),
        ("Is Successful", "OutputPin", False),
        ("On Data", "OutputPin", False),
        ("In Progress", "OutputPin", False),
    ):
        pins[name] = pin(node, name, kind, hidden=hidden)
    return node, pins


def split_string(bounds: str) -> tuple[etree._Element, dict[str, str]]:
    node = etree.Element("Node", Bounds=bounds, Id=new_id())
    ref = etree.SubElement(node, P + "NodeReference")
    ref.set("LastCategoryFullName", "Primitive.String")
    ref.set("LastSymbolSource", "CoreLibBasics.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    etree.SubElement(ref, "Choice", Kind="OperationCallFlag", Name="Split (String)")
    pins = {
        "Input": pin(node, "Input", "StateInputPin"),
        "Separator": pin(node, "Separator", "InputPin", ","),
        "Options": pin(node, "Options", "InputPin"),
        "Output": pin(node, "Output", "OutputPin"),
    }
    return node, pins


def try_parse(bounds: str) -> tuple[etree._Element, dict[str, str]]:
    node = etree.Element("Node", Bounds=bounds, Id=new_id())
    ref = etree.SubElement(node, P + "NodeReference")
    ref.set("LastCategoryFullName", "System.Conversion")
    ref.set("LastSymbolSource", "CoreLibBasics.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    etree.SubElement(ref, "Choice", Kind="OperationCallFlag", Name="TryParse")
    pins = {
        "String": pin(node, "String", "InputPin"),
        "Value": pin(node, "Value", "OutputPin"),
        "Success": pin(node, "Success", "OutputPin"),
    }
    return node, pins


def lfo(bounds: str) -> tuple[etree._Element, dict[str, str]]:
    node = etree.Element("Node", Bounds=bounds, Id=new_id())
    ref = etree.SubElement(node, P + "NodeReference")
    ref.set("LastCategoryFullName", "Animation")
    ref.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ref, "Choice", Kind="NodeFlag", Name="Node", Fixed="true")
    etree.SubElement(ref, "Choice", Kind="ProcessAppFlag", Name="LFO")
    pins = {
        "Node Context": pin(node, "Node Context", "InputPin", hidden=True),
        "Clock": pin(node, "Clock", "InputPin", hidden=True),
        "New Clock": pin(node, "New Clock", "InputPin", hidden=True),
        "Period": pin(node, "Period", "InputPin"),
        "Pause": pin(node, "Pause", "InputPin"),
        "Reset": pin(node, "Reset", "ApplyPin"),
        "Phase": pin(node, "Phase", "OutputPin"),
        "On New Cycle": pin(node, "On New Cycle", "OutputPin"),
        "Cycles": pin(node, "Cycles", "OutputPin"),
    }
    return node, pins


def float_pad(bounds: str, value: str, comment: str) -> etree._Element:
    pad = etree.Element(
        "Pad", Id=new_id(), Bounds=bounds, ShowValueBox="true", isIOBox="true",
        Value=value, Comment=comment,
    )
    ta = etree.SubElement(pad, P + "TypeAnnotation")
    ta.set("LastCategoryFullName", "Primitive")
    ta.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ta, "Choice", Kind="TypeFlag", Name="Float32")
    settings = etree.SubElement(pad, P + "ValueBoxSettings")
    etree.SubElement(settings, P + "stepsize", **{P + "Type": "Single"}).text = "0.01"
    return pad


def string_pad(bounds: str, value: str, comment: str | None = None,
               fontsize: str | None = None) -> etree._Element:
    pad = etree.Element(
        "Pad", Id=new_id(), Bounds=bounds, ShowValueBox="true", isIOBox="true", Value=value
    )
    if comment:
        pad.set("Comment", comment)
    ta = etree.SubElement(pad, P + "TypeAnnotation")
    ta.set("LastCategoryFullName", "Primitive")
    ta.set("LastDependency", "VL.CoreLib.vl")
    etree.SubElement(ta, "Choice", Kind="TypeFlag", Name="String")
    if fontsize:
        settings = etree.SubElement(pad, P + "ValueBoxSettings")
        etree.SubElement(settings, P + "fontsize", **{P + "Type": "Int32"}).text = fontsize
        etree.SubElement(
            settings, P + "stringtype",
            **{P + "Assembly": "VL.Core", P + "Type": "VL.Core.StringType"},
        ).text = "Comment"
    return pad


def link(patch: etree._Element, source: str, sink: str) -> None:
    etree.SubElement(patch, "Link", Id=new_id(), Ids=f"{source},{sink}")


def main() -> int:
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(BASE), parser)
    root = tree.getroot()

    root.set("Id", new_id())

    # dependency on the HTTP nodes
    if not any(d.get("Location") == "VL.SimpleHTTP" for d in root.iter("NugetDependency")):
        etree.SubElement(
            root, "NugetDependency", Id=new_id(), Location="VL.SimpleHTTP", Version="1.3.1"
        )
        print("added dependency VL.SimpleHTTP 1.3.1")

    app = next(n for n in root.iter("Node") if n.get("Name") == "Application")
    inner = app.find("Patch")
    canvas = inner.find("Canvas")

    # drop the local pose -> AxisTarget link
    removed = None
    for candidate in list(root.iter("Link")):
        if candidate.get("Id") == LOCAL_POSE_LINK:
            candidate.getparent().remove(candidate)
            removed = candidate
            break
    if removed is None:
        print(f"ERROR: link {LOCAL_POSE_LINK} not found")
        return 1
    print("disconnected Cons.Result -> AxisTarget.AxisValues")

    # --- nodes ---
    lfo_node, lfo_pins = lfo("1300,880,45,19")
    req_node, req_pins = request_async("1440,880,105,19")
    split_node, split_pins = split_string("1650,880,45,19")
    parse_node, parse_pins = try_parse("1800,880,55,19")

    # --- pads ---
    url_pad = string_pad("1440,840,330,16", BRIDGE_URL)
    period_pad = float_pad("1300,840,44,16", "0.2", "poll period (s)")
    heading = string_pad(
        "1100,700,620,31",
        "Python bridge — 对话 → 动作 → 7 轴",
        fontsize="15",
    )
    note = string_pad(
        "1100,735,780,30",
        "先启动 uv run kuroko-bridge 再按 play。GET /robot/pose 返回 j1..j7；"
        "左边原来的 distance → shy/dance 链保持不动，改回本地行为时把 Cons.Result 重新接回 AxisTarget.AxisValues。",
        fontsize="9",
    )

    for element in (heading, note, url_pad, period_pad, lfo_node, req_node, split_node, parse_node):
        canvas.append(element)

    # --- links ---
    link(inner, period_pad.get("Id"), lfo_pins["Period"])
    link(inner, lfo_pins["On New Cycle"], req_pins["Refresh"])
    link(inner, url_pad.get("Id"), req_pins["URL"])
    link(inner, req_pins["Content"], split_pins["Input"])
    link(inner, split_pins["Output"], parse_pins["String"])
    link(inner, parse_pins["Value"], AXIS_TARGET_VALUES)

    # --- sanity checks ---
    ids = [el.get("Id") for el in root.iter() if el.get("Id")]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        print("ERROR duplicate ids:", duplicates)
        return 1
    endpoints = {el.get("Id") for el in root.iter() if el.tag in ("Node", "Pad", "ControlPoint")}
    endpoints |= {
        p.get("Id")
        for el in root.iter("Node", "Pad")
        for p in el.findall("Pin")
        if p.get("Id")
    }
    for el in root.iter("Link"):
        for endpoint in (el.get("Ids") or "").split(","):
            if endpoint not in endpoints:
                print(f"ERROR unresolved link endpoint {endpoint!r} in {el.get('Id')}")
                return 1

    etree.indent(tree, space="  ")
    body = etree.tostring(tree, xml_declaration=False, encoding="utf-8")
    OUT.write_bytes(b'<?xml version="1.0" encoding="utf-8"?>\n' + body)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
