---
name: mojiemoji-propose
description: "prestamp が拾えなかった 2-8 字日本語連続 (Kanji / Katakana) を抽出し、`mojiemoji-selector` subagent に flavor を選ばせて usage cache に追記する。catalog 育成パイプライン (#46) の入力枯渇 (#92) を解決する Phase 1 (#93)。ユーザーが draft markdown ファイルを指定して呼ぶ。"
allowed-tools:
  - Bash(python3 skills/mojiemoji-github/scripts/prestamp.py*)
  - Bash(python3 */skills/mojiemoji-github/scripts/prestamp.py*)
  - Bash(python3 skills/mojiemoji-github/scripts/cache_record.py*)
  - Bash(python3 */skills/mojiemoji-github/scripts/cache_record.py*)
  - Read
  - Agent(mojiemoji-selector)
---

# Mojiemoji Propose

prestamp 後の draft に残った未 stamp 日本語語に対して、
`mojiemoji-selector` subagent に flavor を考案させて usage cache
に記録する。これにより `bump-catalog` の入力が補充され、catalog が
自然に育つ。

## 起動条件

- ユーザーが `/mojiemoji-propose <path>` を叩いたとき
- ユーザーが「未 stamp 語を catalog に育てたい」「propose を回して」など
  明示的に要求したとき

## なぜ必要か

`prestamp.py` は決定論的に catalog hit を `<img>` 化するため
selector 起動機会を奪う (#92)。`usage.jsonl` が空のまま放置されると
`bump-catalog` (#46) が永久に発火せず catalog が育たない。この skill は
prestamp の隙間を埋め、selector を起動するための入口になる。

## 手順

### 1. draft を prestamp + report 取得

```bash
DRAFT="<path>"
REPORT="$(mktemp /tmp/propose-XXXXXX.json)"
python3 "${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/scripts/prestamp.py" \
  --report-unstamped < "$DRAFT" > "$REPORT"
```

`unstamped` 配列が空なら「育成候補なし」を報告して終了。

### 2. 上位 N 件を抽出

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
標準動作)。

Input contract に従って:

- フレーズ: 抽出した term
- mode: `inline` (catalog 育成用の標準形式)
- context: `report.unstamped[i].contexts[0]` (selector に文脈を提供)

複数候補は並列起動可。

### 4. dry-run モード

`--dry-run` フラグでは候補リストだけ表示し、selector を起動しない。
ユーザーが「どんな語が候補に出るか先に見たい」ときに使う:

```
未 stamp 候補 (count 順):
  - 特殊用語 (2 件): "これは特殊用語と未収録単語と…"
  - 未収録語 (1 件): "本文の未収録語は対象。"
  ...
```

### 5. 報告

最後に N 件のうち selector が記録した件数を報告:

```
mojiemoji-propose: 5 件の候補語を selector に渡し、
5 件すべて usage.jsonl に追記しました。
次回 /bump-catalog で promotion 対象になります。
```

## オプション

- `--top N` — 処理する候補数上限 (default: 5)
- `--dry-run` — 候補リストだけ出力、selector 起動しない
- `--min-count N` — count >= N の候補だけ処理 (default: 1)

## 副作用

- `usage.jsonl` に N 件追記される
- 次回 `/bump-catalog --dry-run` で新規 variant 候補として visible に
  なる

## 関連

- #92 — 構造問題の原 issue
- #93 — この skill 自体の implementation
- #46 — `bump-catalog` パイプライン (下流)
- `agents/mojiemoji-selector.md` — 起動先 subagent
- `skills/bump-catalog/SKILL.md` — promotion 段
