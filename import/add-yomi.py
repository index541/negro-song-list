# -*- coding: utf-8 -*-
"""全曲の曲名・アーティストに読み仮名(カタカナ)を付け、titleYomi / artistYomi として保存する。"""
import json
from janome.tokenizer import Tokenizer

t = Tokenizer()
def yomi(text):
    out = []
    for tok in t.tokenize(text or ""):
        out.append(tok.reading if tok.reading and tok.reading != "*" else tok.surface)
    return "".join(out)

songs = json.load(open("songs.json", encoding="utf-8"))
for s in songs:
    s["titleYomi"] = yomi(s["title"])
    s["artistYomi"] = yomi(s["artist"])
json.dump(songs, open("songs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
open("songs.json", "a", encoding="utf-8").write("\n")
print("done:", len(songs))
for s in songs[:3] + [x for x in songs if x["title"] in ("天体観測", "千本桜", "残酷な天使のテーゼ", "紅一葉")]:
    print(" ", s["title"], "->", s["titleYomi"], "|", s["artist"], "->", s["artistYomi"])
