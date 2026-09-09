from pathlib import Path
import zipfile,xml.etree.ElementTree as E,json,numpy as np
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'build';N='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';P='http://schemas.microsoft.com/3dmanufacturing/production/2015/06';q=lambda x:'{'+N+'}'+x
E.register_namespace('',N);E.register_namespace('p',P);E.register_namespace('BambuStudio','http://schemas.bambulab.com/package/2021')
with zipfile.ZipFile(R/'bambu/painted.3mf') as zi:
 cfg=E.fromstring(zi.read('Metadata/model_settings.config'));main=E.fromstring(zi.read('3D/3dmodel.model'));settings=json.loads(zi.read('Metadata/project_settings.config'));build={i.get('objectid'):i for i in main.find(q('build'))};objects={o.get('id'):o for o in main.find(q('resources'))};bounds=[]
 for n,plate in enumerate(cfg.findall('plate')):
  pts=[];origin=np.array([(n%4)*307.2,-(n//4)*307.2,0])
  for inst in plate.findall('model_instance'):
   oid=inst.find("metadata[@key='object_id']").get('value');item=build[oid];tr=np.array(list(map(float,item.get('transform').split())));tr[9]+=20
   if n==4:
    # Rotate the packed spars together, preserving their clearances after auto-arrange.
    a=np.pi/4;rotation=np.array([[np.cos(a),np.sin(a),0],[-np.sin(a),np.cos(a),0],[0,0,1]])
    pivot=origin+np.array([148,128,0]);tr[:9]=(tr[:9].reshape(3,3)@rotation).reshape(9);tr[9:]=(tr[9:]-pivot)@rotation+pivot
   item.set('transform',' '.join(f'{v:.10g}' for v in tr))
   for comp in objects[oid].find(q('components')):
    path=comp.get('{'+P+'}path').lstrip('/');m=E.fromstring(zi.read(path));me=m.find(q('resources')).find(q('object')+"[@id='"+comp.get('objectid')+"']").find(q('mesh'));v=np.array([[float(e.get(c)) for c in ['x','y','z']] for e in me.find(q('vertices'))]);ct=np.array(list(map(float,comp.get('transform').split())));v=(v@ct[:9].reshape(3,3)+ct[9:])@tr[:9].reshape(3,3)+tr[9:]-origin;pts.append(v)
  v=np.concatenate(pts);mi=v.min(axis=0);ma=v.max(axis=0);assert mi[0]>45 and ma[0]<250,(n,mi,ma);assert mi[1]>5 and ma[1]<250,(n,mi,ma);bounds.append({'plate':n+1,'min_mm':mi.tolist(),'max_mm':ma.tolist(),'tower_reserved_xy_mm':[7,97,43,190]})
 settings['wipe_tower_x']=['10']*len(cfg.findall('plate'));settings['wipe_tower_y']=['100']*len(cfg.findall('plate'));settings['wipe_tower_rotation_angle']='0'
 with zipfile.ZipFile(R/'bambu/arranged.3mf','w',zipfile.ZIP_DEFLATED) as zo:
  for n in zi.namelist():
   b=zi.read(n)
   if n=='3D/3dmodel.model':b=E.tostring(main,encoding='utf-8',xml_declaration=True)
   if n=='Metadata/project_settings.config':b=json.dumps(settings).encode()
   zo.writestr(n,b)
 (R/'plate_placement_check.json').write_text(json.dumps(bounds,indent=2));print(bounds)
