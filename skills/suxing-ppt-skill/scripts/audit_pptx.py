#!/usr/bin/env python3
"""Structural PPTX risk scanner; NOT PowerPoint/WPS playback/editability validation."""
import argparse
import json
import sys
import zipfile
import re
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
}
P = '{' + NS['p'] + '}'
A = '{' + NS['a'] + '}'


def scan_pptx(path, mode='editable'):
    report = {'file': str(path), 'mode': mode, 'slides': [], 'warnings': [], 'errors': []}
    try:
        with zipfile.ZipFile(path, 'r') as z:
            corrupt = z.testzip()
            if corrupt:
                report['errors'].append(f'ZIP CRC failure: {corrupt}')
            allnames = z.namelist()
            if 'ppt/presentation.xml' not in allnames:
                report['errors'].append('presentation.xml is missing')
                return report
            root = ET.fromstring(z.read('ppt/presentation.xml'))
            size = root.find('p:sldSz', NS)
            width = int(size.get('cx', 0)) if size is not None else 0
            height = int(size.get('cy', 0)) if size is not None else 0
            slidepaths = sorted((p for p in allnames if re.fullmatch(r'ppt/slides/slide\d+\.xml', p)), key=lambda x: int(re.search(r'slide(\d+)', x).group(1)))
            if not slidepaths:
                report['errors'].append('No slide XML files found')
            for slidepath in slidepaths:
                element = ET.fromstring(z.read(slidepath))
                spTree = element.find('.//p:spTree', NS)
                if spTree is None:
                    report['errors'].append(f'{slidepath}: missing spTree')
                    continue
                shapes = list(spTree.findall('p:sp', NS))
                pics = list(spTree.findall('p:pic', NS))
                frames = list(spTree.findall('p:graphicFrame', NS))
                texts = [s for s in shapes if ''.join(t.text or '' for t in s.findall('.//a:t', NS)).strip()]
                timing = element.find('p:timing', NS) is not None
                fullpics = 0
                for pic in pics:
                    xfrm = pic.find('p:spPr/a:xfrm', NS)
                    if xfrm is None or not(width and height):
                        continue
                    off, ext = xfrm.find('a:off', NS), xfrm.find('a:ext', NS)
                    if off is None or ext is None:
                        continue
                    x, y = int(off.get('x', 0)), int(off.get('y', 0))
                    cx, cy = int(ext.get('cx', 0)), int(ext.get('cy', 0))
                    if cx >= width*.95 and cy >= height*.95 and abs(x) <= width*.05 and abs(y) <= height*.05:
                        fullpics += 1
                obj = {'number': int(re.search(r'slide(\d+)', slidepath).group(1)), 'native_shapes': len(shapes), 'text_shapes': len(texts), 'pictures': len(pics), 'graphic_frames': len(frames), 'has_timing_node': timing, 'near_full_slide_pictures': fullpics, 'risks': []}
                if not (shapes or pics or frames):
                    obj['risks'].append('EMPTY_SLIDE')
                if mode == 'editable' and fullpics and not (texts or frames or (len(shapes) > 2)):
                    obj['risks'].append('LIKELY_FLATTENED_SLIDE')
                if mode == 'editable' and not texts and not frames and not shapes and pics:
                    obj['risks'].append('NO_NATIVE_EDITABLE_CONTENT')
                report['slides'].append(obj)
        report['slide_count'] = len(report['slides'])
        report['risk_count'] = sum(len(s['risks']) for s in report['slides'])
    except (OSError, zipfile.BadZipFile, ET.ParseError, ValueError) as exc:
        report['errors'].append(f'Invalid or unreadable PPTX: {exc}')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pptx')
    parser.add_argument('--mode', choices=['editable', 'hybrid', 'image'], default='editable')
    parser.add_argument('--json', dest='json_file', help='optional JSON report path')
    args = parser.parse_args()
    report = scan_pptx(args.pptx, args.mode)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.json_file:
        Path(args.json_file).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_file).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return 2 if report['errors'] else (1 if report.get('risk_count', 0) else 0)


if __name__ == '__main__':
    sys.exit(main())
