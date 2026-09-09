from pathlib import Path
import json,zipfile,xml.etree.ElementTree as E,numpy as np
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'build';N='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';P='http://schemas.microsoft.com/3dmanufacturing/production/2015/06';q=lambda n:'{'+N+'}'+n
E.register_namespace('',N);E.register_namespace('p',P);E.register_namespace('BambuStudio','http://schemas.bambulab.com/package/2021')
codes=['','4','8','0C','1C','2C','3C','4C'];patches={};cache={};audit=[]
with zipfile.ZipFile(R/'bambu/base.3mf') as zi:
 cfg=E.fromstring(zi.read('Metadata/model_settings.config'));names={o.get('id'):o.find("metadata[@key='name']").get('value') for o in cfg.findall('object')}
 main=E.fromstring(zi.read('3D/3dmodel.model'))
 for ob in main.find(q('resources')).findall(q('object')):
  name=names[ob.get('id')]
  if not (R/'colors'/(name+'.json')).exists():name=name.removesuffix('_1')
  if name not in cache:
   d=json.loads((R/'colors'/(name+'.json')).read_text());v=np.array(d['vertices']);t=np.array(d['triangles']);centers=v[t].mean(axis=1);cache[name]=(d,centers,cKDTree(centers))
  d,centers,tree=cache[name]
  for comp in ob.find(q('components')):
   path=comp.get('{'+P+'}path').lstrip('/');root=patches.get(path)
   if root is None:root=E.fromstring(zi.read(path));patches[path]=root
   child=root.find(q('resources')).find(q('object')+"[@id='"+comp.get('objectid')+"']");me=child.find(q('mesh'));v=np.array([[float(e.get(c)) for c in ['x','y','z']] for e in me.find(q('vertices'))]);ts=list(me.find(q('triangles')));t=np.array([[int(e.get(c)) for c in ['v1','v2','v3']] for e in ts]);tr=np.array([float(x) for x in comp.get('transform').split()]);v=v@tr[:9].reshape(3,3)+tr[9:];c=v[t].mean(axis=1)
   ds,inds=tree.query(c);assert max(ds)<.00008,(name,max(ds));assert len(ts)==len(d['triangles']),(name,len(ts),len(d['triangles']))
   # Triangles were exported in the same order: retain exact source assignments, including tiny border facets.
   direct_error=float(np.max(np.linalg.norm(c-centers,axis=1)))
   if direct_error<.00008:inds=np.arange(len(ts))
   for tri,ind in zip(ts,inds):tri.set('paint_color',codes[d['filaments'][int(ind)]])
   audit.append({'name':name,'triangles':len(ts),'max_mapping_distance_mm':float(max(ds)),'same_order':direct_error<.00008,'colors':sorted(set(d['filaments']))})
 with zipfile.ZipFile(R/'bambu/painted.3mf','w',zipfile.ZIP_DEFLATED) as zo:
  for n in zi.namelist():zo.writestr(n,E.tostring(patches[n],encoding='utf-8',xml_declaration=True) if n in patches else zi.read(n))
(R/'color_mapping_check.json').write_text(json.dumps(audit,indent=2));print('Painted',len(audit),'objects; max discrepancy',max(x['max_mapping_distance_mm'] for x in audit),flush=True)
