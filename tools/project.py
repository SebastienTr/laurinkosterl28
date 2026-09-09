"""Prepare, review and promote one coherent model delivery through a single entry point."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import delivery

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build'


def run(args):
    subprocess.run(args, check=True, cwd=ROOT)


def blender(script):
    executable = os.environ.get('BLENDER_BIN', '/Applications/Blender.app/Contents/MacOS/Blender')
    run([executable, '--background', '--python-exit-code', '1', '--python', str(ROOT / 'tools' / script)])


def bundle():
    files = [BUILD / name for name in ['Laurine_L28.blend', 'print_layout.json', 'palette.json', 'model_check.json',
             'project_check.json', 'plate_manifest.json', 'bambu/Laurine_Multicolor_A1.3mf', 'bambu/result.json', 'rigging.json']]
    files += [p for d in ['stl', 'tests', 'colors', 'previews', 'sails'] for p in (BUILD / d).rglob('*') if p.is_file()]
    return {str(p.relative_to(BUILD)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def prepare(from_source=False):
    before = delivery.hashes()
    # Only disposable outputs live here. Private references are never cleaned.
    if BUILD.exists():
        shutil.rmtree(BUILD)
    for name in ['stl', 'tests', 'colors', 'previews', 'bambu']:
        (BUILD / name).mkdir(parents=True, exist_ok=True)
    if from_source:
        blender('build_model.py')
        blender('finish_model.py')
    else:
        shutil.copy2(ROOT / 'model/Laurine_L28.blend', BUILD / 'Laurine_L28.blend')
        for name in ['print_layout.json', 'palette.json']:
            shutil.copy2(ROOT / 'source' / name, BUILD / name)
    blender('export_final.py')
    blender('render_previews.py')
    run([sys.executable, str(ROOT / 'tools/sail_patterns.py')])
    assembly = json.loads((ROOT / 'source/assembly.json').read_text())
    for plate in assembly['plates']:
        for obj in plate['objects']:
            source = Path(obj['path'])
            target = BUILD / ('tests' if source.parent.name == 'fit-tests' else 'stl') / source.name
            if not target.is_file():
                raise FileNotFoundError(target)
            obj['path'] = str(target)
    (BUILD / 'bambu/assembly.json').write_text(json.dumps(assembly, indent=2))
    run([sys.executable, str(ROOT / 'tools/package_project.py')])
    run([sys.executable, str(ROOT / 'tools/verify_project.py')])
    if delivery.hashes() != before:
        raise ValueError('Inputs changed during preparation; run prepare again')
    (BUILD / 'candidate.json').write_text(json.dumps({'baseline': before, 'bundle': bundle()}, indent=2))
    print('Candidate checked. Review build/previews and all plates before running promote.')


def promote():
    candidate = json.loads((BUILD / 'candidate.json').read_text())
    if candidate['baseline'] != delivery.hashes() or candidate['bundle'] != bundle():
        raise ValueError('Files changed since preparation; prepare and review again')
    # Replace complete directories so deleted parts cannot survive as stale exports.
    for source, target in [('stl', 'print/stl'), ('tests', 'print/fit-tests'), ('colors', 'source/colors'), ('previews', 'docs/images'), ('sails', 'docs/sails')]:
        if (ROOT / target).exists():
            shutil.rmtree(ROOT / target)
        shutil.copytree(BUILD / source, ROOT / target)
    for source, target in [('Laurine_L28.blend', 'model/Laurine_L28.blend'), ('bambu/Laurine_Multicolor_A1.3mf', 'print/Laurine_Multicolor_A1.3mf'),
                           ('print_layout.json', 'source/print_layout.json'), ('palette.json', 'source/palette.json'), ('plate_manifest.json', 'source/plate_manifest.json'), ('rigging.json', 'source/rigging.json')]:
        shutil.copy2(BUILD / source, ROOT / target)
    # Reports describe this delivery only, not previous generations.
    for path in (ROOT / 'reports').glob('*.json'):
        path.unlink()
    for name in ['model_check.json', 'project_check.json']:
        shutil.copy2(BUILD / name, ROOT / 'reports' / name)
    result = json.loads((BUILD / 'bambu/result.json').read_text())
    usage = {}
    for plate in result['sliced_plates']:
        for filament in plate['filaments']:
            key = str(filament['id'])
            usage[key] = usage.get(key, 0) + filament['total_used_g']
    (ROOT / 'reports/filament_usage.json').write_text(json.dumps({'estimated_PLA_g_by_project_colour': usage}, indent=2) + '\n')
    delivery.write_receipt()
    delivery.verify()
    shutil.rmtree(BUILD)
    print('Coherent delivery promoted; temporary build files removed. Review the diff, stage and commit.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'promote', 'check', 'install-hook', 'clean'])
    parser.add_argument('--from-source', action='store_true', help='Regenerate the model from base geometry; otherwise use the edited final Blender file')
    parser.add_argument('--staged', action='store_true', help='Check the exact files staged for commit')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.from_source)
    elif args.command == 'promote':
        promote()
    elif args.command == 'check':
        delivery.verify(staged=args.staged)
        print('Delivery coherent.')
    elif args.command == 'install-hook':
        run(['git', 'config', '--local', 'core.hooksPath', '.githooks'])
        print('Repository pre-commit hook enabled.')
    elif BUILD.exists():
        shutil.rmtree(BUILD)


if __name__ == '__main__':
    main()
