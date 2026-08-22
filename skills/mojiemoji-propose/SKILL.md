---
name: mojiemoji-propose
description: >-
  Extract unstamped Japanese terms from prestamp output, ask the
  mojiemoji-selector agent for flavor choices, and record them in usage cache.
allowed-tools:
  - Bash(python3 skills/mojiemoji-github/scripts/prestamp.py*)
  - Bash(python3 */skills/mojiemoji-github/scripts/prestamp.py*)
  - Bash(python3 skills/mojiemoji-github/scripts/cache_record.py*)
  - Bash(python3 */skills/mojiemoji-github/scripts/cache_record.py*)
  - Read
  - Agent(mojiemoji-selector)
  - Agent(mojiemoji-github:mojiemoji-selector)
---

# Mojiemoji Propose

prestamp <img src="https://mojiemoji.jozo.beer/emoji/%E5%BE%8C?font=hachimaru&amp;color=f472b6&amp;animation=nami&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="後" height="24" align="absmiddle">の draft に残った未 stamp <img src="https://mojiemoji.jozo.beer/emoji/%E6%97%A5?font=tamanegi&amp;color=f87171&amp;animation=kage_neon&amp;background=transparent&amp;outline=26dc26&amp;outline_width=2" alt="日" height="24" align="absmiddle">本語語に対して、
`mojiemoji-selector` subagent に flavor を考案させて usage cache
に記録する。これにより `bump-catalog` の<img src="https://mojiemoji.jozo.beer/emoji/%E5%85%A5%E5%8A%9B?font=akzk&amp;color=f97316&amp;animation=nami&amp;background=transparent&amp;outline=16f973&amp;outline_width=2" alt="入力" height="24" align="absmiddle">が補充され、catalog が
自然に育つ。

## 起動条件

- ユーザーが `/mojiemoji-propose <path>` を叩いたとき
- ユーザーが「未 stamp 語を catalog に育てたい」「propose を回して」など
  明示的に要求したとき

## なぜ<img src="https://mojiemoji.jozo.beer/emoji/%E5%BF%85%E8%A6%81?font=gothic-bold&amp;color=60a5fa&amp;animation=zairu&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="必要" height="24" align="absmiddle">か

`prestamp.py` は<img src="https://mojiemoji.jozo.beer/emoji/%E6%B1%BA%E5%AE%9A?font=zero&amp;color=10b981&amp;animation=mozaiku&amp;background=transparent&amp;outline=8110b9&amp;outline_width=2" alt="決定" height="24" align="absmiddle">論的に catalog hit を `<img>` 化するため
selector 起<img src="https://mojiemoji.jozo.beer/emoji/%E5%8B%95%E6%A9%9F?font=toge&amp;color=34d399&amp;animation=kaiten&amp;speed=slow&amp;background=transparent&amp;outline=9934d3&amp;outline_width=2" alt="動機" height="24" align="absmiddle">会を奪う (#92)。`usage.jsonl` が空のまま<img src="https://mojiemoji.jozo.beer/emoji/%E6%94%BE%E7%BD%AE?font=pixel&amp;color=fb923c&amp;animation=mabataki&amp;background=transparent&amp;outline=0cea58&amp;outline_width=2" alt="放置" height="24" align="absmiddle">されると
`bump-catalog` (#46) が永久に発火せず catalog が育たない。この skill は
prestamp の隙間を埋め、selector を起動するための入口になる。

## <img src="https://mojiemoji.jozo.beer/emoji/%E6%89%8B%E9%A0%86?font=kurobara&amp;color=c084fc&amp;animation=kaiten&amp;speed=slow&amp;background=transparent&amp;outline=fcc084&amp;outline_width=2" alt="手順" height="24" align="absmiddle">

### 1. draft を prestamp + report 取得

```bash
DRAFT="<path>"
REPORT="$(mktemp /tmp/propose-XXXXXX.json)"
python3 "${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/scripts/prestamp.py" \
  --report-unstamped < "$DRAFT" > "$REPORT"
```

`unstamped` 配列が空なら「育成候補なし」を<img src="https://mojiemoji.jozo.beer/emoji/%E5%A0%B1%E5%91%8A?font=hachimaru&amp;color=60a5fa&amp;animation=yoko_scroll&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="報告" height="24" align="absmiddle">して<img src="https://mojiemoji.jozo.beer/emoji/%E7%B5%82%E4%BA%86?font=tamanegi&amp;color=ec4899&amp;animation=bane&amp;background=transparent&amp;outline=99ec48&amp;outline_width=2" alt="終了" height="24" align="absmiddle">。

### 2. <img src="https://mojiemoji.jozo.beer/emoji/%E4%B8%8A%E4%BD%8D?font=kurobara&amp;color=facc15&amp;animation=norinori&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="上位" height="24" align="absmiddle"> N 件を抽出

`--top` 引数があればその件数、無ければ最大 5 件まで。出現頻度 (count) の
高い順から処理。

```bash
N="${TOP:-5}"
python3 -c "
import json, sys
data = json.load(open('$REPORT'))
for entry in data['unstamped'][:$N]:
    print(entry['term'])
"
```

### 3. 各候補に selector を起動

候補 1 件ごとに `mojiemoji-selector` subagent を呼ぶ。selector は
flavor を選定し、契約通り `cache_record.py` に書き込む (selector の
標準<img src="https://mojiemoji.jozo.beer/emoji/%E5%8B%95%E4%BD%9C?font=gothic-bold&amp;color=60a5fa&amp;animation=psycho&amp;background=transparent&amp;outline_width=0" alt="動作" height="24" align="absmiddle">)。

Input contract に従って:

- フレーズ: 抽出した term
- mode: `inline` (catalog 育成用の標準形式)
- context: `report.unstamped[i].contexts[0]` (selector に文脈を<img src="https://mojiemoji.jozo.beer/emoji/%E6%8F%90%E4%BE%9B?font=dela&amp;color=ef4444&amp;animation=yatta&amp;background=transparent&amp;outline=44ef44&amp;outline_width=2" alt="提供" height="24" align="absmiddle">)

複数候補は並列起動可。

### 4. dry-run <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%A2%E3%83%BC%E3%83%89?font=hachimaru&amp;color=4ade80&amp;animation=bane&amp;background=transparent&amp;outline=4a16a3&amp;outline_width=2" alt="モード" height="24" align="absmiddle">

`--dry-run` <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%95%E3%83%A9%E3%82%B0?font=maru-bold&amp;color=ef4444&amp;animation=kirari&amp;background=transparent&amp;outline=44ef44&amp;outline_width=2" alt="フラグ" height="24" align="absmiddle">では候補リストだけ<img src="https://mojiemoji.jozo.beer/emoji/%E8%A1%A8%E7%A4%BA?font=kurobara&amp;color=fdba74&amp;animation=kaiten&amp;speed=slow&amp;background=transparent&amp;outline=74fdba&amp;outline_width=2" alt="表示" height="24" align="absmiddle">し、selector を起動しない。
ユーザーが「どんな語が候補に出るか先に見たい」ときに使う:

```
未 stamp 候補 (count 順):
  - 特殊用語 (2 件): "これは特殊用語と未収録単語と…"
  - 未収録語 (1 件): "本文の未収録語は対象。"
  ...
```

### 5. <img src="https://mojiemoji.jozo.beer/emoji/%E5%A0%B1%E5%91%8A?font=toge&amp;color=f472b6&amp;animation=yokomoya&amp;background=transparent&amp;outline=77db27&amp;outline_width=2" alt="報告" height="24" align="absmiddle">

最後に N 件のうち selector が記録した件数を<img src="https://mojiemoji.jozo.beer/emoji/%E5%A0%B1%E5%91%8A?font=toge&amp;color=f472b6&amp;animation=yokomoya&amp;background=transparent&amp;outline=77db27&amp;outline_width=2" alt="報告" height="24" align="absmiddle">:

```
mojiemoji-propose: 5 件の候補語を selector に渡し、
5 件すべて usage.jsonl に追記しました。
次回 /bump-catalog で promotion 対象になります。
```

## オプション

- `--top N` — 処理する候補数<img src="https://mojiemoji.jozo.beer/emoji/%E4%B8%8A%E9%99%90?font=maru&amp;color=3b82f6&amp;animation=yokomoya&amp;background=transparent&amp;outline=f63b82&amp;outline_width=2" alt="上限" height="24" align="absmiddle"> (default: 5)
- `--dry-run` — 候補リストだけ<img src="https://mojiemoji.jozo.beer/emoji/%E5%87%BA%E5%8A%9B?font=tamanegi&amp;color=22c55e&amp;animation=kage_bokashi&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="出力" height="24" align="absmiddle">、selector 起動しない
- `--min-count N` — count >= N の候補だけ処理 (default: 1)

## <img src="https://mojiemoji.jozo.beer/emoji/%E5%89%AF?font=zero&amp;color=60a5fa&amp;animation=kage_bokashi&amp;background=transparent&amp;outline=fa60a5&amp;outline_width=2" alt="副" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E4%BD%9C%E7%94%A8?font=zero&amp;color=60a5fa&amp;animation=kage_bokashi&amp;background=transparent&amp;outline=fa60a5&amp;outline_width=2" alt="作用" height="24" align="absmiddle">

- `usage.jsonl` に N 件<img src="https://mojiemoji.jozo.beer/emoji/%E8%BF%BD%E8%A8%98?font=akzk&amp;color=c084fc&amp;animation=chirichiri&amp;background=transparent&amp;outline=fcc084&amp;outline_width=2" alt="追記" height="24" align="absmiddle">される
- 次回 `/bump-catalog --dry-run` で<img src="https://mojiemoji.jozo.beer/emoji/%E6%96%B0%E8%A6%8F?font=toge&amp;color=fb7185&amp;animation=yoko_scroll&amp;background=transparent&amp;outline=85fb71&amp;outline_width=2" alt="新規" height="24" align="absmiddle"> variant 候補として visible に
  なる

## <img src="https://mojiemoji.jozo.beer/emoji/%E9%96%A2%E9%80%A3?font=kurobara&amp;color=c084fc&amp;animation=patapata&amp;background=transparent&amp;outline=fcc084&amp;outline_width=2" alt="関連" height="24" align="absmiddle">

- #92 — <img src="https://mojiemoji.jozo.beer/emoji/%E6%A7%8B%E9%80%A0?font=maru&amp;color=fb923c&amp;animation=neruneru&amp;background=transparent&amp;outline=0cea58&amp;outline_width=2" alt="構造" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E5%95%8F%E9%A1%8C?font=mincho&amp;color=facc15&amp;animation=zairu&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="問題" height="24" align="absmiddle">の原 issue
- #93 — この skill 自体の implementation
- #46 — `bump-catalog` パイプライン (下流)
- `agents/mojiemoji-selector.md` — 起動先 subagent
- `skills/bump-catalog/SKILL.md` — promotion 段
