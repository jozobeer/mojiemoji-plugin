---
name: mojiemoji-github
description: >
  GitHub の issue / PR / レビュー / リリースノート向けに共有 mojiemoji
  core を呼び出す Grok スキル。日本語本文のインライン強調が主用途。
---

<!-- mojiemoji-schema-version: 2.1.0 -->

# mojiemoji-github (Grok)

Grok ユーザー向け mojiemoji 装飾スキル。

## 使い方

1. core 公開後は `uvx mojiemoji` を利用。
2. Grok の `~/.config/grok/skills/mojiemoji-github/SKILL.md` として
   配置 (本ファイルまたは port-policy で最適化したもの)。
3. 日本語の GitHub body を作成する際 ( /make-issue, /make-pr, edit など ) や `.md` 編集時に自動または明示的に発火。

## 下処理 first (中心原則)

Grok の Bash ツールを使って必ず prestamp を最初に通す:

```bash
# 推奨
uvx mojiemoji < body.md > decorated.md

# core 公開前 / checkout からの fallback
python3 /path/to/mojiemoji-plugin/skills/mojiemoji-github/scripts/prestamp.py \
  --surface issue-body < body.md > decorated.md
```

出力のスニペットを本文に埋め込んでユーザーに提示 → 確認 → 投稿。

## URL 契約

レンダ済み stamp は `/emoji/<encoded-text>` を使い、次の必須パラメータを持つ:

- `font`
- `color`
- `animation`
- `background=transparent`
- `outline`
- `outline_width=2`

色は `a855f7` / `22c55e` / `f59e0b` / `06b6d4` / `f472b6` のような
Tailwind 300-500 帯を使う。animation は `bane` / `bure` / `kirari` /
`yoko_scroll` / `zairu` のような canonical 名を使う。

## トリガー

- Grok slash コマンド (`/make-issue`, `/make-pr`, `/address-review` など) の返答時
- GitHub 関連の投稿操作前 (`gh issue ...`, `gh pr ...` など Bash 経由)
- 日本語を含む .md ファイルの編集時 (README, docs, skills/**/*.md など)
- 必要に応じて MCP / GitHub ツールの body フィールド

## スコープ / スキップ

- 日本語 GitHub markdown のみ
- 英語のみ、謝罪/セキュリティ/法務/コンプライアンス/受け入れ基準テキストはスキップ
- `<!-- mojiemoji:off -->` ... `<!-- mojiemoji:on -->` で明示 skip

## Canonical ポリシー

canonical skill と同じ扱いをこの harness でも手動で適用する:

- 投稿先 surface に合わせて `--surface issue-body` / `pr-body` /
  `review-body` / `comment-body` / `release-note` を渡す。`--surface
  pr-body` は、対象リポジトリが PR body を merge commit message に転記する
  設定のとき、意図的に入力をそのまま出力する (skip)。skip が発火したら
  手動でも PR body を装飾しない。
- 色循環 animation (`kira` / `disco` / `psycho`) では `outline` と
  `outline_width` を付けない。それ以外の animation は 6 パラメータ全部を
  維持する。
- shields.io badge 行は本文 1 行目に置き、stamp はその下から始める。
- prestamp 出力は機械的な下処理 (catalog hit のみ)。残りのフレーズへの
  インライン装飾はその後に行い、装飾済み本文をユーザーに提示して確認を
  得てから投稿する。

このアダプタと canonical skill の記述が食い違う場合は、plugin リポジトリの
`skills/mojiemoji-github/SKILL.md` が正となる。

詳細な契約・パラメータ・workflow は親リポの
`skills/mojiemoji-github/references/*.md` および
`skills/mojiemoji-github/SKILL.md` (Claude 版、参考) を port-policy で
適宜翻訳・最適化して参照。

Grok の強力な bash + agent ツールと組み合わせることで、Claude 相当の gate (6 必須パラメータ強制 + 未装飾 block) を再現可能。

## 参考

- port-policy スキルで "copy then optimize" を徹底
- 親 issue: <https://github.com/jozobeer/mojiemoji-plugin/issues/144>
- 監査: `scripts/audit-harness-skills.sh` に "grok" を追加済み
