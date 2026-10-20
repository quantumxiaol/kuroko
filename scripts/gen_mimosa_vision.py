"""Generate test_vl_code/MimosaVision.vl — camera person-distance input for the Mimosa patch.

Chain:
  MediaPipe node (hosts the camera via its embedded browser; pose detection on GPU)
    -> PoseDetector (1 pose) -> GetSlice(0) -> SelectJoint x4
    (LeftShoulder / RightShoulder / LeftHip / RightHip) -> Y positions
    -> torso = |avg(shoulderY) - avg(hipY)|
    -> distance = K / torso            (calibrate K once, see comment pad in patch)
    -> presence gate (no valid pose -> No-person distance)
    -> Damper -> Distance (m) display
  Feed the Distance value into Mimosa.vl's MapClamp Input (replacing the simulated IOBox).

Preview: MediaPipe browser output -> ToStrideRenderer -> RenderWindow
(camera image with the pose skeleton overlay).

Node references copied from the installed packages:
  VL.MediaPipe 0.11.0-alpha help patches, VL.CEF 0.8.2 help, VL.Bunraku.vl (math nodes).
NOTE: VL.CEF.Stride is pulled in for the preview window; vvvv will offer to install it
on first open if missing.

Run:  uv run python scripts/gen_mimosa_vision.py
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


def math2(kind: str, name: str, bounds: str, d1: str | None = None, d2: str | None = None) -> str:
    dd1 = f' DefaultValue="{d1}"' if d1 is not None else ""
    dd2 = f' DefaultValue="{d2}"' if d2 is not None else ""
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="Math" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="{kind}" />
            </p:NodeReference>
            <Pin Id="{I(name + '_in1')}" Name="Input" Kind="InputPin"{dd1} />
            <Pin Id="{I(name + '_in2')}" Name="Input 2" Kind="InputPin"{dd2} />
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


def vsplit(name: str, bounds: str) -> str:
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="3D.Vector3" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="4043309058" Name="Vector3" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="Vector (Split)" />
            </p:NodeReference>
            <Pin Id="{I(name + '_in')}" Name="Input" Kind="StateInputPin" />
            <Pin Id="{I(name + '_x')}" Name="X" Kind="OutputPin" />
            <Pin Id="{I(name + '_y')}" Name="Y" Kind="OutputPin" />
            <Pin Id="{I(name + '_z')}" Name="Z" Kind="OutputPin" />
          </Node>"""


def selectjoint(name: str, bounds: str, joint: str) -> str:
    return f"""<Node Bounds="{bounds}" Id="{I(name)}">
            <p:NodeReference LastCategoryFullName="MediaPipe.PoseDetector" LastDependency="VL.MediaPipe.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="SelectJoint" />
            </p:NodeReference>
            <Pin Id="{I(name + '_in')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I(name + '_joint')}" Name="Joint" Kind="InputPin" />
            <Pin Id="{I(name + '_pos')}" Name="Position" Kind="OutputPin" />
            <Pin Id="{I(name + '_valid')}" Name="Is Valid" Kind="OutputPin" />
          </Node>
          <Pad Id="{I(name + '_jointpad')}" Comment="" Bounds="{bounds.split(',')[0]},{int(bounds.split(',')[1]) - 40},99,15" ShowValueBox="true" isIOBox="true" Value="{joint}">
            <p:TypeAnnotation LastCategoryFullName="VL.MediaPipe.PoseResults" LastDependency="VL.MediaPipe.dll">
              <Choice Kind="TypeFlag" Name="PoseJoints" />
            </p:TypeAnnotation>
          </Pad>"""


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


def boolpad(name: str, comment: str, bounds: str, value: str, mode: str = "Toggle") -> str:
    return f"""<Pad Id="{I(name)}" Comment="{comment}" Bounds="{bounds}" ShowValueBox="true" isIOBox="true" Value="{value}">
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="ImmutableTypeFlag" Name="Boolean" />
            </p:TypeAnnotation>
            <p:ValueBoxSettings>
              <p:buttonmode p:Assembly="VL.UI.Forms" p:Type="VL.HDE.PatchEditor.Editors.ButtonModeEnum">{mode}</p:buttonmode>
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


TEMPLATE = f"""<?xml version="1.0" encoding="utf-8"?>
<Document xmlns:p="property" xmlns:r="reflection" Id="{I('doc')}" LanguageVersion="2026.8.0-0158-gda117bc374" Version="0.128">
  <NugetDependency Id="{I('dep_corelib')}" Location="VL.CoreLib" />
  <NugetDependency Id="{I('dep_mediapipe')}" Location="VL.MediaPipe" Version="0.11.0-alpha" />
  <NugetDependency Id="{I('dep_cefstride')}" Location="VL.CEF.Stride" Version="0.7.3" />
  <NugetDependency Id="{I('dep_stride')}" Location="VL.Stride" />
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
          {commentpad('pad_title', '100,50,560,30', 'Mimosa Vision — MediaPipe person distance for Mimosa.vl', 15)}
          {commentpad('pad_note', '100,88,760,30', 'Pick your camera in the Camera dropdown. Calibrate: stand at 1 m facing the camera, read the torso value, set K to that value. Then feed Distance (m) into the MapClamp Input of Mimosa.vl (replacing the simulated IOBox).')}

          {boolpad('pad_detect', 'Detect poses', '140,150,35,35', 'True')}
          {boolpad('pad_overlay', 'Show overlays', '140,220,35,35', 'True')}
          <Pad Id="{I('pad_camera')}" Comment="Camera (pick from dropdown)" Bounds="140,300,220,15" ShowValueBox="true" isIOBox="true" Value="Intel(R) RealSense(TM) Depth Camera 435i RGB (8086:0b3a)">
            <p:TypeAnnotation LastCategoryFullName="MediaPipe" LastDependency="VL.MediaPipe.vl">
              <Choice Kind="TypeFlag" Name="CamerasEnum" />
            </p:TypeAnnotation>
          </Pad>
          {boolpad('pad_reset', 'Reset', '500,240,35,35', 'false', 'Bang')}
          <Node Bounds="140,360,305,19" Id="{I('mediapipe')}">
            <p:NodeReference LastCategoryFullName="Main" LastDependency="VL.MediaPipe.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="MediaPipe" />
            </p:NodeReference>
            <Pin Id="{I('mp_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('mp_faces')}" Name="Detect faces" Kind="InputPin" DefaultValue="False" />
            <Pin Id="{I('mp_facelm')}" Name="Detect facial landmarks" Kind="InputPin" DefaultValue="False" />
            <Pin Id="{I('mp_hands')}" Name="Detect hands" Kind="InputPin" />
            <Pin Id="{I('mp_gestures')}" Name="Detect gestures" Kind="InputPin" />
            <Pin Id="{I('mp_poses')}" Name="Detect poses" Kind="InputPin" />
            <Pin Id="{I('mp_objects')}" Name="Detect objects" Kind="InputPin" />
            <Pin Id="{I('mp_classify')}" Name="Classify images" Kind="InputPin" />
            <Pin Id="{I('mp_seg')}" Name="Image segmentation" Kind="InputPin" />
            <Pin Id="{I('mp_embed')}" Name="Detect image embeddings" Kind="InputPin" />
            <Pin Id="{I('mp_overlays')}" Name="Show overlays" Kind="InputPin" DefaultValue="False" />
            <Pin Id="{I('mp_camera')}" Name="Camera" Kind="InputPin" />
            <Pin Id="{I('mp_flip')}" Name="Flip Camera" Kind="InputPin" />
            <Pin Id="{I('mp_imgsize')}" Name="Image Size" Kind="InputPin" />
            <Pin Id="{I('mp_wsport')}" Name="Webserver Port" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('mp_wssport')}" Name="Websocket Port" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('mp_state')}" Name="State Output" Kind="OutputPin" />
            <Pin Id="{I('mp_out')}" Name="Output" Kind="OutputPin" />
            <Pin Id="{I('mp_sharedtex')}" Name="Shared Texture Enabled" Kind="InputPin" DefaultValue="False" />
            <Pin Id="{I('mp_reset')}" Name="Reset" Kind="InputPin" DefaultValue="False" />
            <Pin Id="{I('mp_enabled')}" Name="Enabled" Kind="InputPin" />
          </Node>
          <Node Bounds="620,300,95,19" Id="{I('tostride')}">
            <p:NodeReference LastCategoryFullName="CEF" LastDependency="VL.CEF.Stride.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <FullNameCategoryReference ID="CEF" />
              <Choice Kind="ProcessAppFlag" Name="ToStrideRenderer" />
            </p:NodeReference>
            <Pin Id="{I('tostride_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('tostride_browser')}" Name="Browser" Kind="InputPin" />
            <Pin Id="{I('tostride_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          <Node Bounds="860,320,165,19" Id="{I('renderwindow')}">
            <p:NodeReference LastCategoryFullName="Stride" LastDependency="VL.Stride.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="RenderWindow" />
            </p:NodeReference>
            <Pin Id="{I('rw_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rw_bounds')}" Name="Bounds" Kind="InputPin" DefaultValue="1156, 90, 640, 360" IsHidden="true" />
            <Pin Id="{I('rw_btd')}" Name="Bound to Document" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rw_dialog')}" Name="Dialog If Document Changed" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rw_savebounds')}" Name="Save Bounds" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rw_bbf')}" Name="Back Buffer Format" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rw_dbf')}" Name="Depth Buffer Format" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rw_msaa')}" Name="Multisample Count" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rw_inprio')}" Name="Input Priority" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rw_input')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('rw_view')}" Name="Render View" Kind="InputPin" />
            <Pin Id="{I('rw_title')}" Name="Title" Kind="InputPin" />
            <Pin Id="{I('rw_clearflags')}" Name="Clear Flags" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rw_clearcolor')}" Name="Clear Color" Kind="InputPin" DefaultValue="0.23, 0.23, 0.23, 1" />
            <Pin Id="{I('rw_cleardepth')}" Name="Clear Depth" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rw_clearstencil')}" Name="Clear Stencil" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rw_clear')}" Name="Clear" Kind="InputPin" />
            <Pin Id="{I('rw_editmode')}" Name="Edit Mode" Kind="InputPin" />
            <Pin Id="{I('rw_commands')}" Name="Commands" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rw_keys')}" Name="Enable Keyboard Shortcuts" Kind="InputPin" />
            <Pin Id="{I('rw_enabled')}" Name="Enabled" Kind="InputPin" />
            <Pin Id="{I('rw_present')}" Name="Present Interval" Kind="InputPin" />
            <Pin Id="{I('rw_out')}" Name="Output" Kind="OutputPin" />
            <Pin Id="{I('rw_clientbounds')}" Name="Client Bounds" Kind="OutputPin" />
            <Pin Id="{I('rw_inputsource')}" Name="Input Source" Kind="OutputPin" />
            <Pin Id="{I('rw_backbuffer')}" Name="Back Buffer" Kind="OutputPin" />
            <Pin Id="{I('rw_depthbuffer')}" Name="Depth Buffer" Kind="OutputPin" />
            <Pin Id="{I('rw_pci')}" Name="Present Call Intercept" Kind="InputPin" IsHidden="true" />
          </Node>

          <Pad Id="{I('pad_maxposes')}" Comment="Max Number of Poses" Bounds="160,580,35,15" ShowValueBox="true" isIOBox="true" Value="1">
            <p:TypeAnnotation LastCategoryFullName="Primitive" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="Integer32" />
            </p:TypeAnnotation>
          </Pad>
          <Node Bounds="140,660,105,19" Id="{I('posedet')}">
            <p:NodeReference LastCategoryFullName="MediaPipe" LastDependency="VL.MediaPipe.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="PoseDetector" />
            </p:NodeReference>
            <Pin Id="{I('pd_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('pd_in')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('pd_max')}" Name="Max Number of Poses" Kind="InputPin" />
            <Pin Id="{I('pd_model')}" Name="Pose Model Type" Kind="InputPin" />
            <Pin Id="{I('pd_detconf')}" Name="Min Detection Confidence" Kind="InputPin" />
            <Pin Id="{I('pd_presconf')}" Name="Min Presence Confidence" Kind="InputPin" />
            <Pin Id="{I('pd_trackconf')}" Name="Min Tracking Confidence" Kind="InputPin" />
            <Pin Id="{I('pd_landmarks')}" Name="Landmarks" Kind="OutputPin" />
            <Pin Id="{I('pd_world')}" Name="World Landmarks" Kind="OutputPin" />
          </Node>
          <Node Bounds="430,680,52,19" Id="{I('getpose')}">
            <p:NodeReference LastCategoryFullName="Collections.Interfaces.IReadOnlyList" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="MutableInterfaceType" Name="IReadOnlyList" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="GetSlice" />
            </p:NodeReference>
            <Pin Id="{I('getpose_in')}" Name="Input" Kind="StateInputPin" />
            <Pin Id="{I('getpose_def')}" Name="Default Value" Kind="InputPin" />
            <Pin Id="{I('getpose_index')}" Name="Index" Kind="InputPin" DefaultValue="0" />
            <Pin Id="{I('getpose_out')}" Name="Result" Kind="OutputPin" />
          </Node>

          {selectjoint('sj_ls', '650,560', 'LeftShoulder')}
          {selectjoint('sj_rs', '650,700', 'RightShoulder')}
          {selectjoint('sj_lh', '650,840', 'LeftHip')}
          {selectjoint('sj_rh', '650,980', 'RightHip')}
          {vsplit('sp_ls', '900,560')}
          {vsplit('sp_rs', '900,700')}
          {vsplit('sp_lh', '900,840')}
          {vsplit('sp_rh', '900,980')}
          {math2('+', 'add_shoulder', '1100,600')}
          {scale('avg_shoulder', '1260,600', '0.5')}
          {math2('+', 'add_hip', '1100,880')}
          {scale('avg_hip', '1260,880', '0.5')}
          {math2('-', 'sub_torso', '1440,740')}
          <Node Bounds="1600,740,45,19" Id="{I('abs')}">
            <p:NodeReference LastCategoryFullName="Math" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="Abs" />
            </p:NodeReference>
            <Pin Id="{I('abs_in')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('abs_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          {f32pad('pad_torso', 'torso (calibrate at 1 m)', '1760,720,60,16', None)}
          {f32pad('pad_k', 'Calibration K', '1500,880,44,16', '0.35', stepsize='0.01')}
          {math2('/', 'div_dist', '1760,820')}
          {f32pad('pad_far', 'No-person distance (m)', '1000,1080,56,16', '4', minimum='0', stepsize='0.5')}
          <Node Bounds="900,1080,52,19" Id="{I('toint')}">
            <p:NodeReference LastCategoryFullName="System.Conversion" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="OperationCallFlag" Name="ToInt32" />
            </p:NodeReference>
            <Pin Id="{I('toint_in')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('toint_result')}" Name="Result" Kind="OutputPin" />
          </Node>
          <Node Bounds="1260,1080,65,19" Id="{I('switch')}">
            <p:NodeReference LastCategoryFullName="Control" LastDependency="VL.CoreLib.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <CategoryReference Kind="Category" Name="Control" NeedsToBeDirectParent="true" />
              <Choice Kind="OperationCallFlag" Name="Switch" />
            </p:NodeReference>
            <Pin Id="{I('switch_index')}" Name="Index" Kind="InputPin" />
            <Pin Id="{I('switch_in1')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('switch_in2')}" Name="Input 2" Kind="InputPin" />
            <Pin Id="{I('switch_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          {damper('damper', '1440,1080', '0.3')}
          {f32pad('pad_distance', 'Distance (m) → Mimosa MapClamp', '1640,1060,80,16', None)}
          {commentpad('pad_note2', '140,760,460,40', '⚠ Changing any PoseDetector input requires a manual trigger of Reset on the MediaPipe node. If the presence gate (ToInt32) shows red, delete it and link Switch Index to 1.', 9)}
        </Canvas>
        <Patch Id="{I('create')}" Name="Create" />
        <Patch Id="{I('update')}" Name="Update" />
        <ProcessDefinition Id="{I('processdef')}">
          <Fragment Id="{I('frag_create')}" Patch="{I('create')}" Enabled="true" />
          <Fragment Id="{I('frag_update')}" Patch="{I('update')}" Enabled="true" />
        </ProcessDefinition>
        {link('detect', 'pad_detect', 'mp_poses')}
        {link('overlay', 'pad_overlay', 'mp_overlays')}
        {link('camera', 'pad_camera', 'mp_camera')}
        {link('reset', 'pad_reset', 'mp_reset')}
        {link('browser', 'mp_out', 'tostride_browser')}
        {link('render', 'tostride_out', 'rw_input')}
        {link('state', 'mp_state', 'pd_in')}
        {link('maxp', 'pad_maxposes', 'pd_max')}
        {link('lm', 'pd_landmarks', 'getpose_in')}
        {link('pose1', 'getpose_out', 'sj_ls_in')}
        {link('pose2', 'getpose_out', 'sj_rs_in')}
        {link('pose3', 'getpose_out', 'sj_lh_in')}
        {link('pose4', 'getpose_out', 'sj_rh_in')}
        {link('j1', 'sj_ls_jointpad', 'sj_ls_joint')}
        {link('j2', 'sj_rs_jointpad', 'sj_rs_joint')}
        {link('j3', 'sj_lh_jointpad', 'sj_lh_joint')}
        {link('j4', 'sj_rh_jointpad', 'sj_rh_joint')}
        {link('p1', 'sj_ls_pos', 'sp_ls_in')}
        {link('p2', 'sj_rs_pos', 'sp_rs_in')}
        {link('p3', 'sj_lh_pos', 'sp_lh_in')}
        {link('p4', 'sj_rh_pos', 'sp_rh_in')}
        {link('s1', 'sp_ls_y', 'add_shoulder_in1')}
        {link('s2', 'sp_rs_y', 'add_shoulder_in2')}
        {link('s3', 'add_shoulder_out', 'avg_shoulder_in')}
        {link('h1', 'sp_lh_y', 'add_hip_in1')}
        {link('h2', 'sp_rh_y', 'add_hip_in2')}
        {link('h3', 'add_hip_out', 'avg_hip_in')}
        {link('t1', 'avg_shoulder_out', 'sub_torso_in1')}
        {link('t2', 'avg_hip_out', 'sub_torso_in2')}
        {link('t3', 'sub_torso_out', 'abs_in')}
        {link('t4', 'abs_out', 'pad_torso')}
        {link('k', 'pad_k', 'div_dist_in1')}
        {link('d1', 'abs_out', 'div_dist_in2')}
        {link('v1', 'sj_ls_valid', 'toint_in')}
        {link('v2', 'toint_result', 'switch_index')}
        {link('far', 'pad_far', 'switch_in1')}
        {link('dist', 'div_dist_out', 'switch_in2')}
        {link('sw', 'switch_out', 'damper_goto')}
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
    out = ROOT / "test_vl_code" / "MimosaVision.vl"
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
