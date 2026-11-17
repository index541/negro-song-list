# -*- coding: utf-8 -*-
"""ジャケット未設定の曲に iTunes / Deezer のジャケット画像を照合して付ける。
使い方: python3 import/add-jackets.py [--apply]
採用条件は add-previews.py と同じ:
  tier1: 曲名スコア>=80 かつ アーティスト一致(コア表記一致 or 重なり)
  tier2: 曲名が完全一致(100) かつ 曲名が4文字以上 かつ カバー/歌い手名義でない
曲名・アーティスト・よみがなは変更しない。jacket フィールドだけを埋める。
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

def artwork_of(r):
    u = r.get("artworkUrl100", "")
    if u:
        return u.replace("100x100bb.jpg", "600x600bb.jpg")
    return ""

def find_jacket(s):
    title, artist = s["title"], s["artist"]
    wn = norm(title)
    term = title + " " + artist_core(artist)
    # iTunes
    cands = []
    for r in itunes_search(term):
        t = r.get("trackName", "")
        art = artwork_of(r)
        if "カラオケ" in t or not art:
            continue
        sc = title_score(wn, t)
        if sc >= 80:
            cands.append((sc, r.get("artistName", ""), art, r.get("collectionName", ""), t))
    cands.sort(key=lambda x: -x[0])
    for sc, ca, art, col, t in cands:
        if artist_match(ca, artist):
            return art, f"iTunes tier1 score={sc} track={t} artist={ca} album={col}"
    for sc, ca, art, col, t in cands:
        if sc == 100 and len(wn) >= 4 and not blocked(ca):
            return art, f"iTunes tier2 score={sc} track={t} artist={ca} album={col}"
    # Deezer
    cands = []
    for r in deezer_search(term):
        t = r.get("title", "")
        alb = r.get("album") or {}
        art = alb.get("cover_xl") or alb.get("cover_big") or ""
        if "カラオケ" in t or not art:
            continue
        sc = title_score(wn, t)
        if sc >= 80:
            cands.append((sc, ((r.get("artist") or {}).get("name") or ""), art, alb.get("title", ""), t))
    cands.sort(key=lambda x: -x[0])
    for sc, ca, art, col, t in cands:
        if artist_match(ca, artist):
            return art, f"Deezer tier1 score={sc} track={t} artist={ca} album={col}"
    for sc, ca, art, col, t in cands:
        if sc == 100 and len(wn) >= 4 and not blocked(ca):
            return art, f"Deezer tier2 score={sc} track={t} artist={ca} album={col}"
    return "", ""

todo = [s for s in songs if not s.get("jacket")]
print("to check:", len(todo), "| already have jacket:", len(songs) - len(todo), flush=True)

def work(s):
    art, why = find_jacket(s)
    return s, art, why

hits, misses = [], []
with ThreadPoolExecutor(max_workers=4) as ex:
    for s, art, why in ex.map(work, todo):
        if art:
            hits.append((s, art, why))
        else:
            misses.append(s)

print(f"\n== matched: {len(hits)} / {len(todo)}")
for s, art, why in hits:
    print(f"HIT {s['id']} {s['title']} / {s['artist']}  [{why}]")
    if APPLY:
        s["jacket"] = art
print(f"\n== no match: {len(misses)}")
for s in misses:
    print(f"MISS {s['id']} {s['title']} / {s['artist']}  genres={s.get('genres')}")

if APPLY:
    json.dump(songs, open("songs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\napplied.")
