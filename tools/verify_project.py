"""Compare the sliced 3MF with the final model's STL geometry and face colours."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'build'
N = '{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
P = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
CODES = ['', '4', '8', '0C', '1C', '2C', '3C', '4C']
TOLERANCE = 0.0001  # Millimetres: accommodates STL and 3MF floating-point rounding.

def require(condition, message):
    if not condition:
        raise ValueError(message)

def metadata(element, key):
    return element.find(f"metadata[@key='{key}']").get('value')

def verify(work=WORK):
    layout = json.loads((work / 'print_layout.json').read_text())
    names = {item['name'] for item in layout}
    require(len(names) == len(layout), 'Duplicate layout entry')
    require({p.stem for p in (work / 'colors').glob('*.json')} == names, 'Colour file inventory differs')
    require({p.stem for d in ['stl', 'tests'] for p in (work / d).glob('*.stl')} == names, 'STL inventory differs')
    cache = {}
    for item in layout:
        name = item['name']
        data = json.loads((work / 'colors' / f'{name}.json').read_text())
        points = np.array(data['vertices'])[np.array(data['triangles'])]
        path = work / ('tests' if item['kind'] == 'fit-test' else 'stl') / f'{name}.stl'
        raw = path.read_bytes()
        count = struct.unpack_from('<I', raw, 80)[0]
        require(len(raw) == 84 + count * 50 and count == len(points), f'STL triangle count: {name}')
        stl = np.ndarray((count,), dtype=np.dtype([('normal', '<f4', 3), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')]), buffer=raw, offset=84)
        require(np.max(np.abs(stl['vertices'] - points)) < TOLERANCE, f'STL differs from final-model export: {name}')
        cache[name] = (points, data['filaments'])
    assembly = json.loads((ROOT / 'source/assembly.json').read_text())['plates']
    palette = json.loads((work / 'palette.json').read_text())
    summary = []
    with zipfile.ZipFile(work / 'bambu/Laurine_Multicolor_A1.3mf') as archive:
        require(archive.testzip() is None, 'Corrupt 3MF archive')
        for name in archive.namelist():
            if name.endswith(('.config', '.model', '.xml', '.json', '.gcode')):
                content = archive.read(name)
                require(b'/Users/' not in content and b'/home/' not in content, f'Local path in 3MF: {name}')
        config = ET.fromstring(archive.read('Metadata/model_settings.config'))
        main = ET.fromstring(archive.read('3D/3dmodel.model'))
        object_names = {o.get('id'): metadata(o, 'name') for o in config.findall('object')}
        checked_names = {}
        for obj in main.find(N + 'resources').findall(N + 'object'):
            label = object_names[obj.get('id')]
            name = label if label in cache else label.removesuffix('_1')
            require(name in cache, f'Unexpected 3MF object: {label}')
            components = list(obj.find(N + 'components'))
            require(len(components) == 1, f'Unsupported component layout: {name}')
            component = components[0]
            model = ET.fromstring(archive.read(component.get(P + 'path').lstrip('/')))
            mesh = model.find(N + 'resources').find(N + f"object[@id='{component.get('objectid')}']").find(N + 'mesh')
            vertices = np.array([[float(v.get(c)) for c in ['x', 'y', 'z']] for v in mesh.find(N + 'vertices')])
            transform = np.array(list(map(float, component.get('transform').split())))
            vertices = vertices @ transform[:9].reshape(3, 3) + transform[9:]
            # Bambu centres local meshes when saving the sliced project.
            vertices -= vertices.min(axis=0)
            faces = list(mesh.find(N + 'triangles'))
            indices = np.array([[int(t.get(c)) for c in ['v1', 'v2', 'v3']] for t in faces])
            expected, colours = cache[name]
            require(vertices[indices].shape == expected.shape, f'3MF triangle count differs: {name}')
            require(np.max(np.abs(vertices[indices] - expected)) < TOLERANCE, f'3MF geometry differs: {name}')
            require([t.get('paint_color') for t in faces] == [CODES[i] for i in colours], f'3MF face colours differ: {name}')
            checked_names[obj.get('id')] = name
        plates = config.findall('plate')
        require(len(plates) == len(assembly), 'Plate count differs')
        result = json.loads((work / 'bambu/result.json').read_text())
        require(result['return_code'] == 0, 'Slicing failed')
        require(len(result['sliced_plates']) == len(assembly), 'Incomplete slicing')
        for i, (plate, expected, sliced) in enumerate(zip(plates, assembly, result['sliced_plates']), 1):
            present = Counter(checked_names[metadata(o, 'object_id')] for o in plate.findall('model_instance'))
            wanted = Counter()
            for part in expected['objects']:
                wanted[Path(part['path']).stem] += part['count']
            require(present == wanted, f'Plate {i} has missing or extra parts')
            gcode = metadata(plate, 'gcode_file')
            require(archive.read(gcode + '.md5').decode().strip().lower() == hashlib.md5(archive.read(gcode)).hexdigest(), f'Plate {i} G-code checksum differs')
            require(not sliced.get('warning') and not sliced.get('warnings') and not sliced.get('warning_message'), f'Plate {i} has slicing warnings')
            expected_colours = {colour for name in wanted for colour in cache[name][1]}
            require({f['id'] for f in sliced['filaments']} == expected_colours, f'Plate {i} sliced colours differ')
            require(len(sliced['filaments']) <= 4, f'Plate {i} requires more than four filaments')
            summary.append({'plate': expected['plate_name'], 'instances': sum(present.values()), 'seconds': sliced['total_predication'],
                            'filaments': sliced['filaments'], 'parts': list(wanted.elements()), 'colours': sorted(expected_colours)})
        settings = json.loads(archive.read('Metadata/project_settings.config'))
        require([s.upper().lstrip('#') for s in settings['filament_colour']] == [p['hex'].upper().lstrip('#') for p in palette], 'Project palette differs')
    report = {'parts': len(names), 'plates': len(summary), 'instances': sum(x['instances'] for x in summary),
              'geometry_and_colours_match': True, 'gcode_checksums_valid': True, 'slicing_successful': True, 'plate_details': summary}
    (work / 'plate_manifest.json').write_text(json.dumps([{'plate': p['plate'], 'colors': p['colours'], 'parts': p['parts']} for p in summary], indent=2) + '\n')
    (work / 'project_check.json').write_text(json.dumps(report, indent=2) + '\n')
    return report

if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
