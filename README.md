# mojiemoji-plugin

<p align="center">
  <img src="./assets/hero.png" alt="mojiemoji-plugin hero" width="100%">
</p>

[![License: MIT](https://img.shields.io/github/license/jozobeer/mojiemoji-plugin?color=ec4899)](LICENSE) [![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-blue?logo=anthropic)](https://docs.claude.com/en/docs/claude-code/plugins) [![mojiemoji service](https://img.shields.io/badge/service-mojiemoji.jozo.beer-a855f7?logo=cloudflare&logoColor=white)](https://mojiemoji.jozo.beer) [![Version](https://img.shields.io/github/v/tag/jozobeer/mojiemoji-plugin?label=version&color=22c55e)](https://github.com/jozobeer/mojiemoji-plugin/releases) [![Last commit](https://img.shields.io/github/last-commit/jozobeer/mojiemoji-plugin?color=f59e0b)](https://github.com/jozobeer/mojiemoji-plugin/commits/main) [![Stars](https://img.shields.io/github/stars/jozobeer/mojiemoji-plugin?style=flat&color=fbbf24)](https://github.com/jozobeer/mojiemoji-plugin/stargazers) [![Made for Japanese GitHub](https://img.shields.io/badge/made%20for-日本語%20GitHub-3b82f6)](https://mojiemoji.jozo.beer)

[**mojiemoji.jozo.beer**](https://mojiemoji.jozo.beer) のスタンプ画像を GitHub Markdown (issue / PR / レビュー / リプライ / リリースノート) に **自動で適切に埋め込む** ための Claude Code <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%97%E3%83%A9%E3%82%B0?font=maru-bold&color=8b5cf6&animation=patapata&background=transparent&outline=f68b5c&outline_width=2" alt="プラグ" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E3%82%A4%E3%83%B3?font=maru-bold&color=8b5cf6&animation=patapata&background=transparent&outline=f68b5c&outline_width=2" alt="イン" height="24" align="absmiddle"> 🚀

日本語の GitHub 本文を <img src="https://mojiemoji.jozo.beer/emoji/%E8%A1%A8%E6%83%85?font=pixel&color=60a5fa&animation=kirari&background=transparent&outline=fa60a5&outline_width=2" alt="表情" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E8%B1%8A%E3%81%8B?font=maru-bold&color=4ade80&animation=mochimochi&background=transparent&outline=804ade&outline_width=2" alt="豊か" height="24" align="absmiddle"> に。`これは【マジで】やばい【バグ】ですね` のように **キーワードだけスタンプ化** する mid-sentence インライン強調が主目的。<img src="https://mojiemoji.jozo.beer/emoji/%E3%82%B7%E3%83%A7%E3%83%BC?font=toge&color=fbbf24&animation=tate_ekken&background=transparent&outline=24fbbf&outline_width=2" alt="ショー" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E3%82%B1%E3%83%BC%E3%82%B9?font=rampart&color=f472b6&animation=kage_kaiten&background=transparent&outline=b6f472&outline_width=2" alt="ケース" height="24" align="absmiddle"> 的にはこの README 自体が dogfooding なので、上から下までスタンプまみれ ✨

---

## 🎭 ビフォー・アフター

プレーンな日本語 PR コメント:

> これはマジでやばいバグですね。緊急で修正お願いします。LGTM したら歓迎です。

mojiemoji-plugin が掛かった世界:

> これは<img src="https://mojiemoji.jozo.beer/emoji/%E3%83%9E%E3%82%B8%E3%81%A7?font=dela&color=a855f7&animation=bane&background=transparent&outline=f7a855&outline_width=2" alt="マジで" height="24" align="absmiddle">やばい<img src="https://mojiemoji.jozo.beer/emoji/%E3%83%90%E3%82%B0?font=pixel&color=f97316&animation=bure&background=transparent&outline=16f973&outline_width=2" alt="バグ" height="24" align="absmiddle">ですね。<img src="https://mojiemoji.jozo.beer/emoji/%E7%B7%8A%E6%80%A5?font=dela&color=ef4444&animation=shuchusen&background=transparent&outline=44ef44&outline_width=2" alt="緊急" height="24" align="absmiddle">で<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3?font=gothic-bold&color=0ea5e9&animation=patapata&background=transparent&outline=e90ea5&outline_width=2" alt="修正" height="24" align="absmiddle">お願いします。<img src="https://mojiemoji.jozo.beer/emoji/LGTM?font=maru-bold&color=22c55e&animation=tada&background=transparent&outline=5e22c5&outline_width=2" alt="LGTM" height="24" align="absmiddle">したら<img src="https://mojiemoji.jozo.beer/emoji/%E6%AD%93%E8%BF%8E?font=noto&color=ec4899&animation=kirari&background=transparent&outline=99ec48&outline_width=2" alt="歓迎" height="24" align="absmiddle">です。

同じ文章 / 同じ情報量、印象は完全に別物。プラグインが面倒な装飾作業を全部やる 🎨

---

## 📦 <img src="https://mojiemoji.jozo.beer/emoji/%E5%90%8C%E6%A2%B1?font=maru&color=34d399&animation=yurayura&background=transparent&outline=9934d3&outline_width=2" alt="同梱" height="24" align="absmiddle"> されるもの

3 層構造で <img src="https://mojiemoji.jozo.beer/emoji/%E7%B5%B1%E5%90%88?font=maru-bold&color=3b82f6&animation=tate_ekken&background=transparent&outline=f63b82&outline_width=2" alt="統合" height="24" align="absmiddle"> されています。

| 種別 | 名前 | 役割 |
|---|---|---|
| <img src="https://mojiemoji.jozo.beer/emoji/%E3%82%B9%E3%82%AD%E3%83%AB?font=gothic-bold&color=06b6d4&animation=bane&background=transparent&outline=d406b6&outline_width=2" alt="スキル" height="24" align="absmiddle"> Skill | `mojiemoji-github` | GitHub の各 surface (issue / PR / レビュー等) ごとのスタンプ配置ポリシー、6 必須パラメータ規約、helper script を提供 |
| <img src="https://mojiemoji.jozo.beer/emoji/%E3%82%A8%E3%83%BC?font=akzk&color=ec4899&animation=kira&background=transparent" alt="エー" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E3%82%B8%E3%82%A7%E3%83%B3%E3%83%88?font=akzk&color=ec4899&animation=kira&background=transparent" alt="ジェント" height="24" align="absmiddle"> Subagent | `mojiemoji-selector` | フレーズ群を受け取り、フォント / 色 / アニメーション / アウトラインを多様性確保しつつ選定して `<img>` スニペットを返す |
| <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%95%E3%83%83%E3%82%AF?font=pixel&color=22c55e&animation=norinori&background=transparent&outline=5e22c5&outline_width=2" alt="フック" height="24" align="absmiddle"> Hook (PreToolUse / Bash) | `mojiemoji-japanese-gate.py` | `gh (issue\|pr\|release) (create\|comment\|review)` や `gh api .../reviews` 等で日本語本文を投稿しようとした時、6 必須パラメータ揃わない mojiemoji URL を含むコマンドを **送信前にブロック** |

---

## 🚀 ![インス](https://mojiemoji.jozo.beer/emoji/%E3%82%A4%E3%83%B3%E3%82%B9?font=chikara&color=86efac&animation=chirichiri&background=transparent&outline=ac86ef&outline_width=2) ![トール](https://mojiemoji.jozo.beer/emoji/%E3%83%88%E3%83%BC%E3%83%AB?font=tamanegi&color=fca5a5&animation=ekken&background=transparent&outline=a5fca5&outline_width=2)

### マーケットプレイス追加 + インストール (推奨)

Claude Code 内で:

```
/plugin marketplace add jozobeer/mojiemoji-plugin
/plugin install mojiemoji-github@mojiemoji-plugin
```

これで <img src="https://mojiemoji.jozo.beer/emoji/%E5%AE%8C%E6%88%90?font=hachimaru&color=10b981&animation=disco&background=transparent" alt="完成" height="24" align="absmiddle"> 🎉

### ローカルチェックアウトから

```bash
git clone https://github.com/jozobeer/mojiemoji-plugin.git ~/mojiemoji-plugin
```

Claude Code 内で:

```
/plugin marketplace add ~/mojiemoji-plugin
/plugin install mojiemoji-github@mojiemoji-plugin
```

### <img src="https://mojiemoji.jozo.beer/emoji/%E5%8B%95%E4%BD%9C?font=gothic-bold&color=3b82f6&animation=tenmetsu&background=transparent&outline=f63b82&outline_width=2" alt="動作" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E7%A2%BA%E8%AA%8D?font=maru-bold&color=f59e0b&animation=poyoon&background=transparent&outline=0bf59e&outline_width=2" alt="確認" height="24" align="absmiddle">

インストール後、Claude Code に日本語 issue を作るよう依頼してみてください。フック (`mojiemoji-japanese-gate.py`) が `gh issue create` を一旦止めて、本文を mojiemoji 装飾した上で送信し直すはずです。

```
/plugin
```
で `mojiemoji-github` が `enabled` になっていれば <img src="https://mojiemoji.jozo.beer/emoji/%E5%B0%8E%E5%85%A5?font=chikara&color=a855f7&animation=zanzo&background=transparent&outline=f7a855&outline_width=2" alt="導入" height="24" align="absmiddle"> <img src="https://mojiemoji.jozo.beer/emoji/%E5%AE%8C%E4%BA%86?font=hachimaru&color=10b981&animation=tada&background=transparent&outline=8110b9&outline_width=2" alt="完了" height="24" align="absmiddle"> 🎊

---

## 🏗️ ![仕組み](https://mojiemoji.jozo.beer/emoji/%E4%BB%95%E7%B5%84%E3%81%BF?font=akzk&color=a855f7&animation=kaiten&background=transparent&outline=f7a855&outline_width=2) — 3 層構造

```mermaid
flowchart TD
    A([Claude Code セッション])
    A -->|日本語 GitHub 本文を書こうとする| B
    B[<b>Skill: mojiemoji-github</b><br/>規約・6 必須パラメータ・helper script]
    B -.->|3つ以上 / カタログ / バリエーション が必要なとき dispatch| C
    C[<b>Subagent: mojiemoji-selector</b><br/>presets.md / flavor-guide.md を読み<br/>font / color / animation / outline<br/>4 軸で多様性確保したスニペット表を返す]
    C -.->|ready-to-paste な &lt;img&gt; 群| A
    A -->|gh issue/pr/release/api コマンド| D
    D{<b>Hook (PreToolUse / Bash)</b><br/>mojiemoji-japanese-gate.py}
    D -->|6 必須パラメータ揃う| E([✅ GitHub に送信])
    D -->|未装飾 / パラメータ不足| F([🚧 exit 2 でブロック])
    F -.->|stderr の修正指示で Claude が再装飾| B

    style B fill:#a855f7,color:#fff,stroke:#7c3aed,stroke-width:2px
    style C fill:#ec4899,color:#fff,stroke:#db2777,stroke-width:2px
    style D fill:#3b82f6,color:#fff,stroke:#2563eb,stroke-width:2px
    style E fill:#22c55e,color:#fff,stroke:#16a34a,stroke-width:2px
    style F fill:#ef4444,color:#fff,stroke:#dc2626,stroke-width:2px
    style A fill:#fbbf24,color:#000,stroke:#f59e0b,stroke-width:2px
```

緊急 bypass: gh コマンドの先頭に `HOOK_DISABLE=1 ` を付けると Hook がスキップされる（推奨しない、ダークモードで不可視のまま投稿される）。

---

## ❓ なぜこのプラグインが <img src="https://mojiemoji.jozo.beer/emoji/%E5%BF%85%E8%A6%81?font=mincho&color=ef4444&animation=shuchusen&background=transparent&outline=44ef44&outline_width=2" alt="必要" height="24" align="absmiddle"> か

mojiemoji の画像 URL を生で組み立てると、**色だけで dark mode 不可視になる致命傷** + **他パラメータ欠落で読めないスタンプを量産する** という事故が起こる:

| パラメータ | 必須値 | 欠落時の影響 | 致命度 |
|---|---|---|:---:|
| `color` | 明るめの hex (例: `#a855f7` / `#22c55e` — Tailwind パレットの 300〜500 帯が目安として便利) または `vivid-blue` 等のサービスプリセット名。**サービスは Tailwind クラス名は受け付けない**、hex か名前付きプリセットのみ | サービスデフォルトが黒 → **dark mode で完全不可視** | 💀 致命 |
| `background` | `transparent` | dark mode で白ブロックが本文を切り裂く | ⚠️ 大 |
| `animation` | 34 種の正準アニメから選ぶ。rotational 系 (`kaiten` 等) は **`speed=step` または `slow` の時のみ可読** — `normal` / `fast` だと回転が早すぎて読めない | 欠落時は静止画 → スタンプとしての視覚的 punch が消える | ⚠️ 中 |
| `font` | 17 種の正準フォント | サービスデフォルトの素フォント → body 高さで読みづらい | ⚠️ 中 |
| `outline` | `triadic` 推奨 / `complement` / `darker` / `lighter` / 6-hex | 字形が背景と融合してぼやける | ⚠️ 中 |
| `outline_width` | `2` | 1px は線が細すぎ、3px+ は字形が潰れる | 💡 小 |

特に `color` 欠落 → dark mode 黒不可視は **3 回ユーザにフラグされた実害事例**（直近: cross-repo-review 2026-05-12 で 7 レビュー分のスタンプが全部見えない状態で投稿された 💣）。LLM が手書きで URL を組み立てると `background=transparent` だけ付けて他を忘れる事故が頻発する。このプラグインは:

1. **Skill** で 6 必須パラメータをドキュメント化
2. **Subagent** に丸投げして手書きを回避
3. **Hook** で「もし手書きで送信しようとしたら止める」 last-mile gate を実装

の 3 段で防ぐ 🛡️

---

## ⚙️ ![設定](https://mojiemoji.jozo.beer/emoji/%E8%A8%AD%E5%AE%9A?font=noto&color=06b6d4&animation=mabataki&background=transparent&outline=d406b6&outline_width=2)

### Hook を一時 <img src="https://mojiemoji.jozo.beer/emoji/%E7%84%A1%E5%8A%B9?font=dela&color=fb923c&animation=zanzo&background=transparent&outline=3cfb92&outline_width=2" alt="無効" height="24" align="absmiddle"> 化

```bash
HOOK_DISABLE=1 gh issue create --title "..." --body "..."
```

### Hook 自体を <img src="https://mojiemoji.jozo.beer/emoji/%E7%84%A1%E5%8A%B9?font=dela&color=fb923c&animation=zanzo&background=transparent&outline=3cfb92&outline_width=2" alt="無効" height="24" align="absmiddle"> 化したい

Claude Code の `/plugin` メニューで disable するか、`hooks/hooks.json` を編集。

### Skill / Subagent の <img src="https://mojiemoji.jozo.beer/emoji/%E3%82%AB%E3%82%B9%E3%82%BF?font=zero&color=10b981&animation=patapata&background=transparent&outline=8110b9&outline_width=2" alt="カスタ" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E3%83%9E%E3%82%A4%E3%82%BA?font=hachimaru&color=d8b4fe&animation=neruneru&background=transparent&outline=fed8b4&outline_width=2" alt="マイズ" height="24" align="absmiddle">

`skills/mojiemoji-github/references/presets.md` でフォント / 色 / アニメの preset 群を編集できます。

---

## 🔗 ![関連](https://mojiemoji.jozo.beer/emoji/%E9%96%A2%E9%80%A3?font=kurobara&color=67e8f9&animation=tate_scroll&background=transparent&outline=f967e8&outline_width=2)

- mojiemoji 本体サービス: https://mojiemoji.jozo.beer
- Claude Code プラグインドキュメント: https://docs.claude.com/en/docs/claude-code/plugins
- agent-browser (参考にしたプラグインマーケットプレイス構成): https://github.com/vercel-labs/agent-browser

---

## 📄 License

[MIT](LICENSE) — `jozobeer`

---

<p align="center">
  <sub>Made with <img src="https://mojiemoji.jozo.beer/emoji/%E8%A1%A8%E6%83%85?font=pixel&color=60a5fa&animation=kirari&background=transparent&outline=fa60a5&outline_width=2" alt="表情" height="20" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E8%B1%8A%E3%81%8B?font=maru-bold&color=4ade80&animation=mochimochi&background=transparent&outline=804ade&outline_width=2" alt="豊か" height="20" align="absmiddle"> for Japanese GitHub.</sub>
</p>
