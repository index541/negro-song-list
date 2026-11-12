#!/usr/bin/env python3
# WALKMAN取り込み: inventory jsonl -> 照合済み新規曲リスト
# tier A: 曲名+アーティストがカタログと一致 -> カタログの曲名/アーティスト/ジャケット/ジャンルを採用
# tier B: 曲名だけ一致 -> ジャケット/ジャンルだけ採用（アーティストは手元の情報を維持、ゴミ値ならカタログ採用）
# tier C: 一致なし -> 手元の情報をそのまま
import json, re, sys, time, threading, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

INV = "import/walkman-inventory.jsonl"
EXISTING = "songs.json"
OUT = "import/walkman-songs.json"
REPORT = "import/walkman-report.json"
ADDED_AT = "2026-11-12"

GENRE_MAP = {
    "J-Pop": "J-POP", "Pop": "J-POP", "Anime": "アニソン", "Rock": "ロック",
    "Alternative": "ロック", "Vocaloid": "ボカロ", "Soundtrack": "アニソン",
}
JUNK_ARTISTS = {"", "000", "a", "ac", "g", "?", "？", "vocaloid", "不明", "unknown", "(・ω・)"}
_lock = threading.Lock()
_last = [0.0]

def pace():
    with _lock:
        wait = 0.45 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()

def get_json(url):
    pace()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (song-list import)"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.load(r)

def norm(s):
    s = (s or "").lower()
    s = re.sub(r"《[^》]*》|〈[^〉]*〉", "", s)
    return re.sub(r"[\s\-_・/\\|()\[\]{}'\".,!?☆★×:;〜~～＝=]+", "", s)

def title_score(want_norm, cand_title):
    c = norm(cand_title)
    if not c:
        return 0
    if c == want_norm:
        return 100
    if want_norm and (c.startswith(want_norm) or want_norm.startswith(c)):
        return 70
    if want_norm and (want_norm in c or c in want_norm):
        return 60
    return 0

def artist_core(a):
    a = re.split(r"\s+feat\.?|\s+Feat\.?|\(", a or "")[0]
    return a.split("[")[0].split("/")[0].strip()

def artist_overlap(a, b):
    na, nb = norm(artist_core(a)), norm(artist_core(b))
    if not na or not nb:
        return False
    return na in nb or nb in na

def fname_title(path):
    base = path.replace("\\", "/").split("/")[-1]
    base = re.sub(r"\.[A-Za-z0-9]+$", "", base)
    return re.sub(r"^\d{1,4}\s+", "", base).strip()

def top_of(path):
    parts = [p for p in (path or "").replace("/", "\\").split("\\") if p]
    return parts[0] if parts else ""

def is_junk_artist(a):
    return norm(a) in {norm(x) for x in JUNK_ARTISTS} or (a or "").strip().isdigit()

_itunes_cache = {}
_deezer_cache = {}
_cache_lock = threading.Lock()

def itunes_search(term):
    with _cache_lock:
        if term in _itunes_cache:
            return _itunes_cache[term]
    q = urllib.parse.urlencode({"term": term, "country": "JP", "media": "music",
                                "entity": "song", "limit": 8, "lang": "ja_jp"})
    try:
        d = get_json("https://itunes.apple.com/search?" + q)
        res = d.get("results", [])
    except Exception:
        res = []
    with _cache_lock:
        _itunes_cache[term] = res
    return res

def deezer_search(term):
    with _cache_lock:
        if term in _deezer_cache:
            return _deezer_cache[term]
    q = urllib.parse.urlencode({"q": term, "limit": 8})
    try:
        d = get_json("https://api.deezer.com/search?" + q)
        res = d.get("data", [])
    except Exception:
        res = []
    with _cache_lock:
        _deezer_cache[term] = res
    return res

def pick_best(results, want_norm, get_title, avoid_karaoke=True):
    best, best_sc = None, 0
    for r in results:
        t = get_title(r)
        if avoid_karaoke and "カラオケ" in t:
            continue
        sc = title_score(want_norm, t)
        if sc > best_sc:
            best, best_sc = r, sc
    if best is None and avoid_karaoke:
        return pick_best(results, want_norm, get_title, avoid_karaoke=False)
    return best, best_sc

def enrich(cand):
    title, artist = cand["title"], cand["artist"]
    want = norm(re.sub(r"《[^》]*》|〈[^〉]*〉", "", title))
    core = artist_core(artist)
    out = {"title": title, "artist": artist, "genre": "", "jacket": "", "tier": "C"}
    # --- iTunes: title + artist ---
    res = itunes_search((title + " " + core).strip())
    best, sc = pick_best(res, want, lambda r: r.get("trackName", ""))
    if best and sc >= 60 and artist_overlap(artist, best.get("artistName", "")):
        out.update(title=best["trackName"], artist=best["artistName"],
                   jacket=best["artworkUrl100"].replace("100x100bb.jpg", "600x600bb.jpg") if best.get("artworkUrl100") else "",
                   genre=GENRE_MAP.get(best.get("primaryGenreName", ""), best.get("primaryGenreName", "")), tier="A")
        return out
    # --- iTunes: title only ---
    res2 = itunes_search(title)
    best2, sc2 = pick_best(res2, want, lambda r: r.get("trackName", ""))
    if best2 and sc2 >= 60:
        out["jacket"] = best2["artworkUrl100"].replace("100x100bb.jpg", "600x600bb.jpg") if best2.get("artworkUrl100") else ""
        out["genre"] = GENRE_MAP.get(best2.get("primaryGenreName", ""), best2.get("primaryGenreName", ""))
        out["tier"] = "B"
        if is_junk_artist(artist):
            out["artist"] = best2["artistName"]
        return out
    # --- Deezer: title + artist ---
    res3 = deezer_search((title + " " + core).strip())
    best3, sc3 = pick_best(res3, want, lambda r: r.get("title", ""))
    if best3 and sc3 >= 60 and artist_overlap(artist, (best3.get("artist") or {}).get("name", "")):
        alb = best3.get("album", {})
        out.update(title=best3["title"], artist=best3["artist"]["name"],
                   jacket=alb.get("cover_xl") or alb.get("cover_big") or alb.get("cover_medium", ""), tier="A")
        return out
    res4 = deezer_search(title)
    best4, sc4 = pick_best(res4, want, lambda r: r.get("title", ""))
    if best4 and sc4 >= 60:
        alb = best4.get("album", {})
        out["jacket"] = alb.get("cover_xl") or alb.get("cover_big") or alb.get("cover_medium", "")
        out["tier"] = "B"
        if is_junk_artist(artist):
            out["artist"] = (best4.get("artist") or {}).get("name", artist)
        return out
    if cand.get("tagGenre"):
        g = cand["tagGenre"].strip()
        out["genre"] = GENRE_MAP.get(g, g)
    return out

def main():
    rows = [json.loads(ln) for ln in open(INV, encoding="utf-8") if ln.strip()]
    existing = json.load(open(EXISTING, encoding="utf-8"))
    ex_titles = {norm(s["title"]) for s in existing}
    cands = {}
    for r in rows:
        title = (r["tagTitle"] or fname_title(r["path"])).strip()
        artist = (r["tagArtist"] or top_of(r["path"])).strip()
        if not title:
            continue
        key = (norm(title), norm(artist_core(artist)))
        if key not in cands:
            cands[key] = {"title": title, "artist": artist, "tagGenre": r.get("tagGenre", ""), "files": 0}
        cands[key]["files"] += 1
    cand_list = list(cands.values())
    excluded, todo = [], []
    for c in cand_list:
        if norm(c["title"]) in ex_titles:
            excluded.append(c)
        else:
            todo.append(c)
    print("candidates=%d excluded_existing=%d todo=%d" % (len(cand_list), len(excluded), len(todo)), flush=True)
    # 再開対応: 完了分はJSONLに随時追記し、再起動時は読み込んで飛ばす
    partial_path = "import/walkman-progress.jsonl"
    done_map = {}
    try:
        for ln in open(partial_path, encoding="utf-8"):
            if ln.strip():
                r = json.loads(ln)
                done_map[(norm(r["orig_title"]), norm(artist_core(r["orig_artist"])))] = r
    except FileNotFoundError:
        pass
    todo2 = [c for c in todo if (norm(c["title"]), norm(artist_core(c["artist"]))) not in done_map]
    print("already done=%d remaining=%d" % (len(done_map), len(todo2)), flush=True)
    pf = open(partial_path, "a", encoding="utf-8")
    done = [len(done_map)]
    def work(c):
        e = enrich(c)
        r = {"orig_title": c["title"], "orig_artist": c["artist"], **e}
        with _lock:
            pf.write(json.dumps(r, ensure_ascii=False) + "\n")
            pf.flush()
            done[0] += 1
            if done[0] % 100 == 0:
                print("progress %d/%d" % (done[0], len(todo)), flush=True)
        return r
    with ThreadPoolExecutor(max_workers=3) as ex:
        new_results = list(ex.map(work, todo2))
    pf.close()
    res_by_key = {}
    for r in list(done_map.values()) + new_results:
        res_by_key[(norm(r["orig_title"]), norm(artist_core(r["orig_artist"])))] = r
    results = [res_by_key[(norm(c["title"]), norm(artist_core(c["artist"])))] for c in todo]
    songs, report = [], {"A": 0, "B": 0, "C": 0, "excluded": len(excluded), "corrections": []}
    for i, r in enumerate(results, 1):
        report[r["tier"]] += 1
        if r["tier"] == "A" and (r["title"] != r["orig_title"] or r["artist"] != r["orig_artist"]):
            report["corrections"].append({"from": [r["orig_title"], r["orig_artist"]], "to": [r["title"], r["artist"]]})
        songs.append({
            "id": "w%03d" % i, "title": r["title"], "artist": r["artist"],
            "genre": r["genre"] or "その他", "keyLabel": "原曲キー", "keyShift": 0,
            "memo": "", "jacket": r["jacket"], "addedAt": ADDED_AT,
        })
    json.dump(songs, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"excluded_titles": sorted({c["title"] for c in excluded}), **report},
              open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("DONE new=%d A=%d B=%d C=%d jackets=%d" % (
        len(songs), report["A"], report["B"], report["C"], sum(1 for s in songs if s["jacket"])), flush=True)

if __name__ == "__main__":
    main()
