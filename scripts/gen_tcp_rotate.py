"""Generate test_vl_code/TCPRotate.vl — a Bunraku patch that rotates the robot around its TCP.

All NodeReference blocks are copied verbatim from the installed VL.Bunraku 1.0.3 nuget
(help/Overview/Example Motion Types.vl, help/Overview/HowTo Send Robot profiles via MQTT.vl)
and from VL.Bunraku.vl itself (LFO, Vector (Join)).

Chain: LFO -> Vector (Join).Y -> CartesianTarget.Orientation  (Position stays fixed)
       KR50R2500 -> RobotAssembly <- CartesianTarget
       RobotAssembly -> RobotVisualizer -> BunrakuSceneWindow

Run:  uv run python scripts/gen_tcp_rotate.py
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
    """Stable symbolic id -> fresh VL base62 id."""
    if name not in _ids:
        _ids[name] = vl_ids.new_vl_id()
    return _ids[name]


TEMPLATE = f"""<?xml version="1.0" encoding="utf-8"?>
<Document xmlns:p="property" xmlns:r="reflection" Id="{I('doc')}" LanguageVersion="2026.8.0-0158-gda117bc374" Version="0.128">
  <NugetDependency Id="{I('dep_corelib')}" Location="VL.CoreLib" />
  <NugetDependency Id="{I('dep_bunraku')}" Location="VL.Bunraku" Version="1.0.3" />
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
          <Pad Id="{I('pad_title')}" Bounds="100,60,420,30" ShowValueBox="true" isIOBox="true" Value="TCP Rotate — rotate the robot around its TCP (Bunraku)">
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="String" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:fontsize p:Type="Int32">15</p:fontsize>
              <p:stringtype p:Assembly="VL.Core" p:Type="VL.Core.StringType">Comment</p:stringtype>
            </p:ValueBoxSettings>
          </Pad>
          <Pad Id="{I('pad_note')}" Bounds="100,95,560,30" ShowValueBox="true" isIOBox="true" Value="Position is fixed; LFO drives Orientation.Y (cycles: 1 = one full turn), so the arm reorients around the tool centre point.">
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="String" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:fontsize p:Type="Int32">9</p:fontsize>
              <p:stringtype p:Assembly="VL.Core" p:Type="VL.Core.StringType">Comment</p:stringtype>
            </p:ValueBoxSettings>
          </Pad>
          <Node Bounds="140,320,45,19" Id="{I('lfo')}">
            <p:NodeReference LastCategoryFullName="Animation" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="LFO" />
            </p:NodeReference>
            <Pin Id="{I('lfo_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('lfo_clock')}" Name="Clock" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('lfo_newclock')}" Name="New Clock" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('lfo_period')}" Name="Period" Kind="InputPin" />
            <Pin Id="{I('lfo_pause')}" Name="Pause" Kind="InputPin" />
            <Pin Id="{I('lfo_reset')}" Name="Reset" Kind="ApplyPin" />
            <Pin Id="{I('lfo_phase')}" Name="Phase" Kind="OutputPin" />
            <Pin Id="{I('lfo_onnewcycle')}" Name="On New Cycle" Kind="OutputPin" />
            <Pin Id="{I('lfo_cycles')}" Name="Cycles" Kind="OutputPin" />
          </Node>
          <Pad Id="{I('pad_period')}" Comment="Period (s)" Bounds="140,270,44,16" ShowValueBox="true" isIOBox="true" Value="4">
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="Float32" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:minimum p:Type="Single">0.1</p:minimum>
              <p:stepsize p:Type="Single">0.5</p:stepsize>
            </p:ValueBoxSettings>
          </Pad>
          <Pad Id="{I('pad_pause')}" Comment="Pause" Bounds="140,380,35,35" ShowValueBox="true" isIOBox="true" Value="false">
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="ImmutableTypeFlag" Name="Boolean" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:buttonmode p:Assembly="VL.UI.Forms" p:Type="VL.HDE.PatchEditor.Editors.ButtonModeEnum">Toggle</p:buttonmode>
            </p:ValueBoxSettings>
          </Pad>
          <Node Bounds="330,340,46,19" Id="{I('vjoin')}">
            <p:NodeReference LastCategoryFullName="3D.Vector3" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="Vector3Type" Name="Vector3" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="Vector (Join)" />
            </p:NodeReference>
            <Pin Id="{I('vjoin_x')}" Name="X" Kind="InputPin" DefaultValue="0" />
            <Pin Id="{I('vjoin_y')}" Name="Y" Kind="InputPin" />
            <Pin Id="{I('vjoin_z')}" Name="Z" Kind="InputPin" DefaultValue="0" />
            <Pin Id="{I('vjoin_out')}" Name="Output" Kind="StateOutputPin" />
          </Node>
          <Pad Id="{I('pad_position')}" Comment="Position (mm)" Bounds="470,200,52,43" ShowValueBox="true" isIOBox="true" Value="472, 1010, -69">
            <p:TypeAnnotation LastCategoryFullName="3D" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="Vector3" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:stepsize p:Type="Single">10</p:stepsize>
            </p:ValueBoxSettings>
          </Pad>
          <Node Bounds="470,380,88,19" Id="{I('ctarget')}">
            <p:NodeReference LastCategoryFullName="Main.Target" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="CartesianTarget" />
            </p:NodeReference>
            <Pin Id="{I('ctarget_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('ctarget_pos')}" Name="Position" Kind="InputPin" />
            <Pin Id="{I('ctarget_ori')}" Name="Orientation" Kind="InputPin" />
            <Pin Id="{I('ctarget_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          <Node Bounds="470,560,76,19" Id="{I('robot')}">
            <p:NodeReference LastCategoryFullName="Bunraku.Robot.Iontech" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="Category" Name="Iontech" />
              <Choice Kind="ProcessAppFlag" Name="KR50R2500" />
            </p:NodeReference>
            <Pin Id="{I('robot_data')}" Name="RobotData" Kind="OutputPin" />
            <Pin Id="{I('robot_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
          </Node>
          <Node Bounds="740,470,87,19" Id="{I('assembly')}">
            <p:NodeReference LastCategoryFullName="Bunraku.Robot" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="RobotAssembly" />
            </p:NodeReference>
            <Pin Id="{I('assembly_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('assembly_data')}" Name="RobotData" Kind="InputPin" />
            <Pin Id="{I('assembly_transform')}" Name="Transform" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('assembly_target')}" Name="TargetHandlerStrategy" Kind="InputPin" />
            <Pin Id="{I('assembly_out')}" Name="Output" Kind="StateOutputPin" />
            <Pin Id="{I('assembly_fk')}" Name="ForwardKinematic" Kind="OutputPin" IsHidden="true" />
            <Pin Id="{I('assembly_flange')}" Name="FlangPosition" Kind="OutputPin" IsHidden="true" />
          </Node>
          <Node Bounds="740,640,67,26" Id="{I('th_axis')}">
            <p:NodeReference LastCategoryFullName="Main.Traget.TargetHandler" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="ClassType" Name="TargetHandler" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="AxisValues" />
            </p:NodeReference>
            <Pin Id="{I('th_axis_in')}" Name="Input" Kind="StateInputPin" />
            <Pin Id="{I('th_axis_out')}" Name="Output" Kind="StateOutputPin" />
            <Pin Id="{I('th_axis_values')}" Name="AxisValues" Kind="OutputPin" />
          </Node>
          <Pad Id="{I('pad_axis')}" Comment="AxisValues (live)" Bounds="860,610,56,111" ShowValueBox="true" isIOBox="true">
            <p:ValueBoxSettings>
              <p:maxvisibleentries p:Type="Int32">6</p:maxvisibleentries>
            </p:ValueBoxSettings>
          </Pad>
          <Node Bounds="740,790,185,19" Id="{I('vsettings')}">
            <p:NodeReference LastCategoryFullName="Bunraku.Visulization" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="VisualizationSettings" />
            </p:NodeReference>
            <Pin Id="{I('vsettings_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('vsettings_out')}" Name="Output" Kind="StateOutputPin" />
            <Pin Id="{I('vsettings_constant')}" Name="Constant" Kind="InputPin" DefaultValue="False" />
            <Pin Id="{I('vsettings_constantcolor')}" Name="ConstantColor" Kind="InputPin" />
            <Pin Id="{I('vsettings_xray')}" Name="XRay" Kind="InputPin" DefaultValue="False" />
            <Pin Id="{I('vsettings_xraycolor')}" Name="XRayColor" Kind="InputPin" />
            <Pin Id="{I('vsettings_bbox')}" Name="BoundingBox" Kind="InputPin" />
            <Pin Id="{I('vsettings_shadow')}" Name="IsShadowCaster" Kind="InputPin" />
            <Pin Id="{I('vsettings_lightint')}" Name="LightIntensity" Kind="InputPin" DefaultValue="0.91" />
            <Pin Id="{I('vsettings_enablelight')}" Name="EnableLight" Kind="InputPin" DefaultValue="True" />
            <Pin Id="{I('vsettings_flanggimbal')}" Name="FlangGimbal" Kind="InputPin" DefaultValue="True" />
            <Pin Id="{I('vsettings_basegimbal')}" Name="BaseGimbal" Kind="InputPin" DefaultValue="True" />
          </Node>
          <Node Bounds="1010,480,88,19" Id="{I('visualizer')}">
            <p:NodeReference LastCategoryFullName="Bunraku.RobotState" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="Category" Name="RobotState" NeedsToBeDirectParent="true">
                <p:OuterCategoryReference Kind="Category" Name="Bunraku" NeedsToBeDirectParent="true" />
              </CategoryReference>
              <Choice Kind="ProcessAppFlag" Name="RobotVisualizer" />
            </p:NodeReference>
            <Pin Id="{I('visualizer_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('visualizer_in')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('visualizer_settings')}" Name="Settings" Kind="InputPin" />
            <Pin Id="{I('visualizer_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          <Node Bounds="1010,700,116,19" Id="{I('scenesettings')}">
            <p:NodeReference LastCategoryFullName="Main.Visulization" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="BunrakuSceneSettings" />
            </p:NodeReference>
            <Pin Id="{I('scenesettings_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('scenesettings_cave')}" Name="EnableCave" Kind="InputPin" />
            <Pin Id="{I('scenesettings_cavecolour')}" Name="CaveColour" Kind="InputPin" />
            <Pin Id="{I('scenesettings_grid')}" Name="EnableSceneGrid" Kind="InputPin" DefaultValue="True" />
            <Pin Id="{I('scenesettings_out')}" Name="Output" Kind="StateOutputPin" />
          </Node>
          <Node Bounds="1260,560,115,19" Id="{I('scenewindow')}">
            <p:NodeReference LastCategoryFullName="Main.Visulization" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="BunrakuSceneWindow" />
            </p:NodeReference>
            <Pin Id="{I('scenewindow_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('scenewindow_child')}" Name="Child" Kind="InputPin" />
            <Pin Id="{I('scenewindow_lights')}" Name="Lights" Kind="InputPin" />
            <Pin Id="{I('scenewindow_defcam')}" Name="DefaultCamera" Kind="InputPin" DefaultValue="True" />
            <Pin Id="{I('scenewindow_cam')}" Name="Camera" Kind="InputPin" />
            <Pin Id="{I('scenewindow_extra')}" Name="ShowAdditionalRenderWindow" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('scenewindow_settings')}" Name="Settings" Kind="InputPin" />
          </Node>
        </Canvas>
        <Patch Id="{I('create')}" Name="Create" />
        <Patch Id="{I('update')}" Name="Update" />
        <ProcessDefinition Id="{I('processdef')}">
          <Fragment Id="{I('frag_create')}" Patch="{I('create')}" Enabled="true" />
          <Fragment Id="{I('frag_update')}" Patch="{I('update')}" Enabled="true" />
        </ProcessDefinition>
        <Link Id="{I('lnk1')}" Ids="{I('lfo_phase')},{I('vjoin_y')}" />
        <Link Id="{I('lnk2')}" Ids="{I('pad_period')},{I('lfo_period')}" />
        <Link Id="{I('lnk3')}" Ids="{I('pad_pause')},{I('lfo_pause')}" />
        <Link Id="{I('lnk4')}" Ids="{I('vjoin_out')},{I('ctarget_ori')}" />
        <Link Id="{I('lnk5')}" Ids="{I('pad_position')},{I('ctarget_pos')}" />
        <Link Id="{I('lnk6')}" Ids="{I('ctarget_out')},{I('assembly_target')}" />
        <Link Id="{I('lnk7')}" Ids="{I('ctarget_out')},{I('th_axis_in')}" />
        <Link Id="{I('lnk8')}" Ids="{I('th_axis_values')},{I('pad_axis')}" />
        <Link Id="{I('lnk9')}" Ids="{I('robot_data')},{I('assembly_data')}" />
        <Link Id="{I('lnk10')}" Ids="{I('assembly_out')},{I('visualizer_in')}" />
        <Link Id="{I('lnk11')}" Ids="{I('vsettings_out')},{I('visualizer_settings')}" />
        <Link Id="{I('lnk12')}" Ids="{I('visualizer_out')},{I('scenewindow_child')}" />
        <Link Id="{I('lnk13')}" Ids="{I('scenesettings_out')},{I('scenewindow_settings')}" />
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
    for link in root.iter("Link"):
        for endpoint in link.get("Ids", "").split(","):
            if endpoint not in ids:
                errors.append(f"link {link.get('Id')} references missing id {endpoint}")
    frags = {f.get("Patch") for f in root.iter("Fragment")}
    patch_ids = {p.get("Id") for p in root.iter("Patch")}
    for f in frags:
        if f not in patch_ids:
            errors.append(f"fragment references missing patch {f}")
    return errors


def main() -> int:
    out = ROOT / "test_vl_code" / "TCPRotate.vl"
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
