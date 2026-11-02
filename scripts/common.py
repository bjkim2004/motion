"""Shared helpers. Every tool takes <project>: the folder holding one video's scenes.json, src/, audio/, tts.json."""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")

# Scenes without "voice" (projects from before voices existed) were synthesized in the first voice.
VOICES = {"female": "ko-KR-SunHiNeural", "male": "ko-KR-InJoonNeural"}
DEFAULT_VOICE = "female"

def asset(name):
    return open(os.path.join(ASSETS, name), encoding="utf-8").read()

def load(project, name):
    return json.load(open(os.path.join(project, name), encoding="utf-8"))

def wrap(html):
    """Inject the player bridge and fonts right after <head>, as the built player does."""
    i = html.index("<head>") + len("<head>")
    return html[:i] + asset("scene_prefix.html") + html[i:]

def safe_name(s):
    """Scene titles and outputs become file names; ':' etc. are illegal on Windows."""
    return re.sub(r'[\\/:*?"<>|]', "_", s).strip(" .")

def browser(p):
    """Installed Edge, then Chrome, then Playwright's own Chromium."""
    last = None
    for ch in ("msedge", "chrome", None):
        try:
            return p.chromium.launch(channel=ch) if ch else p.chromium.launch()
        except Exception as e:
            last = e
    raise SystemExit(f"No browser for Playwright: {last}\nRun: python -m playwright install chromium")
