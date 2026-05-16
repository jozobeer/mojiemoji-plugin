---
name: bump-catalog
description: "ローカル mojiemoji usage cache (`~/.local/share/mojiemoji-plugin/usage.jsonl`) から閾値を満たした variant を `prestamp-catalog.yml` に昇格させ、自動 PR を作る。selector が catalog miss 時に記録した flavor を、複利型 catalog 育成の入口にする。LLM 不要・全部 Ruby script で決定論的。"
allowed-tools:
  # bump_catalog.py 本体。`--dry-run` / `--apply` / `--pr` モード全てで使用。
  # `--pr` モードでは内部から `git` / `gh pr create` を `system()` で呼ぶが、
  # Ruby プロセス内 subprocess なので外側の Bash gate 1 つで通る。
  - Bash(python3 skills/mojiemoji-github/scripts/bump_catalog.py*)
  - Bash(python3 */skills/mojiemoji-github/scripts/bump_catalog.py*)
---

# Bump Catalog

`mojiemoji-github` プラグインの catalog をローカル usage cache から
自動的に育てる skill。selector subagent が catalog miss した term に
flavor を選定したとき、`cache_record.py` が JSONL に追記する。
この skill はその cache を集計して、しきい値を満たした variant を
`prestamp-catalog.yml` に昇格させる PR を 1 件作る。

**全工程はトークン不要・LLM 不要・決定論的。**
このスキル本体は単にスクリプトを呼ぶだけ。

## 起動条件

ユーザーが明示的に「catalog を育てて」「bump-catalog 走らせて」など
要求したとき。あるいは `/bump-catalog` を叩いたとき。

## 手順

1. まず引数なしで dry-run して何が追加されるか確認する(デフォルトが
   `--dry-run` なので破壊的操作は起きない):

   ```bash
   python3 skills/mojiemoji-github/scripts/bump_catalog.py
   ```

   出力に「would add N variant(s) ...」が出たら次へ。「no new variants
   to add」だけならその回はスキップして終わり。

2. 内容に問題なければ `--pr` を付けて本実行する:

   ```bash
   python3 skills/mojiemoji-github/scripts/bump_catalog.py --pr
   ```

   `--pr` モードがやること:
   - `usage.jsonl` を読む(`$MOJIEMOJI_CACHE_FILE` または
     `${XDG_DATA_HOME:-~/.local/share}/mojiemoji-plugin/usage.jsonl`)
   - 閾値(デフォルト 2)を満たした variant を diff として抽出
   - 既存 variant とまったく同一の flavor はスキップ
   - `prestamp-catalog.yml` をマージ
   - `plugin.json` の patch version を bump
   - clean tree 検証 + `git fetch origin main && git checkout main && git pull`
   - `feat/auto-catalog-grow-<yyyymmdd>` ブランチを切って commit + push
   - `gh pr create --assignee @me` で PR を作成
   - PR URL を stdout に出す

3. PR URL をユーザーに報告する。それだけ。

## オプション

- catalog だけ更新したい(PR は手で出す)なら `--apply`:

  ```bash
  python3 skills/mojiemoji-github/scripts/bump_catalog.py --apply
  ```

  これは `prestamp-catalog.yml` のマージのみ。`plugin.json` も触らず git
  操作もしない。

- 閾値を変えたいなら `--threshold N` (デフォルト 2)。1 件単位でも
  複利が効くという観点で、しきい値は低めに保つのが推奨。

## モードまとめ

| モード | catalog | plugin.json | git/PR |
|---|---|---|---|
| `--dry-run` (default) | — | — | — |
| `--apply` | ✓ | — | — |
| `--pr` | ✓ | ✓ (patch bump) | ✓ |

## 注意

- このスキルは catalog の自動マージのみを担当する。**人間レビューは
  必須** — auto-merge は禁止。
- スクリプトは Phase 1 実装(参照: GitHub Issue #46)。今後の Phase で
  GitHub Actions による週次 cron、公開 cache 集約方法などを追加する予定。

## 入力枯渇時 (#92 / #93)

`usage.jsonl` が空 / ほぼ空のときは `bump-catalog` を回しても "no
new variants to add" しか出ない。これは selector subagent が
起動していないサイン (prestamp 過剰効率化による)。draft markdown が
あるなら `/mojiemoji-propose <path>` を先に回して、未 stamp の 2-8 字
日本語連続を selector に投げて cache に追記してから `bump-catalog` を
呼ぶ。
