# GitHub 用 Mojiemoji プリセット

GitHub markdown のデフォルトとして使うプリセット集。表現豊かな視覚的
ノイズが許容され、しばしば歓迎される社内利用向けにチューニングされている。

## 基本ルール

- mojiemoji はスタンプとして使う。
- 本文の散文は普通のままにする。
- ユーザーが明示的にうるさめスタイルを望むときは多めに使う。
- 公開 API が今のところ行バランスパラメータを公開していないため、長すぎる
  フレーズは避ける。

## block vs inline

2 つの配置モードがある。他のパラメータを選ぶ前に必ずこちらを決めること。

| モード | いつ | 出力形式 | フレーズ長 |
|---|---|---|---|
| `block` | 独立行: 見出し、コールアウト、チェックリスト、締めの行 | Markdown `![alt](url)` | 2–6 字 |
| `inline` | 文中の強調、例 【マジで】やばい【バグ】ですね | HTML `<img ... height align>` | 2–4 字 |

### inline レンダリングのルール

- GitHub サニタイザは `style` を剥がし、`height` の CSS 単位を無視する。
  integer ピクセルだけ使うこと。
- 典型的な GitHub 本文の line-box はおよそ 21px。`height="20"` は実本文での
  ユーザーの観測上のデフォルト; `height="24"` も有効。どちらも読みやすい。
  28–32 まで上げるのはユーザーがうるさめスタイルを要求した時だけ。
- 必ず `align="absmiddle"` をペアにしてスタンプをテキスト中央に座らせる。
- ほとんどの animation は inline で有効。**`bakusan` は block 専用** —
  放射バーストの動きがデフォルト `height="20"–"24"` で内側の letterform を
  覆ってしまう(`parameters.md` § Valid animation values を参照)。それ以外は
  `kira` も含めて inline で歓迎。多様性のため意図的にばらつかせる
  (SKILL.md § Animation diversity を参照)。
- 落ち着いた / ニュートラルなトーンでは 1 文あたり inline スタンプは
  最大 2 個まで。飽和 / うるさめトーンでは 1 文あたりの上限は緩む。

## font 役割

| Font | 用途 |
|---|---|
| `gothic-bold` | 実務的なステータス、WIP、調査中、完了 |
| `maru` | ソフトなお礼、待ち、フレンドリーな促し |
| `maru-bold` | フレンドリーだが見える程度のレビュー / 依頼の促し |
| `mincho` | 重めの告知、注意、フォーマルな強調 |
| `pixel` | 祝福、遊び心ある承認、リリース感 |
| `dela` | タイトル級のうるさめ強調 |

## speed 役割

| Speed | 用途 |
|---|---|
| `slow` | GitHub コメント / 本文のデフォルト |
| `normal` | 祝福系スタンプのデフォルト |
| `fast` | 稀; 意図的にうるさめの緊急 / 冗談に限る |
| `step` | 機械的・レトロ感を出したい時 |

## animation バイアス: `kira`

ユーザーは `kira`(色相回転する色循環) が好み。animation 選定時の
グローバルバイアスとして適用する:

- 祝福系 / 勝ちトリ系 / 「やりきった」系のスタンプは **`kira` 寄り** に —
  `LGTM`、`完成`、`リリース`、`マージした`、`ありがとう`、`お疲れ様`、
  `めでたい`。テーブルのデフォルトより `kira` を多めに採用する。
- 注意 / 警告 / エラー / blocker 系には **絶対 `kira` を使わない**
  (`注意`、`バグ`、`要修正`、`緊急`、`困った`) — うるさめ効果の意味を
  保つため。
- **1 メッセージ / issue / PR / コメントあたり `kira` は最大 1 個。**
  循環スタンプを重ねると目を引く効果が殺される(「極端はダメ」)。
  残りは非 kira animation をデフォルトに。
- **`kira` は inline でも歓迎** — ムードが要求するなら使う。古い
  「inline では kira 使わない」ルールは撤回された。文中のオチ強調に使う。

## トーンプリセット

| フレーズ | コンテキスト | Font | Color | Animation | Speed | 備考 |
|---|---|---|---|---|---|---|
| `WIP` | PR draft、issue 進捗 | `gothic-bold` | `f59e0b` | none | - | 安定デフォルト |
| `調査中` | 調査 | `gothic-bold` | `f59e0b` | `yoko_scroll` | `slow` | 継続中の探索向け |
| `確認待ち` | 待ち | `maru` | `60a5fa` | `yurayura` | `slow` | ソフトなプレッシャー |
| `レビュー歓迎` | レビュー依頼 | `maru-bold` | `3b82f6` | `bane` | `slow` | フレンドリーな依頼 |
| `見てほしい` | 明示的なレビュー促し | `maru-bold` | `2563eb` | `poyoon` | `slow` | 少し遊び心 |
| `修正中` | 修正進行中 | `gothic-bold` | `fb923c` | `norinori` | `slow` | 動きあり |
| `修正済み` | 対応済み | `gothic-bold` | `22c55e` | `mochimochi` | `slow` | やわらかい完了 |
| `直した` | カジュアルな修正報告 | `maru-bold` | `10b981` | `poyoon` | `slow` | フレンドリートーン |
| `LGTM` | 承認 | `pixel` | `22c55e` | `bane` | `normal` | 強めの定番 |
| `よさそう` | ソフトな承認 | `maru-bold` | `34d399` | `mabataki` | `slow` | うるさすぎない |
| `ありがとう` | お礼 | `maru` | `ec4899` | `yurayura` | `slow` | 暖色デフォルト |
| `助かる` | 感謝 | `maru-bold` | `f472b6` | `mochimochi` | `slow` | 短くてスタンプ向き |
| `急ぎ` | 緊急の注意喚起 | `dela` | `ef4444` | `disco` | `normal` | 意図的にうるさめ |
| `重要` | 重要な注記 | `mincho` | `dc2626` | `shuchusen` | `slow` | ドラマチックな強調 |
| `要相談` | 要議論 | `mincho` | `8b5cf6` | `nami` | `slow` | 曖昧さを示す |
| `困った` | ブロック | `maru-bold` | `f97316` | `gatagata` | `slow` | 控えめに使う |
| `マージした` | マージ完了 | `pixel` | `22c55e` | `yatta` | `normal` | 祝福 |
| `出した` | PR or リリース投稿 | `pixel` | `06b6d4` | `bakusan` | `normal` | 告知 |
| `リリース` | リリースノート | `pixel` | `a855f7` | `kaiten` | `normal` | お祭り感 |
| `めでたい` | 社内祝い | `pixel` | `f59e0b` | `kira` | `normal` | 明るくて遊び心 |

## 配置ガイダンス

- Issue 本文:
  - 冒頭のステータススタンプ
  - セクション見出しのアクセント
  - 締めの依頼
- PR 本文:
  - 冒頭のステータススタンプ
  - チェックリスト付近のレビュー依頼
  - 末尾付近のマージ / リリースノート
- レビューコメント:
  - 普通は 1 スタンプで十分(ユーザーがうるさめ希望でない限り)
- フォローアップ返信:
  - `修正済み`
  - `確認待ち`
  - `ありがとう`

## inline スタンププリセット

短くパンチのあるフレーズを使う。落ち着いた animation のみ。デフォルトで
`height=24 align=absmiddle`。

| フレーズ | コンテキスト | Font | Color | Animation | Speed |
|---|---|---|---|---|---|
| `マジで` | 形容詞前の強調修飾 | `maru-bold` | `ef4444` | `bure` | `normal` |
| `バグ` | 文中で欠陥を指す | `gothic-bold` | `dc2626` | `gatagata` | `slow` |
| `注意` | 文中の注意喚起 | `mincho` | `f59e0b` | `mabataki` | `slow` |
| `ここ` | コード内の位置を文中で指す | `maru-bold` | `3b82f6` | `poyoon` | `slow` |
| `これ` | 文中の指示強調 | `maru-bold` | `60a5fa` | `yurayura` | `slow` |
| `多分` | 文中のヘッジ | `maru` | `94a3b8` | `yurayura` | `slow` |
| `要注意` | 注意 より強い文中注意 | `mincho` | `dc2626` | `mabataki` | `slow` |
| `OK` | 文中の承認 | `pixel` | `22c55e` | `mabataki` | `slow` |
| `NG` | 文中の却下 | `pixel` | `ef4444` | `mabataki` | `slow` |
| `草` | 社内ウケスタンプ | `maru-bold` | `22c55e` | `poyoon` | `slow` |

## 改行による構成

複数セグメントのフレーズは、1 行の長いスタンプにするより
**バランス取れた 2 行** にした方がきれいにレンダされる。URL の `text` 部分の
自然な意味境界に `%0A` をエンコードする。markdown の `alt` テキストは
**1 行のまま** にすること — `alt` にリテラルな改行を入れると一部の
markdown パーサが壊れる。

### いつ適用するか

- **4 字 → デフォルトで 2+2 に分割。** これはグローバルルール: 4 字
  フレーズは、1 単位として読まれる慣用句(「いつスキップするか」を参照)
  でない限り、バランスのとれた 2 字 × 2 行に分ける。
  例: `糖衣` + `構文`、`動作` + `確認`、`修正` + `完了`、`本番` + `反映`、
  `仕様` + `変更`、`要件` + `定義`。
- 5 字以上で、2 つのサブフレーズの間に明確な意味境界があるもの。
  例: `レビュー` + `歓迎`、`マージ` + `完了`、`修正` + `お願い`、
  `確認` + `お願い`、`デプロイ` + `完了`、`リリース` + `準備`。
- 両行の幅をバランス取ること(1 行 2–4 字くらいが良い)。

### いつスキップするか

- 2–3 字の単一セグメントフレーズ: `バグ`、`注意`、`これ`、`ここ`、
  `OK`、`NG`、`草`
- 1 単位として読まれる慣用句 / 語: `あとちょい`、`ありがとう`、
  `おつかれ`、`LGTM`
- inline スタンプ(mode = `inline`)— 文中のタイポグラフィックフローを
  保つため 1 行のままにする

### やり方

1. 自然な縫い目(2 つのサブフレーズの間)を見つける。
2. URL パス内で縫い目を `%0A` に置き換える。両側はだいたい同じ幅に
   なるように(1 行 2–4 字が良い)。
3. markdown の `alt` テキストは結合した 1 行形式のままにする。

### 例

```md
![レビュー歓迎](https://mojiemoji.jozo.beer/emoji/%E3%83%AC%E3%83%93%E3%83%A5%E3%83%BC%0A%E6%AD%93%E8%BF%8E?font=maru-bold&color=3b82f6&animation=bane&speed=slow)
```

スタンプ内ではバランスのとれた 2 行(`レビュー` / `歓迎`)としてレンダリング
され、alt テキストはアクセシビリティとパーサ互換性のため `レビュー歓迎` の
ままになる。

これは `mojiemoji-github` skill のグローバルデフォルト — 上記基準に
合致する全呼び出しで適用する。

## サンプルスニペット

block(独立行):

```md
![レビュー歓迎](https://mojiemoji.jozo.beer/emoji/%E3%83%AC%E3%83%93%E3%83%A5%E3%83%BC%E6%AD%93%E8%BF%8E?font=maru-bold&color=3b82f6&animation=bane&speed=slow)
```

```md
修正しました。![確認待ち](https://mojiemoji.jozo.beer/emoji/%E7%A2%BA%E8%AA%8D%E5%BE%85%E3%81%A1?font=maru&color=60a5fa&animation=yurayura&speed=slow)
```

```md
![LGTM](https://mojiemoji.jozo.beer/emoji/LGTM?font=pixel&color=22c55e&animation=bane&speed=normal)
```

inline(文中):

```md
この関数は<img src="https://mojiemoji.jozo.beer/emoji/%E3%83%9E%E3%82%B8%E3%81%A7?font=maru-bold&color=ef4444&animation=bure&speed=normal" alt="マジで" height="24" align="absmiddle">やばい<img src="https://mojiemoji.jozo.beer/emoji/%E3%83%90%E3%82%B0?font=gothic-bold&color=dc2626&animation=gatagata&speed=slow" alt="バグ" height="24" align="absmiddle">ですね。
```
