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
for first,second in [('WINCH_PORT','WOOD_COAMING_ASSEMBLY'),('WINCH_STARBOARD','WOOD_COAMING_ASSEMBLY'),('MAINSHEET_TRAVELLER','WOOD_COAMING_ASSEMBLY'),('MAINSHEET_TRAVELLER','UPPER_DECK'),('GENOA_TRACK_PORT','UPPER_DECK'),('GENOA_TRACK_STARBOARD','UPPER_DECK'),('WOOD_TILLER','RUDDER')]:
 tmp=bpy.data.objects[first].copy();tmp.data=tmp.data.copy();sc.collection.objects.link(tmp)
 mod=tmp.modifiers.new('Fit intersection','BOOLEAN');mod.operation='INTERSECT';mod.solver='EXACT';mod.object=bpy.data.objects[second]
 bpy.context.view_layer.objects.active=tmp;bpy.ops.object.modifier_apply(modifier=mod.name)
 bm=bmesh.new();bm.from_mesh(tmp.data);vol=abs(bm.calc_volume(signed=True));bm.free();bpy.data.objects.remove(tmp,do_unlink=True)
 audit.append({'part':first,'against':second,'intersection_mm3':vol})
 if vol>.01:raise RuntimeError(f'Fitting overlap: {first} / {second}: {vol} mm3')
# Confirm the actual reinforcing rods pass through the completed spar geometry.
for names,a,b,radius in [(['MAST_1','MAST_2'],(105.667,0,39),(109.667,0,400),1.0),(['BOOM'],(110,0,74),(230,0,74.8),.75)]:
 direction=Vector(b)-Vector(a)
 bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=direction.length,location=(Vector(a)+Vector(b))/2)
 core=bpy.context.object;core.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
 for name in names:
  tmp=bpy.data.objects[name].copy();tmp.data=tmp.data.copy();sc.collection.objects.link(tmp)
  mod=tmp.modifiers.new('Continuous core clearance','BOOLEAN');mod.operation='INTERSECT';mod.solver='EXACT';mod.object=core
  bpy.context.view_layer.objects.active=tmp;bpy.ops.object.modifier_apply(modifier=mod.name)
  bm=bmesh.new();bm.from_mesh(tmp.data);vol=abs(bm.calc_volume(signed=True));bm.free();bpy.data.objects.remove(tmp,do_unlink=True)
  audit.append({'part':name,'core_intersection_mm3':vol})
  if vol>.01:raise RuntimeError(f'Blocked reinforcing core: {name}: {vol} mm3')
 bpy.data.objects.remove(core,do_unlink=True)
print('SEAT CHECK',json.dumps(audit),flush=True)
(R/'seat_intersection_check.json').write_text(json.dumps(audit,indent=2))
bpy.ops.outliner.orphans_purge(do_recursive=True)
sc.render.filepath='//../docs/images/assembled_model.png'
bpy.context.preferences.filepaths.save_version=0
for text in list(bpy.data.texts):bpy.data.texts.remove(text)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Laurine_L28.blend'),compress=True)
