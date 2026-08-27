# <img src="https://mojiemoji.jozo.beer/emoji/%E6%9C%AB%E5%B0%BE?font=dela&amp;color=4ade80&amp;animation=bane&amp;background=transparent&amp;outline=4a16a3&amp;outline_width=2" alt="末尾" height="24" align="absmiddle">装飾 — 文末・段落末・見出し末の trailing 絵文字

文中インライン埋め込み(mojiemoji の主用途)とは別に、文末・段落末・見出し末に絵文字を添える「装飾(decoration)」スロットがある。これは埋め込みと役割が違うので混同しないこと。

## 埋め込み vs 装飾 — 2 つの別物

| パターン | 何 | <img src="https://mojiemoji.jozo.beer/emoji/%E9%85%8D%E7%BD%AE?font=akzk&amp;color=eab308&amp;animation=bane&amp;background=transparent&amp;outline=08eab3&amp;outline_width=2" alt="配置" height="24" align="absmiddle"> | 文法的役割 |
|---|---|---|---|
| **埋め込み(embed)** | スタンプが文中の単語を置き換える | 文中 | **その文に合う**名詞・動詞・副詞の代わり |
| **装飾(decoration)** | 文法的役割なくムードや勢いを添える | 文の下に独立行、`→` を<img src="https://mojiemoji.jozo.beer/emoji/%E5%89%8D?font=chikara&amp;color=ec4899&amp;animation=poyoon&amp;background=transparent&amp;outline=99ec48&amp;outline_width=2" alt="前" height="24" align="absmiddle">置 | なし — 純粋に装飾 |

**ルール: 散文の文末に装飾スタンプを付け足してはいけない。** 文末の trailing 装飾(例: `…したい <マジで> <大事>。`)は埋め込みと視覚的に混ざり、読み手は文の終わりを認識できなくなる。trailing 装飾は専用行に移すこと:

```markdown
…したい。

→ <マジで> <大事>
```

見出し末の trailing 装飾は OK(見出しは散文と視覚的に<img src="https://mojiemoji.jozo.beer/emoji/%E5%88%86%E9%9B%A2?font=rampart&amp;color=fbbf24&amp;animation=zanzo&amp;background=transparent&amp;outline=06d977&amp;outline_width=2" alt="分離" height="24" align="absmiddle">される)。例: `## デプロイ順序 <大事>`。

## 2 段階<img src="https://mojiemoji.jozo.beer/emoji/%E5%84%AA%E5%85%88?font=pixel&amp;color=f472b6&amp;animation=zanzo&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="優先" height="24" align="absmiddle"> — catalog にあれば mojiemoji 化、無ければ素の Unicode

core package (`mojiemoji`) 同梱の emoji catalog に登録のある絵文字 (162 種、<img src="https://mojiemoji.jozo.beer/emoji/%F0%9F%8E%89?font=maru-bold&amp;color=fbbf24&amp;animation=patapata&amp;background=transparent&amp;outline=24fbbf&amp;outline_width=2" alt="🎉" height="24" align="absmiddle"> / <img src="https://mojiemoji.jozo.beer/emoji/%F0%9F%94%A5?font=chikara&amp;color=f43f5e&amp;animation=psycho&amp;background=transparent&amp;outline_width=0" alt="🔥" height="24" align="absmiddle"> / <img src="https://mojiemoji.jozo.beer/emoji/%E2%9C%A8?font=noto&amp;color=ec4899&amp;animation=kira&amp;background=transparent&amp;outline_width=0" alt="✨" height="24" align="absmiddle"> / <img src="https://mojiemoji.jozo.beer/emoji/%F0%9F%92%AF?font=dela&amp;color=f43f5e&amp;animation=bane&amp;background=transparent&amp;outline=5ef43f&amp;outline_width=2" alt="💯" height="24" align="absmiddle"> / <img src="https://mojiemoji.jozo.beer/emoji/%E2%9A%A0?font=gothic-bold&amp;color=f59e0b&amp;animation=gatagata&amp;background=transparent&amp;outline=0bf59e&amp;outline_width=2" alt="⚠" height="24" align="absmiddle"> / <img src="https://mojiemoji.jozo.beer/emoji/%E2%9D%A4?font=maru-bold&amp;color=f472b6&amp;animation=mochimochi&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="❤" height="24" align="absmiddle"> / <img src="https://mojiemoji.jozo.beer/emoji/%F0%9F%98%82?font=maru-bold&amp;color=fbbf24&amp;animation=patapata&amp;background=transparent&amp;outline=24fbbf&amp;outline_width=2" alt="😂" height="24" align="absmiddle"> / <img src="https://mojiemoji.jozo.beer/emoji/%F0%9F%8E%8A?font=pixel&amp;color=ec4899&amp;animation=kirari&amp;background=transparent&amp;outline=99ec48&amp;outline_width=2" alt="🎊" height="24" align="absmiddle"> / <img src="https://mojiemoji.jozo.beer/emoji/%F0%9F%9A%A8?font=chikara&amp;color=fbbf24&amp;animation=shuchusen&amp;background=transparent&amp;outline=24fbbf&amp;outline_width=2" alt="🚨" height="24" align="absmiddle"> / <img src="https://mojiemoji.jozo.beer/emoji/%F0%9F%A4%96?font=zero&amp;color=60a5fa&amp;animation=mabataki&amp;background=transparent&amp;outline=fa60a5&amp;outline_width=2" alt="🤖" height="24" align="absmiddle"> 等) は **mojiemoji 化してアニメ付きで埋める**。catalog から該当 emoji の variant 1 つを引き、`<img src=".../emoji/<emoji>?font=<font>&color=<color>&animation=<anim>&background=transparent&outline=<outline>&outline_width=2" alt="<emoji>" height="24" align="absmiddle">` 形式で展開する。

登録の無い絵文字 (例 🚀 = U+1F680、🪐 = U+1FA90) は**素の Unicode** にフォールバック。例: `## デプロイ手順 🚀`、`これは未対応 🪐`。

1 スロット 1 絵文字、連続させない(mojiemoji 化しても<img src="https://mojiemoji.jozo.beer/emoji/%E5%90%8C%E3%81%98?font=dela&amp;color=60a5fa&amp;animation=mochimochi&amp;background=transparent&amp;outline=fa60a5&amp;outline_width=2" alt="同じ" height="24" align="absmiddle"> — 並べない)。

## catalog 在否を<img src="https://mojiemoji.jozo.beer/emoji/%E7%A2%BA%E8%AA%8D?font=gothic-bold&amp;color=d946ef&amp;animation=zairu&amp;background=transparent&amp;outline=efd946&amp;outline_width=2" alt="確認" height="24" align="absmiddle">する<img src="https://mojiemoji.jozo.beer/emoji/%E6%89%8B%E9%A0%86?font=dela&amp;color=a855f7&amp;animation=mochimochi&amp;background=transparent&amp;outline=f7a855&amp;outline_width=2" alt="手順" height="24" align="absmiddle">

- **VS16 を剥がす**: <img src="https://mojiemoji.jozo.beer/emoji/%E5%89%8D?font=maru&amp;color=8b5cf6&amp;animation=yokomoya&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="前" height="24" align="absmiddle">段に `❤️` (U+2764 U+FE0F) や `⚠️` (U+26A0 U+FE0F) など variation selector (U+FE0F) が混じっていたら、catalog の<img src="https://mojiemoji.jozo.beer/emoji/%E3%82%AD%E3%83%BC?font=chikara&amp;color=a855f7&amp;animation=yoko_scroll&amp;background=transparent&amp;outline=f7a855&amp;outline_width=2" alt="キー" height="24" align="absmiddle">は base codepoint (`❤` / `⚠`) しか持たないので、lookup <img src="https://mojiemoji.jozo.beer/emoji/%E5%89%8D?font=chikara&amp;color=ec4899&amp;animation=poyoon&amp;background=transparent&amp;outline=99ec48&amp;outline_width=2" alt="前" height="24" align="absmiddle">に `tr -d $'\xef\xb8\x8f'` 等で剥がす。剥がさないと「未登録」と<img src="https://mojiemoji.jozo.beer/emoji/%E8%AA%A4?font=kurobara&amp;color=60a5fa&amp;animation=chirichiri&amp;background=transparent&amp;outline=fa60a5&amp;outline_width=2" alt="誤" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E5%88%A4%E5%AE%9A?font=kurobara&amp;color=60a5fa&amp;animation=chirichiri&amp;background=transparent&amp;outline=fa60a5&amp;outline_width=2" alt="判定" height="24" align="absmiddle">して素の Unicode に fallback してしまう。
- **YAML <img src="https://mojiemoji.jozo.beer/emoji/%E3%82%AD%E3%83%BC?font=chikara&amp;color=a855f7&amp;animation=yoko_scroll&amp;background=transparent&amp;outline=f7a855&amp;outline_width=2" alt="キー" height="24" align="absmiddle">に一致**させる: 実 catalog の key 形は `␠␠🎉:` のように 2 字インデント + bare emoji + `:` で、コメント中に未<img src="https://mojiemoji.jozo.beer/emoji/%E5%AF%BE%E5%BF%9C?font=zero&amp;color=a78bfa&amp;animation=yatta&amp;background=transparent&amp;outline=ed7c3a&amp;outline_width=2" alt="対応" height="24" align="absmiddle"> glyph が出てくることもある (`🚀` は upstream 未<img src="https://mojiemoji.jozo.beer/emoji/%E5%AF%BE%E5%BF%9C?font=pixel&amp;color=fbbf24&amp;animation=tatemoya&amp;background=transparent&amp;outline=06d977&amp;outline_width=2" alt="対応" height="24" align="absmiddle">の例として SKILL.md / catalog header の prose にも登場する)。素朴な `grep "<emoji>"` だとコメント / prose にもヒットするので、catalog ファイルを直接読まず core package の API で問い合わせる: `python3 -c "import sys; from mojiemoji.prestamp import load_emoji_catalog; _, e = load_emoji_catalog(); sys.exit(0 if '$EMOJI' in e else 1)"`。catalog は `mojiemoji` の package data なので checkout の path を書く必要がない (import が通らない環境では `<MOJIEMOJI_GITHUB_SKILL_DIR>/scripts` を cwd にして `from lib.core_path import ensure_core_importable; ensure_core_importable()` を先に実行する)。

## catalog variant の params を字面通り使う

catalog には color-shifting 系 variant (`disco` / `psycho` / `kira`) も含まれ、それらは `outline` フィールドを持たず代わりに `outline_width: "0"` を持つ。テンプレ通りに `outline=...&outline_width=2` を埋めると hook (`mojiemoji_japanese_gate.py`) で reject される。catalog 上の variant に書かれた params を字面通り写すのが<img src="https://mojiemoji.jozo.beer/emoji/%E5%AE%89%E5%85%A8?font=gothic-bold&amp;color=ec4899&amp;animation=mabataki&amp;background=transparent&amp;outline=99ec48&amp;outline_width=2" alt="安全" height="24" align="absmiddle">。

## mojiemoji と Unicode 絵文字の組み合わせ — その場で工夫する

mojiemoji(漢字熟語 / 略語 / カタカナ語のテキストスタンプ)と絵文字(Unicode シンボル)は 2 つの層で、**組み合わせるための道具**である。固定テンプレートに頼らず、本文ごとにパターンを変え、自由に混ぜる。active `mojiemoji-github/SKILL.md` からの相対 path `references/` 配下の各 reference は非<img src="https://mojiemoji.jozo.beer/emoji/%E7%B6%B2%E7%BE%85?font=kurobara&amp;color=fbbf24&amp;animation=gatagata&amp;background=transparent&amp;outline=06d977&amp;outline_width=2" alt="網羅" height="24" align="absmiddle">的な踏み台であって、レシピではない。

### 絵文字側の選択フロー

文末・段落末・見出し末の trailing 装飾に絵文字を置くとき:

1. VS16 を剥がす — `❤️` / `⚠️` のような emoji-presentation 形式は U+FE0F が<img src="https://mojiemoji.jozo.beer/emoji/%E5%BE%8C?font=noto&amp;color=60a5fa&amp;animation=kage_neon&amp;background=transparent&amp;outline=fa60a5&amp;outline_width=2" alt="後" height="24" align="absmiddle">ろに付くが、catalog の<img src="https://mojiemoji.jozo.beer/emoji/%E3%82%AD%E3%83%BC?font=dela&amp;color=f472b6&amp;animation=tate_scroll&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="キー" height="24" align="absmiddle">は base codepoint (`❤` / `⚠`) しか持たない。素朴に grep すると miss する。
2. API で lookup — `python3 -c "import sys; from mojiemoji.prestamp import load_emoji_catalog; _, e = load_emoji_catalog(); sys.exit(0 if '$EMOJI' in e else 1)"` で**実 YAML <img src="https://mojiemoji.jozo.beer/emoji/%E3%82%AD%E3%83%BC?font=chikara&amp;color=a855f7&amp;animation=yoko_scroll&amp;background=transparent&amp;outline=f7a855&amp;outline_width=2" alt="キー" height="24" align="absmiddle">**を問い合わせる。catalog ファイルを素朴に grep すると header コメント中の例 (`🚀` 等) にも当たって false positive になる。
3. 居れば mojiemoji 化(catalog variant の params を字面通り使う — color-shift 系は outline 無し / `outline_width: "0"` なので、手書きテンプレで `outline=...&outline_width=2` を勝手に補わない)。
4. 居なければ素の Unicode。

どちらも文末/見出し末の「シンボル位置」専用 — 文中の単語<img src="https://mojiemoji.jozo.beer/emoji/%E7%BD%AE%E6%8F%9B?font=hachimaru&amp;color=facc15&amp;animation=norinori&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="置換" height="24" align="absmiddle"> mojiemoji と役割を混ぜない。**装飾の絵文字を mojiemoji 化しても役割は装飾のまま** — 文中の単語埋め込み (`【マジで】`) と混同せず、文末のシンボル位置に留める。

## ひらがな専用: `%0A` 改行単独スタンプ(3〜5 字)

ヘルパースクリプトは `--text` 中のリテラル `\n` を <img src="https://mojiemoji.jozo.beer/emoji/URL?font=kurobara&amp;color=facc15&amp;animation=mozaiku&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="URL" height="24" align="absmiddle"> クエリ内の `%0A` にエンコードする。全ひらがな 3〜5 字の単語に対して 2 行スタンプを作るのに使う(各行 ≤3 ひらがな):

```bash
python3 "<MOJIEMOJI_GITHUB_SKILL_DIR>/scripts/mojiemoji_markdown.py" --text $'よろ\nしく' --inline \
  --font maru-bold --color 22c55e --animation poyoon \
  --outline triadic --outline-width 2

python3 "<MOJIEMOJI_GITHUB_SKILL_DIR>/scripts/mojiemoji_markdown.py" --text $'ありが\nとう' --inline \
  --font hachimaru --color ec4899 --animation bane \
  --outline triadic --outline-width 2
```

`%0A` を**使わない**ケース:

- 単語に漢字やカタカナを含む(画数が潰れる)
- 1〜2 字のひらがな語(単行で収まるので<img src="https://mojiemoji.jozo.beer/emoji/%E4%B8%8D%E8%A6%81?font=akzk&amp;color=60a5fa&amp;animation=kirari&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="不要" height="24" align="absmiddle">)
- 6 字以上のひらがな語(代わりに 2 スタンプに<img src="https://mojiemoji.jozo.beer/emoji/%E5%88%86%E5%89%B2?font=dela&amp;color=f43f5e&amp;animation=tenmetsu&amp;background=transparent&amp;outline=5ef43f&amp;outline_width=2" alt="分割" height="24" align="absmiddle">)

**ひらがな `%0A` ルールの正確な<img src="https://mojiemoji.jozo.beer/emoji/%E7%AF%84%E5%9B%B2?font=noto&amp;color=4ade80&amp;animation=poyoon&amp;background=transparent&amp;outline=4a16a3&amp;outline_width=2" alt="範囲" height="24" align="absmiddle">:** スタンプ内 `%0A` の形式は**ちょうど 3〜4 字の全ひらがな語**専用(4 字のときは `%0A` を入れる)。単語に漢字やカタカナが混ざる場合は複数スタンプ<img src="https://mojiemoji.jozo.beer/emoji/%E5%88%86%E5%89%B2?font=hachimaru&amp;color=d946ef&amp;animation=kaiten&amp;speed=slow&amp;background=transparent&amp;outline=efd946&amp;outline_width=2" alt="分割" height="24" align="absmiddle">で、絶対に `%0A` を使わない — ひらがな以外のグリフは 2 行の狭いキャンバスで細部が潰れる。
