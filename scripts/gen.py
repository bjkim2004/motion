"""Generate self-contained <project>/sNN.html from <project>/src/sNN.html fragments.

usage: python gen.py <project> [s01 s02 ...]
Fragment = head extras (<style>…) + '<!--body-->' + body markup.
Timing tokens (replaced with seconds):
  {cN} start of sentence N (1-based), {eN} end of sentence N, {end} audio length, {dur} audio+1
  optional offset: {c3+0.6}, {e2-0.3}
Icons: [[name]] or [[name classes]], names in assets/icons.json.
"""
import json, os, re, sys
import common

ICONS = json.loads(common.asset("icons.json"))
ICON_RE = re.compile(r"\[\[(\w+)(?: ([^\]]+))?\]\]")
TOK = re.compile(r"\{(c|e)(\d+)([+-][\d.]+)?\}|\{(end|dur)([+-][\d.]+)?\}")

def icon(m):
    if m.group(1) not in ICONS:
        raise SystemExit(f"unknown icon {m.group(0)}; see assets/icons.json")
    return f'<svg class="ico {m.group(2) or ""}" viewBox="0 0 24 24">{ICONS[m.group(1)]}</svg>'

def build(d, sid, tts, spec, css):
    t = tts[sid]
    cues, end = t["cues"], t["audioSec"]
    src = open(os.path.join(d, "src", sid + ".html"), encoding="utf-8").read()
    def rep(m):
        if m.group(1):
            i = int(m.group(2)) - 1
            if i >= len(cues):
                raise SystemExit(f"{sid}: token {m.group(0)} but only {len(cues)} cues")
            v = cues[i]["start"] if m.group(1) == "c" else cues[i]["end"]
            off = m.group(3)
        else:
            v = end if m.group(4) == "end" else end + 1
            off = m.group(5)
        if off: v += float(off)
        return f"{max(v, 0):.2f}"
    src = ICON_RE.sub(icon, TOK.sub(rep, src))
    head, body = src.split("<!--body-->", 1)
    title = spec[sid]["title"].replace("&", "&amp;").replace("<", "&lt;")
    html = (f'<!DOCTYPE html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n<title>{title}</title>\n'
            f"<style>\n{css}</style>\n{head.strip()}\n</head>\n<body style=\"--T:{end:.2f}s\">\n"
            f'<div class="dots"></div>\n<div class="bloom"></div>\n{body.strip()}\n</body>\n</html>\n')
    open(os.path.join(d, sid + ".html"), "w", encoding="utf-8").write(html)
    print("gen", sid, f"{end:.1f}s", len(cues), "cues")

if __name__ == "__main__":
    d = sys.argv[1]
    tts = common.load(d, "tts.json")
    spec = {s["id"]: s for s in common.load(d, "scenes.json")["scenes"]}
    css = common.asset("common.css")
    ids = sys.argv[2:] or sorted(f[:-5] for f in os.listdir(os.path.join(d, "src")) if f.endswith(".html"))
    for i in ids:
        build(d, i, tts, spec, css)
