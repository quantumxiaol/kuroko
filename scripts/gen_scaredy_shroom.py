"""Generate test_vl_code/ScaredyShroom.vl — minimal viewer for the vertex-color GLB.

FileModel (path ../assert/Scaredy-shroom.glb, relative to the document)
  -> ModelEntity -> RootScene -> SceneWindow, plus a SkyboxLight for lighting.
Vertex colors need no material/texture wiring.

Node references copied from VL.Bunraku 1.0.3 (CoveBase) and the VL.PRC help patch.

Run:  uv run python scripts/gen_scaredy_shroom.py
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


def link(n: str, src: str, dst: str) -> str:
    return f'<Link Id="{I("lnk" + n)}" Ids="{I(src)},{I(dst)}" />'


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


TEMPLATE = f"""<?xml version="1.0" encoding="utf-8"?>
<Document xmlns:p="property" xmlns:r="reflection" Id="{I('doc')}" LanguageVersion="2026.8.0-0158-gda117bc374" Version="0.128">
  <NugetDependency Id="{I('dep_corelib')}" Location="VL.CoreLib" />
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
          {commentpad('pad_title', '100,60,420,30', 'Scaredy-shroom viewer (vertex-color GLB)', 15)}
          {commentpad('pad_note', '100,95,520,30', 'FileModel -> ModelEntity -> SceneWindow. Vertex colors need no material. Path is relative to this document.')}
          <Pad Id="{I('pad_path')}" Comment="Path" Bounds="100,180,260,15" ShowValueBox="true" isIOBox="true" Value="..\\assert\\Scaredy-shroom.glb">
            <p:TypeAnnotation LastCategoryFullName="IO" LastDependency="VL.CoreLib.vl">
              <Choice Kind="TypeFlag" Name="Path" />
            </p:TypeAnnotation>
          </Pad>
          <Node Bounds="100,260,65,19" Id="{I('filemodel')}">
            <p:NodeReference LastCategoryFullName="Stride.Assets" LastDependency="VL.Stride.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="FileModel" />
            </p:NodeReference>
            <Pin Id="{I('fm_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('fm_path')}" Name="Path" Kind="InputPin" />
            <Pin Id="{I('fm_scale')}" Name="Import Scale" Kind="InputPin" />
            <Pin Id="{I('fm_pivot')}" Name="Pivot Position" Kind="InputPin" />
            <Pin Id="{I('fm_merge')}" Name="Merge Meshes" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('fm_reload')}" Name="Reload" Kind="InputPin" />
            <Pin Id="{I('fm_model')}" Name="Model" Kind="OutputPin" />
            <Pin Id="{I('fm_loading')}" Name="Is Loading" Kind="OutputPin" />
            <Pin Id="{I('fm_loaded')}" Name="Already Loaded" Kind="OutputPin" />
            <Pin Id="{I('fm_url')}" Name="Url" Kind="OutputPin" IsHidden="true" />
          </Node>
          <Node Bounds="360,300,94,19" Id="{I('vcshader')}">
            <p:NodeReference LastCategoryFullName="Stride.Rendering.ShaderFX" LastDependency="VL.Stride.Rendering.EffectShaderNodes">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessNode" Name="VertexColor" />
            </p:NodeReference>
            <Pin Id="{I('vc_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          <Node Bounds="360,380,125,19" Id="{I('pbr')}">
            <p:NodeReference LastCategoryFullName="Stride.Materials" LastDependency="VL.Stride.Rendering.ShaderFX.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="PBRMaterial (Metallic)" />
            </p:NodeReference>
            <Pin Id="{I('pbr_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('pbr_diffuse')}" Name="Diffuse" Kind="InputPin" />
            <Pin Id="{I('pbr_metal')}" Name="Metalness" Kind="InputPin" DefaultValue="0" />
            <Pin Id="{I('pbr_rough')}" Name="Roughness" Kind="InputPin" DefaultValue="0.6" />
            <Pin Id="{I('pbr_normal')}" Name="Normal" Kind="InputPin" />
            <Pin Id="{I('pbr_displ')}" Name="Displacement" Kind="InputPin" />
            <Pin Id="{I('pbr_tess')}" Name="Tessellation" Kind="InputPin" />
            <Pin Id="{I('pbr_occl')}" Name="Occlusion" Kind="InputPin" />
            <Pin Id="{I('pbr_sss')}" Name="Subsurface Scattering" Kind="InputPin" />
            <Pin Id="{I('pbr_emis')}" Name="Emissive" Kind="InputPin" />
            <Pin Id="{I('pbr_transp')}" Name="Transparency" Kind="InputPin" />
            <Pin Id="{I('pbr_layers')}" Name="Layers" Kind="InputPin" />
            <Pin Id="{I('pbr_cull')}" Name="Cull Mode" Kind="InputPin" />
            <Pin Id="{I('pbr_state')}" Name="State Output" Kind="OutputPin" IsHidden="true" />
            <Pin Id="{I('pbr_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          <Node Bounds="100,380,145,19" Id="{I('modelentity')}">
            <p:NodeReference LastCategoryFullName="Stride.Models" LastDependency="VL.Stride.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="ModelEntity" />
            </p:NodeReference>
            <Pin Id="{I('me_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('me_trans')}" Name="Transformation" Kind="InputPin" />
            <Pin Id="{I('me_model')}" Name="Model" Kind="InputPin" />
            <Pin Id="{I('me_mat')}" Name="Material" Kind="InputPin" />
            <Pin Id="{I('me_shadow')}" Name="Is Shadow Caster" Kind="InputPin" DefaultValue="False" />
            <Pin Id="{I('me_comp')}" Name="Components" Kind="InputPin" />
            <Pin Id="{I('me_children')}" Name="Children" Kind="InputPin" />
            <Pin Id="{I('me_name')}" Name="Name" Kind="InputPin" />
            <Pin Id="{I('me_enabled')}" Name="Enabled" Kind="InputPin" />
            <Pin Id="{I('me_out')}" Name="Output" Kind="OutputPin" IsHidden="true" />
            <Pin Id="{I('me_entity')}" Name="Entity" Kind="OutputPin" />
          </Node>
          <Node Bounds="100,500,63,19" Id="{I('rootscene')}">
            <p:NodeReference LastCategoryFullName="Stride" LastDependency="VL.Stride.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="RootScene" />
            </p:NodeReference>
            <Pin Id="{I('rs_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rs_child')}" Name="Child" Kind="InputPin" />
            <Pin Id="{I('rs_child2')}" Name="Child 2" Kind="InputPin" />
            <Pin Id="{I('rs_childs')}" Name="Child Scenes" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('rs_enabled')}" Name="Enabled" Kind="InputPin" />
            <Pin Id="{I('rs_out')}" Name="Output" Kind="OutputPin" />
          </Node>
          <Node Bounds="360,480,205,19" Id="{I('skybox')}">
            <p:NodeReference LastCategoryFullName="Stride.Lights" LastDependency="VL.Stride.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="SkyboxLight" />
            </p:NodeReference>
            <Pin Id="{I('sb_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('sb_trans')}" Name="Transformation" Kind="InputPin" />
            <Pin Id="{I('sb_cube')}" Name="Cube Map" Kind="InputPin" />
            <Pin Id="{I('sb_spec')}" Name="Is Specular Only" Kind="InputPin" />
            <Pin Id="{I('sb_intensity')}" Name="Intensity" Kind="InputPin" DefaultValue="0.63" />
            <Pin Id="{I('sb_shorder')}" Name="Diffuse SHOrder" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('sb_cubemapsize')}" Name="Specular Cube Map Size" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('sb_force')}" Name="Force Build" Kind="InputPin" />
            <Pin Id="{I('sb_bgint')}" Name="Background Intensity" Kind="InputPin" DefaultValue="0.98" />
            <Pin Id="{I('sb_bgenabled')}" Name="Background Enabled" Kind="InputPin" DefaultValue="False" />
            <Pin Id="{I('sb_comp')}" Name="Component" Kind="InputPin" />
            <Pin Id="{I('sb_children')}" Name="Children" Kind="InputPin" />
            <Pin Id="{I('sb_name')}" Name="Name" Kind="InputPin" />
            <Pin Id="{I('sb_enabled')}" Name="Enabled" Kind="InputPin" />
            <Pin Id="{I('sb_out')}" Name="Output" Kind="OutputPin" IsHidden="true" />
            <Pin Id="{I('sb_entity')}" Name="Entity" Kind="OutputPin" />
          </Node>
          <Node Bounds="100,620,205,19" Id="{I('scenewindow')}">
            <p:NodeReference LastCategoryFullName="Stride" LastDependency="VL.Stride.vl">
              <Choice Kind="NodeFlag" Name="Node" Fixed="true" />
              <Choice Kind="ProcessAppFlag" Name="SceneWindow" />
            </p:NodeReference>
            <Pin Id="{I('sw_ctx')}" Name="Node Context" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('sw_bounds')}" Name="Bounds" Kind="InputPin" DefaultValue="925, 134, 640, 480" IsHidden="true" />
            <Pin Id="{I('sw_btd')}" Name="Bound to Document" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('sw_dialog')}" Name="Dialog If Document Changed" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('sw_savebounds')}" Name="Save Bounds" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('sw_bbf')}" Name="Back Buffer Format" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('sw_dbf')}" Name="Depth Buffer Format" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('sw_prio')}" Name="Input Priority" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('sw_ontop')}" Name="Always On Top" Kind="InputPin" IsHidden="true" />
            <Pin Id="{I('sw_input')}" Name="Input" Kind="InputPin" />
            <Pin Id="{I('sw_camera')}" Name="Camera" Kind="InputPin" />
            <Pin Id="{I('sw_defcam')}" Name="Enable Default Camera" Kind="InputPin" />
            <Pin Id="{I('sw_title')}" Name="Title" Kind="InputPin" />
            <Pin Id="{I('sw_clearcolor')}" Name="Clear Color" Kind="InputPin" />
            <Pin Id="{I('sw_clear')}" Name="Clear" Kind="InputPin" />
            <Pin Id="{I('sw_postfx')}" Name="Post Effects" Kind="InputPin" />
            <Pin Id="{I('sw_defpostfx')}" Name="Enable Default Post Effects" Kind="InputPin" />
            <Pin Id="{I('sw_keys')}" Name="Enable Keyboard Shortcuts" Kind="InputPin" />
            <Pin Id="{I('sw_enabled')}" Name="Enabled" Kind="InputPin" />
            <Pin Id="{I('sw_present')}" Name="Present Interval" Kind="InputPin" />
            <Pin Id="{I('sw_out')}" Name="Output" Kind="OutputPin" />
            <Pin Id="{I('sw_clientbounds')}" Name="Client Bounds" Kind="OutputPin" />
            <Pin Id="{I('sw_inputsrc')}" Name="Input Source" Kind="OutputPin" />
          </Node>
        </Canvas>
        <Patch Id="{I('create')}" Name="Create" />
        <Patch Id="{I('update')}" Name="Update" />
        <ProcessDefinition Id="{I('processdef')}">
          <Fragment Id="{I('frag_create')}" Patch="{I('create')}" Enabled="true" />
          <Fragment Id="{I('frag_update')}" Patch="{I('update')}" Enabled="true" />
        </ProcessDefinition>
        {link('p', 'pad_path', 'fm_path')}
        {link('m', 'fm_model', 'me_model')}
        {link('vc', 'vc_out', 'pbr_diffuse')}
        {link('mat', 'pbr_out', 'me_mat')}
        {link('e', 'me_entity', 'rs_child')}
        {link('l', 'sb_entity', 'rs_child2')}
        {link('w', 'rs_out', 'sw_input')}
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
    out = ROOT / "test_vl_code" / "ScaredyShroom.vl"
    out.write_text(TEMPLATE, encoding="utf-8", newline="\n")
    errors = validate(out)
    print(f"wrote {out} ({out.stat().st_size} bytes, {len(_ids)} unique ids)")
    if errors:
        for e in errors:
            print("ERROR:", e)
        return 1
    print("basic validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
