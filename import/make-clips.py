# -*- coding: utf-8 -*-
"""サビ登録 (ytLink) がある曲について、公式試聴 (preview) の有無にかかわらず
登録範囲の音源を切り出して audio/<id>.m4a に置き、songs.json に ytClip を付ける。
公開ページでは ytClip が公式試聴より優先されるため、登録した範囲が
キー変更付きでそのまま再生される。
使い方: python3 import/make-clips.py [--dry-run]
変更があった時だけ commit + push する。結果は標準出力に要約を出す。
"""
import json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SONGS = os.path.join(REPO, "songs.json")
AUDIO_DIR = os.path.join(REPO, "audio")
YTDLP_PKG = os.path.expanduser("~/workspace/tools/yt-dlp-pkg")
MAX_CLIP_SEC = 90  # 終了秒が無い/長すぎる場合の上限

def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args),
                          capture_output=True, text=True)

def clip_key(s):
    return "%s|%s|%s" % (s.get("ytLink", ""), s.get("ytStart") or 0, s.get("ytEnd") or 0)

def make_clip(s):
    start = int(s.get("ytStart") or 0)
    end = int(s.get("ytEnd") or 0)
    if end <= start:
        end = start + MAX_CLIP_SEC
    if end - start > MAX_CLIP_SEC:
        end = start + MAX_CLIP_SEC
    out = os.path.join(AUDIO_DIR, s["id"] + ".%(ext)s")
    env = dict(os.environ, PYTHONPATH=YTDLP_PKG)
    cmd = [sys.executable, "-m", "yt_dlp",
           "-f", "bestaudio[ext=m4a]/bestaudio",
           "--download-sections", "*%d-%d" % (start, end),
           "--force-keyframes-at-cuts",
           "-o", out, s["ytLink"]]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
    final = os.path.join(AUDIO_DIR, s["id"] + ".m4a")
    if r.returncode != 0 or not os.path.exists(final) or os.path.getsize(final) < 10000:
        tail = (r.stderr or r.stdout or "").strip().splitlines()
        return None, (tail[-1] if tail else "unknown error")
    return "audio/" + s["id"] + ".m4a", None

def main():
    dry = "--dry-run" in sys.argv
    git("pull", "-q", "origin", "main")
    songs = json.load(open(SONGS, encoding="utf-8"))
    os.makedirs(AUDIO_DIR, exist_ok=True)
    made, cleaned, failed = [], [], []
    referenced = set()
    for s in songs:
        target_file = os.path.join(AUDIO_DIR, s["id"] + ".m4a")
        needs = bool(s.get("ytLink"))
        if needs:
            referenced.add(s["id"] + ".m4a")
            if s.get("ytClip") and s.get("ytClipKey") == clip_key(s) and os.path.exists(target_file):
                continue
            if dry:
                made.append(s["title"] + " (dry-run)")
                continue
            path, err = make_clip(s)
            if path:
                s["ytClip"] = path
                s["ytClipKey"] = clip_key(s)
                made.append(s["title"])
            else:
                failed.append(s["title"] + ": " + str(err))
        else:
            if s.get("ytClip") or s.get("ytClipKey"):
                s.pop("ytClip", None)
                s.pop("ytClipKey", None)
                cleaned.append(s["title"])
    # 参照されていない clip ファイルを掃除
    for f in os.listdir(AUDIO_DIR):
        if f.endswith(".m4a") and f not in referenced:
            os.remove(os.path.join(AUDIO_DIR, f))
            cleaned.append("file:" + f)
    changed = bool(made or cleaned) and not dry
    if changed:
        with open(SONGS, "w", encoding="utf-8") as fh:
            json.dump(songs, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        git("add", "-A")
        msg = "試聴音源を用意: " + "、".join(made) if made else "試聴音源を整理"
        r = git("-c", "user.name=index541", "-c",
                "user.email=index541@users.noreply.github.com",
                "commit", "-q", "-m", msg)
        if r.returncode == 0:
            git("push", "-q", "origin", "main")
    print("made:", made)
    print("cleaned:", cleaned)
    print("failed:", failed)

if __name__ == "__main__":
    main()
