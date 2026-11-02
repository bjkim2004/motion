"""Capture each scene's finished frame as a 1280x720 PNG, one per scene.

usage: python capture.py <project> [--out DIR] [--at SECONDS_BEFORE_END]     (default DIR: ./outputs)
Writes DIR/<output>/NN_<scene title>.png. The frame is taken at scene end - 0.2s, when everything has landed.
"""
import argparse, math, os
from playwright.sync_api import sync_playwright
import common

def main(d, outdir, before):
    spec = common.load(d, "scenes.json")
    tts = common.load(d, "tts.json")
    folder = os.path.join(outdir, common.safe_name(spec["output"]))
    os.makedirs(folder, exist_ok=True)
    with sync_playwright() as p:
        b = common.browser(p)
        for n, s in enumerate(spec["scenes"], 1):
            pg = b.new_page(viewport={"width": 1280, "height": 720})
            pg.set_content(common.wrap(open(os.path.join(d, s["id"] + ".html"), encoding="utf-8").read()), wait_until="networkidle")
            pg.evaluate("document.fonts.ready.then(() => 0)")
            pg.wait_for_timeout(600)
            t = math.ceil(tts[s["id"]]["audioSec"] + 1.0) - before
            pg.evaluate("""t => { document.getAnimations().forEach(a => { a.pause(); a.currentTime = t; });
                document.querySelectorAll('svg').forEach(s => { s.pauseAnimations && (s.pauseAnimations(), s.setCurrentTime && s.setCurrentTime(t/1000)); }); }""", t * 1000)
            pg.wait_for_timeout(150)
            pg.screenshot(path=os.path.join(folder, f"{n:02d}_{common.safe_name(s['title'])}.png"))
            pg.close()
        b.close()
    print("captured", len(spec["scenes"]), "scenes to", os.path.normpath(folder))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("--out", default="outputs"); ap.add_argument("--at", type=float, default=0.2)
    a = ap.parse_args()
    main(a.project, a.out, a.at)
