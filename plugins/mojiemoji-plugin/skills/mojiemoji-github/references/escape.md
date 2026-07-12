# 著者明示のエスケープ — `<!-- mojiemoji:off -->` / `<!-- mojiemoji:on -->`

`prestamp.py` が機械的に<img src="https://mojiemoji.jozo.beer/emoji/%E7%BD%AE%E6%8F%9B?font=hachimaru&amp;color=facc15&amp;animation=norinori&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="置換" height="24" align="absmiddle">する<img src="https://mojiemoji.jozo.beer/emoji/%E7%AF%84%E5%9B%B2?font=gothic-bold&amp;color=8b5cf6&amp;animation=zairu&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="範囲" height="24" align="absmiddle">を、著者側で明示的に区切ってスキップさせる仕組み。before/after 例示、<img src="https://mojiemoji.jozo.beer/emoji/%E5%BC%95%E7%94%A8?font=chikara&amp;color=f43f5e&amp;animation=tate_scroll&amp;background=transparent&amp;outline=5ef43f&amp;outline_width=2" alt="引用" height="24" align="absmiddle">、プレーン文章サンプルなど「装飾されたくない<img src="https://mojiemoji.jozo.beer/emoji/%E7%AF%84%E5%9B%B2?font=maru-bold&amp;color=22c55e&amp;animation=ekken&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="範囲" height="24" align="absmiddle">」を<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%9D%E8%AD%B7?font=akzk&amp;color=22d3ee&amp;animation=kira&amp;background=transparent&amp;outline_width=0" alt="保護" height="24" align="absmiddle">する。

## 構文

`<!-- mojiemoji:off -->` を独立した行に置くと、`<!-- mojiemoji:on -->` まで `prestamp.py` の term / emoji <img src="https://mojiemoji.jozo.beer/emoji/%E7%BD%AE%E6%8F%9B?font=mincho&amp;color=22c55e&amp;animation=tatemoya&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="置換" height="24" align="absmiddle">が完全に skip される。

```markdown
ここは <img stamp="変換" /> されます。

<!-- mojiemoji:off -->
> 以下は素の例示。プラグインが何もしない世界線。
> これはマジでやばいバグですね。緊急で修正お願いします。
<!-- mojiemoji:on -->

ここからまた変換されます。
```

## ルール

- `:off` 出現以降、`:on` まで term/emoji <img src="https://mojiemoji.jozo.beer/emoji/%E7%BD%AE%E6%8F%9B?font=pixel&amp;color=ef4444&amp;animation=kirari&amp;background=transparent&amp;outline=44ef44&amp;outline_width=2" alt="置換" height="24" align="absmiddle">を完全 skip。`:on` で再開
- file <img src="https://mojiemoji.jozo.beer/emoji/%E6%9C%AB%E5%B0%BE?font=dela&amp;color=4ade80&amp;animation=bane&amp;background=transparent&amp;outline=4a16a3&amp;outline_width=2" alt="末尾" height="24" align="absmiddle">までに `:on` が出なかったら EOF まで skip 継続
- nesting は flat 扱い (off 中の off は no-op、redundant on も no-op)
- markers は HTML コメントなので GitHub では何も描画されない (本文に痕跡が残らない)
- 行頭 / 行末の空白は許容、ただし markers はそれぞれ独立した行に書くこと (mid-line は HTML コメントとして無視されるだけで escape は発動しない)

## ユースケース

| 用途 | 例 |
|---|---|
| before/after の "before" を生のまま見せる | 例えば prestamp <img src="https://mojiemoji.jozo.beer/emoji/%E5%89%8D?font=maru&amp;color=8b5cf6&amp;animation=yokomoya&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="前" height="24" align="absmiddle">の draft を<img src="https://mojiemoji.jozo.beer/emoji/%E5%BC%95%E7%94%A8?font=pixel&amp;color=f87171&amp;animation=poyoon&amp;background=transparent&amp;outline=26dc26&amp;outline_width=2" alt="引用" height="24" align="absmiddle">するとき |
| <img src="https://mojiemoji.jozo.beer/emoji/%E5%BC%95%E7%94%A8?font=akzk&amp;color=fbbf24&amp;animation=patapata&amp;background=transparent&amp;outline=06d977&amp;outline_width=2" alt="引用" height="24" align="absmiddle">ブロックの原文<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%9D%E8%AD%B7?font=akzk&amp;color=22d3ee&amp;animation=kira&amp;background=transparent&amp;outline_width=0" alt="保護" height="24" align="absmiddle"> | 他人の発言や issue の原文を改変したくない |
| エスケープ機構自体の<img src="https://mojiemoji.jozo.beer/emoji/%E8%AA%AC%E6%98%8E?font=toge&amp;color=f97316&amp;animation=mochimochi&amp;background=transparent&amp;outline=16f973&amp;outline_width=2" alt="説明" height="24" align="absmiddle"> | この file のような meta documentation |
| プレーン文章サンプル | 装飾なしの素の Japanese を見せたいデモ |

## prestamp.py 側の<img src="https://mojiemoji.jozo.beer/emoji/%E5%AE%9F%E8%A3%85?font=toge&amp;color=fb7185&amp;animation=tate_ekken&amp;background=transparent&amp;outline=85fb71&amp;outline_width=2" alt="実装" height="24" align="absmiddle">

`prestamp.py` は line-based scan で `:off` / `:on` markers を<img src="https://mojiemoji.jozo.beer/emoji/%E6%A4%9C%E5%87%BA?font=mincho&amp;color=3b82f6&amp;animation=yoko_scroll&amp;background=transparent&amp;outline=f63b82&amp;outline_width=2" alt="検出" height="24" align="absmiddle">し、`:off` 区間内の term-pattern / emoji-pattern マッチを全てスキップする。fenced code block / inline code 等の<img src="https://mojiemoji.jozo.beer/emoji/%E6%97%A2%E5%AD%98?font=dela&amp;color=f472b6&amp;animation=kira&amp;background=transparent&amp;outline_width=0" alt="既存" height="24" align="absmiddle"> safe-zone とは別レイヤーで動く(safe-zone は構文ベース、escape markers は著者の<img src="https://mojiemoji.jozo.beer/emoji/%E6%84%8F%E5%9B%B3?font=dela&amp;color=8b5cf6&amp;animation=shuchusen&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="意図" height="24" align="absmiddle">ベース)。

<img src="https://mojiemoji.jozo.beer/emoji/CI?font=kurobara&amp;color=22c55e&amp;animation=tatemoya&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="CI" height="24" align="absmiddle"> の prestamp drift check (#91) は escape markers を尊重するので、`:off` 区間内の Japanese は drift とみなされない。
