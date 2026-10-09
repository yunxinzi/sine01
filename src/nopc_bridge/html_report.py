"""Single portable HTML result for phone readers; no network/CDN requirement."""
import base64
from html import escape
from pathlib import Path


def write_html_report(folder, summary):
    folder = Path(folder)
    pic = folder / 'displacement.png'
    img = ''
    if pic.exists():
        encoded = base64.b64encode(pic.read_bytes()).decode('ascii')
        img = ('<img alt="Numerically computed axial displacement vs analytic reference" '
               'style="max-width:100%;height:auto;border-radius:8px" '
               f'src="data:image/png;base64,{encoded}">')
    lines=[]
    for k,v in summary.items():
        if isinstance(v,(str,int,float)):
            lines.append(f'<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>')
    body=''.join(lines)
    doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NoPC CAE calculated result</title>
<style>body{{font-family:system-ui,-apple-system,sans-serif;margin:auto;max-width:800px;padding:18px;line-height:1.5}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:8px;border-bottom:1px solid #ddd;text-align:left;overflow-wrap:anywhere}}
th{{width:48%}}.note{{border:1px solid #aaa;border-radius:9px;padding:10px}}</style>
</head><body><h1>NoPC CAE — Computed Result</h1>
<p class="note">Genuine 3D linear-static FEM output. NOT experimentally validated, NOT a complex composite impact simulation, NOT industrial-certified.</p>
{img}<h2>Numerical summary</h2><table>{body}</table>
<p>Numerical fields are stored in fields.npz and result.vtk. See the package inputs, validation reports and SHA-256 manifest for reproducibility.</p>
</body></html>'''
    (folder/'report.html').write_text(doc,encoding='utf-8')
