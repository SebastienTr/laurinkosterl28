import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'build'
bpy.ops.wm.open_mainfile(filepath=str(R/'Laurine_L28.blend'))
sc=bpy.context.scene;deck=bpy.data.objects['UPPER_DECK']
for p in deck.data.polygons:
 if p.material_index==4:p.material_index=0
# Remove orphaned source data; all delivered object and material labels are English.
bpy.ops.outliner.orphans_purge(do_recursive=True)
for o in bpy.data.objects:
 for k in list(o.keys()):
  if k not in ['_RNA_UI']:del o[k]
for c in bpy.data.collections:
 if c.name.startswith('02'):c.name='02 - Metal rods and rigging - DO NOT PRINT'
 if c.name.startswith('01'):c.name='01 - Printable parts'
 if c.name.startswith('03'):c.name='03 - Fit tests'
for i,m in enumerate(bpy.data.materials):
 if not m.name.startswith('PLA'):m.name='Assembly reference material '+str(i+1)
rem=[o for o in sc.objects if o.name.startswith(('WINDOW_','HATCH_RAIL_','COMPANIONWAY_CHANNEL_','MAST_DECK_SHOE'))]
audit=[]
for o in rem:
 tmp=o.copy();tmp.data=o.data.copy();sc.collection.objects.link(tmp)
 mod=tmp.modifiers.new('Intersection check','BOOLEAN');mod.operation='INTERSECT';mod.solver='EXACT';mod.object=deck
 bpy.context.view_layer.objects.active=tmp;bpy.ops.object.modifier_apply(modifier=mod.name)
 bm=bmesh.new();bm.from_mesh(tmp.data);vol=abs(bm.calc_volume(signed=True));bm.free()
 audit.append({'part':o.name,'intersection_with_deck_mm3':vol});bpy.data.objects.remove(tmp,do_unlink=True)
print('SEAT CHECK',json.dumps(audit),flush=True)
(R/'seat_intersection_check.json').write_text(json.dumps(audit,indent=2))
bpy.ops.outliner.orphans_purge(do_recursive=True)
sc.render.filepath='//../docs/images/assembled_model.png'
bpy.context.preferences.filepaths.save_version=0
for text in list(bpy.data.texts):bpy.data.texts.remove(text)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Laurine_L28.blend'),compress=True)
