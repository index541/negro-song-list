#!/usr/bin/env python3
# うたスキ「マイうた」取り込み: raw TSV -> songs.json (iTunes/Deezerでジャケット+ジャンル自動付与)
import json, re, sys, time, urllib.parse, urllib.request

RAW = "import/myuta-raw.txt"
OUT = "songs.json"
REPORT = "import/enrich-report.json"
ADDED_AT = "2026-11-12"

GENRE_MAP = {
    "J-Pop": "J-POP", "Pop": "J-POP", "Anime": "アニソン", "Rock": "ロック",
    "Alternative": "ロック", "Vocaloid": "ボカロ", "Soundtrack": "アニソン",
    "Rock / Metal": "ロック", "Metal": "ロック", "Dance": "ダンス",
}
VOCALOID_HINTS = ["初音ミク", "鏡音リン", "鏡音レン", "GUMI", "KAITO", "巡音ルカ", "MEIKO", "IA", "v flower"]

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (song-list import)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)

def norm(s):
    s = (s or "").lower()
    s = re.sub(r"《[^》]*》|〈[^〉]*〉", "", s)
    s = re.sub(r"[\s\-_・/\\|()\[\]{}'\".,!?☆★×:;]+", "", s)
    return s

def clean_title(t):
    return re.sub(r"《[^》]*》|〈[^〉]*〉", "", t).strip()

def artist_core(a):
    a = re.split(r"\s+feat\.?|\s+Feat\.?|\(", a)[0]
    a = a.split("[")[0].split("/")[0]
    return a.strip()

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

cache = {}

def enrich(title, artist):
    key = (norm(clean_title(title)), norm(artist_core(artist)))
    if key in cache:
        return cache[key]
    want = norm(clean_title(title))
    core = artist_core(artist)
    result = {"jacket": "", "genre": "", "source": ""}
    # iTunes first
    try:
        q = urllib.parse.urlencode({"term": clean_title(title) + " " + core, "country": "JP",
                                    "media": "music", "entity": "song", "limit": 8, "lang": "ja_jp"})
        d = get_json("https://itunes.apple.com/search?" + q)
        best, best_score = None, 0
        for r in d.get("results", []):
            sc = title_score(want, r.get("trackName", ""))
            if sc > best_score:
                best, best_score = r, sc
        if best and best_score >= 60 and best.get("artworkUrl100"):
            result["jacket"] = best["artworkUrl100"].replace("100x100bb.jpg", "600x600bb.jpg")
            g = best.get("primaryGenreName", "")
            result["genre"] = GENRE_MAP.get(g, g)
            result["source"] = "itunes"
    except Exception as e:
        print("itunes err:", title, e, file=sys.stderr)
    time.sleep(0.2)
    if not result["jacket"]:
        try:
            q = urllib.parse.urlencode({"q": clean_title(title) + " " + core, "limit": 8})
            d = get_json("https://api.deezer.com/search?" + q)
            best, best_score = None, 0
            for r in d.get("data", []):
                t = r.get("title", "")
                if "カラオケ" in t or "Key(" in t:
                    continue
                sc = title_score(want, t)
                if sc > best_score:
                    best, best_score = r, sc
            if best and best_score >= 60:
                alb = best.get("album", {})
                result["jacket"] = alb.get("cover_xl") or alb.get("cover_big") or alb.get("cover_medium", "")
                result["source"] = "deezer"
                try:
                    ad = get_json("https://api.deezer.com/album/" + str(alb.get("id")))
                    gs = (ad.get("genres") or {}).get("data") or []
                    if gs:
                        g = gs[0].get("name", "")
                        result["genre"] = GENRE_MAP.get(g, g)
                except Exception:
                    pass
        except Exception as e:
            print("deezer err:", title, e, file=sys.stderr)
        time.sleep(0.2)
    if not result["genre"]:
        hay = title + " " + artist
        if any(h in hay for h in VOCALOID_HINTS):
            result["genre"] = "ボカロ"
        elif "《アニメカラオケ》" in title:
            result["genre"] = "アニソン"
        else:
            result["genre"] = "その他"
    cache[key] = result
    return result

def key_label(shift):
    if shift == 0:
        return "原曲キー"
    if shift > 0:
        return "原曲 +%d" % shift
    return "原曲 −%d" % abs(shift)

def main():
    songs, report = [], []
    lines = [ln.rstrip("\n") for ln in open(RAW, encoding="utf-8") if ln.strip()]
    assert len(lines) == 200, len(lines)
    for i, ln in enumerate(lines, 1):
        head, keyval = ln.rsplit(" / キー:", 1)
        title, artist = head.split(" / ", 1)
        shift = int(keyval.replace("±", ""))
        en = enrich(title, artist)
        songs.append({
            "id": "u%03d" % i, "title": title, "artist": artist, "genre": en["genre"],
            "keyLabel": key_label(shift), "keyShift": shift, "memo": "",
            "jacket": en["jacket"], "addedAt": ADDED_AT,
        })
        report.append({"title": title, "artist": artist, "source": en["source"], "genre": en["genre"], "jacket": bool(en["jacket"])})
        if i % 25 == 0:
            print("progress %d/200" % i, flush=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(songs, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    nj = sum(1 for r in report if r["jacket"])
    print("DONE songs=%d jackets=%d" % (len(songs), nj))

if __name__ == "__main__":
    main()
