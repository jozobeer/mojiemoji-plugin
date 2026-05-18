# ワークフロー — prestamp → selector → submit

mojiemoji を使った Japanese GitHub body 作成の標準フロー。SKILL.md は<img src="https://mojiemoji.jozo.beer/emoji/%E6%A6%82%E5%BF%B5?font=noto&amp;color=f97316&amp;animation=bane&amp;background=transparent&amp;outline=16f973&amp;outline_width=2" alt="概念" height="24" align="absmiddle">と<img src="https://mojiemoji.jozo.beer/emoji/%E5%8E%9F%E5%89%87?font=kurobara&amp;color=f472b6&amp;animation=patapata&amp;background=transparent&amp;outline=77db27&amp;outline_width=2" alt="原則" height="24" align="absmiddle">を、この file は<img src="https://mojiemoji.jozo.beer/emoji/%E5%85%B7%E4%BD%93?font=noto&amp;color=f59e0b&amp;animation=yatta&amp;background=transparent&amp;outline=0bf59e&amp;outline_width=2" alt="具体" height="24" align="absmiddle">的な<img src="https://mojiemoji.jozo.beer/emoji/%E6%89%8B%E9%A0%86?font=dela&amp;color=a855f7&amp;animation=mochimochi&amp;background=transparent&amp;outline=f7a855&amp;outline_width=2" alt="手順" height="24" align="absmiddle"> / コマンド / コントラクト形式を扱う。

## 正しいフロー(ダイアグラム)

```
[1] plain markdown (人 or AI が起草)
      ↓
[2] prestamp.py で機械的下処理  <-- トークン 0 / 時間ほぼ 0 / 決定論的
      ↓ pre-stamped markdown (catalog hit はすべて img 化済)
[3] AI が catalog 外の語に追加装飾  <-- AI の判断はここだけ
      ↓ final body
[4] PreToolUse hook が最終 gate (catalog 残存も含めて検証)
      ↓
[5] 投稿 (gh / MCP github_*)
```

## prestamp.py の呼び方

`gh pr create --body-file body.md` する<img src="https://mojiemoji.jozo.beer/emoji/%E7%9B%B4%E5%89%8D?font=mincho&amp;color=f472b6&amp;animation=kage_neon&amp;background=transparent&amp;outline=77db27&amp;outline_width=2" alt="直前" height="24" align="absmiddle">に:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/scripts/prestamp.py" \
  < body.md > body-pre.md
gh pr create --body-file body-pre.md ...
```

stdin / stdout なので pipe でもよい:

```bash
prestamp.py < draft.md | gh pr create --body-file -
```

`prestamp.py` は `data/prestamp-catalog.yml` の全 `terms` <img src="https://mojiemoji.jozo.beer/emoji/%E3%82%AD%E3%83%BC?font=chikara&amp;color=a855f7&amp;animation=yoko_scroll&amp;background=transparent&amp;outline=f7a855&amp;outline_width=2" alt="キー" height="24" align="absmiddle"> (447+ entries) を 1 単語ずつ最長一致で `<img>` <img src="https://mojiemoji.jozo.beer/emoji/%E7%BD%AE%E6%8F%9B?font=pixel&amp;color=ef4444&amp;animation=kirari&amp;background=transparent&amp;outline=44ef44&amp;outline_width=2" alt="置換" height="24" align="absmiddle">する。catalog 外の語は素通し。冪等 (再実行で<img src="https://mojiemoji.jozo.beer/emoji/%E5%89%AF?font=kurobara&amp;color=facc15&amp;animation=mochimochi&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="副" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E4%BD%9C%E7%94%A8?font=kurobara&amp;color=facc15&amp;animation=mochimochi&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="作用" height="24" align="absmiddle">無し)。

`--report-unstamped` <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%95%E3%83%A9%E3%82%B0?font=chikara&amp;color=10b981&amp;animation=shuchusen&amp;background=transparent&amp;outline=8110b9&amp;outline_width=2" alt="フラグ" height="24" align="absmiddle">で、prestamp <img src="https://mojiemoji.jozo.beer/emoji/%E5%BE%8C?font=hachimaru&amp;color=f472b6&amp;animation=nami&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="後" height="24" align="absmiddle">も `<img>` 化されなかった 2-8 字 Kanji / Katakana 連続を JSON で<img src="https://mojiemoji.jozo.beer/emoji/%E5%87%BA%E5%8A%9B?font=tamanegi&amp;color=22c55e&amp;animation=kage_bokashi&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="出力" height="24" align="absmiddle">できる。`/mojiemoji-propose` skill (#93) がこれを selector 起動の入口に使い、`bump-catalog` (#46) の<img src="https://mojiemoji.jozo.beer/emoji/%E5%85%A5%E5%8A%9B?font=mincho&amp;color=ef4444&amp;animation=bane&amp;background=transparent&amp;outline=44ef44&amp;outline_width=2" alt="入力" height="24" align="absmiddle">枯渇 (#92) を解消する。

## 10 ステップワークフロー

1. surface を特定する(issue / <img src="https://mojiemoji.jozo.beer/emoji/PR?font=toge&amp;color=3b82f6&amp;animation=zairu&amp;background=transparent&amp;outline=f63b82&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> 本文 / レビューコメント / 返信 / リリースノート)。surface が **issue 本文 / <img src="https://mojiemoji.jozo.beer/emoji/PR?font=maru&amp;color=34d399&amp;animation=gatagata&amp;background=transparent&amp;outline=9934d3&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> 本文 / リリースノート**なら、まずバッジの有無を<img src="https://mojiemoji.jozo.beer/emoji/%E7%A2%BA%E8%AA%8D?font=toge&amp;color=f59e0b&amp;animation=zanzo&amp;background=transparent&amp;outline=0bf59e&amp;outline_width=2" alt="確認" height="24" align="absmiddle">する。surface に応じた先頭/締め語の引き当ては § Surface ごとの top/closing 装飾ヒューリスティック を<img src="https://mojiemoji.jozo.beer/emoji/%E5%8F%82%E7%85%A7?font=mincho&amp;color=60a5fa&amp;animation=tate_scroll&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="参照" height="24" align="absmiddle">。
2. draft が<img src="https://mojiemoji.jozo.beer/emoji/%E6%97%A5?font=maru-bold&amp;color=d946ef&amp;animation=yatta&amp;background=transparent&amp;outline=efd946&amp;outline_width=2" alt="日" height="24" align="absmiddle">本語 markdown なら、まず `scripts/prestamp.py` を通す。高頻度語(<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3?font=noto&amp;color=c084fc&amp;animation=tatemoya&amp;background=transparent&amp;outline=fcc084&amp;outline_width=2" alt="修正" height="24" align="absmiddle">/<img src="https://mojiemoji.jozo.beer/emoji/%E5%AF%BE%E5%BF%9C?font=maru&amp;color=fdba74&amp;animation=chirichiri&amp;background=transparent&amp;outline=74fdba&amp;outline_width=2" alt="対応" height="24" align="absmiddle">/<img src="https://mojiemoji.jozo.beer/emoji/%E9%87%8D%E8%A6%81?font=tamanegi&amp;color=f472b6&amp;animation=zairu&amp;background=transparent&amp;outline=77db27&amp;outline_width=2" alt="重要" height="24" align="absmiddle">/<img src="https://mojiemoji.jozo.beer/emoji/%E7%B7%8A%E6%80%A5?font=noto&amp;color=22d3ee&amp;animation=kage_neon&amp;background=transparent&amp;outline=b20891&amp;outline_width=2" alt="緊急" height="24" align="absmiddle"> など)はここで<img src="https://mojiemoji.jozo.beer/emoji/%E6%B1%BA%E5%AE%9A?font=noto&amp;color=fb923c&amp;animation=zairu&amp;background=transparent&amp;outline=0cea58&amp;outline_width=2" alt="決定" height="24" align="absmiddle">論的に `<img>` 化し、code fence / inline code / `<details>` 内 / mermaid / link target / shields.io badge などの safe-zone は<img src="https://mojiemoji.jozo.beer/emoji/%E9%99%A4%E5%A4%96?font=pixel&amp;color=f472b6&amp;animation=gatagata&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="除外" height="24" align="absmiddle">される。
3. mode を決める(`block` vs `inline`。混在も可)。
4. **各スタンプを 3 字以内に切る**(inline・block <img src="https://mojiemoji.jozo.beer/emoji/%E5%85%B1%E9%80%9A?font=maru-bold&amp;color=facc15&amp;animation=bure&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="共通" height="24" align="absmiddle">)。4 字以上のフレーズは左から 2 字ずつ厳密にチャンク化(<img src="https://mojiemoji.jozo.beer/emoji/%E6%9C%AB%E5%B0%BE?font=tamanegi&amp;color=22d3ee&amp;animation=chirichiri&amp;background=transparent&amp;outline=b20891&amp;outline_width=2" alt="末尾" height="24" align="absmiddle"> 1 字は許容)し、隣接する独立スタンプとしてセパレータ無しでレンダリングする。チャンクごとに font / color / animation を選ぶ。長さ<img src="https://mojiemoji.jozo.beer/emoji/%E8%A6%8F%E5%89%87?font=mincho&amp;color=a855f7&amp;animation=gatagata&amp;background=transparent&amp;outline=f7a855&amp;outline_width=2" alt="規則" height="24" align="absmiddle">・<img src="https://mojiemoji.jozo.beer/emoji/%E5%88%86%E5%89%B2?font=hachimaru&amp;color=d946ef&amp;animation=kaiten&amp;speed=slow&amp;background=transparent&amp;outline=efd946&amp;outline_width=2" alt="分割" height="24" align="absmiddle">ヒューリスティックは `references/parameters.md` § スタンプ<img src="https://mojiemoji.jozo.beer/emoji/%E5%AF%BE%E8%B1%A1?font=maru-bold&amp;color=8b5cf6&amp;animation=psycho&amp;background=transparent&amp;outline_width=0" alt="対象" height="24" align="absmiddle">の選定と長さ<img src="https://mojiemoji.jozo.beer/emoji/%E4%B8%8A%E9%99%90?font=toge&amp;color=60a5fa&amp;animation=yoko_scroll&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="上限" height="24" align="absmiddle"> を<img src="https://mojiemoji.jozo.beer/emoji/%E5%8F%82%E7%85%A7?font=mincho&amp;color=60a5fa&amp;animation=tate_scroll&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="参照" height="24" align="absmiddle">。
5. パラメータを選ぶ:
   - **単一フレーズ・単一の自明なプリセット**: まず `references/flavor-guide.md` でそのフレーズがスタンプ<img src="https://mojiemoji.jozo.beer/emoji/%E4%BE%A1%E5%80%A4?font=rampart&amp;color=facc15&amp;animation=tatemoya&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="価値" height="24" align="absmiddle">ありか<img src="https://mojiemoji.jozo.beer/emoji/%E7%A2%BA%E8%AA%8D?font=gothic-bold&amp;color=d946ef&amp;animation=zairu&amp;background=transparent&amp;outline=efd946&amp;outline_width=2" alt="確認" height="24" align="absmiddle">し、次に `references/presets.md` で 1 行を引いて、スクリプトを直接呼ぶ。subagent は<img src="https://mojiemoji.jozo.beer/emoji/%E4%B8%8D%E8%A6%81?font=akzk&amp;color=60a5fa&amp;animation=kirari&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="不要" height="24" align="absmiddle">。
   - **それ以外**(2 フレーズ以上 / バリエーション / カタ<img src="https://mojiemoji.jozo.beer/emoji/%E3%83%AD%E3%82%B0?font=dela&amp;color=facc15&amp;animation=mabataki&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="ログ" height="24" align="absmiddle"> / <img src="https://mojiemoji.jozo.beer/emoji/%E8%B6%A3%E6%97%A8?font=toge&amp;color=fb7185&amp;animation=bane&amp;background=transparent&amp;outline=85fb71&amp;outline_width=2" alt="趣旨" height="24" align="absmiddle">が曖昧 / トーン指定あり)は **必ず `mojiemoji-selector` subagent にデリゲート**する。references をメインスレッドに読み込まない。
   - **強い<img src="https://mojiemoji.jozo.beer/emoji/%E7%A6%81%E6%AD%A2?font=tamanegi&amp;color=22c55e&amp;animation=kira&amp;background=transparent&amp;outline_width=0" alt="禁止" height="24" align="absmiddle">: パラメータを固定して直接スクリプトをフレーズごとにループ呼び出ししない。** ファスト<img src="https://mojiemoji.jozo.beer/emoji/%E3%83%91%E3%82%B9?font=chikara&amp;color=facc15&amp;animation=patapata&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="パス" height="24" align="absmiddle">は単一フレーズ専用。`mojiemoji_markdown.py` を<img src="https://mojiemoji.jozo.beer/emoji/%E5%90%8C%E3%81%98?font=mincho&amp;color=a78bfa&amp;animation=yatta&amp;background=transparent&amp;outline=ed7c3a&amp;outline_width=2" alt="同じ" height="24" align="absmiddle"> `--font --color --animation --speed` で 2 回以上呼ぶのは、issue #166 の単調本文を生んだ仕組みそのもの(15 スタンプ全て `font=maru-bold color=60a5fa animation=spring speed=normal`)。複数フレーズの仕事は常に `mojiemoji-selector` にデリゲートし、Hard contract の多様性<img src="https://mojiemoji.jozo.beer/emoji/%E8%A6%8F%E5%89%87?font=mincho&amp;color=a855f7&amp;animation=gatagata&amp;background=transparent&amp;outline=f7a855&amp;outline_width=2" alt="規則" height="24" align="absmiddle">を本文<img src="https://mojiemoji.jozo.beer/emoji/%E5%85%A8%E4%BD%93?font=gothic-bold&amp;color=8b5cf6&amp;animation=tenmetsu&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="全体" height="24" align="absmiddle">に適用させる。
6. 返ってきたスニペットを核に最終的なメッセージを組み立てる。周辺の散文は自然に保ち、inline ではスタンプを強調として機能させる。
7. **本文向け(issue 本文 / <img src="https://mojiemoji.jozo.beer/emoji/PR?font=hachimaru&amp;color=ef4444&amp;animation=bure&amp;background=transparent&amp;outline=44ef44&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> 本文 / リリースノート、loud トーン)**:
   - **飽和のデフォルト — インライン密度: 1 段落あたりスタンプ 1〜2 個。** 各段落で最も強調すべき<img src="https://mojiemoji.jozo.beer/emoji/%E3%82%AD%E3%83%BC?font=noto&amp;color=06b6d4&amp;animation=mochimochi&amp;background=transparent&amp;outline=d406b6&amp;outline_width=2" alt="キー" height="24" align="absmiddle">ワードを選ぶ。アイデアを担う箇条書き(<img src="https://mojiemoji.jozo.beer/emoji/%E4%BB%95%E6%A7%98?font=rampart&amp;color=d946ef&amp;animation=gatagata&amp;background=transparent&amp;outline=efd946&amp;outline_width=2" alt="仕様" height="24" align="absmiddle"> / 受け入れ条件)では、文法的に収まる名詞・動詞をすべて埋め込む。飽和は「全単語にスタンプする」という意味ではなく、「選択性を保ちつつ一貫した装飾感を出す」こと。コード片 / <img src="https://mojiemoji.jozo.beer/emoji/%E8%AD%98%E5%88%A5?font=dela&amp;color=fdba74&amp;animation=psycho&amp;background=transparent&amp;outline_width=0" alt="識別" height="24" align="absmiddle">子 / リンクを含むセクション(<img src="https://mojiemoji.jozo.beer/emoji/%E5%A4%89%E6%9B%B4?font=gothic&amp;color=22d3ee&amp;animation=tate_scroll&amp;background=transparent&amp;outline=b20891&amp;outline_width=2" alt="変更" height="24" align="absmiddle">ファイル、<img src="https://mojiemoji.jozo.beer/emoji/%E3%83%86%E3%82%B9%E3%83%88?font=zero&amp;color=a78bfa&amp;animation=chirichiri&amp;background=transparent&amp;outline=ed7c3a&amp;outline_width=2" alt="テスト" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E7%B5%90%E6%9E%9C?font=zero&amp;color=c084fc&amp;animation=mozaiku&amp;background=transparent&amp;outline=fcc084&amp;outline_width=2" alt="結果" height="24" align="absmiddle">、references)では、シンボル・<img src="https://mojiemoji.jozo.beer/emoji/%E8%AD%98%E5%88%A5?font=dela&amp;color=fdba74&amp;animation=psycho&amp;background=transparent&amp;outline_width=0" alt="識別" height="24" align="absmiddle">子そのものはスタンプしないが、周辺の<img src="https://mojiemoji.jozo.beer/emoji/%E6%97%A5?font=toge&amp;color=a855f7&amp;animation=kirari&amp;background=transparent&amp;outline=f7a855&amp;outline_width=2" alt="日" height="24" align="absmiddle">本語散文(「<img src="https://mojiemoji.jozo.beer/emoji/%E5%B7%AE%E3%81%97%E6%9B%BF%E3%81%88?font=maru&amp;color=c084fc&amp;animation=kage_neon&amp;background=transparent&amp;outline=fcc084&amp;outline_width=2" alt="差し替え" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E5%AF%BE%E8%B1%A1?font=gothic-bold&amp;color=f97316&amp;animation=gatagata&amp;background=transparent&amp;outline=16f973&amp;outline_width=2" alt="対象" height="24" align="absmiddle">」のような関係性記述、「<img src="https://mojiemoji.jozo.beer/emoji/%E5%A4%89%E6%9B%B4?font=pixel&amp;color=c084fc&amp;animation=disco&amp;background=transparent&amp;outline_width=0" alt="変更" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E4%B8%8D%E8%A6%81?font=hachimaru&amp;color=3b82f6&amp;animation=tatemoya&amp;background=transparent&amp;outline=f63b82&amp;outline_width=2" alt="不要" height="24" align="absmiddle">の想定」のような括弧書き)は**スタンプして良いし、インライン飽和下ではすべき**。
   - ✗ **セクション末オチ装飾**(セクション<img src="https://mojiemoji.jozo.beer/emoji/%E5%BE%8C?font=noto&amp;color=60a5fa&amp;animation=kage_neon&amp;background=transparent&amp;outline=fa60a5&amp;outline_width=2" alt="後" height="24" align="absmiddle">ろの独立行 `→ <stamp1>`)は**<img src="https://mojiemoji.jozo.beer/emoji/%E7%94%9F%E6%88%90?font=maru&amp;color=facc15&amp;animation=tate_scroll&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="生成" height="24" align="absmiddle">しない**。escape valve は、ユーザーがそのターン内で block 装飾要求(「→ つけて」 / 「盛大に」)と<img src="https://mojiemoji.jozo.beer/emoji/%E6%84%8F%E5%9B%B3?font=dela&amp;color=8b5cf6&amp;animation=shuchusen&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="意図" height="24" align="absmiddle">的な<img src="https://mojiemoji.jozo.beer/emoji/%E9%85%8D%E7%BD%AE?font=toge&amp;color=4ade80&amp;animation=nami&amp;background=transparent&amp;outline=4a16a3&amp;outline_width=2" alt="配置" height="24" align="absmiddle">指示の両方を明示した場合のみ。
   - ✗ **締めの装飾**(本文末の `---` + 独立行ムードスタンプ)は**<img src="https://mojiemoji.jozo.beer/emoji/%E7%94%9F%E6%88%90?font=maru&amp;color=facc15&amp;animation=tate_scroll&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="生成" height="24" align="absmiddle">しない**。<img src="https://mojiemoji.jozo.beer/emoji/%E5%90%8C%E6%A7%98?font=chikara&amp;color=f472b6&amp;animation=ekken&amp;background=transparent&amp;outline=77db27&amp;outline_width=2" alt="同様" height="24" align="absmiddle"> escape valve のみ。
8. **貼り付け<img src="https://mojiemoji.jozo.beer/emoji/%E5%89%8D?font=maru&amp;color=8b5cf6&amp;animation=yokomoya&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="前" height="24" align="absmiddle">に必ず<img src="https://mojiemoji.jozo.beer/emoji/%E6%A4%9C%E8%A8%BC?font=gothic&amp;color=22c55e&amp;animation=nami&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="検証" height="24" align="absmiddle">する。** スニペット受け取り<img src="https://mojiemoji.jozo.beer/emoji/%E5%BE%8C?font=hachimaru&amp;color=f472b6&amp;animation=nami&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="後" height="24" align="absmiddle">、`references/verification.md` のスポットチェックブロックを本文<img src="https://mojiemoji.jozo.beer/emoji/%E5%85%A8%E4%BD%93?font=gothic-bold&amp;color=8b5cf6&amp;animation=tenmetsu&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="全体" height="24" align="absmiddle">に対して実行する。<img src="https://mojiemoji.jozo.beer/emoji/%E5%A4%B1%E6%95%97?font=maru-bold&amp;color=3b82f6&amp;animation=yokomoya&amp;background=transparent&amp;outline=f63b82&amp;outline_width=2" alt="失敗" height="24" align="absmiddle">があればローカルで直す(または再ディスパッチ)してから貼り付ける。
9. 本文が固まったら `scripts/coverage.py --surface <...>` で最低密度/文ヒット率/段落偏りを測る。<img src="https://mojiemoji.jozo.beer/emoji/%E8%AD%A6%E5%91%8A?font=gothic&amp;color=fb923c&amp;animation=disco&amp;background=transparent&amp;outline_width=0" alt="警告" height="24" align="absmiddle">が出たら装飾を足し、hook 経路で block したい時は `--mode block` を使う。
10. ユーザーが実際に投稿するよう依頼してきたら、まず文面を組み上げ、その<img src="https://mojiemoji.jozo.beer/emoji/%E5%BE%8C?font=hachimaru&amp;color=f472b6&amp;animation=nami&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="後" height="24" align="absmiddle"> `gh` コマンドを実行する。

## デリゲーション — mojiemoji-selector subagent

`mojiemoji-selector` subagent を `Agent` ツールで `subagent_type: "mojiemoji-selector"` を指定してディスパッチする。引数は以下のコントラクト形式で渡す:

```
SURFACE: <issue-body|pr-body|review-summary|review-inline-comment|reply|release-note>
MODE:    <block|inline|mixed>
TONE:    <calm|neutral|loud>
PHRASES:
- <phrase> — <intent in one short clause>
- <phrase> — <intent>
CONSTRAINTS (optional):
- <e.g. "avoid red", "match thread tone">
SKILL_DIR: ${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github
```

`SKILL_DIR` は絶対<img src="https://mojiemoji.jozo.beer/emoji/%E3%83%91%E3%82%B9?font=pixel&amp;color=a78bfa&amp;animation=mabataki&amp;background=transparent&amp;outline=ed7c3a&amp;outline_width=2" alt="パス" height="24" align="absmiddle">で渡し、subagent が推測しなくて済むようにする。subagent はコンパクトな `phrase | mode | snippet` の表を返す。それ以外はコンテキストに入らない。

`model: opus` にエスカレートするのは、ユーザーが大型カタ<img src="https://mojiemoji.jozo.beer/emoji/%E3%83%AD%E3%82%B0?font=dela&amp;color=facc15&amp;animation=mabataki&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="ログ" height="24" align="absmiddle">や細かい趣味調整を求めるときだけ。多くのケースでデフォルトの `sonnet` で十分。

### Python / cross-boundary interop

複数 <img src="https://mojiemoji.jozo.beer/emoji/PR?font=maru&amp;color=34d399&amp;animation=gatagata&amp;background=transparent&amp;outline=9934d3&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> / 複数 issue を batch で投稿するときに Python (or Ruby / Node) で body テンプレートを組み立てたくなる場面がある。**Python 側で mojiemoji <img src="https://mojiemoji.jozo.beer/emoji/URL?font=noto&amp;color=8b5cf6&amp;animation=kaiten&amp;speed=slow&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="URL" height="24" align="absmiddle"> を文字列<img src="https://mojiemoji.jozo.beer/emoji/%E7%94%9F%E6%88%90?font=maru&amp;color=facc15&amp;animation=tate_scroll&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="生成" height="24" align="absmiddle">してはいけない** — `?text=<text>&background=transparent` だけ並べた `mj(text)` ヘルパーは、6 <img src="https://mojiemoji.jozo.beer/emoji/%E5%BF%85%E9%A0%88?font=dela&amp;color=22c55e&amp;animation=patapata&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="必須" height="24" align="absmiddle">パラメータを<img src="https://mojiemoji.jozo.beer/emoji/%E6%AC%A0%E8%90%BD?font=gothic&amp;color=fb923c&amp;animation=tate_scroll&amp;background=transparent&amp;outline=0cea58&amp;outline_width=2" alt="欠落" height="24" align="absmiddle">して dark mode 不可視のスタンプを大量生産する(2026-05-12 triage-review の 7 <img src="https://mojiemoji.jozo.beer/emoji/PR?font=toge&amp;color=3b82f6&amp;animation=zairu&amp;background=transparent&amp;outline=f63b82&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> で実例、`references/colors.md` § 過去 incident を<img src="https://mojiemoji.jozo.beer/emoji/%E5%8F%82%E7%85%A7?font=pixel&amp;color=60a5fa&amp;animation=zanzo&amp;background=transparent&amp;outline=fa60a5&amp;outline_width=2" alt="参照" height="24" align="absmiddle">)。

2 つの正解経路:

1. **subprocess 経由でヘルパースクリプトを叩く**:
   ```python
   import subprocess
   def render(text, font, color, anim):
       return subprocess.run(
           [HELPER, "--text", text, "--inline",
            "--font", font, "--color", color,
            "--animation", anim,
            "--outline", "triadic", "--outline-width", "2"],
           capture_output=True, text=True, check=True
       ).stdout.strip()
   ```
   毎フレーズで font / color / animation を変えること(さもなくば issue #166 の単調本文と<img src="https://mojiemoji.jozo.beer/emoji/%E5%90%8C%E3%81%98?font=hachimaru&amp;color=f472b6&amp;animation=yurayura&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="同じ" height="24" align="absmiddle">轍を踏む)。
2. **`mojiemoji-selector` に先にバッチをレンダリングさせる**: subagent からスニペット表を受け取り、Python 側ではそれを*不透明な `<img>` 文字列*として変数展開のみする。Python は body 組み立ての糊にとどめ、<img src="https://mojiemoji.jozo.beer/emoji/URL?font=noto&amp;color=8b5cf6&amp;animation=kaiten&amp;speed=slow&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="URL" height="24" align="absmiddle"> クエリには触れない。

PreToolUse hook は `python3 X.py && gh api --input out.json` のような compound コマンドのスクリプト本体まで読みに行く(`mojiemoji_japanese_gate.py` の `SCRIPT_RE`)。中間 JSON がまだ<img src="https://mojiemoji.jozo.beer/emoji/%E5%AD%98%E5%9C%A8?font=maru-bold&amp;color=3b82f6&amp;animation=disco&amp;background=transparent&amp;outline_width=0" alt="存在" height="24" align="absmiddle">しない瞬間でも、スクリプト中の <img src="https://mojiemoji.jozo.beer/emoji/URL?font=pixel&amp;color=f87171&amp;animation=ekken&amp;background=transparent&amp;outline=26dc26&amp;outline_width=2" alt="URL" height="24" align="absmiddle"> テンプレートは<img src="https://mojiemoji.jozo.beer/emoji/%E6%A4%9C%E8%A8%BC?font=tamanegi&amp;color=06b6d4&amp;animation=yoko_scroll&amp;background=transparent&amp;outline=d406b6&amp;outline_width=2" alt="検証" height="24" align="absmiddle">される。手抜きしないこと。

### Hard contract — 逐語で `CONSTRAINTS` に含める行

subagent は歴史的にこれらを落としがちなので、**以下の行を逐語で `CONSTRAINTS` に含める**こと。これでスニペットがすり抜けない:

```
- Every URL MUST include &background=transparent
- Animation MUST come from the canonical list (see references/parameters.md § Valid animation values). For rotational animations (`kaiten`, `spin`) pair with `speed=step` or `slow` — they are unreadable at `normal`/`fast`
- Font MUST come from the canonical list (see references/parameters.md § Valid font values); never `della` (correct: `dela`)
- Color MUST be dark-mode-safe (Tailwind 300–500 range; never 600+ or near-black). See references/parameters.md § Dark-mode-safe color palette.
- For inline mode: height=20 is the observed user default. **Confirmed block-only**: `bakusan` (radial-burst obscures letterforms at small heights). **Likely problematic inline**: `chuuou_zoom`, `mozaiku`, `kage_*` shadow effects. Substitute `gatagata` / `bure` / `tenmetsu` / `shuchusen` / `zanzo` for inline impact moods.
- For inline mode with 4+ char phrases: split into two adjacent single-line stamps (matching font/color/animation), do NOT use `%0A` line break in the URL
- Outline: use `outline=darker outline_width=2` (auto-relative dark halo per stamp). Never use `outline=ffffff` — white blends with light Tailwind 300–400 fills and erases the letterform edges.
- **Animation diversity**: across the full PHRASES list, use **12+ distinct values** from the canonical 34 (see references/parameters.md § Valid animation values). **No animation may appear more than 2×** across distinct terms. Same-term recurrences (e.g. 仕様 × 5) are exempt — count distinct *terms*, not occurrences. Single-animation bodies are the issue #166 anti-pattern.
- **Underused tier requirement**: include at least **3 stamps using animations from the underused tier** (ekken, tate_ekken, neruneru, patapata, mabataki, mozaiku, tatemoya, yokomoya, zairu, zanzo, chirichiri, kage_kaiten, kage_bokashi, kage_neon, kirari, yatta, kaiten, psycho). The user has flagged a recurring bias toward "safe defaults" (`bane`, `nami`, `mochimochi`, `bure`); this rule forces breakout from that comfort zone.
- **Font diversity**: mix at least **3–4 distinct fonts** from the canonical 16. Picking display fonts (`akzk`, `zero`, `kurobara`, `hachimaru`, `chikara`, `tamanegi`, `toge`, `rampart`) for the loudest words and `gothic-bold` / `maru-bold` / `noto` for readability-sensitive ones works well.
- **Color diversity**: use **4+ distinct hex values** across the body, all from the dark-mode-safe palette (Tailwind 300–500). Single-color body is also the #166 anti-pattern (15 stamps, all `60a5fa`).
- FLAVOR GATE OVERRIDE (saturation / loud tone): render EVERY phrase in the PHRASES list. Do NOT skip with "do-not-stamp" reasoning unless the phrase is literally an API name, file path, version string, code identifier, or apology/legal/compliance text. Multi-char Japanese tech nouns and verbs (紐付け, 同居, 修正, 準拠, ユニット, 検証, 検討, 実装, 反映, 伝播, 報告, etc.) ARE stampable. See SKILL.md § Saturation Mode for the concrete stampable list. If unsure, render — the main thread spot-checks before pasting.
```

## 飽和<img src="https://mojiemoji.jozo.beer/emoji/%E5%88%B6%E7%B4%84?font=dela&amp;color=d946ef&amp;animation=yatta&amp;background=transparent&amp;outline=efd946&amp;outline_width=2" alt="制約" height="24" align="absmiddle">ブロック(mojiemoji-selector ディスパッチに貼り付ける)

```
TONE: loud
MODE: inline
CONSTRAINTS:
- FLAVOR GATE OVERRIDE: render factual/design terms; do not skip.
- All inline; height=20 (matches user's observed body style)
- Animation required; only use names from the canonical 34 in references/parameters.md. Rotational animations (`kaiten`, or `spin` if present) require `speed=step` or `slow` — `normal`/`fast` is unreadably fast for rotational glyphs
- Animation diversity: 12+ distinct values across the body; no animation more than 2× across distinct terms
- Include at least 3 picks from the underused tier (ekken, tate_ekken, neruneru, patapata, mabataki, mozaiku, tatemoya, yokomoya, zairu, zanzo, chirichiri, kage_kaiten, kage_bokashi, kage_neon, kirari, yatta, kaiten, psycho)
- Avoid reusing the "safe defaults" (bane, nami, mochimochi, bure) more than once each per body — they're the historical bias the user has flagged
- Avoid animation=bakusan inline (radial-burst obscures letterforms — block-only). Likely-problematic inline: chuuou_zoom, mozaiku, kage_*. Prefer gatagata / bure / tenmetsu / shuchusen / zanzo for inline impact
- Font diversity: mix at least 3–4 distinct fonts from the canonical 17 (see references/parameters.md § Valid font values)
- Color: dark-mode-safe (Tailwind 300–500 range), bias toward 300–400
- background=transparent in every URL
- outline=darker outline_width=2 in every URL (auto-relative dark halo per stamp; never use outline=ffffff — white blends with light Tailwind 300–400 fills)
- Inline only. Do NOT generate own-line "→ <stamps>" section punch-line decoration or "---" + closing flair stamps. For trailing flair at sentence/heading end, use an emoji — prefer mojiemoji-rendered if the emoji is in data/emoji-catalog.yml (162 supported, includes 🎉 🔥 ✨ 💯 ⚠ ❤ 😂 🎊 🚨 🤖 etc.), fall back to plain Unicode for unsupported codepoints (e.g. 🚀 = U+1F680, 🪐 = U+1FA90).
```

## 直接スクリプト(単一フレーズのファスト<img src="https://mojiemoji.jozo.beer/emoji/%E3%83%91%E3%82%B9?font=chikara&amp;color=facc15&amp;animation=patapata&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="パス" height="24" align="absmiddle">)

```bash
# Block
scripts/mojiemoji_markdown.py --text 'レビュー歓迎' \
  --font maru-bold --color 3b82f6 --animation bane --speed slow

# Inline (height=24 align=absmiddle)
scripts/mojiemoji_markdown.py --text 'マジで' --inline \
  --font maru-bold --color ef4444 --animation bure --speed normal
```

オプション: `--text`, `--alt`, `--html`, `--inline`, `--height`, `--width`, `--align`, `--font`, `--color`, `--animation`, `--speed`, `--gradient`, `--flip`, `--padding`, `--background`, `--outline`, `--outline-width`, `--path`, `--query`, `--base-url`。

`--background` のデフォルトは `transparent` で、明示的に上書きしない限りすべての <img src="https://mojiemoji.jozo.beer/emoji/URL?font=kurobara&amp;color=facc15&amp;animation=mozaiku&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="URL" height="24" align="absmiddle"> に適用される。`--outline` はオプトイン(body-class surface では<img src="https://mojiemoji.jozo.beer/emoji/%E6%8E%A8%E5%A5%A8?font=mincho&amp;color=eab308&amp;animation=mabataki&amp;background=transparent&amp;outline=08eab3&amp;outline_width=2" alt="推奨" height="24" align="absmiddle">)。

## Surface ごとの top/closing 装飾ヒューリスティック

飽和インライン埋め込みは全 surface <img src="https://mojiemoji.jozo.beer/emoji/%E5%85%B1%E9%80%9A?font=maru-bold&amp;color=facc15&amp;animation=bure&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="共通" height="24" align="absmiddle">だが、**先頭文と締めの文**(段落として独立して読まれやすい箇所)はトーンが surface タイプによって変わる。以下の表で「先頭文に埋め込みやすい語」と「締めに埋め込みやすい語」を引き当てる。装飾するのは独立行 block ではなく**その文の中の語**。

### Issue 本文(`gh issue create`)

| Issue タイプ | 先頭文に埋め込む語(例) | 締め文に埋め込む語(例) | トーン |
|---|---|---|---|
| Bug / <img src="https://mojiemoji.jozo.beer/emoji/%E4%B8%8D?font=zero&amp;color=8b5cf6&amp;animation=norinori&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="不" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E5%85%B7%E5%90%88?font=zero&amp;color=8b5cf6&amp;animation=norinori&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="具合" height="24" align="absmiddle"> | `バグ` / `要対応` / `不具合` / `致命` | `修正` / `対応` / `お願い` | cautionary — 祝祭は避ける |
| Feature / 機能要望 | `機能` / `提案` / `新規` / `導入` | `よろしく` / `お願い` / `歓迎` | anticipatory neutral |
| Refactor / <img src="https://mojiemoji.jozo.beer/emoji/%E6%95%B4%E5%82%99?font=rampart&amp;color=facc15&amp;animation=kage_bokashi&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="整備" height="24" align="absmiddle"> | `整備` / `整理` / `改善` / `刷新` | `お願い` / `レビュー` | neutral |
| Chore / 雑務 | `雑務` / `整備` / `更新` | (装飾控えめ) | minimal |
| Cosmetic / 微調整 | (装飾控えめ、1 スタンプで足る場合あり) | — | light |

### <img src="https://mojiemoji.jozo.beer/emoji/PR?font=maru&amp;color=34d399&amp;animation=gatagata&amp;background=transparent&amp;outline=9934d3&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> 本文(`gh pr create`)

| <img src="https://mojiemoji.jozo.beer/emoji/PR?font=hachimaru&amp;color=ef4444&amp;animation=bure&amp;background=transparent&amp;outline=44ef44&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> タイプ | 先頭文に埋め込む語(例) | 締め文に埋め込む語(例) | トーン |
|---|---|---|---|
| feat / 新機能 | `新機能` / `機能` / `実装` / `追加` | `レビュー` / `よろしく` / `歓迎` | positive momentum |
| fix / <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%90%E3%82%B0?font=kurobara&amp;color=fb7185&amp;animation=tenmetsu&amp;background=transparent&amp;outline=85fb71&amp;outline_width=2" alt="バグ" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3?font=dela&amp;color=eab308&amp;animation=disco&amp;background=transparent&amp;outline_width=0" alt="修正" height="24" align="absmiddle"> | `修正` / `対応` / `バグ` / `解決` | `確認` / `よろしく` | reassuring |
| refactor / <img src="https://mojiemoji.jozo.beer/emoji/%E6%95%B4%E7%90%86?font=zero&amp;color=f87171&amp;animation=chirichiri&amp;background=transparent&amp;outline=26dc26&amp;outline_width=2" alt="整理" height="24" align="absmiddle"> | `整理` / `整備` / `綺麗` / `刷新` | `レビュー` / `よろしく` | clean / satisfied |
| chore / deps | `更新` / `整備` / `同期` | (装飾控えめ) | neutral |
| docs | `加筆` / `更新` / `整理` | `確認` | neutral / light |

### Review summary body(`gh pr review` / `gh api .../reviews`)

`verdict × finding-count` で summary body のトーンが決まる。inline `comments[].body` も<img src="https://mojiemoji.jozo.beer/emoji/%E5%90%8C%E3%81%98?font=hachimaru&amp;color=f472b6&amp;animation=yurayura&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="同じ" height="24" align="absmiddle"> review-class surface なので、summary とは別に prestamp / selector を通す。装飾が<img src="https://mojiemoji.jozo.beer/emoji/%E9%99%A4%E5%A4%96?font=pixel&amp;color=f472b6&amp;animation=gatagata&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="除外" height="24" align="absmiddle">されるのはコード片・file path・symbol・suggestion block などの token 単位であり、comment body <img src="https://mojiemoji.jozo.beer/emoji/%E5%85%A8%E4%BD%93?font=noto&amp;color=fdba74&amp;animation=mozaiku&amp;background=transparent&amp;outline=74fdba&amp;outline_width=2" alt="全体" height="24" align="absmiddle">ではない。

| verdict | findings | 先頭文に埋め込む語(例) | 締め文に埋め込む語(例) | 備考 |
|---|---|---|---|---|
| `approve` | 0 (clean) | `完璧` / `綺麗` / `見事` / `LGTM` | `マージ` / `歓迎` / `お疲れさま` | celebratory。mojiemoji 単独なら inline / block どちらの LGTM も自由。他の LGTM-imagery skill と併用する場合のみ mojiemoji は inline に留める。 |
| `approve` | nits のみ | `綺麗` / `良い` / `軽微` | `感謝` / `お疲れさま` | thanks 寄り、celebrate しすぎない |
| `comment` | ≤2 | `確認` / `相談` / `提案` | `引き続き` / `よろしく` | tone-setter で軽く |
| `comment` | 3〜5 | `確認` / `指摘` / `検討` | `ご対応` / `よろしく` | neutral, business-like |
| `comment` | 6+ | `要点` / `観点` / `整理` | `確認` / `お願い` | matter-of-fact、スタンプ少なめでメリハリ |
| `request-changes` | — | `相談` / `観点` / `要修正` | `引き続き` / `よろしく` | cautious、pile-on しない |

`comments[].body` の散文にも inline 飽和を適用する。ただし code block / suggestion block / inline code / `<details>` / file path / symbol は safe-zone として必ず<img src="https://mojiemoji.jozo.beer/emoji/%E9%99%A4%E5%A4%96?font=maru-bold&amp;color=4ade80&amp;animation=tate_scroll&amp;background=transparent&amp;outline=4a16a3&amp;outline_width=2" alt="除外" height="24" align="absmiddle">する。review payload の `body` だけを装飾し、`comments[]` を素のまま残すのは不可。

### Reply / コメント返信(`gh api .../comments`)

返信は短いので、**1 段落 1 個の punch-line スタンプ**で足りる。`address-review` / `triage-review` 系<img src="https://mojiemoji.jozo.beer/emoji/%E3%82%B9%E3%82%AD%E3%83%AB?font=akzk&amp;color=22c55e&amp;animation=chirichiri&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="スキル" height="24" align="absmiddle">が action バッジ(`action: fixed/by design/test added/deferred/wontfix`)を先頭に置くので、その下の段落文に inline 埋め込み。

- `action: fixed` の段落 → `修正` / `対応` を埋め込む
- `action: by design` の段落 → `意図` / `仕様` / `想定` を埋め込む
- `action: test added` → `追加` / `検証` を埋め込む
- `action: deferred` → `別件` / `分離` / `分割` を埋め込む
- `action: wontfix` で純粋に技術記述(test 名 / file path / spec ref)だけならスタンプを諦める

### リリースノート(`gh release create`)

`feat` / `fix` の比率に応じて feat 寄りの語(`機能` / `新規` / `追加`)か fix 寄り(`修正` / `解決`)を先頭に。締めは「みなさんありがとうございました」系を inline 埋め込み(独立行の closing block 画像は<img src="https://mojiemoji.jozo.beer/emoji/%E7%A6%81%E6%AD%A2?font=maru&amp;color=8b5cf6&amp;animation=nami&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="禁止" height="24" align="absmiddle">)。
