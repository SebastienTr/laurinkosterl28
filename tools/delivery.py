"""Check the exact delivered file set, including the Git index before a commit."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'reports/delivery.json'
WATCHED = ('source/', 'model/', 'print/', 'profiles/', 'tools/', 'reports/', 'docs/images/', '.githooks/', '.github/')
ROOT_FILES = {'README.md', 'AGENTS.md', 'VERSION', '.gitignore', '.gitattributes', 'LICENSE', 'CHANGELOG.md'}
DIRECTORIES = {'source', 'model', 'print', 'profiles', 'tools', 'reports', 'docs', '.githooks', '.github'}


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root)


def paths(root=ROOT, staged=False):
    tracked = git(root, 'ls-files', '-z').decode().split('\0')
    other = [] if staged else git(root, 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')
    return sorted(set(p for p in tracked + other if p and (staged or (root / p).is_file() or (root / p).is_symlink())))


def read(root, path, staged=False):
    if staged:
        return git(root, 'show', ':' + path)
    return (root / path).read_bytes()


def watched(path):
    return path != RECEIPT and (path.startswith(WATCHED) or path in {'VERSION', 'AGENTS.md'})


def hashes(root=ROOT, staged=False):
    return {p: hashlib.sha256(read(root, p, staged)).hexdigest() for p in paths(root, staged) if watched(p)}


def check_public_paths(root, staged=False):
    for path in paths(root, staged):
        p = Path(path)
        if len(p.parts) == 1:
            if path not in ROOT_FILES:
                raise ValueError(f'Unexpected file at repository root: {path}')
        elif p.parts[0] not in DIRECTORIES:
            raise ValueError(f'Private, temporary or unexpected directory staged: {path}')
        if p.suffix.lower() in {'.tmp', '.log', '.bak', '.zip', '.mp4', '.jpeg', '.jpg', '.pdf', '.pyc'} or re.search(r'\.blend\d+$', p.name) or p.name.startswith('.env') or '__pycache__' in p.parts:
            raise ValueError(f'Temporary or reference file in the public tree: {path}')
        if p.suffix == '.png' and not path.startswith('docs/images/'):
            raise ValueError(f'Public renders belong in docs/images/: {path}')
        if not staged and (root / path).is_symlink():
            raise ValueError(f'Symlinks are not allowed in deliverables: {path}')
    for entry in git(root, 'ls-files', '-s').decode().splitlines():
        if entry.startswith('120000 '):
            raise ValueError('A symlink is staged; replace it with reviewed public content')


def verify(root=ROOT, staged=False):
    check_public_paths(root, staged)
    try:
        receipt = json.loads(read(root, RECEIPT, staged))
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise ValueError('Missing delivery receipt. Run prepare, review, then promote.') from error
    if receipt.get('schema') != 1:
        raise ValueError('Unsupported delivery receipt')
    current = hashes(root, staged)
    expected = receipt['sha256']
    changed = sorted(p for p in current.keys() | expected.keys() if current.get(p) != expected.get(p))
    if changed:
        raise ValueError('Stale delivery; rebuild and promote the complete set:\n' + '\n'.join(changed))
    required = {'model/Laurine_L28.blend', 'print/Laurine_Multicolor_A1.3mf', 'source/print_layout.json', 'reports/model_check.json', 'reports/project_check.json'}
    if not required <= current.keys():
        raise ValueError('Required model, print project or checks are missing')
    project = json.loads(read(root, 'reports/project_check.json', staged))
    if not all(project.get(key) for key in ['geometry_and_colours_match', 'gcode_checksums_valid', 'slicing_successful']):
        raise ValueError('The delivered project has not passed its detailed checks')
    return current


def write_receipt(root=ROOT):
    receipt = {'schema': 1, 'version': (root / 'VERSION').read_text().strip(),
               'scope': 'Final Blender model, exports, colours, slicing inputs, checks and previews. Physical fit still requires a test print.',
               'sha256': hashes(root)}
    (root / RECEIPT).write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged', action='store_true', help='Check index contents, not working copies')
    args = parser.parse_args()
    try:
        files = verify(staged=args.staged)
    except (ValueError, KeyError, FileNotFoundError) as error:
        parser.exit(1, f'Delivery check failed: {error}\n')
    print(f'Delivery coherent: {len(files)} protected files verified.')


if __name__ == '__main__':
    main()
