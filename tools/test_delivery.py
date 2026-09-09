"""Regression checks for stale deliveries and partially staged commits."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import delivery


class DeliveryChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        files = {'VERSION': 'test\n', 'model/Laurine_L28.blend': 'model',
                 'print/Laurine_Multicolor_A1.3mf': 'project', 'source/print_layout.json': '[]',
                 'reports/model_check.json': '{}', 'README.md': 'A boat.\n',
                 'reports/project_check.json': json.dumps({'geometry_and_colours_match': True,
                     'gcode_checksums_valid': True, 'slicing_successful': True})}
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.git('add', '.')
        delivery.write_receipt(self.root)
        self.git('add', '.')

    def git(self, *args):
        subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True)

    def test_documentation_only_commit_keeps_delivery(self):
        (self.root / 'README.md').write_text('A better description.\n')
        self.git('add', 'README.md')
        delivery.verify(self.root, staged=True)

    def test_modified_model_requires_new_project_delivery(self):
        (self.root / 'model/Laurine_L28.blend').write_text('changed model')
        self.git('add', 'model/Laurine_L28.blend')
        with self.assertRaisesRegex(ValueError, 'Stale delivery'):
            delivery.verify(self.root, staged=True)

    def test_unstaged_receipt_cannot_mask_old_index(self):
        (self.root / 'print/Laurine_Multicolor_A1.3mf').write_text('changed project')
        self.git('add', 'print/Laurine_Multicolor_A1.3mf')
        delivery.write_receipt(self.root)
        delivery.verify(self.root)
        with self.assertRaisesRegex(ValueError, 'Stale delivery'):
            delivery.verify(self.root, staged=True)

    def test_missing_piece_is_detected(self):
        self.git('rm', '-f', 'model/Laurine_L28.blend')
        with self.assertRaises(ValueError):
            delivery.verify(self.root, staged=True)

    def test_unexpected_private_file_is_rejected(self):
        path = self.root / 'private/photo.png'
        path.parent.mkdir()
        path.write_bytes(b'private image')
        self.git('add', 'private/photo.png')
        with self.assertRaisesRegex(ValueError, 'Private'):
            delivery.verify(self.root, staged=True)

    def test_unexpected_extra_export_is_detected(self):
        (self.root / 'print/forgotten.stl').write_text('stale export')
        self.git('add', 'print/forgotten.stl')
        with self.assertRaisesRegex(ValueError, 'Stale delivery'):
            delivery.verify(self.root, staged=True)


if __name__ == '__main__':
    unittest.main()
