"""Render the documentation from the exact final model being exported."""
import bpy
from pathlib import Path
from mathutils import Vector
r=Path(__file__).resolve().parents[1]/'build';bpy.ops.wm.open_mainfile(filepath=str(r/'Laurine_L28.blend'))
s=bpy.context.scene;c=s.camera
s.render.engine='BLENDER_WORKBENCH';s.display.shading.show_shadows=False;s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD';s.world.color=(.65,.70,.73);s.view_settings.view_transform='Standard';s.view_settings.exposure=.55
s.render.resolution_x=1500;s.render.resolution_y=950;s.render.resolution_percentage=100
# Documentation renders only: the saved geometry and materials are not changed.
def view(n,loc,target,scale):
 c.location=loc;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=scale;s.render.filepath=str(r/'previews'/f'{n}.png');bpy.ops.render.render(write_still=True)
view('assembled_model',(500,-700,420),(139,0,173),680)
view('straight_rudder_edge',(259,-220,-19),(249,0,-19),87)
view('hull_assembly',(430,-500,240),(139,0,4),335)
view('deck_rigging',(215,-170,190),(175,0,36),180)
view('mast_joint',(140,-75,250),(108,0,229),50)
view('masthead',(134,-65,416),(109,0,395),36)
view('cockpit',(190,-165,135),(259,0,34),125)
view('tiller_fitting',(325,-80,75),(278,0,36),45)
view('bow_pulpit',(-95,-110,100),(24,0,43),105)
view('stern_pushpit',(370,-140,85),(268,0,29),115)
view('rudder_guard',(320,-190,78),(268,0,27),100)
original_locations={o.name:o.location.copy() for o in s.objects}
rem=[o for o in s.objects if o.name.startswith(('WINDOW_','HATCH_RAIL_','COMPANIONWAY_CHANNEL_','MAST_DECK_SHOE'))]
for o in s.objects:
 if o.name.startswith(('RIGGING','BACKSTAY','MAST_','BOOM','SPREADER','DISPLAY_CRADLE')) and o not in rem:o.hide_render=True
view('removable_details_assembled',(230,-170,145),(154,0,39),150)
for o in rem:
 if o.name.startswith('WINDOW'):o.location.y+=20 if 'PORT' in o.name and 'STARBOARD' not in o.name else -20
 else:o.location.z+=15
view('removable_details_exploded',(230,-170,145),(154,0,39),150)
for o in rem:o.location=original_locations[o.name]
for o in s.objects:o.hide_render=o.name not in ['LOWER_HULL','UPPER_DECK'] and not o.name.startswith('ALIGNMENT_PIN')
s.objects['UPPER_DECK'].location.z=35
for o in s.objects:
 if o.name.startswith('ALIGNMENT_PIN'):o.location.z=12
view('exploded_hull_and_deck',(420,-450,230),(139,0,27),355)
