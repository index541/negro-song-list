# -*- coding: utf-8 -*-
"""現在の曲名・アーティストで公式試聴を全曲再照合する。
使い方: python3 import/recheck-previews.py [--apply]
- ytLink がある曲（堅斗が自分でYouTubeから設定した曲）は一切触らない。
- 照合できた場合: preview を正しいURLに付け替える（無ければ付ける）。
- 照合できなかった場合: 付いている preview は間違いとして外す。
照合ロジックは add-previews.py の find_preview をそのまま使う。
"""
import json, sys, importlib.util
from concurrent.futures import ThreadPoolExecutor

spec = importlib.util.spec_from_file_location('we', 'import/walkman-enrich.py')
we = importlib.util.module_from_spec(spec); spec.loader.exec_module(we)

# add-previews.py から BLOCK〜find_preview の定義部分だけを取り出して使う
src = open('import/add-previews.py', encoding='utf-8').read()
start = src.index('BLOCK = set')
end = src.index('todo = [s for s in songs')
ns = dict(we.__dict__)
exec(src[start:end], ns)
find_preview = ns['find_preview']

APPLY = '--apply' in sys.argv
songs = json.load(open('songs.json', encoding='utf-8'))
targets = [s for s in songs if not s.get('ytLink')]
print('targets:', len(targets), '| skipped (ytLink):', len(songs) - len(targets), flush=True)

changes = {'added': [], 'changed': [], 'removed': [], 'kept': 0}
done = [0]
def work(s):
    old = s.get('preview') or ''
    new = find_preview(s)
    done[0] += 1
    if done[0] % 100 == 0:
        print('progress %d/%d' % (done[0], len(targets)), flush=True)
    return (s, old, new)

with ThreadPoolExecutor(max_workers=3) as ex:
    results = list(ex.map(work, targets))

for s, old, new in results:
    if new and new != old:
        s['preview'] = new
        changes['added' if not old else 'changed'].append({'id': s['id'], 'title': s['title'], 'artist': s['artist'], 'old': old, 'new': new})
    elif not new and old:
        del s['preview']
        changes['removed'].append({'id': s['id'], 'title': s['title'], 'artist': s['artist'], 'old': old})
    else:
        changes['kept'] += 1

print('added:', len(changes['added']), '| changed:', len(changes['changed']), '| removed:', len(changes['removed']), '| kept:', changes['kept'])
json.dump(changes, open('import/preview-recheck-report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
if APPLY:
    json.dump(songs, open('songs.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    open('songs.json', 'a', encoding='utf-8').write('\n')
    print('APPLIED')
else:
    print('DRY RUN')
