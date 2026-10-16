"""Generate test_vl_code/Mimosa.vl — a "touch-me-not" (含羞草) robot patch for VL.Bunraku 1.0.3.

Behaviour:
- A distance input (simulated camera; swap the IOBox for a real camera node later)
  is mapped through MapClamp + Damper to a smoothed "openness" factor 0..1.
- Nobody near (openness -> 1): the robot dances — circular X/Z motion plus vertical bob
  (CartesianTarget).
- Someone approaches (openness -> 0): the arm folds into itself (AxisTarget, joint-space
  turtle pose) and TREMBLES — a fast ~5 Hz per-axis oscillation layered on the fold pose,
  reading as nervous shaking (great with a silk scarf on the arm). ToInt32(openness + 0.5)
  gives the switch index, so the flip happens at the midpoint of Near..Far with Damper
  debounce.

vvvv gamma has no automatic spread binops (beta-style), so the tremble is patched as
six scalar chains (fold_i + amp_i * sin(t)) merged into a Spread via one Cons node.

All NodeReference blocks are copied verbatim from the installed VL.Bunraku 1.0.3 nuget
(VL.Bunraku.vl internals + help/Overview patches). Adaptive math nodes (+, *(Scale),
SineWave, MapClamp, ToInt32, Cons) are used exactly as the library uses them.

Position convention for CartesianTarget: mm, Y up (as in "Example Motion Types").

Run:  uv run python scripts/gen_mimosa.py
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


def lfo(name: str, bounds: str, period: str) -> str:
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Animation" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="LFO" />
            </p:NodeReference>
            <Pin Id="{I(name + '_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I(name + '_clock')}" Name="Clock" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I(name + '_newclock')}" Name="New Clock" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I(name + '_period')}" Name="Period" Kind="InputPin" DefaultValue="{period}" />
            <Pin Id="{I(name + '_pause')}" Name="Pause" Kind="InputPin" />
            <Pin Id="{I(name + '_reset')}" Name="Reset" Kind="ApplyPin" />
            <Pin Id="{I(name + '_phase')}" Name="Phase" Kind="OutputPin" />
            <Pin Id="{I(name + '_onnewcycle')}" Name="On New Cycle" Kind="OutputPin" />
            <Pin Id="{I(name + '_cycles')}" Name="Cycles" Kind="OutputPin" />
          </Node>"""


def sinewave(name: str, bounds: str) -> str:
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Math" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="SineWave" />
            </p:NodeReference>
            <Pin Id="{I(name + '_phase')}" Name="Phase" Kind="InputPin" />
            <Pin Id="{I(name + '_out')}" Name="Output" Kind="OutputPin" />
          </Node>"""


def add(name: str, bounds: str, default2: str | None = None) -> str:
    d2 = f' DefaultValue="{default2}"' if default2 is not None else ""
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Math" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="+" />
            </p:NodeReference>
            <Pin Id="{I(name + '_in1')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I(name + '_in2')}" Name="Input 2" Kind="InputPin"{d2} />
            <Pin Id="{I(name + '_out')}" Name="Output" Kind="OutputPin" />
          </Node>"""


def scale(name: str, bounds: str, default_scalar: str | None = None) -> str:
    ds = f' DefaultValue="{default_scalar}"' if default_scalar is not None else ""
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Math" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="* (Scale)" />
            </p:NodeReference>
            <Pin Id="{I(name + '_in')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I(name + '_scalar')}" Name="Scalar" Kind="InputPin"{ds} />
            <Pin Id="{I(name + '_out')}" Name="Output" Kind="OutputPin" />
          </Node>"""


def f32pad(name: str, comment: str, bounds: str, value: str | None, **settings: str) -> str:
    v = f' Value="{value}"' if value is not None else ""
    s = "".join(f'<p:{k} p:Type="Single">{v2}</p:{k}>' for k, v2 in settings.items())
    if s:
        return f"""<Pad Id="{I(name)}" Comment="{comment}" Bounds="{bounds}" ShowValueBox="true" isIOBox="true"{v}>
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="Float32" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>{s}</p:ValueBoxSettings>
          </Pad>"""
    return f"""<Pad Id="{I(name)}" Comment="{comment}" Bounds="{bounds}" ShowValueBox="true" isIOBox="true"{v}>
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="Float32" />
            </p:TypeAnnotation>
          </Pad>"""


def vec3pad(name: str, comment: str, bounds: str, value: str) -> str:
    return f"""<Pad Id="{I(name)}" Comment="{comment}" Bounds="{bounds}" ShowValueBox="true" isIOBox="true" Value="{value}">
            <p:TypeAnnotation LastCategoryFullName="3D" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="Vector3" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:stepsize p:Type="Single">10</p:stepsize>
            </p:ValueBoxSettings>
          </Pad>"""


def link(n: int, src: str, dst: str) -> str:
    return f'<Link Id="{I("lnk" + str(n))}" Ids="{I(src)},{I(dst)}" />'


FOLD = ["0", "-15", "140", "0", "85", "0"]      # A1..A6 shy fold, validated via PRC sim (TCP 708mm out, 125mm up)
TREMBLE_AMP = ["0.8", "1.5", "1.5", "0.5", "2", "1"]  # per-axis tremble amplitude (deg)

fold_pads = "\n          ".join(
    f32pad(f"pad_fold_a{i+1}", f"Fold A{i+1} (deg)", f"1000,{770 + i*26},44,16", FOLD[i], stepsize="1")
    for i in range(6)
)
tremble_scales = "\n          ".join(
    scale(f"scale_t{i+1}", f"1340,{770 + i*26}", TREMBLE_AMP[i])
    for i in range(6)
)
tremble_adds = "\n          ".join(
    add(f"add_t{i+1}", f"1520,{770 + i*26}")
    for i in range(6)
)
cons_inputs = "\n            ".join(
    f'<Pin Id="{I("cons_in" + str(i+1))}" Name="Input{"" if i == 0 else " " + str(i+1)}" Kind="InputPin" />'
    for i in range(6)
)

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
          <Pad Id="{I('pad_title')}" Bounds="100,60,460,30" ShowValueBox="true" isIOBox="true" Value="Mimosa (含羞草) — shy robot that dances when nobody is near">
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="String" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:fontsize p:Type="Int32">15</p:fontsize>
              <p:stringtype p:Assembly="VL.Core" p:Type="VL.Core.StringType">Comment</p:stringtype>
            </p:ValueBoxSettings>
          </Pad>
          <Pad Id="{I('pad_note')}" Bounds="100,95,680,30" ShowValueBox="true" isIOBox="true" Value="Distance below Near: arm folds into itself and trembles. Above Far: it dances (circle + bob). Replace the distance IOBox with a real camera depth node when ready.">
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="String" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:fontsize p:Type="Int32">9</p:fontsize>
              <p:stringtype p:Assembly="VL.Core" p:Type="VL.Core.StringType">Comment</p:stringtype>
            </p:ValueBoxSettings>
          </Pad>

          {f32pad('pad_distance', 'Camera distance (m) [simulated]', '100,220,72,16', '2.5', minimum='0', maximum='5', stepsize='0.1')}
          {f32pad('pad_near', 'Near (m)', '100,310,44,16', '1.2', minimum='0', stepsize='0.1')}
          {f32pad('pad_far', 'Far (m)', '100,370,44,16', '2', minimum='0', stepsize='0.1')}
          <Node Bounds="260,300,85,19" Id="{I('mapclamp')}">
            <p:NodeReference LastCategoryFullName="Math.Ranges" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="MapClamp" />
            </p:NodeReference>
            <Pin Id="{I('mapclamp_in')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('mapclamp_inmin')}" Name="Input Minimum" Kind="InputPin" />
            <Pin Id="{I('mapclamp_inmax')}" Name="Input Maximum" Kind="InputPin" />
            <Pin Id="{I('mapclamp_outmin')}" Name="Output Minimum" Kind="InputPin" DefaultValue="0" />
            <Pin Id="{I('mapclamp_outmax')}" Name="Output Maximum" Kind="InputPin" DefaultValue="1" />
            <Pin Id="{I('mapclamp_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          <Node Bounds="430,300,65,19" Id="{I('damper')}">
            <p:NodeReference LastCategoryFullName="Animation" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="Damper" />
            </p:NodeReference>
            <Pin Id="{I('damper_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('damper_clock')}" Name="Clock" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('damper_newclock')}" Name="New Clock" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('damper_goto')}" Name="Goto Position" Kind="InputPin" />
            <Pin Id="{I('damper_filter')}" Name="Filter Time" Kind="InputPin" DefaultValue="0.8" />
            <Pin Id="{I('damper_cyclic')}" Name="Cyclic" Kind="InputPin" />
            <Pin Id="{I('damper_jump')}" Name="Jump" Kind="InputPin" />
            <Pin Id="{I('damper_force')}" Name="Force New Func" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('damper_pos')}" Name="Position" Kind="OutputPin" />
            <Pin Id="{I('damper_vel')}" Name="Velocity" Kind="OutputPin" />
            <Pin Id="{I('damper_acc')}" Name="Acceleration" Kind="OutputPin" />
            <Pin Id="{I('damper_func')}" Name="Function" Kind="OutputPin" IsHidden="true" />
            <Pin Id="{I('damper_changed')}" Name="Has Changed" Kind="OutputPin" />
          </Node>
          {f32pad('pad_openness', 'openness (0 shy .. 1 dance)', '430,240,72,16', None)}
          {add('add_half', '600,330', '0.5')}
          <Node Bounds="770,330,52,19" Id="{I('toint')}">
            <p:NodeReference LastCategoryFullName="System.Conversion" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="ToInt32" />
            </p:NodeReference>
            <Pin Id="{I('toint_in')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('toint_result')}" Name="Result" Kind="OutputPin" />
          </Node>

          {lfo('lfo_circle', '100,540', '6')}
          {lfo('lfo_bob', '100,720', '3.7')}
          {add('add_phase', '300,590', '0.25')}
          {sinewave('sin_x', '300,510')}
          {sinewave('sin_y', '440,590')}
          {sinewave('sin_z', '300,720')}
          {f32pad('pad_radius', 'Circle R (mm)', '540,450,50,16', '200', minimum='0', stepsize='10')}
          {scale('scale_x', '540,510')}
          {scale('scale_y', '680,590')}
          {f32pad('pad_bobh', 'Bob height (mm)', '540,660,50,16', '120', minimum='0', stepsize='10')}
          {scale('scale_z', '440,780')}
          {vec3pad('pad_center', 'CircleCenter (mm, Y up)', '740,430,52,43', '600, 1000, 0')}
          <Node Bounds="740,530,46,19" Id="{I('split_center')}">
            <p:NodeReference LastCategoryFullName="3D.Vector3" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="4043309058" Name="Vector3" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="Vector (Split)" />
            </p:NodeReference>
            <Pin Id="{I('split_center_in')}" Name="Input" Kind="StateInputPin" />
            <Pin Id="{I('split_center_x')}" Name="X" Kind="OutputPin" />
            <Pin Id="{I('split_center_y')}" Name="Y" Kind="OutputPin" />
            <Pin Id="{I('split_center_z')}" Name="Z" Kind="OutputPin" />
          </Node>
          {add('add_x', '920,490')}
          {add('add_y', '920,560')}
          {add('add_z', '920,630')}
          <Node Bounds="1100,560,46,19" Id="{I('join')}">
            <p:NodeReference LastCategoryFullName="3D.Vector3" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="Vector3Type" Name="Vector3" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="Vector (Join)" />
            </p:NodeReference>
            <Pin Id="{I('join_x')}" Name="X" Kind="InputPin" />
            <Pin Id="{I('join_y')}" Name="Y" Kind="InputPin" />
            <Pin Id="{I('join_z')}" Name="Z" Kind="InputPin" />
            <Pin Id="{I('join_out')}" Name="Output" Kind="StateOutputPin" />
          </Node>
          {vec3pad('pad_ori', 'Orientation (cycles)', '1100,680,52,43', '0, 0, 0')}
          <Node Bounds="1290,630,88,19" Id="{I('ctarget')}">
            <p:NodeReference LastCategoryFullName="Main.Target" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="CartesianTarget" />
            </p:NodeReference>
            <Pin Id="{I('ctarget_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('ctarget_pos')}" Name="Position" Kind="InputPin" />
            <Pin Id="{I('ctarget_ori')}" Name="Orientation" Kind="InputPin" />
            <Pin Id="{I('ctarget_out')}" Name="Output" Kind="OutputPin" />
          </Node>

          {fold_pads}
          {lfo('lfo_tremble', '1000,1010', '0.2')}
          {sinewave('sin_tremble', '1170,1010')}
          {tremble_scales}
          {tremble_adds}
          <Node Bounds="1700,840,45,19" Id="{I('cons')}">
            <p:NodeReference LastCategoryFullName="Collections.Spread" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="ClassType" Name="Spread" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="Cons" />
            </p:NodeReference>
            {cons_inputs}
            <Pin Id="{I('cons_out')}" Name="Result" Kind="OutputPin" />
          </Node>
          <Node Bounds="1850,880,66,19" Id="{I('atarget')}">
            <p:NodeReference LastCategoryFullName="Main.Target" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="AxisTarget" />
            </p:NodeReference>
            <Pin Id="{I('atarget_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('atarget_values')}" Name="AxisValues" Kind="InputPin" />
            <Pin Id="{I('atarget_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          <Node Bounds="2030,760,65,19" Id="{I('switch')}">
            <p:NodeReference LastCategoryFullName="Control" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="Category" Name="Control" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="Switch" />
            </p:NodeReference>
            <Pin Id="{I('switch_index')}" Name="Index" Kind="InputPin" />
            <Pin Id="{I('switch_in1')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('switch_in2')}" Name="Input 2" Kind="InputPin" />
            <Pin Id="{I('switch_out')}" Name="Output" Kind="OutputPin" />
            <Pin Id="{I('switch_in3')}" Name="Input 3" Kind="InputPin" />
          </Node>

          <Node Bounds="1850,1080,76,19" Id="{I('robot')}">
            <p:NodeReference LastCategoryFullName="Bunraku.Robot.Iontech" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="Category" Name="Iontech" />
              <Choice Kind="ProcessAppFlag" Name="KR50R2500" />
            </p:NodeReference>
            <Pin Id="{I('robot_data')}" Name="RobotData" Kind="OutputPin" />
            <Pin Id="{I('robot_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
          </Node>
          <Node Bounds="2200,760,87,19" Id="{I('assembly')}">
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
          <Node Bounds="2200,920,67,26" Id="{I('th_axis')}">
            <p:NodeReference LastCategoryFullName="Main.Traget.TargetHandler" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="ClassType" Name="TargetHandler" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="AxisValues" />
            </p:NodeReference>
            <Pin Id="{I('th_axis_in')}" Name="Input" Kind="StateInputPin" />
            <Pin Id="{I('th_axis_out')}" Name="Output" Kind="StateOutputPin" />
            <Pin Id="{I('th_axis_values')}" Name="AxisValues" Kind="OutputPin" />
          </Node>
          <Pad Id="{I('pad_axis')}" Comment="AxisValues (live)" Bounds="2320,890,56,111" ShowValueBox="true" isIOBox="true">
            <p:ValueBoxSettings>
              <p:maxvisibleentries p:Type="Int32">6</p:maxvisibleentries>
            </p:ValueBoxSettings>
          </Pad>
          <Node Bounds="2200,1090,185,19" Id="{I('vsettings')}">
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
          <Node Bounds="2470,770,88,19" Id="{I('visualizer')}">
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
          <Node Bounds="2470,1000,116,19" Id="{I('scenesettings')}">
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
          <Node Bounds="2720,850,115,19" Id="{I('scenewindow')}">
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
        {link(1, 'pad_distance', 'mapclamp_in')}
        {link(2, 'pad_near', 'mapclamp_inmin')}
        {link(3, 'pad_far', 'mapclamp_inmax')}
        {link(4, 'mapclamp_out', 'damper_goto')}
        {link(5, 'damper_pos', 'pad_openness')}
        {link(6, 'damper_pos', 'add_half_in1')}
        {link(7, 'add_half_out', 'toint_in')}
        {link(8, 'toint_result', 'switch_index')}
        {link(9, 'lfo_circle_phase', 'sin_x_phase')}
        {link(10, 'lfo_circle_phase', 'add_phase_in1')}
        {link(11, 'add_phase_out', 'sin_y_phase')}
        {link(12, 'lfo_bob_phase', 'sin_z_phase')}
        {link(13, 'sin_x_out', 'scale_x_in')}
        {link(14, 'pad_radius', 'scale_x_scalar')}
        {link(15, 'sin_y_out', 'scale_y_in')}
        {link(16, 'pad_radius', 'scale_y_scalar')}
        {link(17, 'sin_z_out', 'scale_z_in')}
        {link(18, 'pad_bobh', 'scale_z_scalar')}
        {link(19, 'pad_center', 'split_center_in')}
        {link(20, 'split_center_x', 'add_x_in1')}
        {link(21, 'scale_x_out', 'add_x_in2')}
        {link(22, 'split_center_y', 'add_y_in1')}
        {link(23, 'scale_y_out', 'add_z_in2')}
        {link(24, 'split_center_z', 'add_z_in1')}
        {link(25, 'scale_z_out', 'add_y_in2')}
        {link(26, 'add_x_out', 'join_x')}
        {link(27, 'add_y_out', 'join_y')}
        {link(28, 'add_z_out', 'join_z')}
        {link(29, 'join_out', 'ctarget_pos')}
        {link(30, 'pad_ori', 'ctarget_ori')}
        {link(31, 'lfo_tremble_phase', 'sin_tremble_phase')}
        {link(32, 'atarget_out', 'switch_in1')}
        {link(33, 'ctarget_out', 'switch_in2')}
        {link(34, 'switch_out', 'assembly_target')}
        {link(35, 'switch_out', 'th_axis_in')}
        {link(36, 'th_axis_values', 'pad_axis')}
        {link(37, 'robot_data', 'assembly_data')}
        {link(38, 'assembly_out', 'visualizer_in')}
        {link(39, 'vsettings_out', 'visualizer_settings')}
        {link(40, 'visualizer_out', 'scenewindow_child')}
        {link(41, 'scenesettings_out', 'scenewindow_settings')}
        {link(42, 'cons_out', 'atarget_values')}
        {chr(10).join(link(50 + i, f'sin_tremble_out', f'scale_t{i+1}_in') for i in range(6))}
        {chr(10).join(link(60 + i, f'pad_fold_a{i+1}', f'add_t{i+1}_in1') for i in range(6))}
        {chr(10).join(link(70 + i, f'scale_t{i+1}_out', f'add_t{i+1}_in2') for i in range(6))}
        {chr(10).join(link(80 + i, f'add_t{i+1}_out', f'cons_in{i+1}') for i in range(6))}
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
    out = ROOT / "test_vl_code" / "Mimosa.vl"
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
