"""Export printable geometry and face colours from the final assembled model."""
import hashlib
import json
import struct
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'build'
bpy.ops.wm.open_mainfile(filepath=str(WORK / 'Laurine_L28.blend'))
layout = json.loads((WORK / 'print_layout.json').read_text())
palette = json.loads((WORK / 'palette.json').read_text())
assert not bpy.data.libraries, 'Linked libraries are not allowed in the public model'
assert not bpy.data.texts, 'Remove embedded notes before delivery'
assert not any(i.packed_file or i.source == 'FILE' for i in bpy.data.images), 'Remove reference images before delivery'
assert abs(bpy.context.scene.unit_settings.scale_length - .001) < 1e-8, 'Model must use millimetres'
expected = {item['name'] for item in layout}
actual = {o.name for c in bpy.data.collections if c.name.startswith(('01', '03')) for o in c.objects if o.type == 'MESH'}
assert actual == expected, f'Printable inventory differs: {actual ^ expected}'
assert len(layout) == len(expected), 'Duplicate part in print layout'
checks = []
for item in layout:
    obj = bpy.data.objects[item['name']]
    assert not obj.modifiers, f'Apply modifiers before delivery: {obj.name}'
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bad_edges = sum(not edge.is_manifold for edge in bm.edges)
    assert bad_edges == 0, f'Open/non-manifold mesh: {obj.name}'
    unseen = set(bm.verts)
    components = 0
    while unseen:
        components += 1
        pending = [unseen.pop()]
        while pending:
            vertex = pending.pop()
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in unseen:
                    unseen.remove(other)
                    pending.append(other)
    assert components == 1, f'Disconnected solids: {obj.name}'
    assert bm.calc_volume(signed=True) > 0, f'Invalid volume: {obj.name}'
    bm.free()
    mesh.calc_loop_triangles()
    rotation = Matrix(item['rotation'])
    points = [rotation @ (obj.matrix_world @ vertex.co) for vertex in mesh.vertices]
    minimum = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    points = [p - minimum for p in points]
    triangles = [list(t.vertices) for t in mesh.loop_triangles]
    colours = [mesh.polygons[t.polygon_index].material_index + 1 for t in mesh.loop_triangles]
    assert len(mesh.materials) == len(palette), f'Palette slots differ: {obj.name}'
    for index, material in enumerate(mesh.materials):
        assert material.name.endswith(palette[index]['name']), f'Palette order differs: {obj.name}'
    target = WORK / ('tests' if item['kind'] == 'fit-test' else 'stl') / (obj.name + '.stl')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('wb') as stream:
        stream.write(b'Laurine L28 - millimetres'.ljust(80, b'\0'))
        stream.write(struct.pack('<I', len(triangles)))
        for indices in triangles:
            a, b, c = (points[i] for i in indices)
            normal = (b - a).cross(c - a)
            assert normal.length > 1e-10, f'Degenerate triangle: {obj.name}'
            stream.write(struct.pack('<12fH', *normal.normalized(), *a, *b, *c, 0))
    data = {'name': obj.name, 'vertices': [[round(float(c), 7) for c in p] for p in points],
            'triangles': triangles, 'filaments': colours}
    (WORK / 'colors').mkdir(exist_ok=True)
    (WORK / 'colors' / (obj.name + '.json')).write_text(json.dumps(data, separators=(',', ':')))
    checks.append({'part': obj.name, 'triangles': len(triangles), 'non_manifold_edges': bad_edges, 'connected_components': components,
                   'dimensions_mm': [round(max(p[i] for p in points), 5) for i in range(3)]})
(WORK / 'model_check.json').write_text(json.dumps({'model_sha256': hashlib.sha256((WORK / 'Laurine_L28.blend').read_bytes()).hexdigest(),
    'private_images': 0, 'embedded_notes': 0, 'linked_libraries': 0, 'parts': checks}, indent=2) + '\n')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/base_geometry.blend'))
assert not bpy.data.libraries and not bpy.data.texts, 'Remove linked data and notes from the base model'
assert not any(i.packed_file or i.source=='FILE' for i in bpy.data.images), 'Remove reference images from the base model'
print(f'Exported {len(checks)} parts from the final model; both Blender files passed privacy checks', flush=True)
