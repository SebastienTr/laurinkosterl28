from pathlib import Path
import json,subprocess,zipfile,sys,os
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'build';app=os.environ.get('BAMBUSTUDIO_BIN','/Applications/BambuStudio.app/Contents/MacOS/BambuStudio')
def run(args,log):
 with (R/'bambu'/log).open('w') as f:p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError((R/'bambu'/log).read_text()[-4000:])
run([app,'--debug','2','--load-settings',str(ROOT/'profiles/machine_A1.json')+';'+str(ROOT/'profiles/process_multi.json'),'--load-filaments',';'.join(str(ROOT/'profiles'/f'PLA_{i}.json') for i in range(1,8)),'--load-assemble-list',str(R/'bambu/assembly.json'),'--allow-multicolor-oneplate','--orient','0','--outputdir',str(R/'bambu'),'--export-3mf','base.3mf'],'assembly.log')
print('Base assembled',flush=True)
subprocess.run([sys.executable,str(ROOT/'tools/paint_project.py')],check=True)
subprocess.run([sys.executable,str(ROOT/'tools/arrange_project.py')],check=True)
with zipfile.ZipFile(R/'bambu/arranged.3mf') as zi:
 d=json.loads(zi.read('Metadata/project_settings.config'));d.update(json.loads((ROOT/'profiles/machine_resolved.json').read_text()));d['printer_settings_id']='Bambu Lab A1 0.4 nozzle'
 pal=json.loads((R/'palette.json').read_text());d['filament_settings_id']=['Laurine - '+p['name'] for p in pal]
 with zipfile.ZipFile(R/'bambu/slice_input.3mf','w',zipfile.ZIP_DEFLATED) as zo:
  for n in zi.namelist():zo.writestr(n,json.dumps(d).encode() if n=='Metadata/project_settings.config' else zi.read(n))
print('Slicing all plates',flush=True)
run([app,'--debug','2','--arrange','0','--orient','0','--slice','0','--outputdir',str(R/'bambu'),'--export-3mf','Laurine_Multicolor_A1.3mf',str(R/'bambu/slice_input.3mf')],'slicing.log')
print('Slicing complete',flush=True)
