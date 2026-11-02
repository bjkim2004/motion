"""Synthesize narration for every scene with edge-tts.

usage: python tts.py <project>
Reads scenes.json -> writes audio/<id>.mp3 and tts.json
tts.json: {id: {"narration":..., "audioSec":float, "cues":[{start,end,text}]}}
Scenes whose narration is unchanged are skipped.
"""
import asyncio, json, os, sys
import edge_tts
import edge_tts.constants as _C, edge_tts.communicate as _CM
from mutagen.mp3 import MP3
import common

# Legacy host speech.platform.bing.com returns 403 since Oct 2026 (edge-tts issue #490 / PR #491).
_C.WSS_URL = _CM.WSS_URL = ("wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
                            "?Ocp-Apim-Subscription-Key=" + _C.TRUSTED_CLIENT_TOKEN)

VOICE, RATE = "ko-KR-SunHiNeural", "+8%"

async def synth(text, path):
    c = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="SentenceBoundary")
    buf, cues = bytearray(), []
    async for ch in c.stream():
        if ch["type"] == "audio":
            buf += ch["data"]
        elif ch["type"] == "SentenceBoundary":
            st = ch["offset"] / 1e7
            cues.append({"start": round(max(0.1, st - 0.05), 3), "end": round(st + ch["duration"] / 1e7, 3), "text": ch["text"]})
    open(path, "wb").write(buf)
    return cues

async def main(d):
    scenes = common.load(d, "scenes.json")["scenes"]
    tp = os.path.join(d, "tts.json")
    old = common.load(d, "tts.json") if os.path.exists(tp) else {}
    os.makedirs(os.path.join(d, "audio"), exist_ok=True)
    out = {}
    for s in scenes:
        mp = os.path.join(d, "audio", s["id"] + ".mp3")
        o = old.get(s["id"])
        if o and o["narration"] == s["narration"] and os.path.exists(mp):
            out[s["id"]] = o
        else:
            for attempt in range(4):
                try:
                    cues = await synth(s["narration"], mp); break
                except Exception as e:
                    print("retry", s["id"], e); await asyncio.sleep(3)
            else:
                raise SystemExit("TTS failed for " + s["id"])
            out[s["id"]] = {"narration": s["narration"], "audioSec": round(MP3(mp).info.length, 3), "cues": cues}
            json.dump({**old, **out}, open(tp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)  # keep progress on failure
        r = out[s["id"]]
        print(f'{s["id"]}  {r["audioSec"]:.1f}s' + ("  LONG? over 45s, consider splitting" if r["audioSec"] > 45 else ""))
        for c in r["cues"]:
            print(f'   {c["start"]:6.2f}-{c["end"]:6.2f}  {c["text"]}')
    json.dump(out, open(tp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
