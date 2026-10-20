"""Generate test_vl_code/MimosaVisioni.vl — pure depth-based proximity input for Mimosa.vl.

No person detection at all: a RealSense D435i measures the nearest distance in a
center-row "interaction zone" (5 Pipet probes) of the depth image. Anything entering
the zone (person, hand, torso, scarf...) lowers the distance. HoleFillingFilter is
enabled so invalid (zero) depth pixels get filled instead of reading as false zeros.

Chain:
  RealSense (device)
    ├─ ColorImage -> FromImage -> DrawImage (RGB view, left)          ┐
    └─ HoleFillingFilter ─┬─ ColorizedDepthImage -> DrawImage (right) ├ Group -> Renderer (Skia)
                          └─ Pipet x5 (center row) -> Min x4 -> Damper -> Distance (m)

Feed Distance into Mimosa.vl's MapClamp Input (replacing the simulated IOBox).
Verify with a tape measure at 1m / 2m / 3m before driving the robot.

Requires: VL.Devices.RealSense (1.11.0), VL.Skia. D435i on a USB 3 port.
Node references copied from the VL.Devices.RealSense 1.11.0 help patches.

Run:  uv run python scripts/gen_mimosa_visioni.py
"""

import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDS_PY = ROOT / ".agent/skills/vvvv-fileformat/scripts/vl-patch-manipulator/src/vl_patch_manipulator/ids.py"

spec = importlib.util.spec_from_file_location("vl_ids", IDS_PY)
vl_ids = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vl_ids)

_ids: dict[str, str] = {}


def I(name: str) -> str:
    if name not in _ids:
        _ids[name] = vl_ids.new_vl_id()
    return _ids[name]


def rs_node(name: str, bounds: str, pins: list[tuple[str, str, str | None]], process: str | None = None) -> str:
    """Devices.RealSense node. pins: list of (pin name, kind, default)."""
    pin_xml = "\n            ".join(
        f'<Pin Id="{I(name + "_" + pname)}" Name="{pname}" Kind="{kind}"'
        + (f' DefaultValue="{d}"' if d is not None else "") + " />"
        for pname, kind, d in pins
    )
    proc = process or name
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Devices.RealSense" LastSymbolSource="VL.Devices.RealSense.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="{proc}" />
            </p:NodeReference>
            {pin_xml}
          </Node>"""


def skia_from_image(name: str, bounds: str) -> str:
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Graphics.Skia.Imaging" LastSymbolSource="VL.Skia.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="FromImage" />
              <CategoryReference Kind="Category" Name="Imaging" NeedsToBeDirectParent="true">
                <p:OuterCategoryReference Kind="Category" Name="Skia" NeedsToBeDirectParent="true" />
              </CategoryReference>
            </p:NodeReference>
            <Pin Id="{I(name + '_in')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I(name + '_discard')}" Name="Discard Higher Bits" Kind="InputPin" />
            <Pin Id="{I(name + '_out')}" Name="Result" Kind="OutputPin" />
          </Node>"""


def draw_image(name: str, bounds: str, pos: str) -> str:
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Graphics.Skia.Layers" LastSymbolSource="VL.Skia.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="DrawImage" />
            </p:NodeReference>
            <Pin Id="{I(name + '_img')}" Name="Image" Kind="InputPin" />
            <Pin Id="{I(name + '_pos')}" Name="Position" Kind="InputPin" DefaultValue="{pos}" />
            <Pin Id="{I(name + '_size')}" Name="Size" Kind="InputPin" />
            <Pin Id="{I(name + '_sizemode')}" Name="Size Mode" Kind="InputPin" DefaultValue="OriginalSize">
              <p:TypeAnnotation LastCategoryFullName="Graphics.Skia.Imaging" LastSymbolSource="VL.Skia.vl">
                <Choice Kind="TypeFlag" Name="SizeMode" />
              </p:TypeAnnotation>
            </Pin>
            <Pin Id="{I(name + '_anchor')}" Name="Anchor" Kind="InputPin" DefaultValue="TopLeft">
              <p:TypeAnnotation LastCategoryFullName="2D" LastSymbolSource="CoreLibBasics.vl">
                <Choice Kind="TypeFlag" Name="RectangleAnchor" />
              </p:TypeAnnotation>
            </Pin>
            <Pin Id="{I(name + '_paint')}" Name="Paint" Kind="InputPin" />
            <Pin Id="{I(name + '_enabled')}" Name="Enabled" Kind="InputPin" />
            <Pin Id="{I(name + '_out')}" Name="Output" Kind="OutputPin" />
            <Pin Id="{I(name + '_bounds')}" Name="Actual Bounds" Kind="OutputPin" />
          </Node>"""


def renderer(name: str, bounds_attr: str, node_bounds: str) -> str:
    return f"""<Node Bounds="{node_bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Graphics.Skia" LastSymbolSource="VL.Skia.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="Renderer" />
              <CategoryReference Kind="Category" Name="Skia" NeedsToBeDirectParent="true" />
            </p:NodeReference>
            <Pin Id="{I(name + '_bounds')}" Name="Bounds" Kind="InputPin" DefaultValue="{bounds_attr}">
              <p:TypeAnnotation LastCategoryFullName="System.Drawing" LastSymbolSource="System.Drawing.dll">
                <Choice Kind="TypeFlag" Name="Rectangle" />
              </p:TypeAnnotation>
            </Pin>
            <Pin Id="{I(name + '_btd')}" Name="Bound to Document" Kind="InputPin" DefaultValue="True">
              <p:TypeAnnotation LastCategoryFullName="Primitive" LastSymbolSource="CoreLibBasics.vl">
                <Choice Kind="TypeFlag" Name="Boolean" />
              </p:TypeAnnotation>
            </Pin>
            <Pin Id="{I(name + '_input')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I(name + '_color')}" Name="Color" Kind="InputPin" />
            <Pin Id="{I(name + '_clear')}" Name="Clear" Kind="InputPin" />
            <Pin Id="{I(name + '_space')}" Name="Space" Kind="InputPin" DefaultValue="DIPTopLeft">
              <p:TypeAnnotation LastCategoryFullName="VL.Skia" LastSymbolSource="VL.Skia.dll">
                <Choice Kind="TypeFlag" Name="CommonSpace" />
              </p:TypeAnnotation>
            </Pin>
            <Pin Id="{I(name + '_cursor')}" Name="Show Cursor" Kind="InputPin" />
            <Pin Id="{I(name + '_vsync')}" Name="VSync" Kind="InputPin" />
            <Pin Id="{I(name + '_enabled')}" Name="Enabled" Kind="InputPin" />
            <Pin Id="{I(name + '_form')}" Name="Form" Kind="OutputPin" />
            <Pin Id="{I(name + '_clientbounds')}" Name="ClientBounds" Kind="OutputPin" />
            <Pin Id="{I(name + '_time')}" Name="Render Time" Kind="OutputPin" />
          </Node>"""


def min2(name: str, bounds: str) -> str:
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Math" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="Min" />
            </p:NodeReference>
            <Pin Id="{I(name + '_in1')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I(name + '_in2')}" Name="Input 2" Kind="InputPin" />
            <Pin Id="{I(name + '_out')}" Name="Output" Kind="OutputPin" />
          </Node>"""


def f32pad(name: str, comment: str, bounds: str, value: str | None, **settings: str) -> str:
    v = f' Value="{value}"' if value is not None else ""
    s = "".join(f'<p:{k} p:Type="Single">{v2}</p:{k}>' for k, v2 in settings.items())
    ann = f"""<p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="Float32" />
            </p:TypeAnnotation>"""
    vs = f"<p:ValueBoxSettings>{s}</p:ValueBoxSettings>" if s else ""
    return f"""<Pad Id="{I(name)}" Comment="{comment}" Bounds="{bounds}" ShowValueBox="true" isIOBox="true"{v}>
            {ann}
            {vs}
          </Pad>"""


def vec2pad(name: str, comment: str, bounds: str, value: str) -> str:
    return f"""<Pad Id="{I(name)}" Comment="{comment}" Bounds="{bounds}" ShowValueBox="true" isIOBox="true" Value="{value}">
            <p:TypeAnnotation LastCategoryFullName="2D" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="Vector2" />
            </p:TypeAnnotation>
          </Pad>"""


def boolpad(name: str, comment: str, bounds: str, value: str) -> str:
    return f"""<Pad Id="{I(name)}" Comment="{comment}" Bounds="{bounds}" ShowValueBox="true" isIOBox="true" Value="{value}">
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="ImmutableTypeFlag" Name="Boolean" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:buttonmode p:Assembly="VL.UI.Forms" p:Type="VL.HDE.PatchEditor.Editors.ButtonModeEnum">Toggle</p:buttonmode>
            </p:ValueBoxSettings>
          </Pad>"""


def commentpad(name: str, bounds: str, text: str, fontsize: int = 9) -> str:
    return f"""<Pad Id="{I(name)}" Bounds="{bounds}" ShowValueBox="true" isIOBox="true" Value="{text}">
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="String" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:fontsize p:Type="Int32">{fontsize}</p:fontsize>
              <p:stringtype p:Assembly="VL.Core" p:Type="VL.Core.StringType">Comment</p:stringtype>
            </p:ValueBoxSettings>
          </Pad>"""


def damper(name: str, bounds: str, filter_time: str) -> str:
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Animation" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="Damper" />
            </p:NodeReference>
            <Pin Id="{I(name + '_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I(name + '_clock')}" Name="Clock" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I(name + '_newclock')}" Name="New Clock" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I(name + '_goto')}" Name="Goto Position" Kind="InputPin" />
            <Pin Id="{I(name + '_filter')}" Name="Filter Time" Kind="InputPin" DefaultValue="{filter_time}" />
            <Pin Id="{I(name + '_cyclic')}" Name="Cyclic" Kind="InputPin" />
            <Pin Id="{I(name + '_jump')}" Name="Jump" Kind="InputPin" />
            <Pin Id="{I(name + '_force')}" Name="Force New Func" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I(name + '_pos')}" Name="Position" Kind="OutputPin" />
            <Pin Id="{I(name + '_vel')}" Name="Velocity" Kind="OutputPin" />
            <Pin Id="{I(name + '_acc')}" Name="Acceleration" Kind="OutputPin" />
            <Pin Id="{I(name + '_func')}" Name="Function" Kind="OutputPin" IsHidden="true" />
            <Pin Id="{I(name + '_changed')}" Name="Has Changed" Kind="OutputPin" />
          </Node>"""


def link(n: str, src: str, dst: str) -> str:
    return f'<Link Id="{I("lnk" + n)}" Ids="{I(src)},{I(dst)}" />'


PIPETS = [("p1", "64, 320"), ("p2", "149, 320"), ("p3", "235, 320"), ("p4", "320, 320"), ("p5", "405, 320"), ("p6", "491, 320"), ("p7", "576, 320")]

pipet_nodes = "\n          ".join(
    rs_node(nm, f"{420 + i * 110},760", [("Input", "InputPin", None), ("Position", "InputPin", None), ("Output", "OutputPin", None)], process="Pipet")
    for i, (nm, _) in enumerate(PIPETS)
)
pipet_pads = "\n          ".join(
    vec2pad(nm + "_pos", f"probe {i+1}", f"{420 + i * 110},700", pos)
    for i, (nm, pos) in enumerate(PIPETS)
)
pipet_displays = "\n          ".join(
    f32pad(nm + "_val", f"probe {i+1} (m)", f"{420 + i * 110},830", None)
    for i, (nm, _) in enumerate(PIPETS)
)

# pairwise Min reduction tree over the probe outputs
def build_min_tree() -> tuple[list[str], str]:
    """Returns (node xml list, output pin symbol of the tree root)."""
    nodes: list[str] = []
    level = [f"p{i+1}_Output" for i in range(len(PIPETS))]
    rnd = 0
    while len(level) > 1:
        nxt: list[str] = []
        for j in range(0, len(level) - 1, 2):
            rnd += 1
            nm = f"min{rnd}"
            nodes.append((nm, level[j], level[j + 1]))
            nxt.append(nm + "_out")
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    xml = "\n          ".join(min2(nm, f"{1250 + k * 120},{700 + k * 60}") for k, (nm, _, _) in enumerate(nodes))
    return xml, nodes, level[0]

_min_xml, MIN_NODES, MIN_ROOT = build_min_tree()
MIN_XML = _min_xml

TEMPLATE = f"""<?xml version="1.0" encoding="utf-8"?>
<Document xmlns:p="property" xmlns:r="reflection" Id="{I('doc')}" LanguageVersion="2026.8.0-0158-gda117bc374" Version="0.128">
  <NugetDependency Id="{I('dep_corelib')}" Location="VL.CoreLib" />
  <NugetDependency Id="{I('dep_rs')}" Location="VL.Devices.RealSense" Version="1.11.0" />
  <NugetDependency Id="{I('dep_skia')}" Location="VL.Skia" />
  <Patch Id="{I('rootpatch')}">
    <Canvas Id="{I('rootcanvas')}" DefaultCategory="Main" CanvasType="FullCategory" />
    <!--

    ************************ Application ************************

-->
    <Node Name="Application" Bounds="100,100" Id="{I('app')}">
      <p:NodeReference>
        <Choice Kind="ContainerDefinition" Name="Process" />
        <CategoryReference Kind="Category" Name="Primitive" />
      </p:NodeReference>
      <Patch Id="{I('apppatch')}">
        <Canvas Id="{I('appcanvas')}" CanvasType="Group">
          {commentpad('pad_title', '100,50,640,30', 'Mimosa Vision i — pure depth proximity (RealSense D435i, no person detection)', 15)}
          {commentpad('pad_note', '100,88,820,30', 'Nearest of 5 depth probes on the center row -> Distance (m). Anything entering the interaction zone triggers the shy response. Verify readings with a tape measure at 1m / 2m / 3m, then feed Distance into Mimosa.vl MapClamp Input. HoleFillingFilter fills invalid zero-depth pixels.')}

          {boolpad('pad_enabled', 'Enabled', '140,220,35,35', 'True')}
          <Node Bounds="140,300,145,19" Id="{I('rs')}">
            <p:NodeReference LastCategoryFullName="Devices.RealSense" LastSymbolSource="VL.Devices.RealSense.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="RealSense" />
            </p:NodeReference>
            <Pin Id="{I('rs_device')}" Name="Device" Kind="InputPin" />
            <Pin Id="{I('rs_colorres')}" Name="Color Resolution" Kind="InputPin" />
            <Pin Id="{I('rs_depthres')}" Name="Depth Resolution" Kind="InputPin" />
            <Pin Id="{I('rs_options')}" Name="Options" Kind="InputPin" />
            <Pin Id="{I('rs_enabled')}" Name="Enabled" Kind="InputPin" />
            <Pin Id="{I('rs_out')}" Name="Output" Kind="OutputPin" />
            <Pin Id="{I('rs_profile')}" Name="Profile" Kind="OutputPin" />
            <Pin Id="{I('rs_error')}" Name="Error" Kind="OutputPin" />
          </Node>
          <Node Bounds="140,420,69,19" Id="{I('colorimg')}">
            <p:NodeReference LastCategoryFullName="Devices.RealSense" LastDependency="VL.Devices.RealSense.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="ColorImage" />
            </p:NodeReference>
            <Pin Id="{I('colorimg_in')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('colorimg_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          <Node Bounds="140,500,87,19" Id="{I('holefill')}">
            <p:NodeReference LastCategoryFullName="Devices.RealSense.DepthFilters" LastSymbolSource="VL.Devices.RealSense.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="HoleFillingFilter" />
            </p:NodeReference>
            <Pin Id="{I('holefill_in')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('holefill_mode')}" Name="Mode" Kind="InputPin" />
            <Pin Id="{I('holefill_enabled')}" Name="Enabled" Kind="InputPin" DefaultValue="True" />
            <Pin Id="{I('holefill_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          <Node Bounds="140,580,115,19" Id="{I('colorized')}">
            <p:NodeReference LastCategoryFullName="Devices.RealSense" LastSymbolSource="VL.Devices.RealSense.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="ColorizedDepthImage" />
            </p:NodeReference>
            <Pin Id="{I('colorized_in')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('colorized_preset')}" Name="Visual Preset" Kind="InputPin" />
            <Pin Id="{I('colorized_scheme')}" Name="Color Scheme" Kind="InputPin" />
            <Pin Id="{I('colorized_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          {skia_from_image('fi_rgb', '380,420')}
          {skia_from_image('fi_depth', '380,580')}
          {draw_image('di_rgb', '640,420', '0, 0')}
          {draw_image('di_depth', '640,580', '0, 0')}
          {renderer('renderer_rgb', '60, 60, 700, 560', '920,420')}
          {renderer('renderer_depth', '800, 60, 700, 560', '920,580')}

          {pipet_pads}
          {pipet_nodes}
          {pipet_displays}
          {MIN_XML}
          {damper('damper', '1560,760', '0.3')}
          {f32pad('pad_distance', 'Distance (m) → Mimosa MapClamp', '1760,740,80,16', None)}
          {commentpad('pad_note2', '420,860,620,40', 'Seven probes span a full row of the 640x480 depth frame (y=320, x=64..576) — anything entering the view side is caught. Move them to taste. If readings flicker at long range, raise Damper Filter Time. Upgrade path: threshold the depth image and take a low percentile instead of point probes.', 9)}
        </Canvas>
        <Patch Id="{I('create')}" Name="Create" />
        <Patch Id="{I('update')}" Name="Update" />
        <ProcessDefinition Id="{I('processdef')}">
          <Fragment Id="{I('frag_create')}" Patch="{I('create')}" Enabled="true" />
          <Fragment Id="{I('frag_update')}" Patch="{I('update')}" Enabled="true" />
        </ProcessDefinition>
        {link('en', 'pad_enabled', 'rs_enabled')}
        {link('c1', 'rs_out', 'colorimg_in')}
        {link('c2', 'colorimg_out', 'fi_rgb_in')}
        {link('c3', 'fi_rgb_out', 'di_rgb_img')}
        {link('h1', 'rs_out', 'holefill_in')}
        {link('h2', 'holefill_out', 'colorized_in')}
        {link('h3', 'colorized_out', 'fi_depth_in')}
        {link('h4', 'fi_depth_out', 'di_depth_img')}
        {link('g1', 'di_rgb_out', 'renderer_rgb_input')}
        {link('g2', 'di_depth_out', 'renderer_depth_input')}
        {chr(10).join(link(f'pp{i+1}', f'p{i+1}_pos', f'p{i+1}_Position') for i in range(7))}
        {chr(10).join(link(f'pi{i+1}', 'holefill_out', f'p{i+1}_Input') for i in range(7))}
        {chr(10).join(link(f'pv{i+1}', f'p{i+1}_Output', f'p{i+1}_val') for i in range(7))}
        {chr(10).join(link(f'mt{k}a', s1, nm + '_in1') for k, (nm, s1, s2) in enumerate(MIN_NODES))}
        {chr(10).join(link(f'mt{k}b', s2, nm + '_in2') for k, (nm, s1, s2) in enumerate(MIN_NODES))}
        {link('mout', MIN_ROOT, 'damper_goto')}
        {link('out', 'damper_pos', 'pad_distance')}
      </Patch>
    </Node>
  </Patch>
</Document>
"""


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    tree = ET.parse(path)
    root = tree.getroot()
    ids: dict[str, int] = {}
    for el in root.iter():
        el_id = el.get("Id")
        if el_id:
            ids[el_id] = ids.get(el_id, 0) + 1
    dupes = [k for k, v in ids.items() if v > 1]
    if dupes:
        errors.append(f"duplicate ids: {dupes}")
    bad = [k for k in ids if len(k) != 22 or not k.isalnum()]
    if bad:
        errors.append(f"malformed ids: {bad}")
    for lnk in root.iter("Link"):
        for endpoint in lnk.get("Ids", "").split(","):
            if endpoint not in ids:
                errors.append(f"link {lnk.get('Id')} references missing id {endpoint}")
    frags = {f.get("Patch") for f in root.iter("Fragment")}
    patch_ids = {p.get("Id") for p in root.iter("Patch")}
    for f in frags:
        if f not in patch_ids:
            errors.append(f"fragment references missing patch {f}")
    return errors


def main() -> int:
    out = ROOT / "test_vl_code" / "MimosaVisioni.vl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE, encoding="utf-8", newline="\n")
    errors = validate(out)
    print(f"wrote {out} ({out.stat().st_size} bytes, {len(_ids)} unique ids)")
    if errors:
        for e in errors:
            print("ERROR:", e)
        return 1
    print("basic validation passed (xml well-formed, ids unique, link endpoints resolve)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
