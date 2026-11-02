"""Render a built player HTML to an MP4 with narration and burned-in subtitles.

usage: python mp4.py <player.html> [-o OUT.mp4] [--fps 30] [--jobs N] [--no-subs]     (default OUT: next to the HTML)
Only build.py output works: it reads the scenes, narration and cues out of the player, so no project folder is needed.
Frames are seeked and screenshotted one by one, not screen-recorded, so nothing drops and the audio cannot drift.
Output is 1280x804: the 720-high scene with a subtitle bar below it, as in the player. --no-subs gives plain 1280x720.
"""
import argparse, base64, concurrent.futures, json, os, shutil, subprocess, tempfile, time
from playwright.sync_api import sync_playwright
import common

SUB_H = 84
HOST = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>html,body{margin:0;background:#0c0d10;overflow:hidden}
#frame{display:block;width:1280px;height:720px;border:0}
#sub{height:%dpx;box-sizing:border-box;display:flex;align-items:center;justify-content:center;padding:0 40px;color:#f4f4f5;
font:500 24px/1.4 "Pretendard Variable",Pretendard,"Malgun Gothic",sans-serif;text-align:center;text-wrap:balance;word-break:keep-all}
</style></head><body><iframe id="frame"></iframe><div id="sub"></div></body></html>""" % SUB_H
# Waiting on document.fonts after a text change keeps a newly needed font subset from flashing the fallback font.
SEEK = """async ([ms, text]) => {
  const doc = document.getElementById("frame").contentDocument, sub = document.getElementById("sub");
  doc.getAnimations().forEach(a => { a.pause(); a.currentTime = ms; });
  doc.querySelectorAll("svg").forEach(s => { s.pauseAnimations && s.pauseAnimations(); s.setCurrentTime && s.setCurrentTime(ms / 1000); });
  if (sub.textContent !== text) { sub.textContent = text; sub.offsetHeight; await document.fonts.ready; }
}"""
# Tag as BT.709 and convert to match, or players show slightly shifted colors at this resolution.
COLOR = ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
         "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]

def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise SystemExit("ffmpeg not found. Install it, or run: pip install imageio-ffmpeg")

def load_player(path):
    text = open(path, encoding="utf-8").read()
    i = text.find("const DATA = ")
    if i < 0:
        raise SystemExit(f"{path} is not a motion player: only HTML written by build.py can be converted")
    return json.JSONDecoder().raw_decode(text, i + len("const DATA = "))[0]["scenes"]

def caption(s, t):
    """The subtitle the player shows at scene time t."""
    cues = (s.get("audio") or {}).get("cues") or []
    if not cues:
        return s.get("caption") or s.get("narration") or ""
    i = 0
    for k, c in enumerate(cues):
        if c["start"] <= t + 0.05:
            i = k
    return cues[i]["text"]

def render_scene(job):
    """One scene becomes one video-only segment, so scenes can render in parallel."""
    ff, s, seg, fps, subs = job
    enc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "png", "-framerate", str(fps), "-i", "-",
                            *COLOR, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", seg], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        b = common.browser(p)
        h = 720 + SUB_H if subs else 720
        pg = b.new_page(viewport={"width": 1280, "height": h})
        clip, size = {"x": 0, "y": 0, "width": 1280, "height": h}, (1280).to_bytes(4, "big") + h.to_bytes(4, "big")
        pg.set_content(HOST)
        pg.evaluate("h => new Promise(r => { const f = document.getElementById('frame'); f.onload = r; f.srcdoc = h; })", s["html"])
        pg.wait_for_load_state("networkidle")
        pg.frames[1].wait_for_function("!document.querySelector('style[data-clean-start]')")
        pg.frames[1].evaluate("document.fonts.ready.then(() => 0)")
        for i in range(s["durationSec"] * fps):
            t = i / fps
            pg.evaluate(SEEK, [t * 1000, caption(s, t) if subs else ""])
            # PNG because JPEG crushes the near-black background. ffmpeg would silently stretch a wrong-sized frame.
            shot = pg.screenshot(clip=clip)
            if shot[16:24] != size:
                raise SystemExit(f"bad frame size at {t:.2f}s in {s['title']}")
            enc.stdin.write(shot)
        b.close()
    enc.stdin.close()
    if enc.wait():
        raise SystemExit("ffmpeg failed on " + s["title"])

def write_audio(ff, scenes, tmp):
    """Each scene's mp3 padded with silence to the scene length, so narration stays locked to its scene."""
    parts = []
    for n, s in enumerate(scenes, 1):
        wav = f"a{n:03d}.wav"
        if s.get("audio"):
            mp3 = os.path.join(tmp, f"a{n:03d}.mp3")
            open(mp3, "wb").write(base64.b64decode(s["audio"]["src"].split(",", 1)[1]))
            src = ["-i", mp3, "-af", "apad"]
        else:
            print("no narration audio, silent:", s["title"])
            src = ["-f", "lavfi", "-i", "anullsrc"]
        subprocess.run([ff, "-y", "-loglevel", "error", *src, "-t", str(s["durationSec"]), "-ar", "48000", "-ac", "2",
                        os.path.join(tmp, wav)], check=True)
        parts.append(wav)
    return parts

def concat_list(tmp, name, parts):
    open(os.path.join(tmp, name), "w", encoding="utf-8").write("".join(f"file '{p}'\n" for p in parts))

def main(html, out, fps, jobs, subs):
    scenes = load_player(html)
    ff = ffmpeg()
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="motion_mp4_") as tmp:
        segs = [f"v{n:03d}.mp4" for n in range(1, len(scenes) + 1)]
        tasks = [(ff, s, os.path.join(tmp, seg), fps, subs) for s, seg in zip(scenes, segs)]
        with concurrent.futures.ProcessPoolExecutor(jobs) as ex:
            for n, _ in enumerate(ex.map(render_scene, tasks), 1):
                print(f"rendered {n}/{len(scenes)} ({time.time() - t0:.0f}s)", flush=True)
        concat_list(tmp, "video.txt", segs)
        concat_list(tmp, "audio.txt", write_audio(ff, scenes, tmp))
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-i", "video.txt", "-f", "concat", "-i", "audio.txt",
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
                        os.path.abspath(out)], cwd=tmp, check=True)
    print("wrote", os.path.normpath(out), f"{os.path.getsize(out)/1e6:.1f} MB,", len(scenes), "scenes,",
          sum(s["durationSec"] for s in scenes), "s, took", f"{time.time() - t0:.0f}s")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("html"); ap.add_argument("-o", "--out"); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2)); ap.add_argument("--no-subs", action="store_true")
    a = ap.parse_args()
    main(a.html, a.out or os.path.splitext(a.html)[0] + ".mp4", a.fps, a.jobs, not a.no_subs)
