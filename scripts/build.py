"""Assemble a project into one self-contained player HTML.

usage: python build.py <project> [--out DIR]     (default DIR: ./outputs)
Needs scenes.json, tts.json, audio/<id>.mp3 and <id>.html for every scene. Writes DIR/<output>.html
"""
import argparse, base64, json, math, os, re
import common

def main(d, outdir):
    spec = common.load(d, "scenes.json")
    tts = common.load(d, "tts.json")
    scenes = []
    for s in spec["scenes"]:
        t = tts[s["id"]]
        assert t["narration"] == s["narration"], "narration changed; rerun tts.py for " + s["id"]
        html = open(os.path.join(d, s["id"] + ".html"), encoding="utf-8").read()
        mp3 = open(os.path.join(d, "audio", s["id"] + ".mp3"), "rb").read()
        # Optional "subtitle": on-screen text (original spelling, e.g. English terms) shown in place of the
        # spoken narration (which may spell terms out in Hangul for the TTS). Sentence i ↔ audio cue i.
        cues = t["cues"]
        if s.get("subtitle"):
            parts = [x for x in re.split(r"(?<=[.?!])\s+", s["subtitle"].strip()) if x]
            assert len(parts) == len(cues), f'{s["id"]}: subtitle has {len(parts)} sentences, audio has {len(cues)} cues'
            cues = [dict(c, text=p) for c, p in zip(cues, parts)]
        scenes.append({
            "title": s["title"], "narration": s["narration"], "caption": s.get("subtitle") or s["narration"],
            "durationSec": math.ceil(t["audioSec"] + 1.0),
            "html": common.wrap(html),
            "audio": {"src": "data:audio/mpeg;base64," + base64.b64encode(mp3).decode(), "cues": cues},
        })
    # Escape "<" so a scene's "</script>" can't close the player's <script> block.
    data = json.dumps({"lang": "ko-KR", "scenes": scenes}, ensure_ascii=False).replace("<", chr(92) + "u003c")
    assert "</script" not in data
    title = spec["title"].replace("&", "&amp;").replace("<", "&lt;")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, common.safe_name(spec["output"]) + ".html")
    open(out, "w", encoding="utf-8").write(common.asset("player_head.html").replace("{{TITLE}}", title)
                                           + "const DATA = " + data + common.asset("player_tail.html"))
    print("wrote", os.path.normpath(out), f"{os.path.getsize(out)/1e6:.1f} MB,", len(scenes), "scenes,",
          sum(s["durationSec"] for s in scenes), "s")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("--out", default="outputs")
    a = ap.parse_args()
    main(a.project, a.out)
