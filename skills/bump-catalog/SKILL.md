---
name: bump-catalog
description: "ローカル mojiemoji usage cache (`~/.local/share/mojiemoji-plugin/usage.jsonl`) から閾値を満たした variant を `prestamp-catalog.yml` に昇格させ、自動 PR を作る。selector が catalog miss 時に記録した flavor を、複利型 catalog 育成の入口にする。LLM 不要・全部 Ruby script で決定論的。"
---

# Bump Catalog

`mojiemoji-github` プラグインの catalog をローカル usage cache から
自動的に育てる skill。selector subagent が catalog miss した term に
flavor を選定したとき、`cache-record.rb` が JSONL に追記する。
この skill はその cache を集計して、しきい値を満たした variant を
`prestamp-catalog.yml` に昇格させる PR を 1 件作る。

**全工程はトークン不要・LLM 不要・決定論的。**
このスキル本体は単にスクリプトを呼ぶだけ。

## 起動条件

ユーザーが明示的に「catalog を育てて」「bump-catalog 走らせて」など
要求したとき。あるいは `/bump-catalog` を叩いたとき。

## 手順

1. 引数なしで `scripts/bump-catalog.rb` を実行する:

   ```bash
   ruby skills/mojiemoji-github/scripts/bump-catalog.rb
   ```

   スクリプトは以下を自動でやる:
   - `usage.jsonl` を読む(`$MOJIEMOJI_CACHE_FILE` または
     `${XDG_DATA_HOME:-~/.local/share}/mojiemoji-plugin/usage.jsonl`)
   - 閾値(デフォルト 2)を満たした variant を diff として抽出
   - 既存 variant とまったく同一の flavor はスキップ
   - `prestamp-catalog.yml` をマージ
   - `plugin.json` の patch version を bump
   - `feat/auto-catalog-grow-<yyyymmdd>` ブランチを切って commit + push
   - `gh pr create --assignee @me` で PR を作成
   - PR URL を stdout に出す

2. PR URL をユーザーに報告する。それだけ。

## オプション

- 何も追加するものがないか先に確認したいなら `--dry-run` を渡す:

  ```bash
  ruby skills/mojiemoji-github/scripts/bump-catalog.rb --dry-run
  ```

- 閾値を変えたいなら `--threshold N` (デフォルト 2)。1 件単位でも
  複利が効くという観点で、しきい値は低めに保つのが推奨。

## 注意

- このスキルは catalog の自動マージのみを担当する。**人間レビューは
  必須** — auto-merge は禁止。
- スクリプトは Phase 1 実装(参照: GitHub Issue #46)。今後の Phase で
  GitHub Actions による週次 cron、公開 cache 集約方法などを追加する予定。
