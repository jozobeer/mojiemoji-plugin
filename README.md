# mojiemoji-plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-blue)](https://docs.claude.com/en/docs/claude-code/plugins)
[![mojiemoji](https://img.shields.io/badge/service-mojiemoji.jozo.beer-ec4899)](https://mojiemoji.jozo.beer)

[**mojiemoji.jozo.beer**](https://mojiemoji.jozo.beer) のスタンプ画像を GitHub Markdown (issue / PR / レビュー / リプライ / リリースノート) に **自動で適切に埋め込む** ための Claude Code プラグイン。

日本語本文中で `これは【マジで】やばい【バグ】ですね` のように **キーワードだけスタンプ化** するインライン強調が主目的。

---

## 同梱されるもの

| 種別 | 名前 | 役割 |
|---|---|---|
| Skill | `mojiemoji-github` | GitHub の各 surface (issue/PR/レビュー等) ごとのスタンプ配置ポリシー、6 必須パラメータ規約、helper script を提供 |
| Subagent | `mojiemoji-selector` | フレーズ群を受け取り、フォント / 色 / アニメーション / アウトラインを多様性確保しつつ選定して `<img>` スニペットを返す |
| Hook (PreToolUse / Bash) | `mojiemoji-japanese-gate.py` | `gh (issue\|pr\|release) (create\|comment\|review)` や `gh api .../reviews` 等で日本語本文を投稿しようとした時に、6 必須パラメータ揃わない mojiemoji URL を含むコマンドを **送信前にブロック** |

---

## インストール

### マーケットプレイス追加 + インストール (推奨)

Claude Code 内で:

```
/plugin marketplace add jozobeer/mojiemoji-plugin
/plugin install mojiemoji-github@mojiemoji-plugin
```

### ローカルチェックアウトから

```bash
git clone https://github.com/jozobeer/mojiemoji-plugin.git ~/mojiemoji-plugin
```

Claude Code 内で:

```
/plugin marketplace add ~/mojiemoji-plugin
/plugin install mojiemoji-github@mojiemoji-plugin
```

### 動作確認

インストール後、Claude Code に日本語 issue を作るよう依頼してみてください。フック (`mojiemoji-japanese-gate.py`) が `gh issue create` を一旦止めて、本文を mojiemoji 装飾した上で送信し直すはずです。

```
/plugin
```
で `mojiemoji-github` が `enabled` になっていれば導入完了。

---

## 仕組み — 3 層構造

```
┌─────────────────────────────────────────────────────────────────┐
│ Skill: mojiemoji-github                                          │
│   ・どこに / どんなとき / どんな密度でスタンプを置くかの規約   │
│   ・helper script (scripts/mojiemoji_markdown.rb) で URL 生成 │
└─────────────────────────────────────────────────────────────────┘
                            ▲
                            │ 「3つ以上 / カタログ / バリエーション」が必要なときに dispatch
                            │
┌─────────────────────────────────────────────────────────────────┐
│ Subagent: mojiemoji-selector                                     │
│   ・presets.md / flavor-guide.md を読んで多様性を確保           │
│   ・フォント・色・アニメ・アウトライン 4 軸で偏らないよう選定   │
│   ・ready-to-paste な <img> スニペット表を返す                  │
└─────────────────────────────────────────────────────────────────┘
                            ▲
                            │ 「送信前最終ゲート」として透過的に発火
                            │
┌─────────────────────────────────────────────────────────────────┐
│ Hook (PreToolUse / Bash): mojiemoji-japanese-gate.py             │
│   ・gh (issue/pr/release) 系コマンドを intercept                │
│   ・日本語本文 + mojiemoji 不在 / パラメータ不足 → exit 2 で阻止 │
│   ・stderr にエラー + 対応指示を出して Claude に修正させる      │
│   ・緊急 bypass: 先頭に `HOOK_DISABLE=1 ` を付ける               │
└─────────────────────────────────────────────────────────────────┘
```

---

## なぜこのプラグインが必要か

mojiemoji の画像 URL は **6 つのパラメータが全て揃わないと dark mode で黒い不可視スタンプになる**:

| パラメータ | 必須値 | 欠落時 |
|---|---|---|
| `background` | `transparent` | dark mode で白ブロック |
| `font` | 17 種の正準フォント | サービスデフォルトの素フォント |
| `color` | Tailwind 300〜500 hex | dark mode で黒不可視 |
| `animation` | 34 種の正準アニメ (`spin` は禁止) | 静止画 |
| `outline` | `triadic` 推奨 / `complement` / `darker` / `lighter` / 6-hex | 文字輪郭が背景と融合 |
| `outline_width` | `2` | 1px は細い / 3px+ は字形崩壊 |

LLM が手書きで URL を組み立てると `background=transparent` だけ付けて他 5 つを忘れる事故が頻発する。このプラグインは:

1. **Skill** で 6 必須パラメータをドキュメント化
2. **Subagent** に丸投げして手書きを回避
3. **Hook** で「もし手書きで送信しようとしたら止める」 last-mile gate を実装

の 3 段で防ぐ。

---

## 設定

### Hook を一時無効化

```bash
HOOK_DISABLE=1 gh issue create --title "..." --body "..."
```

### Hook 自体を無効化したい

Claude Code の `/plugin` メニューで disable するか、`hooks/hooks.json` を編集。

### Skill / Subagent のカスタマイズ

`skills/mojiemoji-github/references/presets.md` でフォント / 色 / アニメの preset 群を編集できます。

---

## 関連

- mojiemoji 本体サービス: https://mojiemoji.jozo.beer
- Claude Code プラグインドキュメント: https://docs.claude.com/en/docs/claude-code/plugins

---

## License

[MIT](LICENSE)
