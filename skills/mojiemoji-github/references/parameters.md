# Mojiemoji パラメータリファレンス

mojiemoji.jozo.beer サービスの正準パラメータ値。SKILL.md から
オンデマンドで読み込まれる(本文を組む時 / `mojiemoji-selector` に
委譲する時)。

## inline 高さ: 24 がデフォルト、20 も可

スキルが文書化しているデフォルトは `height="24"`(本文フォントサイズで
読みやすい)。ただしユーザーは実本文で `height="20"` を使うことが多い。
両方とも有効:

- `height="24"` — ユーザーの声に馴染みのない読み手 / surface 向けの、
  より安全なデフォルト。
- `height="20"` — ユーザー自身の好み。少しコンパクトでベースライン
  テキスト高さに近い。同じリポ内で既存本文の風合いに合わせたい時はこちら。

同リポ内に既存の本文が見えるときは、その `height` 選択をミラーして
視覚的整合を取ること。

## スタンプ対象の選定と長さ上限

mojiemoji は **語レベルのパンチ** であって、文をレンダリングする
手段ではない。本命の対象は **2 字熟語** — `歓迎`、`修正`、`確認`、
`完了`、`重要`、`緊急`、`対応`、`要点` 等。2〜3 字の ASCII 略語
(`PR`、`OK`、`NG`、`WIP`、`API`) と短いカタカナ語(`マージ`、
`テスト`、`バグ`) も決まりやすい。

**スタンプを完全に見送るべき** ケース:

- 文法的に文 / 節になっているもの(動詞 + 丁寧形:
  `気になりました`、`お疲れさまでした`、`書きました`)
- 挨拶ブロック(`〜していただきありがとうございます`)
- 無理矢理スタンプにすると違和感が出るもの — 同じ文の別の content word を
  選び直すか、ここはスタンプ無しで受け入れる。

ユーザーは明示的に
「文章は分割する以前に mojiemoji にしなくていい」 と
「無理してまで mojiemoji にしなくて良い場面もある」 と言っている。

**スクリプト別・1 スタンプあたりの文字数上限** — 文字種ごとにグリフ
キャンバスへの詰まり方が違うので、可読性閾値が異なる:

| 文字種 | 1 スタンプ最大字数 | 備考 |
|---|---|---|
| Kanji | **2** | 画数が多い、3 字は inline 高さで潰れる。「漢字は2文字までじゃないと読めない」 |
| Hiragana | **5** | 3 字以上は `%0A` newline で 2 行スタンプにする、各行 ≤3 字 |
| Katakana | **3** | |
| ASCII | **3** | 例: `WIP`、`API`、`LGTM`(他のスタンプと同様に扱う) |

加えて **語あたり ≤2 スタンプ**。3 連発はやらない(ユーザーは 3 個を
「きつい」、4 個を「無理」とフラグしている)。

文字種が混ざるチャンクは *すべての適用上限を満たす* こと。`お願い`
(漢 1 + 平 2) → 漢字 1 ≤2 ✓、平仮名 2 ≤5 ✓ → 1 スタンプで OK。
`修正お願` (漢 3 + 平 1) → 漢字 3 > 2 → 分割必須。

### 分割の境界ヒューリスティック

機械的な 2 字ずつチャンクは語を切り刻む(例: `マージ歓迎` → `マー` +
`ジ歓` で `マージ` を語の途中で切る)。優先順:

1. **文字種の遷移** — カタカナ ↔ 漢字 ↔ ひらがな の境界。
2. **複合語形態素の境界** — `修正お願い` → `修正` + `お願い`、
   `引き続き` → `引き` + `続き`。
3. **2 字ずつのフォールバック** — きれいな縫い目が無いときは 2 + 残り
   で割り、各チャンクが文字種別の上限を満たすようにする。

具体例:

| 語 | 構成 | 扱い |
|---|---|---|
| `修正` `歓迎` `確認` | 漢 2 | 1 スタンプ |
| `PR` `OK` `API` | ASCII 2–3 | 1 スタンプ |
| `マージ` `テスト` | カタ 3 | 1 スタンプ |
| `緊急対応` | 漢 4 | 分割: `緊急` + `対応` |
| `具体策` | 漢 3 | 分割: `具体` + `策` |
| `マージ歓迎` | カタ 3 + 漢 2 | 分割: `マージ` + `歓迎` (文字種遷移) |
| `修正お願い` | 漢 2 + 平 1 + 漢 1 + 平 1 | 分割: `修正` + `お願い` |
| `引き続き` | 漢 1 + 平 1 + 漢 1 + 平 1 | 分割: `引き` + `続き` (形態素縫い目) |
| `よろしく` | 平 4 | 1 スタンプ `よろ\nしく` (`%0A` 2+2) |
| `おはよう` `おやすみ` | 平 4 | 1 スタンプ `おは\nよう` / `おや\nすみ` |
| `そうだね` | 平 4 | 1 スタンプ `そう\nだね` |
| `ありがとう` | 平 5 | 1 スタンプ `ありが\nとう` (`%0A` 3+2) |
| `おつかれさま` | 平 6 | 分割: `おつかれ` (`%0A` 2+2) + `さま` |

**`%0A` newline はひらがな専用。** 漢字とカタカナの画は窮屈な
2 行キャンバスで潰れる。漢字 / カタカナが少しでも含まれる語は
複数スタンプ分割を使う、`%0A` はダメ。

### レンダリング方法

```bash
# 単一スタンプ・単一行 (1–3 字の典型ケース):
python3 scripts/mojiemoji_markdown.py --text '修正' --inline ...

# 2 スタンプ分割: チャンクを別々にレンダリングして inline で連結
# (区切り無し):
python3 scripts/mojiemoji_markdown.py --text 'マージ' --inline ...
python3 scripts/mojiemoji_markdown.py --text '歓迎'   --inline ...

# ひらがな 3–5 字を %0A newline で 1 スタンプ 2 行に。
# --text にはリテラルな \n を渡す; スクリプトが %0A に URL エンコードする:
python3 scripts/mojiemoji_markdown.py --text $'よろ\nしく' --inline ...
python3 scripts/mojiemoji_markdown.py --text $'ありが\nとう' --inline ...
```

## 有効な animation 値(正準リスト)

mojiemoji サービスは未知の animation 名を受け取ると **無音で静止画**
にレンダリングする。このリストの値しか使ってはいけない — 他はエラーも
吐かずに通る。**ボキャブラリは前回キャッシュされた仕様から大幅に拡張
された; 古い英語名の多くが日本語ローマ字にリネームされた**
(例: 旧 `spring` は今は `bane`、`wave` は `nami`、`scroll` は
`yoko_scroll`、`blink` は `mabataki`、`kanpai` は `yatta`、
`roulette` は `kaiten`、`strobe` は `disco` / `psycho`、
`buruburu` は `bure`)。以下の現行名を使うこと。

```
tate_scroll, yoko_scroll, ekken, tate_ekken, bane, gatagata, bure,
chuuou_zoom, kirari, kira, tenmetsu, shuchusen, kaiten, neruneru,
patapata, yurayura, mabataki, bakusan, norinori, mochimochi, mozaiku,
poyoon, yatta, tatemoya, nami, yokomoya, zairu, zanzo, chirichiri,
disco, psycho, kage_kaiten, kage_bokashi, kage_neon
```

合計 34 種類 — 過去の 16 種から大きく増えた。下の多様性ルールは
この幅広さを活かす。

避けるべきよくある不正値: `rotate`、`bounce`、`shake`、`hooo`(過去
バッチで観測されたタイポ、存在せず静止画にフォールバック)、`poyon`
(正: `poyoon` — 母音 2 個)、`funwari`(存在せず — 似た浮遊感が欲しい
ときは `yurayura` / `mochimochi`)、加えてリネームされた古い英語名
(`spring`、`wave`、`scroll`、`blink`、`kanpai`、`roulette`、`strobe`、
`buruburu`)。`spin` のような rotational animation は **`speed=step`
または `slow` の時のみ可読** で、
`normal` / `fast` では回転が速すぎて読めなくなる — 現行サービスでは
`kaiten`(回転) と `kage_kaiten`(影付き回転) の 2 つが該当する正準名。
両方とも hook (`mojiemoji_japanese_gate.py`) が `speed=step|slow` 以外
(省略含む、デフォルトはサービス側で fast 相当) を拒否する。helper
script (`scripts/mojiemoji_markdown.py`) は `--animation kaiten` /
`--animation kage_kaiten` を受け取って `--speed` 未指定なら自動で
`speed=slow` を注入するので、helper 経由なら気にしなくて良い。名前が
現行か怪しいときは `skills/mojiemoji-github/scripts/verify-lists-vs-service.sh` を走らせる —
hook の allowlist とライブサービスを diff し、ドリフトがあれば非ゼロで
終了する(§ パラメータが効かなくなったとき を参照)。

ほとんどの animation は inline で有効。**block 専用と確認済: `bakusan`**
— 放射バーストの動きがデフォルト `height="20"–"24"` で内側の
letterform を覆ってしまう。`bakusan` は block モード専用に
(独立行で `height ≥ 24` がバーストを吸収できる場面で) 取っておく。

**inline で問題が出やすい(使う前にテスト)**: `chuuou_zoom`
(中央ズーム — 小サイズで letterform を覆うのは同様)、`mozaiku`
(モザイク — テキストがピクセルになる)、`kage_*` 系の影エフェクト
(20px ではクリアな前景が残らない可能性)。inline で「衝撃 / 緊急 /
爆発」系のムードが欲しいときは、`gatagata`(ガタガタ)、`bure`(ブレ)、
`tenmetsu`(点滅)、`shuchusen`(集中線)、`zanzo`(残像) — どれも
小サイズで読みやすい。

同じ文に loud な animation を 3 個チェーンしない — 既存の
「1 文あたり inline 最大 2 個」ルール(飽和モードで緩む) が自然な
ペーシングガードになる。

### animation の多様性(単調さ防止)

**animation 選択は正準リスト全体に広く散らす。** 20 スタンプ全部が
`bane` の本文は単調 — ユーザーが繰り返しフラグした失敗モード。34 種の
animation がある以上、過去の「8 種 distinct を下限」は緩すぎる。
**body-class surface あたり 12 種以上の distinct な animation** を
目指し、**1 つの animation が distinct な語にまたがって 2 回以上
出ない** ようにする。

ユーザーは、小さな「安全デフォルト」セット(歴史的な
`spring/wave/mochimochi/buruburu` の 4 つ、今の名前で
`bane/nami/mochimochi/bure`) に偏るバイアスを観測している。この
バイアスを打ち破るには、本文ごとに **「underused tier」から最低 3 個**
を引いてくる:

```
ekken, tate_ekken, neruneru, patapata, mabataki, mozaiku, tatemoya,
yokomoya, zairu, zanzo, chirichiri, kage_kaiten, kage_bokashi,
kage_neon, kirari, yatta, kaiten, psycho
```

おおまかなムード→ animation マッピング(あくまで出発点のパレット、
ロックインではない — 「安全」な候補が出ても underused tier から
広げて引くこと)。ほとんどの animation は `block` でも `inline` でも
動く; block 専用 / inline 注意は右端の列に記す:

| ムード | inline で安全な候補 | block 推奨 / inline 危険 |
|---|---|---|
| 祝福 / 完了 | `bane`, `kira`, `kirari`, `yatta`, `norinori`, `disco`, `kage_neon` | `bakusan` |
| 緊急 / 警告 / 衝撃 | `gatagata`, `bure`, `tenmetsu`, `shuchusen`, `zanzo` | `bakusan`, `chuuou_zoom` |
| 発見 / 焦点 | `mabataki`, `tenmetsu`, `kaiten`, `tate_scroll`, `yoko_scroll` | `chuuou_zoom` |
| ソフト / 穏やか / ステータス | `yurayura`, `poyoon`, `mochimochi`, `nami`, `neruneru`, `chirichiri`, `patapata` | — |
| エネルギー / 勢い | `norinori`, `bane`, `yatta`, `patapata`, `disco` | `bakusan` |
| ムードピボット / ポップ | `poyoon`, `kira`, `kirari`, `kage_neon` | `psycho` (激しめ) |
| エフェクト / テクスチャ | `mozaiku`, `tatemoya`, `yokomoya`, `zairu`, `kage_kaiten`, `kage_bokashi` | `psycho`, `mozaiku` |
| スクロール / 連続 | `tate_scroll`, `yoko_scroll`, `ekken`, `tate_ekken`, `kaiten` | — |

`mojiemoji-selector` に委譲するときは、明示的な制約を渡すこと:

```
- Animation diversity: across the full PHRASES list, use at least 12
  distinct values from the canonical 34. No animation should appear
  more than 2× across distinct terms. Include at least 3 picks from
  the underused tier (ekken, tate_ekken, neruneru, patapata, mabataki,
  mozaiku, tatemoya, yokomoya, zairu, zanzo, chirichiri, kage_kaiten,
  kage_bokashi, kage_neon, kirari, yatta, kaiten, psycho). Avoid
  reusing the same "safe defaults" (bane, nami, mochimochi, bure)
  more than once each per body. Same-term recurrences (e.g., 仕様 × 5)
  count as one term and may keep a stable animation for visual
  consistency.
```

同じ語が繰り返し出るとき(例: `仕様` が 5 回)は、**1 本文の中では**
その animation/font/color を安定させて視覚的整合を取って良い。多様性
ルールは distinct な語の間に効くもので、同じ語の反復出現には効かない。

## 有効な font 値(正準リスト)

```
gothic, gothic-bold, maru, maru-bold, mincho, dela, akzk, zero,
kurobara, hachimaru, chikara, tamanegi, pixel, toge, rampart, noto
```

避けるべきよくあるタイポ: `della`(正: `dela`)、`fude`(存在しない —
無音でデフォルトの mplus にフォールバック)、`noto-sans-jp`(サービスには
`noto` しかない)。ライブリストは 16 エントリ。このリストとライブ
サービス間のドリフトを検出するには `skills/mojiemoji-github/scripts/verify-lists-vs-service.sh`
を走らせる(ドリフトがあれば非ゼロで終了)。ディスプレイ系フォント
(`akzk`、`zero`、`kurobara`、`hachimaru`、`chikara`、`tamanegi`、
`toge`、`rampart`) は一番うるさい語に向く; `gothic-bold` /
`maru-bold` / `noto` は可読性重視の選択肢。font も散らすこと —
全スタンプが `maru-bold` の本文は単調。本文ごとに 3〜4 種類は混ぜる。

## 有効な speed 値

```
step, slow, normal, fast
```

`step` はキャッシュ仕様以降に追加されたフレーム送りバリアント — animation
を滑らかではなく機械的・ピクセル的に見せたい時に有用。未指定時の
デフォルトは `~40ms/frame` 相当。

## ダークモードセーフな color パレット

GitHub のダークテーマ背景はほぼ黒(`#0d1117`)。Tailwind の 600 以上は
この背景でコントラストが低く、「黒地に黒」に見える(ユーザーの繰り返しの
苦情ポイント)。**300–500** に寄せる — ユーザーの観測上の好みはレンジ内の
明るい側(300–400)に傾く。

| Hue | 避ける(暗すぎる) | 推奨(明るい側を優先) |
|---|---|---|
| Red | `dc2626`, `b91c1c`, `991b1b` | `fca5a5`, `f87171`, `ef4444` |
| Orange | `c2410c` | `fdba74`, `fb923c`, `f97316`, `f59e0b` |
| Yellow | `ca8a04` | `fde047`, `facc15`, `fbbf24` |
| Green | `15803d`, `16a34a` | `86efac`, `4ade80`, `22c55e`, `34d399`, `10b981` |
| Cyan | `0e7490` | `67e8f9`, `22d3ee`, `06b6d4` |
| Blue | `1d4ed8`, `2563eb` | `93c5fd`, `60a5fa`, `3b82f6` |
| Indigo | `4338ca` | `a5b4fc`, `818cf8`, `6366f1` |
| Purple | `7e22ce` | `d8b4fe`, `c084fc`, `a855f7`, `8b5cf6`, `a78bfa` |
| Pink | `be185d` | `f9a8d4`, `f472b6`, `ec4899` |

黒・準黒(`#000000`–`#1f2937`)・かなり暗いグレーは絶対にスタンプ文字色
として使わない。脳内テスト: 「この色、黒い T シャツに乗せて読めるか?」
読めないなら明るくする。

### CSS named-color は使わない

`color=red` / `color=teal` / `color=vivid-purple` のような CSS / Tailwind
名前は **使用禁止**。mojiemoji サービスの color パーサが不整合で、
`red` / `green` / `blue` / `yellow` / `cyan` / `pink` / `orange` は
silently 200 を返す一方、`teal` / `purple` / `indigo` / `violet` /
`lime` / `brown` は 400 (`invalid color: expected 6 or 8 hex digits`)
を返す (#110)。200 を引いた場合も Tailwind 300–500 帯から外れるため
ダークモードで黒不可視になる。常に 6-digit hex を指定する。

PreToolUse hook (`hooks/gate/validators/canonical.py`) は 6-hex 必須で
gate しているため、プラグイン経由の投稿は守られている。プラグイン外
経路で named color が混入した body を投稿してしまった場合は、`gh pr
view <N> --json body --jq .body | grep -oE 'color=[a-z]+' | sort -u` で
混入語を抽出してから body を編集し直して `gh pr edit --body-file` で
再投稿する。自動 lint CLI は #110 中期案として別 issue で追跡。

## outline(body-class surface で推奨)

mojiemoji サービスは `outline`(色、hex または `darker` / `lighter`)と
`outline_width`(0〜4 px integer; 0 = outline 無し)をサポートする。
outline はスタンプにハロー(縁取り) を付けて、letterform をさまざまな
背景にアンカーする — ライト / ダーク両モードの GitHub で効く。

body-class surface(issue 本文 / PR 本文 / リリースノート)向けの
推奨デフォルト:

```
outline=triadic         # 120° 回した色相 (ユーザーの好みのデフォルト) — 塗りに対して高コントラスト
outline_width=2         # 目立つが太すぎない; 1 は控えめ、3+ は太い
```

`triadic` が今のデフォルトな理由: ダークモードセーフな塗り(Tailwind
300–500)に対し `darker` は塗りに近いハローを作り、小さな letterform で
両者が混ざる — ユーザーが明示的にフラグしたポイント。`triadic` は塗りの
色相を 120° 回して(blue → red-pink、green → purple 等) ハローを常に
別の色として読ませる、しかも輝度帯は同じなので clown 効果は出ない。

ヘルパースクリプトでの `--outline triadic` / `--outline complement` の
動き:

| flag | 色相回転 | 性格 |
|---|---|---|
| `--outline triadic` | +120° | 高コントラスト、complement ほどキツくない; ユーザーの選択 |
| `--outline complement` | +180° | 最大コントラスト; うるさく見えやすい |
| `--outline darker` | n/a (サービス側で自動 darker) | 控えめ、小サイズでは混ざる |
| `--outline lighter` | n/a (サービス側で自動 lighter) | 明るい塗りには効かないことが多い |
| `--outline <6-hex>` | n/a (リテラル) | 全スタンプ統一フレーム |

`triadic` / `complement` はクライアント側(`scripts/mojiemoji_markdown.py`)
で解決される — サービスには具体的な hex が渡る。PreToolUse hook は
`darker` / `lighter` / 6-hex を有効な outline 値として受理する。

### 色がシフトする animation(outline は省略)

`disco`、`psycho`、`kira` は塗り色をレインボー / ストロボ的に循環させる。
固定色 outline はレインボーと喧嘩する — ハローは 1 色のままで塗りが
循環するので、汚い結果になる。

ヘルパースクリプトは、この 3 種類の animation のときは `--outline triadic`
等を明示的に渡しても `outline` と `outline_width` を出力 URL から自動的に
落とす。PreToolUse hook もこの 3 種類を outline 必須要件から免除する —
`animation` が {`disco`, `psycho`, `kira`} の場合は 4-param URL
(`background` / `font` / `color` / `animation`) が有効。

outline を省略する(一般)条件:

- animation が `disco` / `psycho` / `kira`(自動処理される)
- ユーザーがプレーンスタンプを明示的に要求(ハロー無し)
- 本文が謝罪 / postmortem / セキュリティ — 視覚的なリフトが落ち着いた
  トーンと矛盾する
- 単発のレビューコメント(1 つの action バッジ); 1 つのために
  outline オーバーヘッドをかけても元が取れない

`mojiemoji-selector` に委譲するときは、outline 設定を `CONSTRAINTS` に
渡すこと:

```
- Add outline=triadic outline_width=2 to every URL (high-contrast halo via 120° hue rotation from fill; auto-dropped on disco/psycho/kira)
```

## パラメータが効かなくなったとき

mojiemoji の公開 API は進化する — animation 名・font・クエリキーは
予告なく追加・リネーム・削除される。レンダした URL がパラメータエラー
/ 画像破損 / 明らかに間違った結果を出すなら、**仕様がドリフトしている
可能性が高い**。リトライ前にやること:

1. `https://mojiemoji.jozo.beer` からライブのドキュメントを取得する
   (トップページにパラメータ UI と受理値が載っている; `/docs`、
   `/help`、`/about` のリンクがあれば確認)。
2. ライブのパラメータリストを `presets.md`(font 役割、animation
   リスト、speed 値)と `scripts/mojiemoji_markdown.py` の `--font` /
   `--animation` / `--speed` フラグと突き合わせる。
3. ドリフトしている方を更新する:
   - `presets.md` — preset テーブル、animation/font/speed リスト
   - `scripts/mojiemoji_markdown.py` — 今は有効な値を rejection している
     場合はフラグ検証を更新
   - `SKILL.md` Defaults — 推奨 preset 名が変わった場合
   - `parameters.md` (このファイル) — animation/font/color リスト
4. 修正パラメータで再レンダして作業を続ける。

「だいたい近い」パラメータに無言で差し替えてドキュメント更新しないのは
ダメ — 次のセッションで同じエラーを踏む。パラメータエラーは「仕様を
リフレッシュする合図」として扱う、その場限りのリトライではない。
