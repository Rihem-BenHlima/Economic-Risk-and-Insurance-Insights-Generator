"""Packs the whole frontend into ONE html file (styles, scripts, chart library, data and the hero pictures inlined): frontend/dist/tunisia-insights.html.
It opens by double-click, works offline and can be sent by email or put on any web host.
Run:  python frontend/build_data.py      (only if the numbers changed)
      python frontend/build_single.py
"""
import base64
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "dist" / "tunisia-insights.html"


def safe(js):
    return js.replace("</script", "<\\/script")          # a script text must never contain a closing script tag


def main():
    html = (HERE / "index.html").read_text(encoding="utf-8")
    html = re.sub(r'<link rel="stylesheet" href="([^"]+)">', lambda m: "<style>\n" + (HERE / m.group(1)).read_text(encoding="utf-8") + "\n</style>", html)
    slides = sorted((HERE / "img").glob("*.jpg"))
    if slides:                                           # the slideshow pictures travel inside the file as data addresses
        data = "{" + ",".join(f'"img/{p.name}":"data:image/jpeg;base64,' + base64.b64encode(p.read_bytes()).decode() + '"' for p in slides) + "}"
        html = html.replace('  <script src="data/data.js"></script>', "  <script>window.HERO_DATA = " + data + ";</script>\n  <script src=\"data/data.js\"></script>", 1)
    html = re.sub(r'<script src="([^"]+)"></script>', lambda m: "<script>\n" + safe((HERE / m.group(1)).read_text(encoding="utf-8")) + "\n</script>", html)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT.relative_to(HERE.parent)}  ({OUT.stat().st_size / 1024 / 1024:.1f} MB, no external files)")


if __name__ == "__main__":
    main()
