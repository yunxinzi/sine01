import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audit_pptx', ROOT/'scripts/audit_pptx.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

PRES = '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldSz cx="9144000" cy="5143500"/></p:presentation>'
HEAD = '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree>'
TAIL = '</p:spTree></p:cSld></p:sld>'


class PPTXTest(unittest.TestCase):
    def create(self, xml):
        tmp = tempfile.TemporaryDirectory()
        out = Path(tmp.name) / 'sample.pptx'
        with zipfile.ZipFile(out, 'w') as z:
            z.writestr('ppt/presentation.xml', PRES)
            z.writestr('ppt/slides/slide1.xml', HEAD+xml+TAIL)
        return tmp,out

    def test_empty_detected(self):
        tmp, out = self.create('')
        with tmp:
            self.assertIn('EMPTY_SLIDE', audit.scan_pptx(out)['slides'][0]['risks'])

    def test_flattened_detected(self):
        xml = '<p:pic><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="9144000" cy="5143500"/></a:xfrm></p:spPr></p:pic>'
        tmp,out = self.create(xml)
        with tmp:
            scan = audit.scan_pptx(out)
            self.assertIn('LIKELY_FLATTENED_SLIDE', scan['slides'][0]['risks'])
            self.assertNotIn('LIKELY_FLATTENED_SLIDE', audit.scan_pptx(out, mode='image')['slides'][0]['risks'])

    def test_native_text_not_empty(self):
        tmp, out = self.create('<p:sp><p:txBody><a:p><a:r><a:t>Hi</a:t></a:r></a:p></p:txBody></p:sp>')
        with tmp:
            s = audit.scan_pptx(out)['slides'][0]
            self.assertEqual(s['text_shapes'], 1)
            self.assertEqual(s['risks'], [])


if __name__ == '__main__':
    unittest.main()
