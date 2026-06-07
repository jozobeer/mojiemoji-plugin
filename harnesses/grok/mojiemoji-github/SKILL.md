---
name: mojiemoji-github
description: GitHub の issue / PR / レビュー / リリースノート向けに mojiemoji.jozo.beer スタンプを自動挿入する Grok スキル。日本語本文のインライン強調が主用途。port-policy 経由で Claude 版から最適化。
---

# mojiemoji-github (Grok)

Grok ユーザー向け mojiemoji 装飾スキル (Grok only スコープ)。

## 使い方

1. このリポを clone するか、core 公開後は `uvx mojiemoji` を利用。
2. Grok の `~/.config/grok/skills/mojiemoji-github/SKILL.md` として配置 (本ファイルまたは port-policy で最適化したもの)。
3. 日本語の GitHub body を作成する際 ( /make-issue, /make-pr, edit など ) や `.md` 編集時に自動または明示的に発火。

## 下処理 first (中心原則)

Grok の Bash ツールを使って必ず prestamp を最初に通す:

```bash
# 現行 (このリポ checkout 時)
python3 /path/to/mojiemoji-plugin/scripts/prestamp.py < body.md > decorated.md

# core 公開後 (推奨)
uvx mojiemoji < body.md > decorated.md
```

出力のスニペットを本文に埋め込んでユーザーに提示 → 確認 → 投稿。

## トリガー

- Grok slash コマンド (`/make-issue`, `/make-pr`, `/address-review` など) の返答時
- GitHub 関連の投稿操作前 (`gh issue ...`, `gh pr ...` など Bash 経由)
- 日本語を含む .md ファイルの編集時 (README, docs, skills/**/*.md など)
- 必要に応じて MCP / GitHub ツールの body フィールド

## スコープ / スキップ

- 日本語 GitHub markdown のみ
- 英語のみ、謝罪/セキュリティ/法務/受け入れ基準テキストはスキップ
- `<!-- mojiemoji:off -->` ... `<!-- mojiemoji:on -->` で明示 skip

詳細な契約・パラメータ・workflow は親リポの `skills/mojiemoji-github/references/*.md` および `skills/mojiemoji-github/SKILL.md` (Claude 版、参考) を port-policy で適宜翻訳・最適化して参照。

Grok の強力な bash + agent ツールと組み合わせることで、Claude 相当の gate (6 必須パラメータ強制 + 未装飾 block) を再現可能。

## 参考

- port-policy スキルで "copy then optimize" を徹底
- 親 issue: https://github.com/jozobeer/mojiemoji-plugin/issues/144 (Grok 専用トラック)
- 監査: `scripts/audit-harness-skills.sh` に "grok" を追加済み
