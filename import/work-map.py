# -*- coding: utf-8 -*-
"""作品名を (曲名, アーティスト) のペア完全一致でだけ設定する。--apply で適用。
WORK_MAP の各行は「その曲がその作品の主題歌/挿入歌/キャラソン」であることが
確実なものだけ。ペアが現在のデータと一致しない行は単に適用されない。
"""
import json, sys, importlib.util

spec = importlib.util.spec_from_file_location('we', 'import/walkman-enrich.py')
we = importlib.util.module_from_spec(spec); spec.loader.exec_module(we)
norm, artist_core = we.norm, we.artist_core

W = "化物語"
WORK_MAP = [
 # 化物語
 ("君の知らない物語", "super sell", W),
 ("staple stable", "戦場ヶ原ひたぎ(斎藤千和)", W),
 ("sugar sweet nightmare", "羽川翼", W),
 ("ambivalent world", "神原駿河", W),
 # けいおん！
 ("ふでペン ～ボールペン～", "放課後ティータイム", "けいおん！"),
 ("GO!GO!MANIAC", "放課後ティータイム", "けいおん！"),
 ("NO, Thank You!", "放課後ティータイム", "けいおん！"),
 ("Utauyo!!MIRACLE", "放課後ティータイム", "けいおん！"),
 ("Don't say lazy", "放課後ティータイム", "けいおん！"),
 ("Diaryはフォルテシモ", "琴吹紬(寿美菜子)", "けいおん！"),
 ("Lovely Sister LOVE", "平沢憂(米澤円)", "けいおん！"),
 ("ギー太に首ったけ", "平沢唯(CV:豊崎愛生)", "けいおん！"),
 ("Dear My Keys ~鍵盤の魔法~", "琴吹紬(CV:寿美菜子)", "けいおん！"),
 ("Humming Bird", "琴吹紬(CV:寿美菜子)", "けいおん！"),
 # 涼宮ハルヒの憂鬱
 ("ハレ晴レユカイ", "涼宮ハルヒ(CV.平野綾)、長門有希(CV.茅原実里)、朝比奈みくる(CV.後藤邑子)", "涼宮ハルヒの憂鬱"),
 ("God knows...", "涼宮ハルヒ(CV.平野綾)", "涼宮ハルヒの憂鬱"),
 ("Super Driver", "涼宮ハルヒ", "涼宮ハルヒの憂鬱"),
 # らき☆すた
 ("もってけ!セーラーふく", "泉こなた (CV.平野 綾), 柊かがみ (CV.加藤英美里), 柊つかさ (CV.福原香織) & 高良みゆき (CV.遠藤 綾)", "らき☆すた"),
 ("スケッチスイッチ", "石田燿子", "ひだまりスケッチ"),
 # 新世紀エヴァンゲリオン
 ("残酷な天使のテーゼ", "高橋洋子", "新世紀エヴァンゲリオン"),
 ("魂のルフラン", "高橋洋子", "新世紀エヴァンゲリオン"),
 ("心よ原始に戻れ", "高橋洋子", "新世紀エヴァンゲリオン"),
 ("集結の園へ", "林原めぐみ", "新世紀エヴァンゲリオン"),
 # Angel Beats!
 ("Alchemy", "Girls Dead Monster", "Angel Beats!"),
 ("Crow Song", "Girls Dead Monster", "Angel Beats!"),
 ("My Soul, Your Beats!", "Lia", "Angel Beats!"),
 ("小さなてのひら", "Lia", "CLANNAD"),
 # とあるシリーズ
 ("only my railgun", "fripSide", "とある科学の超電磁砲"),
 ("under the cry", "ステイル=マグヌス(谷山紀章)", "とある魔術の禁書目録"),
 ("Salvia farinacea", "神裂火織(伊藤静)", "とある魔術の禁書目録"),
 ("ゼロからの逆襲", "上条当麻(阿部 敦)", "とある魔術の禁書目録"),
 ("シリウス", "藍井エイル", "キルラキル"),
 ("masterpiece", "川田まみ", "とある魔術の禁書目録"),
 ("No buts!", "川田まみ", "とある魔術の禁書目録"),
 # プリキュア
 ("Let's go!スマイルプリキュア!", "池田彩", "スマイルプリキュア！"),
 ("イェイ!イェイ!イェイ!", "吉田仁美", "スイートプリキュア♪"),
 ("DANZEN!ふたりはプリキュア", "五條真由美", "ふたりはプリキュア"),
 ("Tomorrow Song ～あしたのうた～", "工藤真由", "スイートプリキュア♪"),
 # 戦隊・特撮
 ("爆竜戦隊アバレンジャー", "遠藤正明", "爆竜戦隊アバレンジャー"),
 ("特捜戦隊デカレンジャー", "サイキックラバー", "特捜戦隊デカレンジャー"),
 ("魔法戦隊マジレンジャー", "岩崎貴文", "魔法戦隊マジレンジャー"),
 ("恐竜戦隊ジュウレンジャー", "佐藤健太", "恐竜戦隊ジュウレンジャー"),
 ("ウルトラマンマックス", "TEAM DASH with Project DMM", "ウルトラマンマックス"),
 ("本気戦隊ガチレンジャー", "遠藤正明", "天装戦隊ゴセイジャー"),
 ("牙狼～SAVIOR IN THE DARK～", "JAM Project", "牙狼〈GARO〉"),
 # ドラゴンボール
 ("CHA-LA HEAD-CHA-LA", "影山ヒロノブ", "ドラゴンボールZ"),
 ("MA-SPER HEAD-CHA-LA", "やまだん", "ドラゴンボールZ"),
 # その他アニメ主題歌・挿入歌
 ("動く、動く", "チト(CV:水瀬いのり)、ユーリ(CV:久保ユリカ)", "少女終末旅行"),
 ("お願いマッスル", "紗倉ひびき(CV:ファイルーズあい)、街雄鳴造(CV:石川界人)", "ダンベル何キロ持てる？"),
 ("革命デュアリズム", "水樹奈々×T.M.Revolution", "革命機ヴァルヴレイヴ"),
 ("カサブタ", "千綿ヒデノリ", "金色のガッシュベル"),
 ("THE HERO !! ～怒れる拳に火をつけろ～", "JAM Project", "ワンパンマン"),
 ("Shangri-La", "angela", "蒼穹のファフナー"),
 ("すーぱー☆あふぇくしょん", "栗林みな実、橋本みゆき、飛蘭、美郷あき、yozuca*、rino", "カーニバル・ファンタズム"),
 ("全力バタンキュー", "A応P", "おそ松さん"),
 ("はなまるぴっぴはよいこだけ", "A応P", "おそ松さん"),
 ("ひぐらしのなく頃に", "島みやえい子", "ひぐらしのなく頃に"),
 ("奈落の花", "島みやえい子", "ひぐらしのなく頃に解"),
 ("BLAZE", "キンヤ", "ツバサ・クロニクル"),
 ("ループ", "坂本真綾", "ツバサ・クロニクル"),
 ("ふ・れ・ん・ど・し・た・い", "学園生活部", "がっこうぐらし！"),
 ("Ring My Bell", "blue drops(吉田仁美&イカロス(早見沙織))", "そらのおとしもの"),
 ("fallen down", "イカロス", "そらのおとしもの"),
 ("最高速 Fall in Love", "ミーア(CV:雨宮天) パピ(CV:小澤亜李) セントレア(CV:相川奈都姫) スー(CV:野村真悠華) メロ(CV:山崎はるか) ラクネラ(CV:中村桜)", "モンスター娘のいる日常"),
 ("アイのシナリオ", "CHiCO with HoneyWorks", "まじっく快斗1412"),
 ("リフレインボーイ", "ALL OFF", "ヘヴィーオブジェクト"),
 ("Catch You Catch Me", "GUMI", "カードキャプターさくら"),
 ("ナイショの話", "ClariS", "偽物語"),
 ("オリオンをなぞる", "UNISON SQUARE GARDEN", "TIGER & BUNNY"),
 ("創聖のアクエリオン", "ヒャダイン", "創聖のアクエリオン"),
 ("紅蓮の弓矢", "Linked Horizon", "進撃の巨人"),
 ("Snow halation", "μ's", "ラブライブ！"),
 ("ようこそジャパリパークへ", "どうぶつビスケッツ&PPP", "けものフレンズ"),
 ("けものパレード ～ジャパリパークメモリアル～", "どうぶつビスケッツ + かばん x PPP", "けものフレンズ"),
 ("大空ドリーマー", "PPP", "けものフレンズ"),
 ("マジLOVE1000%", "ST☆RISH", "うたの☆プリンスさまっ♪"),
 ("マジLOVE2000%", "ST☆RISH", "うたの☆プリンスさまっ♪"),
 ("マジLOVEレボリューションズ", "ST☆RISH", "うたの☆プリンスさまっ♪"),
 ("KUMAMIKO DANCING (feat. 熊出村のみなさん)", "雨宿まち(CV:日岡なつみ)&ナツ(CV:安元洋貴) feat.熊出村のみなさん", "くまみこ"),
 ("私がモテないのはどう考えてもお前らが悪い!", "鈴木このみ＆キバオブアキバ", "私がモテないのはどう考えてもお前らが悪い！"),
 ("どう考えても私は悪くない", "黒木智子(CV:橘田いずみ)", "私がモテないのはどう考えてもお前らが悪い！"),
 ("君じゃなきゃダメみたい", "オーイシマサヨシ", "月刊少女野崎くん"),
 ("撲殺天使ドクロちゃん", "ドクロちゃん", "撲殺天使ドクロちゃん"),
 ("撲殺天使ドクロちゃん2007", "ドクロちゃん(CV:千葉紗子)", "撲殺天使ドクロちゃん"),
 ("オトメロディー (TVサイズ)", "クロミ (竹内順子)", "おねがいマイメロディ"),
 ("ひそやかな欲望 ～ミサカは、発生させます～", "御坂妹(ささきのぞみ)", "とある科学の超電磁砲"),
 ("SKILL", "JAM Project", "第2次スーパーロボット大戦α"),
 ("MOTHER3 ～愛のテーマ～", "酒井省吾", "MOTHER3"),
 # ジブリ・映画
 ("もののけ姫", "Lorenzo Carrera&Erik Castello&Yoko Hallelujah", "もののけ姫"),
 ("さんぽ", "Lorenzo Carrera&Erik Castello&Yoko Hallelujah", "となりのトトロ"),
 ("崖の上のポニョ", "パオロ・コラヴォルベ&Yoko Hallelujah", "崖の上のポニョ"),
 ("カントリー・ロード", "エットレ･リゴッティ&Sophia Aslanidou", "耳をすませば"),
 ("いつも何度でも", "クラウディオ･ラヴィナール&Sophia Aslanidou", "千と千尋の神隠し"),
]

APPLY = "--apply" in sys.argv
songs = json.load(open("songs.json", encoding="utf-8"))
by_pair = {}
for s in songs:
    by_pair.setdefault((norm(s["title"]), norm(artist_core(s["artist"]))), []).append(s)

applied, missed = [], []
for title, artist, work in WORK_MAP:
    hits = by_pair.get((norm(title), norm(artist_core(artist))), [])
    if len(hits) == 1:
        s = hits[0]
        if s.get("work") != work:
            applied.append({"id": s["id"], "title": s["title"], "artist": s["artist"], "work": work})
            s["work"] = work
    else:
        missed.append({"title": title, "artist": artist, "work": work, "hits": len(hits)})

print("applied:", len(applied), "/ map entries:", len(WORK_MAP), "/ missed:", len(missed))
for m in missed:
    print("MISS:", m["title"], "|", m["artist"], "->", m["work"], "(hits=%d)" % m["hits"])
json.dump({"applied": applied, "missed": missed},
          open("import/work-map-report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
if APPLY:
    json.dump(songs, open("songs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open("songs.json", "a", encoding="utf-8").write("\n")
    print("APPLIED")
else:
    print("DRY RUN (not applied)")
