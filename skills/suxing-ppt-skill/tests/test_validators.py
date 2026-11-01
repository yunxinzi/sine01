import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillValidationTest(unittest.TestCase):
    def test_skill(self):
        self.assertEqual(load('validate_skill').validate(ROOT), [])

    def test_project_template(self):
        manifest = json.loads((ROOT / 'assets/project-template.json').read_text(encoding='utf8'))
        self.assertEqual(load('validate_project').validate(manifest), [])

    def test_fake_approval_is_flagged(self):
        manifest = json.loads((ROOT / 'assets/project-template.json').read_text(encoding='utf8'))
        manifest['stage'] = 'approved'
        self.assertTrue(load('validate_project').validate(manifest))

    def test_faux_editability_is_flagged(self):
        manifest = json.loads((ROOT / 'assets/project-template.json').read_text(encoding='utf8'))
        manifest['slides'][0]['elements'][0]['kind'] = 'flattened_page'
        self.assertTrue(any('flattened_page' in x for x in load('validate_project').validate(manifest)))


if __name__ == '__main__':
    unittest.main()
