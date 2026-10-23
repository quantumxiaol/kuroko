"""Generate vlsrc/Mimosa.vl — a "touch-me-not" (含羞草) robot patch for VL.Bunraku 1.0.3.

Robot: KUKA LBR iiwa 7 R800 (7 axes).

Design (v4, unified joint space — no Cartesian IK at runtime, no hard switching):
- Camera distance -> MapClamp -> Damper -> openness o in [0,1] (continuous).
- Per axis i:  out_i = Lerp(shy_i, dance_i, o)
    shy_i   = fold_i + trembleAmp_i * sin(tremble) * (1-o) * mode   (tremble only on A6)
    dance_i = danceBase_i + danceAmp_i * sin(phase_i) * mode
- mode comes from the "0=Sim 1=Real" pad: real mode scales every oscillation by 0.35
  and slows the tremble LFO from 1.2 s to 2.0 s per cycle.
- All joint-space: no IK singularities, no axis alarms, and the graded response
  (half-shy at mid distance) matches a real mimosa.

Fold pose note: A2=+80 bows the body forward (verified visually), A6=-95 points the
tool/flange OUTWARD (Bunraku renders A6 with the opposite sign vs the PRC sim).
Tune live via the Fold A1..A7 IOBoxes.

All NodeReference blocks are copied verbatim from the installed VL.Bunraku 1.0.3 nuget
(VL.Bunraku.vl internals + help/Overview patches).

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


def lfo(name: str, bounds: str, period: str | None) -> str:
    p = f' DefaultValue="{period}"' if period is not None else ""
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Animation" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="LFO" />
            </p:NodeReference>
            <Pin Id="{I(name + '_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I(name + '_clock')}" Name="Clock" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I(name + '_newclock')}" Name="New Clock" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I(name + '_period')}" Name="Period" Kind="InputPin"{p} />
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


def add(name: str, bounds: str, default1: str | None = None, default2: str | None = None) -> str:
    d1 = f' DefaultValue="{default1}"' if default1 is not None else ""
    d2 = f' DefaultValue="{default2}"' if default2 is not None else ""
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Math" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="+" />
            </p:NodeReference>
            <Pin Id="{I(name + '_in1')}" Name="Input" Kind="InputPin"{d1} />
            <Pin Id="{I(name + '_in2')}" Name="Input 2" Kind="InputPin"{d2} />
            <Pin Id="{I(name + '_out')}" Name="Output" Kind="OutputPin" />
          </Node>"""


def sub(name: str, bounds: str, default1: str | None = None) -> str:
    d1 = f' DefaultValue="{default1}"' if default1 is not None else ""
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Math" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="-" />
            </p:NodeReference>
            <Pin Id="{I(name + '_in1')}" Name="Input" Kind="InputPin"{d1} />
            <Pin Id="{I(name + '_in2')}" Name="Input 2" Kind="InputPin" />
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


def lerp(name: str, bounds: str, default2: str | None = None) -> str:
    d2 = f' DefaultValue="{default2}"' if default2 is not None else ""
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Math" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="Lerp" />
            </p:NodeReference>
            <Pin Id="{I(name + '_in1')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I(name + '_in2')}" Name="Input 2" Kind="InputPin"{d2} />
            <Pin Id="{I(name + '_scalar')}" Name="Scalar" Kind="InputPin" />
            <Pin Id="{I(name + '_out')}" Name="Output" Kind="OutputPin" />
          </Node>"""


def switch(name: str, bounds: str, sim: str, real: str) -> str:
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Control" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="Category" Name="Control" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="Switch" />
            </p:NodeReference>
            <Pin Id="{I(name + '_index')}" Name="Index" Kind="InputPin" />
            <Pin Id="{I(name + '_in1')}" Name="Input" Kind="InputPin" DefaultValue="{sim}" />
            <Pin Id="{I(name + '_in2')}" Name="Input 2" Kind="InputPin" DefaultValue="{real}" />
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


def intpad(name: str, comment: str, bounds: str, value: str) -> str:
    return f"""<Pad Id="{I(name)}" Comment="{comment}" Bounds="{bounds}" ShowValueBox="true" isIOBox="true" Value="{value}">
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="Integer32" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:maximum p:Type="Int32">1</p:maximum>
              <p:minimum p:Type="Int32">0</p:minimum>
            </p:ValueBoxSettings>
          </Pad>"""


def link(n: str, src: str, dst: str) -> str:
    return f'<Link Id="{I("lnk" + n)}" Ids="{I(src)},{I(dst)}" />'


N_AXES = 7  # LBR iiwa 7 R800

# Shy fold (Bunraku axis conventions, verified visually in vvvv):
# A2=+25 mild forward lean, A4=+115 elbow deeply folded (forearm tucked to the body),
# A6=-70 points the tool/flange OUTWARD (Bunraku renders A6 with the opposite sign vs
# the PRC sim). End effector stays outside the arm silhouette and above the floor.
FOLD = ["-1", "-110", "90", "20", "30", "40", "0"]
# Tremble on the end axis (A6 wrist) only.
TREMBLE_AMP = ["0", "0", "0", "0", "0", "2.5", "0"]
# Dance: base pose + per-axis sine amplitudes (deg). Symmetric sway around the base.
DANCE_BASE = ["-1", "-65", "60", "35", "30", "20", "0"]
DANCE_AMP = ["35", "10", "0", "15", "0", "12", "30"]
# Phase source per axis: p1 = circle LFO, p2 = bob LFO, q1 = p1+0.25, h2 = p2+0.5
DANCE_PHASE = {"1": "lfo_circle_phase", "2": "lfo_bob_phase", "4": "add_q_out", "6": "add_h_out", "7": "add_r_out"}

ROW_Y = [760 + i * 26 for i in range(N_AXES)]

fold_pads = "\n          ".join(
    f32pad(f"pad_fold_a{i+1}", f"Fold A{i+1} (deg)", f"1000,{ROW_Y[i]},44,16", FOLD[i], stepsize="1")
    for i in range(N_AXES)
)

# per-axis shy/dance/lerp chains
axis_nodes: list[str] = []
for i in range(N_AXES):
    a = i + 1
    y = ROW_Y[i]
    # shy: fold_i + tremble (only A6 has a nonzero tremble chain)
    if TREMBLE_AMP[i] != "0":
        axis_nodes.append(scale(f"scale_t{a}", f"1180,{y}", TREMBLE_AMP[i]))
        axis_nodes.append(add(f"add_shy{a}", f"1340,{y}"))
        shy_out = f"add_shy{a}_out"
    else:
        shy_out = f"pad_fold_a{a}"
    # dance: danceBase_i + danceAmp_i * sin(phase_i) * mode
    if DANCE_AMP[i] != "0":
        axis_nodes.append(sinewave(f"sin_d{a}", f"1000,{y + 330}"))
        axis_nodes.append(scale(f"scale_d{a}", f"1180,{y + 330}", DANCE_AMP[i]))
        axis_nodes.append(scale(f"scale_m{a}", f"1340,{y + 330}"))
        axis_nodes.append(add(f"add_dance{a}", f"1520,{y + 330}", DANCE_BASE[i]))
        dance_out = f"add_dance{a}_out"
    else:
        dance_out = None
    axis_nodes.append(lerp(f"lerp{a}", f"1700,{y}", DANCE_BASE[i] if dance_out is None else None))

cons_inputs = "\n            ".join(
    f'<Pin Id="{I("cons_in" + str(i+1))}" Name="Input{"" if i == 0 else " " + str(i+1)}" Kind="InputPin" />'
    for i in range(N_AXES)
)

links: list[str] = [
    link("d", "pad_distance", "mapclamp_in"),
    link("near", "pad_near", "mapclamp_inmin"),
    link("far", "pad_far", "mapclamp_inmax"),
    link("mc", "mapclamp_out", "damper_goto"),
    link("op", "damper_pos", "pad_openness"),
    link("inv", "damper_pos", "sub_inv_in2"),
    link("mode1", "pad_mode", "switch_scale_index"),
    link("mode2", "pad_mode", "switch_tperiod_index"),
    link("tper", "switch_tperiod_out", "lfo_tremble_period"),
    link("tlfo", "lfo_tremble_phase", "sin_tremble_phase"),
    link("invm", "sub_inv_out", "scale_invm_in"),
    link("invm2", "switch_scale_out", "scale_invm_scalar"),
    link("tshared", "sin_tremble_out", "scale_tshared_in"),
    link("tshared2", "scale_invm_out", "scale_tshared_scalar"),
    link("pq", "lfo_circle_phase", "add_q_in1"),
    link("ph", "lfo_bob_phase", "add_h_in1"),
    link("pr", "lfo_circle_phase", "add_r_in1"),
]
for i in range(N_AXES):
    a = i + 1
    links.append(link(f"lerps{a}", "damper_pos", f"lerp{a}_scalar"))
    if TREMBLE_AMP[i] != "0":
        links.append(link(f"t{a}", "scale_tshared_out", f"scale_t{a}_in"))
        links.append(link(f"fold{a}", f"pad_fold_a{a}", f"add_shy{a}_in1"))
        links.append(link(f"ts{a}", f"scale_t{a}_out", f"add_shy{a}_in2"))
        links.append(link(f"shy{a}", f"add_shy{a}_out", f"lerp{a}_in1"))
    else:
        links.append(link(f"shy{a}", f"pad_fold_a{a}", f"lerp{a}_in1"))
    if DANCE_AMP[i] != "0":
        links.append(link(f"dph{a}", DANCE_PHASE[str(a)], f"sin_d{a}_phase"))
        links.append(link(f"ds{a}", f"sin_d{a}_out", f"scale_d{a}_in"))
        links.append(link(f"dm{a}", f"scale_d{a}_out", f"scale_m{a}_in"))
        links.append(link(f"mm{a}", "switch_scale_out", f"scale_m{a}_scalar"))
        links.append(link(f"da{a}", f"scale_m{a}_out", f"add_dance{a}_in2"))
        links.append(link(f"dance{a}", f"add_dance{a}_out", f"lerp{a}_in2"))
    # else: lerp Input 2 carries the dance-base default
    links.append(link(f"out{a}", f"lerp{a}_out", f"cons_in{a}"))

links_block = "\n        ".join(links)

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
          <Pad Id="{I('pad_title')}" Bounds="100,60,520,30" ShowValueBox="true" isIOBox="true" Value="Mimosa (含羞草) — LBR iiwa 7 R800, joint-space graded shy/dance">
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="String" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:fontsize p:Type="Int32">15</p:fontsize>
              <p:stringtype p:Assembly="VL.Core" p:Type="VL.Core.StringType">Comment</p:stringtype>
            </p:ValueBoxSettings>
          </Pad>
          <Pad Id="{I('pad_note')}" Bounds="100,95,700,30" ShowValueBox="true" isIOBox="true" Value="openness 0 = shy (fold + A6 wrist tremble), 1 = dance (joint sines), continuous in between. Real-robot mode (pad, 0/1) scales all oscillation 0.35x and slows the tremble. Replace the distance IOBox with a camera depth node when ready.">
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
          {sub('sub_inv', '600,380', '1')}
          {intpad('pad_mode', 'Real robot mode (0=Sim 1=Real)', '430,400,44,16', '0')}
          {switch('switch_scale', '600,440', '1', '0.35')}
          {switch('switch_tperiod', '600,500', '1.2', '2')}
          {lfo('lfo_tremble', '780,500', None)}
          {sinewave('sin_tremble', '950,500')}
          {scale('scale_invm', '780,380')}
          {scale('scale_tshared', '1120,500')}

          {lfo('lfo_circle', '100,560', '6')}
          {lfo('lfo_bob', '100,640', '3.7')}
          {add('add_q', '300,560', None, '0.25')}
          {add('add_h', '300,640', None, '0.5')}
          {add('add_r', '300,720', None, '0.5')}

          {fold_pads}
          {chr(10).join(axis_nodes)}
          <Node Bounds="1880,840,45,19" Id="{I('cons')}">
            <p:NodeReference LastCategoryFullName="Collections.Spread" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="ClassType" Name="Spread" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="Cons" />
            </p:NodeReference>
            {cons_inputs}
            <Pin Id="{I('cons_out')}" Name="Result" Kind="OutputPin" />
          </Node>
          <Node Bounds="2030,880,66,19" Id="{I('atarget')}">
            <p:NodeReference LastCategoryFullName="Main.Target" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="AxisTarget" />
            </p:NodeReference>
            <Pin Id="{I('atarget_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('atarget_values')}" Name="AxisValues" Kind="InputPin" />
            <Pin Id="{I('atarget_out')}" Name="Output" Kind="OutputPin" />
          </Node>

          <Node Bounds="2030,1080,80,19" Id="{I('robot')}">
            <p:NodeReference LastCategoryFullName="Bunraku.Robot.LBR" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="LBRiiwa7R800" />
            </p:NodeReference>
            <Pin Id="{I('robot_data')}" Name="RobotData" Kind="OutputPin" />
            <Pin Id="{I('robot_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
          </Node>
          <Node Bounds="2200,880,87,19" Id="{I('assembly')}">
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
          <Node Bounds="2200,1020,67,26" Id="{I('th_axis')}">
            <p:NodeReference LastCategoryFullName="Main.Traget.TargetHandler" LastDependency="VL.Bunraku.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="ClassType" Name="TargetHandler" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="AxisValues" />
            </p:NodeReference>
            <Pin Id="{I('th_axis_in')}" Name="Input" Kind="StateInputPin" />
            <Pin Id="{I('th_axis_out')}" Name="Output" Kind="StateOutputPin" />
            <Pin Id="{I('th_axis_values')}" Name="AxisValues" Kind="OutputPin" />
          </Node>
          <Pad Id="{I('pad_axis')}" Comment="AxisValues (live)" Bounds="2320,990,56,141" ShowValueBox="true" isIOBox="true">
            <p:ValueBoxSettings>
              <p:maxvisibleentries p:Type="Int32">7</p:maxvisibleentries>
            </p:ValueBoxSettings>
          </Pad>
          <Node Bounds="2200,1190,185,19" Id="{I('vsettings')}">
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
          <Node Bounds="2470,890,88,19" Id="{I('visualizer')}">
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
          <Node Bounds="2470,1100,116,19" Id="{I('scenesettings')}">
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
          <Node Bounds="2720,960,115,19" Id="{I('scenewindow')}">
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
        {links_block}
        {link('atarget', 'cons_out', 'atarget_values')}
        {link('th', 'atarget_out', 'assembly_target')}
        {link('th2', 'atarget_out', 'th_axis_in')}
        {link('ax', 'th_axis_values', 'pad_axis')}
        {link('rb', 'robot_data', 'assembly_data')}
        {link('vis', 'assembly_out', 'visualizer_in')}
        {link('vs', 'vsettings_out', 'visualizer_settings')}
        {link('win', 'visualizer_out', 'scenewindow_child')}
        {link('ss', 'scenesettings_out', 'scenewindow_settings')}
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
    out = ROOT / "vlsrc" / "Mimosa.vl"
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
