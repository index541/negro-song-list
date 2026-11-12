# -*- coding: utf-8 -*-
"""タイトル頭の番号(00-等)を外し、歌い手名義の曲をカタログ照合で元アーティスト名に直す。
使い方: python3 import/fix-artists.py [--apply]  (無指定はドライランでレポートだけ出す)
"""
import json, re, sys, importlib.util
from concurrent.futures import ThreadPoolExecutor

spec = importlib.util.spec_from_file_location('we', 'import/walkman-enrich.py')
we = importlib.util.module_from_spec(spec); spec.loader.exec_module(we)
norm, title_score = we.norm, we.title_score
itunes_search, deezer_search, pick_best = we.itunes_search, we.deezer_search, we.pick_best

APPLY = "--apply" in sys.argv
songs = json.load(open("songs.json", encoding="utf-8"))
report = {"prefix_fixed": [], "artist_changed": [], "unmatched": [], "merged": []}

# --- 1) タイトル頭の番号を外す ---
PRE = re.compile(r"^\s*[0-9０-９]{2,4}\s*[-_]\s*")
for s in songs:
    m = PRE.match(s["title"])
    if m:
        rest = s["title"][m.end():].strip()
        if rest and not re.fullmatch(r"[\d\-_ .]+", rest):
            report["prefix_fixed"].append({"id": s["id"], "from": s["title"], "to": rest})
            s["title"] = rest

# --- 2) 歌い手名義の判定 ---
TOKENS = set("""鋼兵 ネグロ Vin Gero ヤマイ 赤ティン りぶ うさ ろん 96猫 まふまふ そらる ぐるたみん
あるふぁきゅん。 天月-あまつき- ウォルピスカーター ウォルピス・カーター 少年T 少年Ｔ ヲタみん 湯毛
vip店長 kradness SymaG ASK nero ぽこた 花たん ピコ 赤飯 あさまる ぱなまん ルシュカ リツカ
こばたん ふくめん 大根 iciko recog よっぺい ちせちゃん 弟の姉 ばずぱんだ ななひら みゆはん
秋赤音 teksy YACA こいろ みゐや めありー 栗プリン 針鼠 Ｋ太 ｙｔｒ ふさ バルシェ タイ焼き屋
taiga KOOL やまだん ゴー☆ジャス 茶茶子 YAMA-B 電池切れ スケベ 初心者F neko ナノ DEATH姫
ホリゾン パナップォ 犬ロック ｙｔｍｎ roro よるきち 足首 くるみ餅 みき""".split())
JUNK = {"アーティスト名なし", "？", "?", "", "不明"}

def is_target(artist):
    a = (artist or "").strip()
    if a in JUNK:
        return True
    parts = re.split(r"[&＆×、,・]", a)
    return any(p.strip() in TOKENS for p in parts)

EXTRA_BLOCK = {"伊東歌詞太郎", "浦島坂田船", "ナノ", "I LOVE BGM LAB", "Kaive Noir",
"島爺", "鹿乃", "りょーくん", "しゅーず", "ダズビー", "相宮零", "流田Project", "H△G",
"Dancing Dolls", "Will Stetson", "いかさん", "Ado", "和楽器バンド", "No title",
"めいちゃん", "松下", "majiko", "ななもり。"}
PAIR_DENY = {("Afterglow", "ぱなまん"), ("声", "Vin"), ("girlfriend", "Vin"), ("COLOR", "Vin"), ("想イ出カケラ", "Vin"),
("cloud", "Vin"), ("Blind", "Vin"), ("Blue", "Vin"), ("Despair", "Vin"), ("magenta", "Vin"),
("Track", "Vin"), ("Track", "ネグロ"), ("蓮", "Vin"), ("cry", "Vin&neko"), ("DIARRHEA", "Vin&DEATH姫"),
("Holography", "Vin"), ("Sky High", "iciko"), ("L'azur", "iciko"), ("RAINBOW GIRL", "Gero&ろん"),
("HALO", "Gero"), ("Ib", "96猫"), ("Dear", "うさ"), ("Wish", "うさ"), ("Alice", "ばずぱんだ&スケベ"),
("girlfriend", "ばずぱんだ"), ("ハッピーエンドグレーテル", "大根"), ("食事", "赤飯"), ("ニート", "弟の姉"),
("再生", "鋼兵"), ("アルビノ", "鋼兵"), ("自己嫌悪", "鋼兵"), ("孤独の果て", "鋼兵"), ("UNBALANCE", "鋼兵"),
("恋愛勇者", "鋼兵"), ("空中庭園", "ネグロ"), ("キラリ2", "ネグロ"), ("sweet So sweet", "ネグロ"),
("ハッ", "ネグロ"), ("踊る恐竜さん", "ネグロ"), ("初音ミクの暴走", "vip店長"), ("Sorry", "ヤマイ"),
("trick art !", "Vin&初心者F"), ("Cosmos Adventure", "アーティスト名なし"), ("カラス", "アーティスト名なし"),
("目覚まし", "アーティスト名なし"), ("暴風", "アーティスト名なし"), ("アサガオの散る頃に", "めありー"),
("うたうたいのうた", "りぶ"), ("ダヴィンチの告白", "りぶ"), ("WAVE", "鋼兵"), ("前前前世", "ネグロ"),
("rain stops, good-bye", "ばずぱんだ"), ("rain stops, good-bye", "ヤマイ"), ("ぼくのフレンド", "みゆはん"),
("メリーメリー", "あさまる"), ("デリヘル呼んだら君が来た", "鋼兵"), ("La, La, Love You", "少年T"),
("世界の真ん中", "天月-あまつき-"), ("蜜蜂", "よっぺい")}

def artist_blocked(a):
    a = (a or "").strip()
    if a in EXTRA_BLOCK:
        return True
    if "melost" in a or "__" in a:
        return True
    parts = re.split(r"[&＆×、,・/]", re.split(r" feat", a)[0])
    return any(p.strip() in TOKENS for p in parts)

MANUAL = {
"千本桜": "黒うさP", "六兆年と一夜物語": "kemu", "夜咄ディセイブ": "じん", "神のまにまに": "れるりり",
"オツキミリサイタル": "じん", "メランコリック": "Junky", "チルドレンレコード": "じん",
"ブリキノダンス": "日向電工", "ハロ／ハワユ": "ナノウ", "小夜子": "みきとP", "Starduster": "ジミーサムP",
"from Y to Y": "ジミーサムP", "From Y to Y": "ジミーサムP", "Hello, Worker": "KEI", "心拍数♯0822": "蝶々P",
"天ノ弱": "164", "カミサマネジマキ": "kemu", "地球最後の告白を": "kemu", "リンカーネイション": "kemu",
"ヒバナ": "DECO*27", "砂の惑星": "ハチ", "SPiCa": "とくP", "メルト": "ryo (supercell)",
"ワールドイズマイン": "ryo (supercell)", "ブラック★ロックシューター": "ryo (supercell)",
"恋は戦争": "ryo (supercell)", "ローリンガール": "wowaka", "前前前世": "RADWIMPS",
"Butter-Fly": "和田光司", "命のユースティティア": "Neru", "オリオンをなぞる": "UNISON SQUARE GARDEN",
"回る空うさぎ": "Orangestar", "吉原ラメント": "亜沙", "セツナトリップ": "Last Note.",
"桜ノ雨": "halyosy", "VOiCE": "ラヴリーP", "一触即発☆禅ガール": "相対性理論",
"人柱アリス": "ゆがみP", "炉心融解": "iroha(sasaki)", "ジャガーノート": "ナナホシ管弦楽団",
"ピエロ": "KEI", "想像フォレスト": "じん", "サリシノハラ": "みきとP", "ストリーミングハート": "DECO*27",
"アンハッピーリフレイン": "wowaka", "メグメグ★ファイアーエンドレスナイト": "samfree",
"リリリリ★バーニングナイト": "samfree", "人生リセットボタン": "kemu", "インビジブル": "kemu",
"Smiling": "halyosy",
}

def find_original(title):
    """カタログで曲名強一致を探し、歌い手名義でない最初の候補の (artist, jacket) を返す。"""
    wn = norm(title)
    cands = []
    for r in itunes_search(title):
        sc = title_score(wn, r.get("trackName", ""))
        if sc >= 80 and "カラオケ" not in r.get("trackName", ""):
            cands.append((sc, (r.get("artistName") or "").strip(),
                          (r.get("artworkUrl100") or "").replace("100x100", "600x600")))
    for r in deezer_search(title):
        sc = title_score(wn, r.get("title", ""))
        if sc >= 80 and "カラオケ" not in r.get("title", ""):
            cands.append((sc, ((r.get("artist") or {}).get("name") or "").strip(),
                          ((r.get("album") or {}).get("cover_xl") or "")))
    cands.sort(key=lambda x: -x[0])
    for sc, art, jk in cands:
        if art and not artist_blocked(art):
            return art, jk
    return None

targets = [s for s in songs if s["id"].startswith("w") and is_target(s["artist"])]
print("targets:", len(targets), flush=True)

def work(s):
    if s["title"] in MANUAL:
        return s, (MANUAL[s["title"]], "")
    if (s["title"], s["artist"]) in PAIR_DENY:
        return s, None
    got = find_original(s["title"])
    return s, got

done = [0]
with ThreadPoolExecutor(max_workers=3) as ex:
    for s, got in ex.map(work, targets):
        done[0] += 1
        if done[0] % 100 == 0:
            print("progress %d/%d" % (done[0], len(targets)), flush=True)
        if got:
            new_artist, jk = got
            if norm(new_artist) != norm(s["artist"]):
                report["artist_changed"].append({"id": s["id"], "title": s["title"],
                                                 "from": s["artist"], "to": new_artist})
                s["artist"] = new_artist
                if not s["jacket"] and jk:
                    s["jacket"] = jk
        else:
            report["unmatched"].append({"id": s["id"], "title": s["title"], "artist": s["artist"]})

# --- 3) 重複の統合 (title, artist) ---
def key_of(s):
    return (norm(s["title"]), norm(we.artist_core(s["artist"])))
groups = {}
for s in songs:
    groups.setdefault(key_of(s), []).append(s)
out, seen = [], set()
for s in songs:
    k = key_of(s)
    if k in seen:
        continue
    seen.add(k)
    dups = groups[k]
    if len(dups) > 1:
        def rank(x):
            return (0 if not x["id"].startswith("w") else 1, 0 if x["jacket"] else 1, x["id"])
        best = sorted(dups, key=rank)[0]
        for d in dups:
            if d is not best:
                report["merged"].append({"kept": best["id"], "dropped": d["id"],
                                          "title": best["title"], "artist": best["artist"]})
                if not best.get("memo") and d.get("memo"):
                    best["memo"] = d["memo"]
                if best.get("memory") is None and d.get("memory") is not None:
                    best["memory"] = d["memory"]
        out.append(best)
    else:
        out.append(s)

print("prefix_fixed:", len(report["prefix_fixed"]))
print("artist_changed:", len(report["artist_changed"]))
print("unmatched(kept):", len(report["unmatched"]))
print("merged:", len(report["merged"]))
print("total: %d -> %d" % (len(songs), len(out)))
json.dump(report, open("import/fix-artists-report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
if APPLY:
    json.dump(out, open("songs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open("songs.json", "a", encoding="utf-8").write("\n")
    print("APPLIED")
else:
    print("DRY RUN (not applied)")
