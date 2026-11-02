"""Turn script.json (written in subtitle spelling) into scenes.json with Hangul-pronunciation narration.

usage: python mk_scenes.py <project>
script.json: {"title", "output", "pron": {"Qdrant":"큐드란트", ...},
              "scenes": [{"id":"s01", "title":"...", "lines":["문장 하나.", ["내레이션 문장.", "자막 문장."], ...]}]}
A line is one sentence = one subtitle. Terms come from assets/pron.json plus "pron" (which wins).
Warns about Latin text or symbols left in narration, because the TTS voice mangles them.
"""
import json, os, re, sys
import common

def main(d):
    src = common.load(d, "script.json")
    pron = {**json.loads(common.asset("pron.json")), **src.get("pron", {})}
    # Whole Latin words only, so "UI" leaves "GUI" alone; Korean particles may follow ("AI는"). One pass, longest first.
    terms = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(map(re.escape, sorted(pron, key=len, reverse=True))) + r")(?![A-Za-z0-9])")
    def speak(s):
        return re.sub(r"[\"“”]", "", terms.sub(lambda m: pron[m.group(0)], s))
    scenes = []
    for s in src["scenes"]:
        narr, subs = [], []
        for line in s["lines"]:
            sub, say = (line, speak(line)) if isinstance(line, str) else (line[1], line[0])
            if len(re.findall(r"[.?!](?:\s|$)", sub)) != 1 or not re.search(r"[.?!]$", sub):
                print("  SENTENCE?", s["id"], "one line must be exactly one sentence ending in . ? ! :", sub)
            left = re.findall(r"[A-Za-z][A-Za-z0-9-]*", say)
            if left:
                print("  ENGLISH?", s["id"], left, 'add to "pron":', say)
            if len(sub) > 60:
                print("  LONGLINE?", s["id"], len(sub), "chars; a subtitle reads best under 60:", sub)
            sym = re.findall(r"[~×→:/+=]", say)
            if sym:
                print("  SYMBOL?", s["id"], sym, "write it as spoken:", say)
            narr.append(say); subs.append(sub)
        e = {"id": s["id"], "title": s["title"], "narration": " ".join(narr)}
        if subs != narr:
            e["subtitle"] = " ".join(subs)
        scenes.append(e)
    json.dump({"title": src["title"], "output": src.get("output", src["title"]), "scenes": scenes},
              open(os.path.join(d, "scenes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote scenes.json:", len(scenes), "scenes")

if __name__ == "__main__":
    main(sys.argv[1])
