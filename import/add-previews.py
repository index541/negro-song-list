# -*- coding: utf-8 -*-
"""全曲に iTunes / Deezer の公式試聴(30秒プレビューURL)を照合して付ける。
使い方: python3 import/add-previews.py [--apply]
採用条件:
  tier1: 曲名スコア>=80 かつ アーティスト一致(コア表記一致 or 重なり)
  tier2: 曲名が完全一致(100) かつ 曲名が4文字以上 かつ カバー/歌い手名義でない
"""
import json, re, sys, importlib.util
from concurrent.futures import ThreadPoolExecutor

spec = importlib.util.spec_from_file_location('we', 'import/walkman-enrich.py')
we = importlib.util.module_from_spec(spec); spec.loader.exec_module(we)
norm, title_score, artist_core, artist_overlap = we.norm, we.title_score, we.artist_core, we.artist_overlap
itunes_search, deezer_search = we.itunes_search, we.deezer_search

APPLY = "--apply" in sys.argv
songs = json.load(open("songs.json", encoding="utf-8"))

BLOCK = set("""鋼兵 ネグロ Vin Gero ヤマイ 赤ティン りぶ うさ ろん 96猫 まふまふ そらる ぐるたみん
あるふぁきゅん。 天月-あまつき- ウォルピスカーター ウォルピス・カーター 少年T 少年Ｔ ヲタみん 湯毛
vip店長 kradness SymaG ASK nero ぽこた 花たん ピコ 赤飯 あさまる ぱなまん ルシュカ リツカ
こばたん ふくめん 大根 iciko recog よっぺい ちせちゃん 弟の姉 ばずぱんだ みゆはん 秋赤音
伊東歌詞太郎 浦島坂田船 ナノ 島爺 鹿乃 りょーくん しゅーず ダズビー 相宮零 流田Project H△G
Dancing Dolls Will Stetson いかさん Ado 和楽器バンド めいちゃん 松下 majiko ななもり。""".split())

def blocked(a):
    a = (a or "").strip()
    if "melost" in a:
        return True
    parts = re.split(r"[&＆×、,・/]", re.split(r" feat", a)[0])
    return any(p.strip() in BLOCK for p in parts)

def artist_match(cand, mine):
    return norm(artist_core(cand)) == norm(artist_core(mine)) or artist_overlap(cand, mine)

def find_preview(s):
    title, artist = s["title"], s["artist"]
    wn = norm(title)
    term = title + " " + artist_core(artist)
    # iTunes
    cands = []
    for r in itunes_search(term):
        t = r.get("trackName", "")
        if "カラオケ" in t or not r.get("previewUrl"):
            continue
        sc = title_score(wn, t)
        if sc >= 80:
            cands.append((sc, r.get("artistName", ""), r["previewUrl"]))
    cands.sort(key=lambda x: -x[0])
    for sc, ca, url in cands:
        if artist_match(ca, artist):
            return url
    for sc, ca, url in cands:
        if sc == 100 and len(wn) >= 4 and not blocked(ca):
            return url
    # Deezer
    cands = []
    for r in deezer_search(term):
        t = r.get("title", "")
        if "カラオケ" in t or not r.get("preview"):
            continue
        sc = title_score(wn, t)
        if sc >= 80:
            cands.append((sc, ((r.get("artist") or {}).get("name") or ""), r["preview"]))
    cands.sort(key=lambda x: -x[0])
    for sc, ca, url in cands:
        if artist_match(ca, artist):
            return url
    for sc, ca, url in cands:
        if sc == 100 and len(wn) >= 4 and not blocked(ca):
            return url
    return ""

todo = [s for s in songs if not s.get("preview")]
print("to check:", len(todo), "| already have:", len(songs) - len(todo), flush=True)
found = [0]
def work(s):
    url = find_preview(s)
    if url:
        s["preview"] = url
        found[0] += 1
    return s
done = [0]
with ThreadPoolExecutor(max_workers=3) as ex:
    for _ in ex.map(work, todo):
        done[0] += 1
        if done[0] % 200 == 0:
            print("progress %d/%d found %d" % (done[0], len(todo), found[0]), flush=True)
total_with = sum(1 for s in songs if s.get("preview"))
print("newly found:", found[0], "| total with preview: %d/%d" % (total_with, len(songs)))
if APPLY:
    json.dump(songs, open("songs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open("songs.json", "a", encoding="utf-8").write("\n")
    print("APPLIED")
else:
    print("DRY RUN")
