"""Build into an ignored working folder; never overwrite reviewed deliverables."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build'
def run(args):
    subprocess.run(args,check=True,cwd=ROOT)
def prepare_package(from_exports):
    for name in ['stl','tests','colors','bambu','previews']:
        (BUILD/name).mkdir(parents=True,exist_ok=True)
    if from_exports:
        for a,b in [('print/stl','stl'),('print/fit-tests','tests'),('source/colors','colors')]:
            shutil.copytree(ROOT/a,BUILD/b,dirs_exist_ok=True)
        shutil.copy2(ROOT/'source/palette.json',BUILD/'palette.json')
    assembly=json.loads((ROOT/'source/assembly.json').read_text())
    for plate in assembly['plates']:
        for obj in plate['objects']:
            source=Path(obj['path'])
            target=BUILD/('tests' if source.parent.name=='fit-tests' else 'stl')/source.name
            if not target.is_file():raise FileNotFoundError(target)
            obj['path']=str(target)
    (BUILD/'bambu/assembly.json').write_text(json.dumps(assembly,indent=2))
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['geometry','package','all'])
    args=parser.parse_args()
    if args.command in ['geometry','all']:
        blender=os.environ.get('BLENDER_BIN','/Applications/Blender.app/Contents/MacOS/Blender')
        for script in ['build_model.py','finish_model.py']:
            run([blender,'--background','--python-exit-code','1','--python',str(ROOT/'tools'/script)])
    if args.command in ['package','all']:
        prepare_package(from_exports=args.command=='package')
        run([sys.executable,str(ROOT/'tools/package_project.py')])
if __name__=='__main__':main()
