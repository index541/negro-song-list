# -*- coding: utf-8 -*-
"""曲名表記とアーティスト名(原曲)を、iTunes+Deezer の二重照合が一致した時だけ直す。
使い方: python3 import/fix-meta.py [--apply]  (無指定はドライラン)
アーティスト採用条件: 曲名が norm 完全一致する候補のうち、両カタログに載る
アーティストがちょうど1組だけの時。現在のアーティストも両カタログに載る場合は
正規の別バージョンとみなして変更しない。試聴URLがある曲は、その試聴先の
アーティストと矛盾したら採用しない。
曲名表記: 最終アーティストに一致する候補の生タイトルが両カタログで同一の時だけ採用。
MANUAL (fix-artists.py の手検証マップ) も全曲に適用する (PAIR_DENY は除外)。
"""
import json, re, sys, importlib.util
from concurrent.futures import ThreadPoolExecutor
from collections import Counter, defaultdict

spec = importlib.util.spec_from_file_location('we', 'import/walkman-enrich.py')
we = importlib.util.module_from_spec(spec); spec.loader.exec_module(we)
norm, title_score = we.norm, we.title_score
artist_core, artist_overlap = we.artist_core, we.artist_overlap
itunes_search, deezer_search = we.itunes_search, we.deezer_search

src = open('import/fix-artists.py', encoding='utf-8').read()
seg = src[src.index('TOKENS'):src.index('def find_original')]
ns = {"re": re, "json": json, "sys": sys}
exec(seg, ns)
artist_blocked = ns['artist_blocked']
MANUAL = ns['MANUAL']
PAIR_DENY = ns['PAIR_DENY']

APPLY = "--apply" in sys.argv
FROM_REPORT = "--apply-from-report" in sys.argv
# レビューで却下した曲 (同名の別曲・カバーを両カタログが正規扱いしていたもの等)
VETO_IDS = {"u001", "u016", "u052", "u059", "u074", "u076", "w155", "w184", "w403",
            "w461", "w507", "w551", "w866", "w1019", "w1053", "w1149"}
songs = json.load(open("songs.json", encoding="utf-8"))

if FROM_REPORT:
    rep = json.load(open("import/fix-meta-report.json", encoding="utf-8"))
    by_id = {s["id"]: s for s in songs}
    n_a = n_t = 0
    for c in rep["artist_changed"] + rep["manual_applied"]:
        if c["id"] in VETO_IDS:
            continue
        s = by_id[c["id"]]
        assert s["artist"] == c["from"], (c["id"], s["artist"], c["from"])
        s["artist"] = c["to"]
        n_a += 1
    for c in rep["title_changed"]:
        if c["id"] in VETO_IDS:
            continue
        s = by_id[c["id"]]
        assert s["title"] == c["from"], (c["id"], s["title"], c["from"])
        s["title"] = c["to"]
        n_t += 1
    json.dump(songs, open("songs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open("songs.json", "a", encoding="utf-8").write("\n")
    print("APPLIED from report: artist %d, title %d (vetoed %d)" % (n_a, n_t, len(VETO_IDS)))
    sys.exit(0)
report = {"artist_changed": [], "title_changed": [], "manual_applied": [],
          "skipped_ambiguous": [], "skipped_preview_conflict": [], "skipped_collision": []}

def catalog_exact(title):
    wn = norm(title)
    ents = []
    for r in itunes_search(title):
        t = r.get("trackName", "")
        if title_score(wn, t) == 100 and "カラオケ" not in t:
            ents.append(("i", t, (r.get("artistName") or "").strip(), r.get("previewUrl", "")))
    for r in deezer_search(title):
        t = r.get("title", "")
        if title_score(wn, t) == 100 and "カラオケ" not in t:
            ents.append(("d", t, ((r.get("artist") or {}).get("name") or "").strip(), r.get("preview", "")))
    return ents

def decide(s):
    title, artist = s["title"], s["artist"]
    out = {"id": s["id"], "title": title, "from_artist": artist,
           "new_artist": None, "new_title": None, "note": ""}
    # MANUAL first (hand-verified in the earlier pass)
    if title in MANUAL and (title, artist) not in PAIR_DENY:
        want = MANUAL[title]
        if norm(artist_core(want)) != norm(artist_core(artist)):
            out["new_artist"] = want
            out["note"] = "manual"
            return out
    if (title, artist) in PAIR_DENY:
        return out
    if len(norm(title)) < 3:
        return out
    ents = catalog_exact(title)
    if not ents:
        return out
    by_core = defaultdict(Counter)
    raws = defaultdict(Counter)
    for src_, t, a, pv in ents:
        if not a or artist_blocked(a):
            continue
        c = norm(artist_core(a))
        by_core[c][src_] += 1
        raws[c][artist_core(a)] += 1
    both = {c: v for c, v in by_core.items() if v["i"] and v["d"]}
    cur = norm(artist_core(artist))
    final_artist = artist
    if len(both) == 1:
        win = next(iter(both))
        if win != cur:
            pv_cores = set()
            if s.get("preview"):
                for src_, t, a, pv in ents:
                    if pv and pv == s["preview"]:
                        pv_cores.add(norm(artist_core(a)))
            if pv_cores and win not in pv_cores:
                out["note"] = "preview_conflict"
                return out
            out["new_artist"] = raws[win].most_common(1)[0][0]
            out["note"] = "catalog i%d/d%d" % (both[win]["i"], both[win]["d"])
            final_artist = out["new_artist"]
    elif len(both) > 1 and cur not in both:
        out["note"] = "ambiguous"
        return out
    # title notation: raw titles of entries matching the final artist, same raw in both catalogs
    fi = {t for src_, t, a, pv in ents if src_ == "i" and norm(artist_core(a)) == norm(artist_core(final_artist))}
    fd = {t for src_, t, a, pv in ents if src_ == "d" and norm(artist_core(a)) == norm(artist_core(final_artist))}
    common = fi & fd
    if title in common:
        pass
    elif len(common) == 1:
        cand = next(iter(common))
        if cand != title:
            out["new_title"] = cand
    return out

done = [0]
results = {}
with ThreadPoolExecutor(max_workers=3) as ex:
    for s, out in zip(songs, ex.map(decide, songs)):
        results[s["id"]] = out
        done[0] += 1
        if done[0] % 150 == 0:
            print("progress %d/%d" % (done[0], len(songs)), flush=True)

# collision guard: applying changes must not create (title, artist) duplicates
def key_after(s):
    o = results[s["id"]]
    t = o["new_title"] or s["title"]
    a = o["new_artist"] or s["artist"]
    return (norm(t), norm(artist_core(a)))
seen = {}
for s in songs:
    k = key_after(s)
    if k in seen:
        o = results[s["id"]]
        if o["new_artist"] or o["new_title"]:
            report["skipped_collision"].append({"id": s["id"], "title": s["title"],
                                                "artist": s["artist"], "clashes_with": seen[k]})
            o["new_artist"] = None
            o["new_title"] = None
    else:
        seen[k] = s["id"]

for s in songs:
    o = results[s["id"]]
    if o["note"] == "ambiguous":
        report["skipped_ambiguous"].append({"id": s["id"], "title": s["title"], "artist": s["artist"]})
    elif o["note"] == "preview_conflict":
        report["skipped_preview_conflict"].append({"id": s["id"], "title": s["title"], "artist": s["artist"]})
    if o["new_artist"]:
        rec = {"id": s["id"], "title": o["new_title"] or s["title"],
               "from": s["artist"], "to": o["new_artist"], "via": o["note"]}
        (report["manual_applied"] if o["note"] == "manual" else report["artist_changed"]).append(rec)
        s["artist"] = o["new_artist"]
    if o["new_title"]:
        report["title_changed"].append({"id": s["id"], "artist": s["artist"],
                                        "from": s["title"], "to": o["new_title"]})
        s["title"] = o["new_title"]

print("artist_changed:", len(report["artist_changed"]))
print("manual_applied:", len(report["manual_applied"]))
print("title_changed:", len(report["title_changed"]))
print("skipped_ambiguous:", len(report["skipped_ambiguous"]))
print("skipped_preview_conflict:", len(report["skipped_preview_conflict"]))
print("skipped_collision:", len(report["skipped_collision"]))
json.dump(report, open("import/fix-meta-report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
if APPLY:
    json.dump(songs, open("songs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open("songs.json", "a", encoding="utf-8").write("\n")
    print("APPLIED")
else:
    print("DRY RUN (not applied)")
