#!/usr/bin/env python3
"""Create an absolute-difference heatmap for equally-sized page renders (Pillow required)."""
import argparse
import json
import sys
from pathlib import Path


def compare(reference, render, heatmap):
    try:
        from PIL import Image, ImageChops, ImageEnhance, ImageStat
    except ImportError as exc:
        raise RuntimeError('Pillow is required: pip install Pillow') from exc
    a = Image.open(reference).convert('RGB')
    b = Image.open(render).convert('RGB')
    if a.size != b.size:
        raise ValueError(f'Image size mismatch: {a.size} != {b.size}; use consistent page size / rendering')
    diff = ImageChops.difference(a, b)
    mae = sum(ImageStat.Stat(diff).mean) / 3.0
    nonzero_bbox = diff.getbbox()
    if heatmap:
        # These enhanced differences are for defect inspection, not aesthetic scoring.
        ImageEnhance.Contrast(diff).enhance(2).save(heatmap)
    return {'reference': str(reference), 'render': str(render), 'size': list(a.size), 'mae_0_255': round(mae, 3), 'identical': nonzero_bbox is None, 'heatmap': str(heatmap) if heatmap else None, 'note': 'Pixel difference only; human comparison and editability/playback tests still required.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference')
    parser.add_argument('render')
    parser.add_argument('--heatmap')
    args = parser.parse_args()
    try:
        result = compare(args.reference, args.render, args.heatmap)
    except (RuntimeError, ValueError, OSError) as exc:
        print('FAIL:', exc, file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
