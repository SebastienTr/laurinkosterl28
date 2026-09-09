import bpy,bmesh,math,json,struct,hashlib
from mathutils.geometry import convex_hull_2d
from mathutils import Vector,Matrix
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'build'
SRC=ROOT/'source/base_geometry.blend'
for name in ['stl','tests','colors','previews']:(R/name).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SRC))
sc=bpy.context.scene;sc.frame_set(1);dg=bpy.context.evaluated_depsgraph_get()
source={}
for o in list(sc.objects):
 if o.type=='MESH':
  ev=o.evaluated_get(dg);me=bpy.data.meshes.new_from_object(ev,depsgraph=dg);me.transform(Matrix.Scale(1000/30,4)@o.matrix_world)
  source[o.name]=me
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
for c in list(bpy.data.collections):bpy.data.collections.remove(c)
sc.name='Laurine - hybrid model 1:30';sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=.001
sc.frame_start=sc.frame_end=1
for m in list(sc.timeline_markers):sc.timeline_markers.remove(m)
col=bpy.data.collections.new('01 - Printable parts');sc.collection.children.link(col)
ref=bpy.data.collections.new('02 - Rods and thread - DO NOT PRINT');sc.collection.children.link(ref)
proto=bpy.data.collections.new('03 - Fit tests');sc.collection.children.link(proto)
proto.hide_render=True
parts=[];tests=[];records=[]
def log(s):print(s,flush=True)
def mat(name,c):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);return m
cream=mat('Impression — ivoire',(.76,.72,.53));red=mat('Impression — bordeaux',(.35,.035,.06));blue=mat('Impression — sous-marine',(.09,.24,.3));silver=mat('Pièces — aluminium',(.53,.59,.64));wood=mat('Menuiserie — acajou',(.30,.10,.04));dark=mat('Fils et vitrages',(.035,.07,.095))
def obj(name,me,collection=col,material=None):
 o=bpy.data.objects.new(name,me);collection.objects.link(o)
 if material:me.materials.clear();me.materials.append(material)
 return o
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o

def mesh(name,vs,fs,material=cream,collection=col):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=obj(name,me,collection,material)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();return o

def box(name,center,size,material=cream):
 x,y,z=center;a,b,c=[v/2 for v in size]
 return mesh(name,[(x+u*a,y+v*b,z+w*c) for u,v,w in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material)
def cyl(name,a,b,r,material=silver,n=40,inner=0,ry=None,collection=col):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,1,0))).normalized()
 if u.length<.5:u=axis.cross(Vector((1,0,0))).normalized()
 v=axis.cross(u).normalized();ry=ry or r;vs=[]
 for rr,ss in ([(r,ry),(inner,inner)] if inner else [(r,ry)]):
  for p in (a,b):
   for j in range(n):vs.append(tuple(p+u*rr*math.cos(j*2*math.pi/n)+v*ss*math.sin(j*2*math.pi/n)))
 fs=[]
 for j in range(n):
  k=(j+1)%n;fs.append((j,k,n+k,n+j))
  if inner:fs.extend([(2*n+j,3*n+j,3*n+k,2*n+k),(j,2*n+j,2*n+k,k),(n+j,n+k,3*n+k,3*n+j)])
 if not inner:fs += [tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
 o=mesh(name,vs,fs,material,collection)
 for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
 return o
def boolean(o,c,op='DIFFERENCE'):
 # Explicitly align material slots on both operands before the Boolean.
 old=list(c.data.materials);ids=[p.material_index for p in c.data.polygons]
 for m in old:
  if m and m.name not in o.data.materials:o.data.materials.append(m)
 slots=list(o.data.materials)
 c.data.materials.clear()
 for m in slots:c.data.materials.append(m)
 for p,i in zip(c.data.polygons,ids):
  if old:p.material_index=slots.index(old[min(i,len(old)-1)])
 active(o);m=o.modifiers.new('Assemblage','BOOLEAN');m.operation=op;m.solver='EXACT';m.object=c
 bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(c,do_unlink=True)
def dup(o,name):return obj(name,o.data.copy())
def clip(o,axis,value,keep_positive):
 bm=bmesh.new();bm.from_mesh(o.data);normal=Vector(tuple(int(i==axis) for i in range(3)));point=normal*value
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=point,plane_no=normal,clear_inner=keep_positive,clear_outer=not keep_positive)
 edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co[axis]-value)<.001 for v in e.verts)]
 if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
def register(o,rotation=None,test=False):
 (tests if test else parts).append((o,rotation or Matrix.Identity(4)));return o

def cut_hole(o,a,b,r):boolean(o,cyl('Outil trou',a,b,r))

log('STRUCTURE')
hull=obj('Structure maîtresse',source['Coque et cockpit creusé • V05'].copy())
for name in ['Roof • nez et flancs arrondis','Hiloire de cockpit • tribord','Hiloire de cockpit • bâbord','Hiloire arrière']:
 log('Union '+name);boolean(hull,obj('Outil',source[name].copy()),'UNION')
# Separate stainless companionway channels, with recessed glue seats.
seats=[]
for side in (-1,1):
 label='PORT' if side>0 else 'STARBOARD'
 rail=box('COMPANIONWAY_CHANNEL_'+label,(196.2,side*8.7,30.5),(3.6,3.0,21),silver)
 boolean(rail,box('Channel groove',(196.2,side*6.9,31.0),(1.6,4.0,22),silver))
 boolean(hull,box('Channel recess',(196.2,side*8.7,30.425),(3.9,3.3,21.15),cream))
 register(rail,Matrix.Rotation(math.pi/2,4,'Y'))
 seats.append({'part':rail.name,'side_clearance_mm':.15,'bottom_clearance_mm':.15,'assembly':'Glue into recess; keep washboard groove clear.'})
boolean(hull,box('Seuil',(196.2,0,20.0),(3.6,19,1.0)),'UNION')
for side in (-1,1):boolean(hull,box('Clear threshold at channel seat',(196.2,side*8.7,30.425),(3.9,3.3,21.15),cream))
# Detachable metal mast shoe. The continuous bore remains aligned with the mast core.
shoe=box('MAST_DECK_SHOE',(105.667,0,38.4),(9,8,3.2),silver)
cut_hole(shoe,(105.46,0,20),(106.1,0,77),1.15)
boolean(hull,box('Mast shoe recess',(105.667,0,38.325),(9.3,8.3,3.35),cream))
cut_hole(hull,(105.46,0,20),(106.1,0,77),1.15)
register(shoe)
seats.append({'part':shoe.name,'side_clearance_mm':.15,'bottom_clearance_mm':.15,'assembly':'Glue shoe into its recess, align the 2 mm mast-core bore.'})
# Separate metal sliding-hatch rails, with concealed locating pins.
for side in (-1,1):
 label='PORT' if side>0 else 'STARBOARD'
 rail=box('HATCH_RAIL_'+label,(171.7,side*10.0,39.3),(57,1.8,3.0),silver)
 boolean(hull,box('Hatch rail seat',(171.7,side*10.0,39.225),(57.3,2.1,3.15),cream))
 for x in [150,170,189]:
  boolean(rail,cyl('Rail locating pin',(x,side*10,36.6),(x,side*10,38.1),.45,silver),'UNION')
  boolean(hull,cyl('Rail pin socket',(x,side*10,36.4),(x,side*10,38.2),.575,cream))
 register(rail,Matrix.Rotation(math.pi/2,4,'X'))
 seats.append({'part':rail.name,'side_clearance_mm':.15,'pin_diameter_mm':.9,'socket_diameter_mm':1.15,'assembly':'Seat all three locating pins, glue after cleaning.'})
# Glazing inserts follow the original rounded X/Z outlines and roof curvature.
# The back of each insert is planar so it can be printed directly on the bed.
for name,me in source.items():
 if not name.startswith('Vitrage hublot'):continue
 side=1 if 'bâbord' in name else -1;label='PORT' if side>0 else 'STARBOARD';num='1' if 'hublot 1' in name else '2'
 points=[Vector((v.co.x,v.co.z)) for v in me.vertices]
 indices=convex_hull_2d(points);outline=[points[i] for i in indices]
 # Ensure counterclockwise outline for outward offset.
 area=sum(a.x*b.y-b.x*a.y for a,b in zip(outline,outline[1:]+outline[:1]))
 if area<0:outline.reverse()
 def offset_polygon(poly,d):
  out=[]
  for i,p in enumerate(poly):
   a=(p-poly[i-1]).normalized();b=(poly[(i+1)%len(poly)]-p).normalized();na=Vector((a.y,-a.x));nb=Vector((b.y,-b.x));n=(na+nb).normalized();out.append(p+n*(d/max(.2,n.dot(na))))
  return out
 surround=offset_polygon(outline,.15);surface=[]
 for p in outline:
  hit,pt,n,idx=hull.ray_cast(Vector((p.x,side*100,p.y)),Vector((0,-side,0)))
  if not hit:raise RuntimeError('Window outline misses roof: '+name+str(p))
  surface.append(side*pt.y)
 back=min(surface)-1.0;K=len(outline)
 vs=[(p.x,side*back,p.y) for p in outline]+[(p.x,side*(y+.25),p.y) for p,y in zip(outline,surface)]
 fs=[tuple(range(K-1,-1,-1)),tuple(range(K,2*K))]+[(i,(i+1)%K,(i+1)%K+K,i+K) for i in range(K)]
 cutter_faces=list(fs)
 # Sample the actual roof over the whole visible face, not just its outline.
 # Eight radial rings avoid a twisted non-planar n-gon across each window.
 center=sum(outline,Vector((0,0)))/K
 ring_indices=[list(range(K,2*K))]
 for step in range(7,0,-1):
  ring=[]
  for edge in outline:
   p=center.lerp(edge,step/8)
   hit,pt,n,idx=hull.ray_cast(Vector((p.x,side*100,p.y)),Vector((0,-side,0)))
   if not hit:raise RuntimeError('Window face misses roof')
   ring.append(len(vs));vs.append((p.x,pt.y+side*.25,p.y))
  ring_indices.append(ring)
 hit,pt,n,idx=hull.ray_cast(Vector((center.x,side*100,center.y)),Vector((0,-side,0)))
 ci=len(vs);vs.append((center.x,pt.y+side*.25,center.y))
 fs=[fs[0]]+fs[2:]
 front_start=len(fs)
 for outer,inner in zip(ring_indices,ring_indices[1:]):
  for i in range(K):fs.append((outer[i],outer[(i+1)%K],inner[(i+1)%K],inner[i]))
 for i in range(K):fs.append((ring_indices[-1][i],ring_indices[-1][(i+1)%K],ci))
 win=mesh('WINDOW_'+label+'_'+num,vs,fs,dark)
 for f in win.data.polygons:f.use_smooth=f.index>=front_start
 # Recess is a closed, flat-bottomed prism with a 0.15 mm glue allowance.
 vs=[(p.x,side*y,p.y) for y in [back-.15,max(surface)+2] for p in surround]
 cutter=mesh('Window glue recess',vs,cutter_faces,cream);boolean(hull,cutter)
 register(win,Matrix.Rotation(side*math.pi/2,4,'X'))
 seats.append({'part':win.name,'edge_clearance_mm':.15,'back_clearance_mm':.15,'minimum_thickness_mm':1.25,'outline_vertices':K,'assembly':'Flat back onto bed. Glue into matching recess from outside; no snap fit.'})
(R/'removable_details.json').write_text(json.dumps(seats,indent=2))
# Detachable timber handrails: three integral pins and matching blind holes.
for side in (-1,1):
 p0=Vector((116,side*14.33,40));p1=Vector((165.3,side*14.33,40.5))
 hand=cyl('MAIN_COURANTE_BOIS_'+('BABORD' if side>0 else 'TRIBORD'),p0,p1,.65,wood,n=32)
 for t in (0,.5,1):
  pt=p0.lerp(p1,t)
  hit,surf,n,idx=hull.ray_cast(Vector((pt.x,pt.y,100)),Vector((0,0,-1)))
  assert hit
  boolean(hand,cyl('Pied main courante',(pt.x,pt.y,surf.z+.03),pt,.65,wood),'UNION')
  boolean(hand,cyl('Tenon bois',(pt.x,pt.y,surf.z-1.2),(pt.x,pt.y,surf.z+.2),.45,wood),'UNION')
  cut_hole(hull,(pt.x,pt.y,surf.z-1.4),(pt.x,pt.y,surf.z+.3),.575)
 register(hand,Matrix.Rotation(math.pi/2,4,'X'))
# Circular hatch, raised disc (painted glazing), not a thin loose membrane.
boolean(hull,cyl('Panneau avant rond',(89,0,37.8),(89,0,40.4),8.5,cream),'UNION')
# Eyelet pilot holes for metal wire loops. Positions are inherited from interpreted V07 rig.
anchors=[]
# Twin backstays: confirmed by owner; detailed head attachment remains an estimate.
backstays=[]
for side,label in [(-1,'TRIBORD'),(1,'BABORD')]:
 hit,p,n,idx=hull.ray_cast(Vector((264,side*13,100)),Vector((0,0,-1)))
 if not hit:raise RuntimeError('Backstay anchor outside hull')
 cut_hole(hull,p-Vector((0,0,4)),p+Vector((0,0,1)),.4)
 end=p+Vector((0,0,.6));head=Vector((112.15,side*1.6,396))
 cyl('FIL — PATARAS_'+label,end,head,.10,dark,collection=ref)
 backstays.append({'side':label,'foot':list(end),'head':list(head),'material':'fil de maquettisme, non imprimé'})
(R/'pataras.json').write_text(json.dumps(backstays,ensure_ascii=False,indent=2))

# Rounded stainless guard rails. Photo-based study, 1.4 mm reinforced tubes for FDM.
railpaths=[]
def rounded_path(points,trim=2.5):
 points=[Vector(p) for p in points];out=[points[0]]
 for i,p in enumerate(points[1:-1],1):
  prev,nxt=points[i-1],points[i+1];d=min(trim,(p-prev).length*.3,(nxt-p).length*.3)
  a=p+(prev-p).normalized()*d;b=p+(nxt-p).normalized()*d
  for j in range(9):
   t=j/8;out.append((1-t)**2*a+2*t*(1-t)*p+t*t*b)
 out.append(points[-1]);return out

def curved_tube(name,points,r=.7,trim=2.5):
 ps=rounded_path(points,trim);vs=[];K=24;prev_t=None;prev_u=None
 for i,p in enumerate(ps):
  t=(ps[min(i+1,len(ps)-1)]-ps[max(0,i-1)]).normalized()
  if prev_t is None:
   u=t.cross(Vector((0,0,1)))
   if u.length<.01:u=t.cross(Vector((0,1,0)))
  else:u=prev_t.rotation_difference(t)@prev_u
  u=(u-t*u.dot(t)).normalized();v=t.cross(u).normalized();prev_t=t.copy();prev_u=u.copy()
  for j in range(K):q=j*2*math.pi/K;vs.append(tuple(p+r*(u*math.cos(q)+v*math.sin(q))))
 fs=[tuple(range(K-1,-1,-1)),tuple((len(ps)-1)*K+j for j in range(K))]
 for i in range(len(ps)-1):
  for j in range(K):fs.append((i*K+j,i*K+(j+1)%K,(i+1)*K+(j+1)%K,(i+1)*K+j))
 railpaths.append({'name':name,'centreline_mm':[list(p) for p in ps],'tube_print_diameter_mm':2*r})
 o=mesh(name,vs,fs,silver)
 for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
 return o

def rail_foot(rail,x,y,top):
 hit,p,n,idx=hull.ray_cast(Vector((x,y,100)),Vector((0,0,-1)))
 if not hit:raise RuntimeError('Balcon foot outside hull '+str((x,y)))
 foot=p+Vector((0,0,.5))
 boolean(rail,cyl('Jambe balcon',foot,Vector(top),.7,silver),'UNION')
 boolean(rail,cyl('Platine balcon',p,p+Vector((0,0,.7)),1.35,silver),'UNION')
 # An integral locating pin, retained in printed accessory, sits in a hull bore.
 boolean(rail,cyl('Tenon balcon',p-Vector((0,0,2)),p+Vector((0,0,.3)),.6,silver),'UNION')
 cut_hole(hull,p-Vector((0,0,2.4)),p+Vector((0,0,1)),.75)
 return p
# New owner photos, 2026-09-08: the bow tube drops into a central U.
# Rear bases and two narrow forward supports; no high transverse tube across the U.
bowpoints=[(48,-22,30),(38,-23,52),(13,-17,55),(1,-16,55),(0,-5,55),(0,-5,40)]
# Analytic semicircular bottom of the central U, radius 5 mm.
for j in range(1,17):
 angle=math.pi+math.pi*j/16
 bowpoints.append((0,5*math.cos(angle),40+5*math.sin(angle)))
bowpoints += [(0,5,55),(1,16,55),(13,17,55),(38,23,52),(48,22,30)]
bow=curved_tube('BALCON_AVANT_INOX',bowpoints,trim=4)
for side in (-1,1):
 rail_foot(bow,48,side*22,(48,side*22,30))
 rail_foot(bow,12,side*6,(0,side*5,43))
 # Side intermediate rails meet the rear sloping legs and the forward U uprights.
 boolean(bow,curved_tube('Lisse latérale avant',[(43,side*22.5,41),(0,side*5,43)]),'UNION')
register(bow)
# Upper stern pulpit and lower rudder guard are independent accessories on Laurine.
sternpts=[(243,-25,29),(250,-25,48),(276,-22,49),(283,-17,49),(285,-11,49),(285,11,49),(283,17,49),(276,22,49),(250,25,48),(243,25,29)]
stern=curved_tube('BALCON_ARRIERE_INOX',sternpts,trim=4)
for side in (-1,1):rail_foot(stern,240,side*26,(243,side*25,29))
def side_point(x,z,side):
 hit,p,n,idx=hull.ray_cast(Vector((x,side*100,z)),Vector((0,-side,0)))
 if not hit:raise RuntimeError('Side attachment outside hull '+str((x,z,side)))
 return p

def side_fitting(rail,x,z,side):
 p=side_point(x,z,side);outward=Vector((0,side,0))
 boolean(rail,cyl('Platine latérale',p-outward*.15,p+outward*.6,1.3,silver),'UNION')
 cut_hole(rail,p-outward*.5,p+outward*2,.45)
 cut_hole(hull,p-outward*2.5,p+outward*.8,.45)
 return p
for side in (-1,1):
 base=side_point(264,25,side)+Vector((0,side*.5,0));top=Vector((276,side*22,49))
 boolean(stern,curved_tube('Montant arrière sur flanc',[tuple(base),tuple(top)]),'UNION')
 # Intermediate side rail visible below the top rail, joins the two upper-pulpit legs.
 forward=Vector((246.5,side*25,38.5));aft=base.lerp(top,.5625)
 boolean(stern,curved_tube('Lisse latérale arrière',[tuple(forward),tuple(aft)]),'UNION')
 side_fitting(stern,264,25,side)
register(stern)
# Compact independent low guard, with short triangular side braces and no tall rear uprights.
low=[]
qleft=side_point(252,14,-1)+Vector((0,-.5,0));qright=side_point(252,14,1)+Vector((0,.5,0))
low=[tuple(qleft),(281,-14,13),(290,-8,13),(292,0,13),(290,8,13),(281,14,13),tuple(qright)]
guard=curved_tube('BALCON_PROTECTION_SAFRAN_INOX',low,trim=3)
for side in (-1,1):
 upper=side_point(269,23,side)+Vector((0,side*.5,0))
 front=side_point(246,23,side)+Vector((0,side*.5,0))
 boolean(guard,curved_tube('Diagonale courte de protection',[tuple(upper),(281,side*14,13)]),'UNION')
 # Follow the curved hull rather than hiding a straight chord inside it.
 tie=[tuple(upper)]
 for x in (265,261,257,253,249):tie.append(tuple(side_point(x,23,side)+Vector((0,side*1.2,0))))
 tie.append(tuple(front))
 boolean(guard,curved_tube('Tirant haut latéral',tie,trim=1),'UNION')
 for x,z in [(252,14),(269,23),(246,23)]:side_fitting(guard,x,z,side)
register(guard)
(R/'balcons_centre_lignes.json').write_text(json.dumps(railpaths,ensure_ascii=False,indent=2))
hull.name='COQUE_ENTIERE'
register(hull,Matrix.Rotation(math.pi/4,4,'Z'))
# Safran kept at 2 mm, attached by two short metal pins; matching horizontal blind holes.
rudder=obj('SAFRAN',source['Safran • épaisseur provisoire 60 mm'].copy(),material=blue)
# Straighten only the rudder's lower leading edge, from keel toe to below propeller opening.
# Move the adjacent aft edge of the integrated keel by the same amount to keep the 0.833 mm gap.
import bisect
z0=-43.33332824707031;z1=-20.0;x0=221.50188;x1=247.88788
zs=[z0+.0004+(z1-z0-.0004)*i/1600 for i in range(1601)]
old_front=[]
for z in zs:
 hit,pt,n,idx=rudder.ray_cast(Vector((-100,0,z)),Vector((1,0,0)))
 old_front.append(pt.x if hit else x0)
def previous_x(z):
 i=max(0,min(len(zs)-2,bisect.bisect_right(zs,z)-1));t=max(0,min(1,(z-zs[i])/(zs[i+1]-zs[i])))
 return old_front[i]*(1-t)+old_front[i+1]*t
changes={}
for ob,is_hull in [(rudder,False),(hull,True)]:
 moved=0;maxmove=0
 for v in ob.data.vertices:
  x,y,z=v.co
  if z>z1 or z<z0 or x<205:continue
  oldx=previous_x(z)-(1000/30*.025 if is_hull else 0)
  goal=x0+(x1-x0)*(z-z0)/(z1-z0)-(1000/30*.025 if is_hull else 0)
  distance=max(0,oldx-x) if is_hull else max(0,x-oldx)
  t=max(0,min(1,(distance-.5)/12))
  w=1-t*t*(3-2*t)
  dx=(goal-oldx)*w
  if abs(dx)>1e-7:v.co.x+=dx;moved+=1;maxmove=max(maxmove,abs(dx))
 ob.data.update();changes[ob.name]={'vertices_moved':moved,'max_displacement_mm':maxmove}
(R/'correction_safran.json').write_text(json.dumps({'segment_xz_mm':[[x0,z0],[x1,z1]],'gap_mm':.8333333,'changes':changes,'scope':'Bord sous helice seulement et raccord de quille adjacent; autres courbes conservees'},indent=2))
# Cut the bearing holes normal to inclined leading edge using actual mesh ray casting.
for z in (-25,8):
 hit,pt,n,idx=rudder.ray_cast(Vector((-100,0,z)),Vector((1,0,0)))
 if hit:
  cut_hole(rudder,(pt.x-.2,0,z),(pt.x+5,0,z),.45)
  target=hull
  cut_hole(target,(pt.x-6,0,z),(pt.x+.2,0,z),.45)
# Rudder head and wooden tiller, interpreted from close-up photos, dimensions estimated.
zmax=max(v.co.z for v in rudder.data.vertices)
top=[v.co for v in rudder.data.vertices if v.co.z>zmax-.5]
h=sum(top,Vector())/len(top);h.y=0
headtop=Vector((h.x-1,0,36))
# Compact flat-sided rudder-head strap and a two-cheek metal yoke.
def plate_profile(name,outline,y0,y1,material):
 n=len(outline);vs=[(x,y,z) for y in (y0,y1) for x,z in outline]
 fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,vs,fs,material)
hx=headtop.x
neck=plate_profile('Ferrure tête safran',[(h.x-2,zmax-3),(h.x+2,zmax-3),(hx+2,36.1),(hx-2,36.1)],-1.2,1.2,silver)
boolean(rudder,neck,'UNION')
# Two visible cheeks leave a 3.3 mm opening for the wooden heel.
for side in (-1,1):
 cheek=plate_profile('Joue inox de barre',[(hx-7,35.5),(hx-7,38.1),(hx+1.5,39),(hx+2.2,38.3),(hx+2.2,35.5)],side*1.65,side*2.55,silver)
 boolean(rudder,cheek,'UNION')
# Crosspiece below the timber joins both cheeks to the rudder head.
boolean(rudder,box('Fond de chape',(hx-2.5,0,35.9),(8.2,5.1,1.0),silver),'UNION')
# A real cross-pin locates the tiller heel between the compact cheeks.
for side in (-1,1):
 boolean(rudder,cyl('Tête axe barre',(hx-1.5,side*2.45,37.4),(hx-1.5,side*2.9,37.4),.8,silver,n=24),'UNION')
cut_hole(rudder,(hx-1.5,-4,37.4),(hx-1.5,4,37.4),.45)
vs=[];fs=[];N=48;K=32
for i in range(N+1):
 t=i/N;p=headtop+Vector((-42*t,0,1.5+3.0*math.sin(math.pi*t/2)))
 # A slim rounded rectangular heel transitions to the rounded handgrip.
 power=2.8-0.8*t
 for j in range(K):
  q=j*2*math.pi/K;c=math.cos(q);d=math.sin(q)
  vs.append((p.x,p.y+(1.4-.35*t)*math.copysign(abs(c)**(2/power),c),p.z+(1.05+.25*t)*math.copysign(abs(d)**(2/power),d)))
for i in range(N):
 for j in range(K):fs.append((i*K+j,i*K+(j+1)%K,(i+1)*K+(j+1)%K,(i+1)*K+j))
fs += [tuple(range(K-1,-1,-1)),tuple(N*K+j for j in range(K))]
tiller=mesh('BARRE_FRANCHE_BOIS',vs,fs,wood)
for p in tiller.data.polygons:p.use_smooth=len(p.vertices)==4
cut_hole(tiller,(hx-1.5,-4,37.4),(hx-1.5,4,37.4),.45)
register(tiller,Matrix.Rotation(math.pi/2,4,'X'))
# Curved wood caps follow the V07 coamings, thickened for the miniature.
wood_caps=[]
for label in ('tribord','bâbord'):
 o=obj('COURONNEMENT_BOIS_'+('TRIBORD' if label=='tribord' else 'BABORD'),source['Couronnement bois • '+label].copy(),material=wood)
 for v in o.data.vertices:v.co += v.normal*.25
 wood_caps.append(o)
rear=box('WOOD_COAMING_ASSEMBLY',(252.33,0,30.2),(2.0,35.0,1.5),wood)
for cap in wood_caps:
 end=max((v.co for v in cap.data.vertices),key=lambda p:p.x)
 side=1 if end.y>0 else -1
 bridge=box('Timber corner joint',((end.x+252.33)/2,side*17.5,30.2),(252.33-end.x+2.0,3.2,1.5),wood)
 active(bridge);bevel=bridge.modifiers.new('Rounded timber corner','BEVEL');bevel.width=.25;bevel.segments=4
 bpy.ops.object.modifier_apply(modifier=bevel.name)
 boolean(rear,bridge,'UNION');boolean(rear,cap,'UNION')
register(rear)
# U-shaped trim seen on aft cockpit wall, placed above the well floor.
trim=box('ENCADREMENT_BOIS_COCKPIT',(249.7,0,20.3),(1.2,10,1.2),wood)
for side in (-1,1):boolean(trim,box('Montant',(249.7,side*4.4,23.0),(1.2,1.2,6.6),wood),'UNION')
register(trim,Matrix.Rotation(math.pi/2,4,'Y'))
register(rudder,Matrix.Rotation(math.pi/2,4,'X'))
for name,z0,z1 in [('PLANCHE_BASSE',20.8,29),('PLANCHE_HAUTE',29.2,40.2)]:
 o=box(name,(196.2,0,(z0+z1)/2),(1.2,16.6,z1-z0),wood);register(o,Matrix.Rotation(math.pi/2,4,'Y'))
lid=box('CAPOT_COULISSANT',(184.7,0,41.4),(28.6,21.6,1.2),cream)
boolean(lid,box('Prise capot',(197,0,42.2),(1.4,8,1.0),wood),'UNION');register(lid)
# Two longer sleeves meet inside the spreader collar around a continuous metal core.
A=Vector((105.667,0,39));B=Vector((109.667,0,400));D=(B-A).normalized();L=(B-A).length
mast_joint=190.0
mast_spans=[(0,mast_joint-.05),(mast_joint+.05,L)]
def spar_print_rotation(direction):
 # Level the longitudinal axis before turning it diagonally on the print bed.
 return Matrix.Rotation(math.pi/4,4,'Z')@direction.rotation_difference(Vector((1,0,0))).to_matrix().to_4x4()
for i,(start,end) in enumerate(mast_spans):
 o=cyl(f'MAT_{i+1}',A+D*start,A+D*end,2.75,inner=1.15,ry=2.4,n=64)
 register(o,spar_print_rotation(D))
cyl('Mast brass core - diameter 2 mm, length 378 mm',A-D*18,B-D*1,1,silver,collection=ref)
# One-piece boom with thicker sidewalls and a 1.5 mm metal core.
boomA=Vector((110,0,74));boomB=Vector((230,0,74.8));boomD=(boomB-boomA).normalized()
register(cyl('BOME',boomA,boomB,2.35,inner=.9,ry=2.0,n=64),spar_print_rotation(boomD))
cyl('Boom metal core - diameter 1.5 mm, length about 120 mm',boomA,boomB,.75,silver,collection=ref)
# Mast collar with transverse bar aft of the mast core to avoid intersecting it.
sp=A+D*190
collar=box('COLLIER_BARRES_FLECHE',(sp.x+1.2,0,sp.z),(10.5,8.5,5),silver)
cut_hole(collar,(sp.x-1,0,sp.z-100),(sp.x+1.2,0,sp.z+100),2.95)
# round central clearance accommodates entire oval mast; glue collar at marked height.
cut_hole(collar,(sp.x+4,-10,sp.z),(sp.x+4,10,sp.z),.55)
register(collar)
cyl('Barres de flèche — fil laiton Ø1, 56 mm',(sp.x+4,-28,sp.z),(sp.x+4,28,sp.z),.5,silver,collection=ref)
# Glued saddle for boom, cut to oval mast approximate circular seat.
saddle=box('SUPPORT_BOME',(108.9,0,74),(6.5,6,6),silver)
cut_hole(saddle,(105.9,0,60),(105.9,0,90),2.85)
cut_hole(saddle,(108,0,74),(115,0,74.05),.9)
register(saddle)
# Small fittings are functional model interfaces, dimensioned in millimetres.
rig_points={};rig_routes=[]
def deck_eye(label,x,y):
 hit,p,n,idx=hull.ray_cast(Vector((x,y,100)),Vector((0,0,-1)))
 if not hit:raise RuntimeError('Deck eye misses surface: '+label)
 cut_hole(hull,p-Vector((0,0,3)),p+Vector((0,0,1)),.4)
 rig_points[label]=list(p+Vector((0,0,1.5)))
 return p
# Keep the existing chainplate pilot holes; sample their true deck heights.
for i,anchor in enumerate(anchors):
 x,y,z=anchor['position_mm'];deck_eye('CHAINPLATE_'+str(i+1),x,y)
for side,label in [(-1,'STARBOARD'),(1,'PORT')]:
 deck_eye('BACKSTAY_'+label,264,side*13)
 deck_eye('HALYARD_'+label,110,side*11)
 deck_eye('VANG_DECK_'+label,111,side*7)
# Explicit fore/aft lower shrouds and cap shrouds: a consistent, symmetric thread plan.
for side,label in [(-1,'STARBOARD'),(1,'PORT')]:
 for role,x in [('LOWER_FORWARD',94),('CAP_SHROUD',112),('LOWER_AFT',130)]:
  deck_eye(role+'_'+label,x,side*32)
deck_eye('FORESTAY',10,0)
# Paired cockpit winches, seated on the coaming, with integral pins.
for side,label in [(-1,'STARBOARD'),(1,'PORT')]:
 x,y=200,side*25
 hit,p,n,idx=hull.ray_cast(Vector((x,y,100)),Vector((0,0,-1)))
 if not hit:raise RuntimeError('Winch misses coaming')
 # A small timber backing pad keeps the curved cap connected around the socket.
 local_top=max(v.co.z for v in rear.data.vertices if abs(v.co.x-x)<3 and abs(v.co.y-y)<3)
 top=max(p.z+1.2,local_top+.2)
 boolean(rear,cyl('Winch timber backing',p-Vector((0,0,.1)),(x,y,top),2.7,wood),'UNION')
 cut_hole(rear,(x,y,top-2),(x,y,top+1),.75)
 p=Vector((x,y,top+.1))
 win=cyl('WINCH_'+label,p+Vector((0,0,.1)),p+Vector((0,0,1.1)),2.5,dark)
 boolean(win,cyl('Winch drum',p+Vector((0,0,.8)),p+Vector((0,0,4.4)),1.8,dark),'UNION')
 boolean(win,cyl('Winch crown',p+Vector((0,0,4.1)),p+Vector((0,0,4.8)),2.25,dark),'UNION')
 boolean(win,cyl('Winch locating pin',p-Vector((0,0,1.8)),p+Vector((0,0,.5)),.6,dark),'UNION')
 cut_hole(hull,p-Vector((0,0,2)),p+Vector((0,0,.5)),.75)
 cut_hole(win,p+Vector((0,0,3.4)),p+Vector((0,0,5)),.5)
 register(win);rig_points['WINCH_'+label]=list(p+Vector((0,0,2.8)))
# Longer genoa tracks: a provisional 1.80 m full-size length, pending measurement.
for side,label in [(-1,'STARBOARD'),(1,'PORT')]:
 x,y=180,side*31
 support_x=(143,160,177,194)
 contacts=[]
 for tx in support_x:
  hit,q,n,idx=hull.ray_cast(Vector((tx,y,100)),Vector((0,0,-1)))
  if not hit:raise RuntimeError('Genoa track misses deck: '+label)
  contacts.append(q)
 rail_bottom=max(q.z for q in contacts)+.15
 track=box('GENOA_TRACK_'+label,(168,y,rail_bottom+.75),(60,1.8,1.5),silver)
 for q in contacts:
  boolean(track,cyl('Track pedestal',q,(q.x,y,rail_bottom+.8),1.2,silver),'UNION')
  boolean(track,cyl('Track pin',q-Vector((0,0,1.8)),q+Vector((0,0,.4)),.6,silver),'UNION')
  cut_hole(hull,q-Vector((0,0,2)),q+Vector((0,0,.5)),.75)
 boolean(track,box('Genoa car',(x,y,rail_bottom+1.85),(3.2,2.6,1.4),silver),'UNION')
 cut_hole(track,(x,y,rail_bottom+.2),(x,y,rail_bottom+3.2),.4)
 boolean(track,dup(hull,'Deck contact trim'))
 register(track);rig_points['GENOA_CAR_'+label]=[x,y,rail_bottom+3.65]
# The traveller spans the middle of the cockpit directly below the boom sheet tab.
trav_x,trav_y,trav_bottom=225.0,23.85,31.1
trav=box('MAINSHEET_TRAVELLER',(trav_x,0,trav_bottom+.8),(2.4,49.6,1.6),silver)
for side in (-1,1):
 y=side*trav_y
 boolean(rear,cyl('Traveller timber backing',(trav_x,y,29.4),(trav_x,y,31.0),1.8,wood),'UNION')
 boolean(trav,cyl('Traveller pin',(trav_x,y,29.5),(trav_x,y,31.5),.45,silver),'UNION')
 for support in (rear,hull):cut_hole(support,(trav_x,y,29.3),(trav_x,y,32),.575)
boolean(trav,box('Mainsheet car',(trav_x,0,33.2),(3,3.6,1.3),silver),'UNION')
cut_hole(trav,(trav_x,0,31.6),(trav_x,0,35.2),.4)
register(trav);rig_points['MAINSHEET_CAR']=[trav_x,0,34.9]
# Blind holes in external lugs avoid the metal cores through the spars.
def spar_eye(owner,label,point):
 p=Vector(point)
 lug=box('External rigging lug',p,(3.2,3.2,3.2),silver)
 active(lug);bevel=lug.modifiers.new('Rounded eye tab','BEVEL');bevel.width=.4;bevel.segments=4
 bpy.ops.object.modifier_apply(modifier=bevel.name)
 boolean(owner,lug,'UNION')
 cut_hole(owner,p-Vector((0,2.2,0)),p+Vector((0,2.2,0)),.5)
 rig_points[label]=list(p)
for label,x,z in [('MASTHEAD_FORWARD',106.4,396),('MASTHEAD_AFT',112.6,396)]:
 spar_eye(bpy.data.objects['MAT_2'],label,(x,0,z))
for label,x,z in [('LOWER_SHROUDS',110.7,224),('MAIN_TACK',109.6,79)]:
 spar_eye(bpy.data.objects['MAT_2' if (Vector((x,0,z))-A).dot(D)>mast_joint else 'MAT_1'],label,(x,0,z))
for label,x,z in [('BOOM_TACK',113,77.0),('BOOM_CLEW',225,77.8),('BOOM_SHEET',225,71.8),('BOOM_VANG',139,71.2)]:
 spar_eye(bpy.data.objects['BOME'],label,(x,0,z))
rig_points['SPREADER_PORT']=[sp.x+4,28,sp.z]
rig_points['SPREADER_STARBOARD']=[sp.x+4,-28,sp.z]
# Metal eyelets shown at every deck/car attachment; install from 0.3 mm wire.
for label,coords in rig_points.items():
 if label.startswith(('MAST','LOWER_SHROUDS','BOOM','MAIN_TACK','SPREADER','WINCH')):continue
 p=Vector(coords)
 curve=[tuple(p+Vector((.7*math.cos(j*2*math.pi/32),0,.7*math.sin(j*2*math.pi/32)))) for j in range(33)]
 eye=curved_tube('EYELET_'+label,curve,r=.15,trim=.05)
 col.objects.unlink(eye);ref.objects.link(eye)
 cyl('Eyelet stem',p-Vector((0,0,2.8)),p-Vector((0,0,.6)),.15,silver,collection=ref)
# Replace the legacy floating rig lines with point-to-point assembly references.
for ob in list(ref.objects):
 if ob.name.startswith('FIL'):bpy.data.objects.remove(ob,do_unlink=True)
def route(label,names):
 coords=[rig_points[n] for n in names]
 for a,b in zip(coords,coords[1:]):cyl('THREAD_'+label,a,b,.08,dark,collection=ref)
 rig_routes.append({'name':label,'points':names,'cut_length_mm':math.ceil(sum((Vector(b)-Vector(a)).length for a,b in zip(coords,coords[1:]))+40)})
route('FORESTAY',['FORESTAY','MASTHEAD_FORWARD'])
for label in ('PORT','STARBOARD'):
 route('BACKSTAY_'+label,['BACKSTAY_'+label,'MASTHEAD_AFT'])
 route('CAP_SHROUD_'+label,['CAP_SHROUD_'+label,'SPREADER_'+label,'MASTHEAD_AFT'])
 for role in ('LOWER_FORWARD','LOWER_AFT'):route(role+'_'+label,[role+'_'+label,'LOWER_SHROUDS'])
route('MAINSHEET',['BOOM_SHEET','MAINSHEET_CAR','BOOM_SHEET','MAINSHEET_CAR'])
route('VANG',['BOOM_VANG','VANG_DECK_PORT'])
# A representative eyelet coupon: reopen pilot holes with a hand pin vice after printing.
coupon=box('TEST_RIGGING_EYES',(60,65,2),(22,10,4),cream)
for x,diam in [(53,.7),(60,.8),(67,.9)]:cut_hole(coupon,(x,65,1),(x,65,5),diam/2)
register(coupon,test=True)
sc['rigging_json']=json.dumps({'scale':30,'points_mm':rig_points,'routes':rig_routes,'wire_diameter_mm':.3,'thread_diameter_mm':[.15,.25]})
(R/'rigging.json').write_text(sc['rigging_json'])
# Only actual remaining interfaces have specimens; no hull cut or alignment dowel.
cp=box('ESSAI_TIGE_MAT',(15,60,3),(30,14,6),cream)
for x,d in [(6,2.2),(15,2.3),(24,2.4)]:cut_hole(cp,(x,60,-1),(x,60,7),d/2)
boolean(cp,box('Encoche de repérage',(0,53,3),(4,4,8)))
register(cp,test=True)
for name,bounds in [('ESSAI_DESCENTE',[(191,201),(-12,12),(18,42)]),('ESSAI_PIED_MAT',[(99,113),(-6,6),(19,42)])]:
 piece=dup(hull,name)
 for axis,(lo,hi) in enumerate(bounds):clip(piece,axis,lo,True);clip(piece,axis,hi,False)
 register(piece,test=True)
# Stand made from two hull-subtracted cradles; bottom at -54 mm; hull intersection includes clearance.
for i,x in enumerate((80,210)):
 foot=box(f'BER_{i+1}',(x,0,-29),(8,86,50),wood)
 cutter=obj('Empreinte',source['Coque et cockpit creusé • V05'].copy())
 for v in cutter.data.vertices:v.co.y*=1.008;v.co.z-=.3
 boolean(foot,cutter)
 # Cut space below side hull leaving supportive V profile; add keel support kept in remaining mesh.
 register(foot,Matrix.Rotation(math.pi/2,4,'Y'))
# Owner-authorized horizontal separation, after all original interfaces are generated.
# Z=17 is 1.6 mm below the lowest hull/deck colour boundary (about 18.6 mm).
CUT_Z=17.0
parts=[(o,rot) for o,rot in parts if o!=hull]
lower=dup(hull,'COQUE_BASSE')
upper=dup(hull,'PONT_SUPERIEUR')
boolean(lower,box('Demi-espace inférieur',(139,0,CUT_Z-250),(800,800,500),cream),'INTERSECT')
boolean(upper,box('Demi-espace supérieur',(139,0,CUT_Z+250),(800,800,500),cream),'INTERSECT')
pin_centres=[(60,0),(125,-30),(125,30),(242,-23),(242,23)]
for i,(x,y) in enumerate(pin_centres,1):
 cut_hole(lower,(x,y,CUT_Z-3.2),(x,y,CUT_Z+.5),1.625)
 cut_hole(upper,(x,y,CUT_Z-.5),(x,y,CUT_Z+3.2),1.625)
 pin=cyl(f'PION_COLLAGE_{i:02d}',(x,y,CUT_Z-3),(x,y,CUT_Z+3),1.5,cream,n=48)
 register(pin)
bpy.data.objects.remove(hull,do_unlink=True)
hull=upper
register(lower,Matrix.Rotation(math.pi/4,4,'Z')@Matrix.Rotation(math.pi,4,'X'))
register(upper,Matrix.Rotation(math.pi/4,4,'Z'))
# Fit coupon: three blind holes at the actual depth, with 3.15 / 3.25 / 3.35 mm diameters.
fit=box('ESSAI_COLLAGE',(15,80,2.3),(30,12,4.6),cream)
for x,d in [(6,3.15),(15,3.25),(24,3.35)]:cut_hole(fit,(x,80,1.4),(x,80,5.2),d/2)
boolean(fit,box('Encoche repère',(0,74,2.3),(4,4,8)))
register(fit,test=True)
(R/'assemblage_pont_coque.json').write_text(json.dumps({'cut_Z_mm':CUT_Z,'scale':'1:30','pins_xy_mm':pin_centres,'pin_diameter_mm':3.0,'hole_diameter_mm':3.25,'pin_length_mm':6.0,'depth_each_side_mm':3.2,'external_gap_designed_mm':0.0,'finish':'Araser les bavures; présenter à blanc, coller, mastiquer légèrement le joint, poncer puis peindre. Invisible après finition, pas garanti à brut.'},ensure_ascii=False,indent=2))
# Seven intended shades, real filament assignment handled by native Bambu paint annotations.
palette=[('IVOIRE','#E6DFC0'),('BORDEAUX','#6C2037'),('CARENE_BLEU_VERT','#355C66'),('BOIS_ACAJOU','#8C4825'),('INOX_ALUMINIUM','#B8BEC4'),('VITRAGES_FUMES','#263B48'),('LIGNE_FLOTTAISON','#79918B')]
def srgb_linear(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
printmats=[]
for label,h in palette:
 rgb=[int(h[i:i+2],16)/255 for i in (1,3,5)]
 printmats.append(mat('PLA — '+label,tuple(srgb_linear(v) for v in rgb)))
def choose_color(ob,face,oldname):
 c=face.center;name=ob.name
 if name.startswith(('WINDOW_','WINCH_')):return 6
 if name.startswith(('WOOD_','BARRE_FRANCHE_BOIS')):return 4
 if name.startswith('TEST_'):return 1
 if name.startswith(('COMPANIONWAY_CHANNEL_','HATCH_RAIL_','MAST_DECK_SHOE','GENOA_TRACK_','MAINSHEET_TRAVELLER')):return 5
 if name.startswith('ESSAI') or name.startswith('PION'):return 1
 if name.startswith('BER'):return 4
 if name=='PONT_SUPERIEUR' and 'aluminium' in oldname:return 1
 if name=='COQUE_BASSE':
  if 'ivoire' in oldname:return 1
  # Interior cut faces/holes carry no unnecessary extra colors.
  return 2 if c.z>.833333 else (7 if c.z>-.833333 else 3)
 if name=='SAFRAN':
  if 'aluminium' in oldname and c.z>20:return 5
  return 2 if c.z>.833333 else (7 if c.z>-.833333 else 3)
 if 'acajou' in oldname:return 4
 if 'aluminium' in oldname:return 5
 if 'hublot' in oldname.lower() or 'vitrage' in oldname.lower():return 6
 if 'Bordeaux' in oldname:return 2
 if 'Flottaison' in oldname:return 7
 if 'Carène' in oldname or 'sous-marine' in oldname:return 3
 return 1
for ob,_ in parts+tests:
 ob.data.update();old=list(ob.data.materials);ids=[choose_color(ob,f,old[f.material_index].name) for f in ob.data.polygons]
 ob.data.materials.clear()
 for m in printmats:ob.data.materials.append(m)
 for f,i in zip(ob.data.polygons,ids):f.material_index=i-1
(R/'palette.json').write_text(json.dumps([{'id':i+1,'name':x[0],'hex':x[1],'material':'PLA','commercial_reference':'a choisir apres validation'} for i,x in enumerate(palette)],ensure_ascii=False,indent=2))
# All user-visible names are English.
translations={'COQUE_BASSE': 'LOWER_HULL', 'PONT_SUPERIEUR': 'UPPER_DECK', 'SAFRAN': 'RUDDER', 'BARRE_FRANCHE_BOIS': 'WOOD_TILLER', 'COURONNEMENT_BOIS_BABORD': 'WOOD_COAMING_CAP_PORT', 'COURONNEMENT_BOIS_TRIBORD': 'WOOD_COAMING_CAP_STARBOARD', 'ENCADREMENT_BOIS_COCKPIT': 'WOOD_COCKPIT_TRIM', 'MAIN_COURANTE_BOIS_BABORD': 'WOOD_HANDRAIL_PORT', 'MAIN_COURANTE_BOIS_TRIBORD': 'WOOD_HANDRAIL_STARBOARD', 'PLANCHE_BASSE': 'LOWER_WASHBOARD', 'PLANCHE_HAUTE': 'UPPER_WASHBOARD', 'TRAVERSE_BOIS_ARRIERE': 'WOOD_AFT_CROSSPIECE', 'BER_1': 'DISPLAY_CRADLE_1', 'BER_2': 'DISPLAY_CRADLE_2', 'BOME': 'BOOM', 'CAPOT_COULISSANT': 'SLIDING_HATCH', 'COLLIER_BARRES_FLECHE': 'SPREADER_COLLAR', 'MAT_1': 'MAST_1', 'MAT_2': 'MAST_2', 'MAT_3': 'MAST_3', 'SUPPORT_BOME': 'BOOM_SADDLE', 'ESSAI_COLLAGE': 'TEST_HULL_JOINT', 'ESSAI_DESCENTE': 'TEST_COMPANIONWAY', 'ESSAI_PIED_MAT': 'TEST_MAST_STEP', 'ESSAI_TIGE_MAT': 'TEST_MAST_ROD', 'BALCON_AVANT_INOX': 'BOW_PULPIT', 'BALCON_ARRIERE_INOX': 'STERN_PUSHPIT', 'BALCON_PROTECTION_SAFRAN_INOX': 'LOWER_RUDDER_GUARD', 'PION_COLLAGE_01': 'ALIGNMENT_PIN_01', 'PION_COLLAGE_02': 'ALIGNMENT_PIN_02', 'PION_COLLAGE_03': 'ALIGNMENT_PIN_03', 'PION_COLLAGE_04': 'ALIGNMENT_PIN_04', 'PION_COLLAGE_05': 'ALIGNMENT_PIN_05'}
for ob,_ in parts+tests:ob.name=translations.get(ob.name,ob.name);ob.data.name=ob.name+' mesh'
sc.name='Laurine — V1 hybrid display model 1:30'
col.name='01 — Printable parts';ref.name='02 — Metal rods and rigging thread — DO NOT PRINT';proto.name='03 — Fit tests'
english_palette=['IVORY','BURGUNDY','DARK_TEAL','MAHOGANY_BROWN','SILVER_GREY','SMOKED_GLAZING','WATERLINE_GREY_GREEN']
for m,n in zip(printmats,english_palette):m.name='PLA — '+n
for i,ob in enumerate(ref.objects):
 ob.name='REFERENCE — '+('BACKSTAY_PORT' if 'PATARAS_BABORD' in ob.name else 'BACKSTAY_STARBOARD' if 'PATARAS_TRIBORD' in ob.name else 'RIGGING_'+str(i+1).zfill(2));ob.data.name=ob.name+' mesh'
(R/'palette.json').write_text(json.dumps([{'id':i+1,'name':english_palette[i],'hex':x[1],'material':'PLA','commercial_reference':'To be selected'} for i,x in enumerate(palette)],indent=2))
# manifest & STL: each export placed on Z=0, in millimetres, triangulated.
def audit(o):
 bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for f in list(bm.faces):
  if f.is_valid and f.calc_area()<1e-9 and min(e.calc_length() for e in f.edges)<.01:bmesh.ops.collapse(bm,edges=[min(f.edges,key=lambda e:e.calc_length())])
 if o.name=='RUDDER':
  bmesh.ops.remove_doubles(bm,verts=[v for v in bm.verts if v.co.z>20],dist=.003)
  bmesh.ops.dissolve_degenerate(bm,edges=[e for e in bm.edges if all(v.co.z>20 for v in e.verts)],dist=.003)
 bad=sum(not e.is_manifold for e in bm.edges);deg=sum(f.calc_area()<1e-9 for f in bm.faces)
 # Components count using vertices/edges, to catch floating union fragments.
 unseen=set(bm.verts);cc=[]
 while unseen:
  todo=[unseen.pop()];n=0
  while todo:
   v=todo.pop();n+=1
   for e in v.link_edges:
    w=e.other_vert(v)
    if w in unseen:unseen.remove(w);todo.append(w)
  cc.append(n)
 vol=bm.calc_volume(signed=True);bm.to_mesh(o.data);bm.free()
 return {'non_manifold_edges':bad,'degenerate_triangles':deg,'connected_components':len(cc),'component_vertex_counts':sorted(cc,reverse=True),'volume_mm3':round(vol,3)}
def export(o,rot,directory):
 au=audit(o);pts=[rot@v.co for v in o.data.vertices];mins=Vector(tuple(min(p[i] for p in pts) for i in range(3)));maxs=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
 p=directory/(o.name+'.stl');o.data.calc_loop_triangles()
 with p.open('wb') as f:
  f.write(b'Laurine L28 V1 - millimetres'.ljust(80,b'\0'));f.write(struct.pack('<I',len(o.data.loop_triangles)))
  for t in o.data.loop_triangles:
   vs=[pts[i]-mins for i in t.vertices];normal=(vs[1]-vs[0]).cross(vs[2]-vs[0]).normalized();f.write(struct.pack('<12fH',*normal,*vs[0],*vs[1],*vs[2],0))
 data={'name':o.name,'vertices':[[round(float(c),7) for c in pt-mins] for pt in pts],'triangles':[list(t.vertices) for t in o.data.loop_triangles],'filaments':[o.data.polygons[t.polygon_index].material_index+1 for t in o.data.loop_triangles]}
 (R/'colors'/(o.name+'.json')).write_text(json.dumps(data,separators=(',',':')))
 rec={'piece':o.name,'file':str(p.relative_to(R)),'dimensions_print_mm':[round(v,3) for v in maxs-mins],'quantity':1,**au};records.append(rec);log(json.dumps(rec))
(R/'print_layout.json').write_text(json.dumps([{'name':o.name,'rotation':[list(row) for row in rot],'kind':kind} for group,kind in [(parts,'part'),(tests,'fit-test')] for o,rot in group],indent=2))
for o,rot in parts:export(o,rot,R/'stl')
for o,rot in tests:
 for c in list(o.users_collection):c.objects.unlink(o)
 proto.objects.link(o);export(o,rot,R/'tests');o.hide_set(True)
(R/'controle_impression.json').write_text(json.dumps({'scale':'1:30','source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'units':'mm','printer':'FDM, à confirmer','checks_scope':'Fermeture, composantes, triangles degeneres et volume. Pas une validation physique ni une analyse exhaustive des collisions ou epaisseurs.','pieces':records,'anchors':anchors},ensure_ascii=False,indent=2))
# Review the requested finishes on final faces, symmetrically.
def region_materials(xlo,xhi,ylo,yhi,zlo,zhi):
 result={}
 for p in hull.data.polygons:
  c=p.center
  if xlo<c.x<xhi and ylo<c.y<yhi and zlo<c.z<zhi:
   name=hull.data.materials[p.material_index].name;result[name]=result.get(name,0)+1
 return result
finish={}
for side in (-1,1):
 y0,y1=sorted([side*13.5,side*15.2])
 finish['main_courante_'+str(side)]=region_materials(115,166,y0,y1,39.6,41.3)
 y0,y1=sorted([side*7.3,side*10.3])
 finish['glissiere_descente_'+str(side)]=region_materials(194.3,198.1,y0,y1,22,38)
(R/'controle_finitions.json').write_text(json.dumps(finish,ensure_ascii=False,indent=2))
# Attractive assembled preview, workbench studio.
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.studiolight_rotate_z=.4;sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='BOTH';sc.display.shading.background_type='WORLD';sc.world.color=(.12,.12,.12)
sc.render.resolution_x=1500;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
camdata=bpy.data.cameras.new('Model review camera');camdata.type='ORTHO';cam=bpy.data.objects.new('Model review camera',camdata);sc.collection.objects.link(cam);sc.camera=cam
for o,rot in parts:
 if o.name=='PION_3x8':o.hide_render=True;o.hide_set(True)
def view(loc,target,scale,path):
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=scale
 sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
view((500,-700,420),(139,0,173),680,R/'previews/assembled_model.png')
view((430,-500,290),(139,0,0),345,R/'previews/hull_assembly.png')
view((190,-165,135),(259,0,34),125,R/'previews/cockpit.png')
view((240,-150,135),(150,0,38),135,R/'previews/deck_and_companionway.png')
view((325,-80,75),(278,0,36),45,R/'previews/tiller_fitting.png')
view((-95,-110,100),(24,0,43),105,R/'previews/bow_pulpit.png')
view((370,-140,85),(268,0,29),115,R/'previews/stern_pushpit.png')
view((100,0,58),(0,0,43),75,R/'previews/bow_pulpit_from_deck.png')
view((320,-190,78),(268,0,27),100,R/'previews/rudder_guard.png')
for ob in sc.objects:
 if ob.name.startswith('DISPLAY_CRADLE'):ob.hide_render=True
view((259,-220,-19),(249,0,-19),87,R/'previews/straight_rudder_edge.png')
for ob in sc.objects:
 if ob.name.startswith('DISPLAY_CRADLE'):ob.hide_render=False
# Exploded view of the two primary parts and hidden alignment pins only.
visibility={o:o.hide_render for o in list(sc.objects)}
for o in sc.objects:o.hide_render=o not in [lower,upper,cam] and not o.name.startswith('ALIGNMENT_PIN')
upper.location.z=35
for o in sc.objects:
 if o.name.startswith('ALIGNMENT_PIN'):o.location.z=12
view((420,-450,270),(139,0,28),345,R/'previews/exploded_hull_and_deck.png')
upper.location.z=0
for o in sc.objects:
 if o.name.startswith('ALIGNMENT_PIN'):o.location.z=0
for o,value in visibility.items():o.hide_render=value
cam.location=(500,-700,420);cam.rotation_euler=(Vector((139,0,173))-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=680
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   space=area.spaces.active;space.overlay.show_extras=False;space.clip_end=10000;space.region_3d.view_location=(139,0,150);space.region_3d.view_distance=580;space.region_3d.view_rotation=cam.rotation_euler.to_quaternion();space.region_3d.view_perspective='ORTHO'
sc['Status']='Hybrid prototype 1:30 — test fits and slicer verification required before printing'
sc['Do_not_print']='Collection 02: metal rods and rigging thread, assembly references only'
bpy.ops.object.select_all(action='DESELECT')
sc.render.filepath='//../docs/images/assembled_model.png'
bpy.context.preferences.filepaths.save_version=0
for text in list(bpy.data.texts):bpy.data.texts.remove(text)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Laurine_L28.blend'),compress=True)
log('COMPLETE')
