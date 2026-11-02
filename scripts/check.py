"""Screenshot scenes and report layout problems.

usage: python check.py <project> [s01:10,27 s02:L s03 ...]
Times in seconds; 'L' = audio end - 0.5 (the default). No scene args = every scene at L.
Writes <project>/snaps/<id>_<t>.png. No scene args also clears old snaps first.
Prints OVERFLOW?/CLIPPED?/TIMING?/ERROR/RULE lines, then CLEAN (exit 0) or N issues (exit 1).
"""
import os, re, sys
from playwright.sync_api import sync_playwright
import common

BANNED = [(r"\b(setTimeout|setInterval|requestAnimationFrame)\s*\(", "timer-driven motion can't pause"),
          (r"<img\b", "no external images"), (r"gsap", "no animation libraries")]

def main(d, args):
    tts = common.load(d, "tts.json")
    os.makedirs(os.path.join(d, "snaps"), exist_ok=True)
    if not args:
        args = [s["id"] for s in common.load(d, "scenes.json")["scenes"]]
        for f in os.listdir(os.path.join(d, "snaps")):
            if f.endswith(".png"): os.remove(os.path.join(d, "snaps", f))
    issues = []
    def report(*a):
        issues.append(a); print(" ", *a)
    with sync_playwright() as p:
        b = common.browser(p)
        for a in args:
            sid, _, ts = a.partition(":")
            times = [tts[sid]["audioSec"] - 0.5 if t == "L" else float(t) for t in (ts or "L").split(",")]
            html = open(os.path.join(d, sid + ".html"), encoding="utf-8").read()
            for rx, why in BANNED:
                if re.search(rx, html, re.I): report("RULE", sid, why, rx)
            pg = b.new_page(viewport={"width": 1280, "height": 720})
            errs = []
            pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.set_content(common.wrap(html), wait_until="networkidle")
            pg.wait_for_timeout(600)
            # Everything must land before the voice ends. 999s is the unset default of .lit/.dimout; ambience is exempt.
            late = pg.evaluate("""end => document.getAnimations().map(a => [a.effect.target, a.effect.getComputedTiming()])
              .filter(([e, c]) => isFinite(c.endTime) && c.delay < 9e5 && c.endTime > end + 300 && !e.matches('.cam, .dots, .bloom'))
              .slice(0, 5).map(([e, c]) => e.tagName + '.' + (e.className.baseVal ?? e.className) + ' ends ' + (c.endTime / 1000).toFixed(1) + 's')""", tts[sid]["audioSec"] * 1000)
            for o in late: report("TIMING?", sid, o, f'(audio {tts[sid]["audioSec"]:.1f}s)')
            for t in times:
                pg.evaluate("""t => { document.getAnimations().forEach(a => { a.pause(); a.currentTime = t; });
                    document.querySelectorAll('svg').forEach(s => { s.pauseAnimations && (s.pauseAnimations(), s.setCurrentTime && s.setCurrentTime(t/1000)); }); }""", t * 1000)
                pg.wait_for_timeout(120)
                out = os.path.join(d, "snaps", f"{sid}_{t:.0f}.png")
                pg.screenshot(path=out)
                print("saved", os.path.normpath(out))
            # Overflow is judged with the camera breath off; the bloom is decorative.
            over = pg.evaluate("""() => { document.querySelectorAll('.cam').forEach(c => c.style.animation = 'none');
              return [...document.body.querySelectorAll('*')].filter(e => {
                if (e.closest('.bloom') || e.matches('.cam, svg.st, .dots')) return false;
                const r = e.getBoundingClientRect(); return r.width && (r.right > 1282 || r.bottom > 722 || r.left < -2 || r.top < -2);
              }).slice(0, 8).map(e => e.tagName + '.' + (e.className.baseVal ?? e.className) + ' ' + JSON.stringify(e.getBoundingClientRect()))}""")
            for o in over: report("OVERFLOW?", sid, o)
            tight = pg.evaluate("""() => [...document.body.querySelectorAll('div,span,b,i,em')].filter(e =>
                e.children.length === 0 && e.textContent.trim() && (e.scrollWidth > e.clientWidth + 2) && getComputedStyle(e).overflow !== 'visible'
              ).slice(0, 5).map(e => e.className + ': ' + e.textContent.slice(0, 30))""")
            for o in tight: report("CLIPPED?", sid, o)
            for e in errs: report("ERROR", sid, e)
            pg.close()
        b.close()
    print(f"{len(issues)} issues" if issues else "CLEAN")
    return 1 if issues else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2:]))
