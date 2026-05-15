# Mojiemoji 検証とサービス制約

サービスのハードリミットと、ディスパッチ後の検証ブロック。
SKILL.md からオンデマンドで読み込まれる(`mojiemoji-selector` から
スニペットを受け取った後 / 手書き URL を貼る前)。

## 15 字フレーズ上限

URL の `text` 部分(`/emoji/` と `?` の間)は **15 字** 上限、
URL エンコードされた `%0A`(1 文字としてカウント) を **含む**。
超過すると HTTP 400 が返り、ボディは
`too many characters (max 15)`、画像はレンダされない。

具体例:

| フレーズ(デコード後) | 字数 | ステータス |
|---|---|---|
| `5指標スキーマ` (7 字) | 7 | ✅ OK |
| `cluster5\nsub-A 起点` (エンコード `cluster5%0Asub-A%20起点`) | 16 (`%0A` 込み) | ✗ 400 |
| `レビュー歓迎` (5 字) | 5 | ✅ OK |
| `この長い宣伝文を一気に` (12 字) | 12 | ✅ OK |

欲しいフレーズが 15 字を超える場合:

- **inline**: 隣接する 2 スタンプに分割する(SKILL.md
  § Phrase-length & line-break rules を参照)
- **block**: 短いフレーズを選ぶ、または 2 行に分けて連続する 2 スタンプ
  にする(それぞれ自前の `![...](...)`)

## プリフライト検証

mojiemoji URL を本文に貼る前(特に新しいフレーズの場合)、HTTP 200 が
返ることを確認する:

```bash
curl -sI 'https://mojiemoji.jozo.beer/emoji/<encoded>?...' | head -2
```

200 = レンダ可能。400 = 15 字超過(または無効文字を含む) — 短縮して
リトライ。`mojiemoji-selector` サブエージェントもスニペットを返す前の
セルフチェックでこれを含めること。

## ディスパッチ後のスポットチェック(返却された全本文に実行)

スニペットを受け取ったら、**すべてのスニペットをスポットチェック**
(最初の 1 個だけではダメ — サブエージェントは最初は OK で個別スニペット
で滑ってきた履歴がある)。以下を返却ボディ全体に対して走らせ、目視では
判断しないこと:

```bash
# 1. ボディを grep 用に保存
SNIPPETS=/tmp/mojiemoji_snippets.txt
# (返却テーブル or 全本文をここに貼る)

# 2. 全 URL に background=transparent があるか
grep -oE 'mojiemoji[^"<)]+' "$SNIPPETS" | grep -v 'background=transparent' && echo "✗ MISSING transparent"

# 3. 全 URL に outline=darker (および outline_width=2) があるか
grep -oE 'mojiemoji[^"<)]+' "$SNIPPETS" | grep -v 'outline=darker' && echo "✗ MISSING outline=darker"
grep -F 'outline=ffffff' "$SNIPPETS" && echo "✗ FORBIDDEN outline=ffffff"

# 4. 禁止色 (Tailwind 600+ の red/orange/blue 等 — ダークモードでは絶対使わない)
grep -oE 'color=(dc2626|b91c1c|991b1b|c2410c|ca8a04|15803d|16a34a|0e7490|1d4ed8|2563eb|4338ca|7e22ce|be185d|000000|111827|1f2937)' "$SNIPPETS" && echo "✗ DARK COLOR — swap to 300–500 range"

# 5. animation は正準リスト内に限る (negative grep — それ以外をフラグ)。
#    値を URL/HTML の区切り文字 (`&`, `"`, `<`, `>`, `)`, space) まで
#    フルに抽出する。そうしないと予期しない文字を含むタイポ (例:
#    `animation=foo-bar`) が正準名のプレフィックスに無音で切り詰められて
#    通ってしまう。negative match では `-x` を使い、抽出された値全体が
#    正準名と一致することを要求する (プレフィックス一致は不可)。
#    正準名はアンダースコアを含む (tate_scroll, kage_kaiten 等)。
grep -oE 'animation=[^"<>&) ]+' "$SNIPPETS" | grep -vxE 'animation=(tate_scroll|yoko_scroll|ekken|tate_ekken|bane|gatagata|bure|chuuou_zoom|kirari|kira|tenmetsu|shuchusen|kaiten|neruneru|patapata|yurayura|mabataki|bakusan|norinori|mochimochi|mozaiku|poyoon|yatta|tatemoya|nami|yokomoya|zairu|zanzo|chirichiri|disco|psycho|kage_kaiten|kage_bokashi|kage_neon)' && echo "✗ INVALID animation"

# 6. bakusan は inline で使わない (`<img` 行は inline を示す)
grep -E '<img[^>]+animation=bakusan' "$SNIPPETS" && echo "✗ bakusan in inline"

# 7. inline: URL text 内に %0A は禁止
grep -E '<img[^>]+/emoji/[^"]*%0A' "$SNIPPETS" && echo "✗ INLINE %0A — split into 2 stamps"

# 8. フレーズ長 ≤15 字 (%0A 込み)。各フレーズをデコードして字数を数える。
python3 -c "
import re, urllib.parse, sys
content = open('$SNIPPETS').read()
for m in re.finditer(r'mojiemoji.jozo.beer/emoji/([^?]+)', content):
    decoded = urllib.parse.unquote(m.group(1))
    if len(decoded) > 15:
        print(f'✗ {len(decoded)} chars: {decoded}')
"

# 9. inline 内の Latin 文字も折り返し得る。\"web UI\" 系のフレーズは
#    分割されているべき — ステップ 8 で検証 (inline で Latin 5 字以上は
#    要疑い)。

# 10. body-class block スタンプ — PR / issue / リリース本文で
#     デフォルト禁止 (SKILL.md § Saturation Mode "Default mode = inline-only"
#     を参照)。
#     `![alt](https://mojiemoji.jozo.beer/...)` markdown 形式は block スタンプ。
#     ユーザーが今ターンで明示的に block 装飾を要求していない限り、
#     ヒット 0 行であるべき。
grep -E '^!\[[^]]*\]\(https://mojiemoji' "$SNIPPETS" && echo "✗ BLOCK STAMP — convert to inline <img> form"

# 11. ライブ URL チェック — 全スタンプが HTTP 200 を返すこと
#     (grep では見えない、漢字のエンコードミスや正準外のフレーズタイポを捕捉)。
grep -oE 'https://mojiemoji\.jozo\.beer/[^"<)]+' "$SNIPPETS" | while read u; do
  code=$(curl -sI -o /dev/null -w "%{http_code}" "$u")
  [ "$code" = "200" ] || echo "✗ HTTP $code: $u"
done

# 12. animation 多様性 — distinct 値 12 種以上、本文全体で同じ animation の
#     使用は 2 回以下。
#     歴史的な 8 種 / 3 回上限から更新: 正準 animation 33 種が
#     使える今、新基準は 12 種以上 distinct かつ反復 ≤2 回
#     (parameters.md § Spread animation choices wide を参照)。
#     これが捕える失敗モード: issue #166 (15 スタンプ全部 animation=bane)。
grep -oE 'animation=[a-z_]+' "$SNIPPETS" | sort | uniq -c | sort -rn > /tmp/_anim_count
awk '$1 > 2 { print "✗ animation overused (>2×): " $2 " (" $1 "×)" }' /tmp/_anim_count
distinct_anim=$(grep -oE 'animation=[a-z_]+' "$SNIPPETS" | sort -u | wc -l | tr -d ' ')
[ "$distinct_anim" -lt 12 ] && echo "✗ animation diversity: only $distinct_anim distinct (want ≥12 across body)"

# 13. color 多様性 — 本文全体で distinct な hex 値 4 種以上。
#     これが捕える失敗モード: issue #166 (15 スタンプ全部 color=60a5fa)。
distinct_color=$(grep -oE 'color=[0-9a-f]{6}' "$SNIPPETS" | sort -u | wc -l | tr -d ' ')
[ "$distinct_color" -lt 4 ] && echo "✗ color diversity: only $distinct_color distinct (want ≥4 across body)"

# 14. スタンプ禁止な識別子 (API 名、英単語の判定語、コード形状トークン)。
#     これが捕える失敗モード: issue #166 (`Promise.all` と `Green` が
#     スタンプとしてレンダされていた)。
python3 -c "
import re, urllib.parse
content = open('$SNIPPETS').read()
BAD = {'Promise.all','Promise','useState','useEffect','Map','Map.from','Vec::new',
       'Result','Option','Iterator::find','null','undefined','OK','NG','Yes','No',
       'True','False','Green','Red','Blue','Success','Error'}
for m in re.finditer(r'mojiemoji\.jozo\.beer/emoji/([^?]+)', content):
    text = urllib.parse.unquote(m.group(1)).split('%0A')[0]
    if text in BAD:
        print(f'✗ identifier stamp (forbidden term): {text}')
    elif re.match(r'^[A-Za-z][A-Za-z0-9._-]+\$', text):
        print(f'✗ identifier-shaped stamp (English/code): {text}')
    elif re.match(r'^[#v]\d', text):
        print(f'✗ issue/version-shaped stamp: {text}')
"

# 15. 回転アニメ (rotational) は speed=slow|step が必須。
#     これが捕える失敗モード: selector が `kaiten` / `kage_kaiten` を
#     speed なし (= デフォルト normal) で出力 — 文字が高速回転して可読性ゼロ。
#     直近 3 dispatch で 2 件発生 (PR #33 禁止 stamp、issue #34 検出 stamp、
#     issue #37 反復 stamp)。
python3 -c "
import re
content = open('$SNIPPETS').read()
for m in re.finditer(r'mojiemoji\.jozo\.beer/[^\"<)]+', content):
    url = m.group(0)
    anim_m = re.search(r'animation=(kaiten|kage_kaiten)', url)
    if not anim_m:
        continue
    speed_m = re.search(r'speed=(\w+)', url)
    speed = speed_m.group(1) if speed_m else ''
    if speed not in ('slow', 'step'):
        print(f'✗ rotational without speed=slow|step: {url[:120]}')
"

# 16. 3 漢字熟語の単独スタンプ禁止 — `2+1` で分割すべき。
#     SKILL.md § Stamp target selection が「漢字 1 スタンプあたり 2 字」を
#     要求しているが、selector が `致命傷` / `具体策` / `緊急時` のような
#     3 漢字熟語を 1 スタンプに突っ込む失敗が反復している。
python3 -c "
import re, urllib.parse
content = open('$SNIPPETS').read()
KANJI = re.compile(r'^[一-鿿]+\$')
for m in re.finditer(r'mojiemoji\.jozo\.beer/emoji/([^?]+)', content):
    text = urllib.parse.unquote(m.group(1)).split('%0A')[0]
    if KANJI.match(text) and len(text) >= 3:
        print(f'✗ {len(text)}-kanji single stamp (must split 2+remainder): {text}')
"
```

どれかチェックに失敗したら、本文に貼る前にローカルで修正(または再
ディスパッチ)する。これらの問題を含んだまま本文を出してはダメ —
レンダされた PR でユーザーが気づき、繰り返しのリワークコストが
雪だるま式に積み上がる。
