---
name: mojiemoji-github
description: GitHub markdown(issue / PR / レビューコメント / 返信 / リリースノート)に向けて mojiemoji.jozo.beer 経由の画像スタンプを差し込むスキル。**文中のインライン強調が主用途**(例 【マジで】やばい【バグ】ですね)で、レビュー・コメント・返信を含むすべての surface に本文と同等の密度で適用する。`![alt](url)` を行頭に置く block スタンプは review-class surface では禁止、body-class surface でも非推奨(ユーザーが明示的に依頼した場合のみ)。文末・見出し末の trailing 装飾は **2 段階優先**: `data/emoji-catalog.yml` に登録のある絵文字(162 種、🎉 / 🔥 / ✨ / 💯 / ⚠ / ❤ / 😂 等)は **mojiemoji 化** してアニメ付きで埋め、無いもの(例 🚀 = U+1F680)だけ素の Unicode に fallback する(プロジェクトに GitHub Markdown 規約があればそちらの「Trailing decoration」節を参照)。`approve` レビューでの LGTM は mojiemoji 単独なら inline / block-image どちらでも自由。他の LGTM-imagery skill を併用する場合のみ mojiemoji は inline に留めるのが推奨(派手な装飾 2 つの並置を避けるため)。body-class surface では shields.io バッジと組み合わせて使う。
when_to_use: |
  日本語の GitHub markdown を作成するときは、たとえ mojiemoji 関連キーワードが無くても**積極的にこのスキルを提案すること**。ユーザーは感情の転換点、ステータス・気分・承認、注意喚起、オチの強調などをプレーンテキストではなく表情豊かなスタンプで表現することを強く好む。装飾前に一度はユーザーに確認すること。強制はしない。

  自動トリガー条件:
  - GitHub に投稿する日本語テキストの作成時(issue 本文、PR 説明、レビューコメント、返信、リリースノート)
  - /make-issue / /make-pr / /address-review / /triage-review / /good-morning / /cross-repo-review / /vibes-review / /copilot-review の返答時
  - 投稿系コマンド実行前: `gh issue create` / `gh issue comment` / `gh pr create` / `gh pr comment` / `gh pr review` / `gh release create` / `gh release edit` 等
  - raw GitHub REST API(`gh api` 経路)で以下の URL パターンに POST / PATCH する直前 — named command を経由しないため別途列挙する必要がある:
    - `gh api repos/{owner}/{repo}/pulls/{n}/reviews` (PR レビュー本文)
    - `gh api repos/{owner}/{repo}/pulls/{n}/comments` (PR インラインコメント / 返信)
    - `gh api repos/{owner}/{repo}/issues/{n}/comments` (issue / PR への top-level コメント)
    - `gh api repos/{owner}/{repo}/issues` (issue 作成 — POST) / `.../issues/{n}` (issue 編集 — PATCH)
    - `gh api repos/{owner}/{repo}/releases` (リリース作成 — POST) / `.../releases/{id}` (リリース編集 — PATCH)
    - `--input <file>` や `-F body=...` / `-f body=...` の payload も同様に対象
  - MCP GitHub ツール経路でも同じ surface に投稿する直前: `mcp__*__github_create_pull_request` / `github_add_issue_comment` / `github_pull_request_review_write` / `github_issue_write` / `github_update_pull_request` / `github_add_comment_to_pending_review` / `github_add_reply_to_pull_request_comment` 等。PreToolUse hook が最後の砦として block するが、ここでスキルが先に発火していれば再装飾のラウンドトリップが発生しない
  - subagent driven batch posting (cross-repo-review / triage-review / vibes-review / copilot-review の review/comment 連投) — gate は「日本語 body 提出」自体に発火するので、`gh` でも `gh api` でも MCP でも subagent 経由でも例外なく適用
  - キーワード: mojiemoji, もじえもじ, スタンプ, スタンプ画像, 絵文字, インライン絵文字, GitHub markdown stamp, LGTM stamp
  - ユーザーの発話(明示的な呼び出しのみ — 「今 mojiemoji をレンダリングしてほしい」相当): "絵文字使って", "絵文字いれて", "もじえもじ使って", "スタンプ入れて", "decorate", "emphasize this part", "もっと文中で", "もっと使って"

  スキップする場合:
  - 本文が英語のみ
  - 対象 surface が Slack / Notion / 一般的な Web (GitHub ではない)
  - 内容が謝罪 / セキュリティ / 法務 / コンプライアンス / 受け入れ基準 — 装飾より明瞭性を優先
allowed-tools:
  - Read
  - Bash
  - Agent
---

# Mojiemoji Github (Claude)

## トリガーとスコープ

ユーザーが GitHub surface 向けの mojiemoji スニペットを欲しているときだけ起動する。Slack のカスタム絵文字、Notion、一般的な Web ページには起動しない — ここで規定するデフォルトはすべて GitHub のサニタイザを前提にしている。

## 下処理 first — 機械的置換を最初に通す (本プロジェクトの中心原則)

**日本語 markdown を扱うとき、AI が装飾判断を始める前に、必ず最初に `prestamp.py` で機械的置換を通す。** これは mojiemoji の中心的な設計原則であり、「高密度 stamp × 低コスト (token / time)」を両立させる唯一の経路。

### なぜ必須か

mojiemoji は本来「高密度 stamp (`inline-saturated`、1 段落最低 1〜2 個)」を理想とするが、AI が毎回 hand-craft で stamp URL を組むと:

- **トークン**: 1 stamp ≈ 100+ token (`<img src="..." alt="..." height="24" align="absmiddle">` の長大 HTML)。15 stamp で **1500+ token / 投稿** が装飾だけで消費される
- **時間**: catalog の語ごとに font / color / animation を選ぶ判断を都度行うため出力が遅い
- **品質**: AI は気まぐれに stamp 対象を選ぶため catalog 登録済の頻出語を取りこぼす ([実例](https://github.com/jozobeer/mojiemoji-plugin/issues/70): PR #65 body で `重複`×4、`追加`×3 などが plain で残存)

**下処理を最初に通せば catalog hit は AI トークン 0 で `<img>` に置換され、AI は catalog 外の語の装飾だけに集中できる。** catalog が育つほど (#46) AI の負荷は逓減する。

### 正しいフロー

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

### 具体的な呼び方

`gh pr create --body-file body.md` する直前に:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/scripts/prestamp.py" \
  < body.md > body-pre.md
gh pr create --body-file body-pre.md ...
```

stdin / stdout なので pipe でもよい:

```bash
prestamp.py < draft.md | gh pr create --body-file -
```

`prestamp.py` は `data/prestamp-catalog.yml` の全 `terms` キー (447+ entries) を 1 単語ずつ最長一致で `<img>` 置換する。catalog 外の語は素通し。冪等 (再実行で副作用無し)。

### よくあるアンチパターン

| アンチパターン | なぜダメ |
|---|---|
| AI が hand-craft で stamp URL を組み始める (下処理を経ずに) | catalog hit を取りこぼす、トークン消費が膨張 |
| 下処理を「最後に通す」 | AI が既に同じ語を手動 stamp 化済 → 二重置換でリンク壊れ。AI の労力も無駄になる |
| 「催促が無いから」と省略 | catalog 育成 (#46) の効果が活きない、`<img>` 大量生成が常態化してトークンが青天井 |
| `prestamp.py` を通さずに hook bypass (`MOJIEMOJI_HOOK_DISABLED=1`) | 本来 hook が catch するべき残存も silent で通る、catalog hit ゼロ置換のまま投稿 |

### Skill / subagent としての必須動作

このスキル (および `mojiemoji-selector` subagent) が起動したら、装飾判断の前に **必ず** `prestamp.py` を呼ぶ。順序が逆になると上記アンチパターンに該当する。draft を作る前 / 編集中 / 投稿直前のいずれの段でも、AI が新しく日本語を書き加えたら下処理を通し直す。

## Hard pre-action gate

**設計原則: gate は「投稿される *body* が日本語の GitHub markdown かどうか」で発火する — どの *コマンド* で投稿するかではない。** 失敗モードは「装飾なしで日本語を silently 投稿してしまう」こと。これを防ぐためなら、新しい投稿経路が増えてもこの原則は不変。

### 発火する surface(完全列挙)

以下のいずれかで日本語 body を提出する直前に、`mojiemoji-github` skill による装飾を行う:

- `gh` CLI 投稿系: `gh issue create` / `gh issue comment` / `gh issue edit` / `gh pr create` / `gh pr comment` / `gh pr review` / `gh pr edit` / `gh release create` / `gh release edit`
- raw GitHub REST: `gh api .../pulls/.../reviews` / `gh api .../pulls/.../comments` / `gh api .../issues/.../comments` / `gh api .../issues` 等(`--input` payload や `-F body=...` も同じ)
- MCP GitHub ツール経路: `mcp__*__github_create_pull_request` / `github_add_issue_comment` / `github_pull_request_review_write` / `github_issue_write` / `github_update_pull_request` / `github_add_comment_to_pending_review` / `github_add_reply_to_pull_request_comment` 等
- subagent 駆動の一括投稿: `cross-repo-review` / `triage-review` / `vibes-review` / `copilot-review` 等が複数 PR を回って review/comment を連投する経路
- 上記いずれでもない新経路でも、日本語 GitHub body を提出するなら例外なく対象

最終 gate として PreToolUse hook (`hooks/mojiemoji-japanese-gate.py`) が submission 直前に発火し、未装飾の日本語 body を block する。Skill を先に呼んでおけば hook で再装飾のラウンドトリップが発生しない、というのが skill 側で gate を実装する意義。

### UX ルール — メニューを出さず、装飾して見せる

ユーザーがこの skill を起動した時点で、装飾の placement(どの単語に stamp を当てるか)の判断権限は skill に委譲されている。「block で付けますか / inline で付けますか / どこに付けますか」と選択肢を並べて聞き返してはいけない。

1. **Auto-decorate** — heuristics で stamp 対象を選び、本ファイルの規約通りに装飾した draft を生成
2. **Show the decorated draft** — ユーザーに 1 度だけ提示
3. **Wait for yes/no** — 「これで投稿してよい?」の確認だけ取る。修正要求があれば 1 に戻る

`mojiemoji-selector` subagent にデリゲートする場合も同じ — selector が返した snippet を本文に embed して draft を完成させ、その draft をユーザーに見せる(selector の生 output を user に見せて「どれにします?」と聞かない)。

### 装飾しない正当ケース(skip 条件)

以下のいずれかに該当する body は装飾せずに投稿してよい:

- 本文が英語のみ(日本語が無い)
- surface が GitHub ではない(Slack / Notion / 一般 Web)
- 内容が謝罪 / セキュリティ advisory / 法務 / コンプライアンス通知 / 受け入れ基準を単独で提示するケース — 明瞭性を装飾より優先

skip 判断が曖昧なら装飾する(後述「飽和モード」参照、迷ったら loud を選ぶ)。

### 緊急 bypass

gate 自体を一時的に黙らせたい場合は Bash command 先頭 / MCP body 内に `MOJIEMOJI_HOOK_DISABLED=1` を含める(PreToolUse hook がこの marker を見ると素通しする)。乱用しない — 1 投稿 1 bypass の最小スコープに留める。

### Reviews API の structural distinction(`body` vs `comments[]`)

`gh api repos/{owner}/{repo}/pulls/{n}/reviews` (および MCP `github_pull_request_review_write`) で POST する review payload は構造上 **2 つの surface** を持つ。装飾の対象範囲が両者で異なる:

| フィールド | 用途 | 装飾 |
|---|---|---|
| `body` | summary text(verdict + 評価 + 締め、通常は日本語 prose) | **対象** — surface ヒューリスティック表(§ Review summary body)に沿って inline 飽和で装飾 |
| `comments[]` | inline findings(file path + line + 技術的指摘) | **対象外** — 素のまま投稿 |

`comments[]` の findings は **コード引用 / ファイルパス / シンボル名 / 行番号** が主体で、スタンプとの相性が悪い(grep 性が落ち、修正提案の可読性が下がる)。`cross-repo-review` / `triage-review` / `vibes-review` / `copilot-review` 等の subagent 駆動 batch posting で `gh api .../reviews` を経由するとき、**装飾は `body` フィールドだけに適用し、`comments[]` 配列の各 element には適用しない**。

action バッジ(`action: fixed/by design/test added/deferred/wontfix`)を返信本文の先頭に置くケース(`gh api .../pulls/.../comments` 経由の reply)は別ルートで、§ Reply / コメント返信 のヒューリスティックに従う — そちらは reply 自体が日本語 prose なので装飾対象。

迷ったときの判定: 「この文字列を逐語 grep したいか?」がコードレビューでの判断軸と一致する。findings は yes(コードを引用するから)、summary body は no(感情・評価・指示の prose だから)。

## バッジと併用する(バッジが見出しの役割)

mojiemoji スタンプと shields.io バッジは**相補的で交換可能ではない** — バッジはメタデータを、スタンプは雰囲気を伝える。よくある失敗パターンは、スタンプは付けたのにバッジを忘れることである。

**surface 別の併用ルール:**

| Surface | バッジ | スタンプ |
|---|---|---|
| Issue 本文 / PR 本文 / リリースノート | 必須 | 任意 |
| レビューコメント / 返信 | 任意 (action バッジ) | 主役 |
| Issue / PR コメント | 任意 | 主役 |

**鉄則: バッジは見出しである。その上に何も置かない。** body-class surface(issue 本文 / PR 本文 / リリースノート)では、shields.io のバッジ行が視覚的にも意味的にも最初の要素である。これより上に何も置かないこと — `![alt](...)` を独立した行に置く block モード mojiemoji スタンプ、単独の装飾、タイトル風の一文、画像バナーなど全て禁止。レビュアーが最初に目にする行はバッジでなければならない。

唯一の例外は、`![action](...)` バッジ(例: `action-fixed-green`)単体で始まるレビューコメント風の返信である。これも**バッジ**なのでルール自体は破られていない — 1 行目はバッジである。

このスキルが issue 本文 / PR 本文 / リリースノートに対して起動されたら、**いったん止めてバッジも同時に追加されているか確認する**こと。バッジが存在しないなら、スタンプの前か並行してバッジを提案する。色の使い分けやバッジの選定基準については、プロジェクト固有の GitHub Markdown 規約があればそちらの Shields.io Badges 節を参照すること。

具体的なレイアウト(以下のブロック全体が例。`## 概要` は SKILL.md の見出しではなく例の一部):

````markdown
![type](...) ![scope](...) ![breaking](...) ![diff](...) ![tests](...)

Closes #N.

## 概要

…インライン埋め込みでスタンプを文中に散りばめた本文…
````

## デフォルトのトーンとインライン飽和

ユーザーがトーンを指定しない場合、surface ごとのデフォルト:

| Surface | デフォルトトーン |
|---|---|
| Issue 本文 / PR 本文 / リリースノート | **loud(インライン飽和)** |
| レビュー本文(verdict + 評価 + 締め) | **loud(インライン飽和)** — issue / PR 本文と同等の密度 |
| レビュー返信 | **loud(インライン飽和)** — 本文と同等の密度 |
| Issue / PR コメント | **loud(インライン飽和)** — 本文と同等の密度 |

かつてはレビューコメント / 返信に「neutral デフォルト」を設けていたが、これは**撤回**された。実際の PR で淡白な文章が指摘されたためである。レビュー系のすべての surface は body-class surface と同じ飽和ルールに従う。違うのは*block* の使用可否だけ — レビュー surface には block スロットが存在せず、body surface でもユーザーがそのターン内で明示的に block 装飾を依頼した場合に限る。

ユーザーが「calm にして」「軽めで」「控えめに」と明示した場合、または本文が「装飾してはいけない」カテゴリ(謝罪 / セキュリティ / 法務 / コンプライアンス / 受け入れ基準を単独で見せるケース)である場合のみオーバーライドする。本文で迷ったら loud を選ぶこと — neutral を選んで装飾不足の文章を出してしまうのが既知の失敗パターンである。

**「loud」とは、段落・箇条書きすべてに渡るインライン密度のこと**であり、大きな block スタンプではない。ユーザーの恒常的な好み(キーワード不要・例外なし):

- ✅ **常にインライン埋め込み**で、文中の単語を置き換える。密度は惜しみなく — 1 段落あたり最低 1〜2 個、アイデアの濃い箇条書きならもっと多く。文法的に収まる名詞・動詞・副詞はすべて埋め込む。
- ✗ **セクション末のオチ装飾**(各セクションの後ろに `→ <stamp1> <stamp2>` を独立行で置く)は**使わない**。「セクション末のブロックスタンプは不要」として明示的に拒否されている。
- ✗ **締めの装飾**(本文末に `---` + 独立行のムードスタンプ)も**使わない**。同じ理由で拒否されている。
- ✅ **文末・段落末・見出し末の trailing 装飾**は 2 段階優先で選ぶ:
  1. **`data/emoji-catalog.yml` に登録のある絵文字** (162 種、🎉 / 🔥 / ✨ / 💯 / ⚠ / ❤ / 😂 / 🎊 / 🚨 / 😎 / 🤖 等) → **mojiemoji 化してアニメ付きで埋める**。catalog から該当 emoji の variant 1 つを引き、`<img src="https://mojiemoji.jozo.beer/emoji/<emoji>?font=<font>&color=<color>&animation=<anim>&background=transparent&outline=<outline>&outline_width=2" alt="<emoji>" height="24" align="absmiddle">` 形式で挿入する。動詞・名詞の inline 埋め込みと同じ URL 構造 — `mojiemoji_markdown.py --text '<emoji>'` でも手で組んでも良い。**variant の params をそのまま使う**こと: catalog には color-shifting 系 variant (`disco` / `psycho` / `kira`) も含まれ、それらは `outline` フィールドを持たず代わりに `outline_width: "0"` を持つ。テンプレ通りに `outline=...&outline_width=2` を埋めると hook (`mojiemoji-japanese-gate.py`) で reject される。catalog 上の variant に書かれた params を字面通り写すのが安全。
  2. **登録の無い絵文字** (例 🚀 = U+1F680、upstream `jozobeer/mojiemoji/assets/emoji` にアセット無し) → **素の Unicode** にフォールバック。例: `## デプロイ手順 🚀`、`これは未対応 🪐`。
  catalog 在否を確認する手順:
  - **VS16 を剥がす**: 入力に `❤️` (U+2764 U+FE0F) や `⚠️` (U+26A0 U+FE0F) など variation selector (U+FE0F) が混じっていたら、catalog キーは base codepoint (`❤` / `⚠`) しか持たないので、lookup 前に `tr -d $'\xef\xb8\x8f'` 等で剥がす。剥がさないと「未登録」と誤判定して素の Unicode に fallback してしまう。
  - **YAML キーに一致** させる: 実 catalog の key 形は `  🎉:` のように 2 字インデント + bare emoji + `:` で、コメント中に同じ glyph が出てくることもある (`🚀` は upstream 未対応の例として SKILL.md / catalog header の prose にも登場する)。素朴な `grep "<emoji>"` だとコメント / prose にもヒットするので、`grep -E "^  $EMOJI:" skills/mojiemoji-github/data/emoji-catalog.yml` のように **行頭 2-space インデント + コロン** にアンカーするか、`python3 -c "import sys, yaml; data = yaml.safe_load(open('skills/mojiemoji-github/data/emoji-catalog.yml')); sys.exit(0 if '$EMOJI' in data['emojis'] else 1)"` で実 key を直接問い合わせる。
  1 スロット 1 絵文字、連結禁止(mojiemoji 化しても同じ — 連続して並べない)。

ユーザーは「独立行の block スタンプは『デカくてよくわからない文節』になって本文を壊す」と指摘している。mojiemoji = インライン埋め込み(文中の強調)、Unicode 絵文字 / mojiemoji 化された絵文字 = 末尾の装飾。2 つのスロット、2 つの道具 — 混同しないこと。**末尾装飾の絵文字を mojiemoji 化しても役割は装飾のまま** — 文中の単語置換 (`【マジで】`) と混同せず、文末のシンボル位置に留める。

**デフォルトモードはすべての日本語 GitHub surface でインラインのみ。** body-class surface に対してユーザーがそのターンで *明示的に* block 装飾を要求した場合(例: 「→ ブロックでつけて」 / 「盛大に」 / 「block でも OK」)を除き、block スタンプはどこにも置かない。例外が一切効かない厳格な排除が 2 つある:

- **レビュー系 surface(レビュー本文、レビュー返信、PR コメント、issue コメント)には block スロットがそもそも存在しない** — ユーザーが明示的に要求してもダメ。escape valve は適用されない。よくある失敗は、approve サマリーの先頭に `![LGTM](mojiemoji...)` を置いたり、末尾に `![ありがとうございました](...)` を置いたりすること — どちらも実 PR で拒否された典型パターンである(`SP-ACL#1712`)。この衝動が出てきたら、verdict 文 / 締めの文中のインライン埋め込みに置き換える。
- セクションの前に「次の一手」見出し風の block を置きたい衝動、PR 本文末に「マージ歓迎」締めブロックを置きたい衝動は、何度も拒否されている section-punch-line / closing-flair パターンそのもの。衝動が出てきたら、そのセクションの文中にインライン埋め込みとして組み込む。

**マントラ**: 「文中に埋める」「文法崩壊しないように自然に埋め込みまくる」。密度は高く*かつ*文法は自然に保つ — どの埋め込みもクリーンな単語置換として読めること、関係ない品詞の間にぎこちなく突っ込まれていないこと。文法的に自然なスロットが無い候補なら、そのフレーズはスタンプせずに諦める。

## 2 つのモード

| Mode | Surface | 出力 | デフォルトサイズ |
|---|---|---|---|
| `block` | **稀。** issue / PR 本文の特定のセクション見出しや、ユーザーが同ターンで明示的に依頼したコールアウト文脈でのみ独立行スタンプを使う。**レビュー系 surface ではすべて禁止**(レビュー本文、レビュー返信、PR コメント、issue コメント) — 何があってもインラインのみ。**本文の先頭・末尾装飾としても禁止**。LGTM mojiemoji は他スタンプと同じく扱う — 別の LGTM-imagery skill と併用しないなら block / inline どちらも OK(詳細は下記 § LGTM 画像 参照)。 | Markdown `![alt](url)` | native |
| `inline` | **すべての日本語 GitHub surface のデフォルト。** 文中強調(例: 【マジで】やばい【バグ】)。body-class でも review-class でも 1 段落最低 1〜2 個で飽和させる。 | HTML `<img ... height="24" align="absmiddle">` | 24 px |

GitHub 仕様で守るべきこと:

- サニタイザは `style` を剥がし、CSS 単位を無視する。整数の `height` ピクセル値を使うこと。
- `height="24"` は本文サイズで読みやすい。`height="20"` がユーザーの観察上の好み。`references/parameters.md` § Inline height を参照。
- 1 文あたりインラインスタンプは最大 2 個(飽和モードでは緩和)。

## LGTM 画像 — mojiemoji 単独なら自由、他 LGTM skill と併用時はインライン

**mojiemoji だけで LGTM するのは何の制限もない。** インラインでも `![LGTM](url)` の block-image でも、見せ方は自由。`完璧` / `見事` / `綺麗` / `完成度` のような verdict 語と同じく、LGTM も普通の語として扱ってよい。

唯一の編集ガイドラインは**併用ケース**:

- **user 環境に別の LGTM-imagery skill(派手な画像を生成する系)があり、それを使って approve に LGTM 画像を載せる場合** — 同じレビュー本文に mojiemoji LGTM の block-image を重ねると、見出し級の装飾が 2 つ並んで強すぎる。そのケースでは mojiemoji LGTM は**インラインだけに留める**(verdict 文中の語として埋め込み)。block-image スロットは別 skill の画像に譲る。
- **mojiemoji 単独 / 他 LGTM skill を使わない**場合 — mojiemoji の block-image LGTM をそのまま使って OK。制限なし。

この棲み分けは「派手な装飾は本文 1 つまで」という美観の問題で、技術的に正しい / 間違っているの話ではない。判断は user / 状況依存。

### Hook 側の挙動

PreToolUse hook (`hooks/mojiemoji-japanese-gate.py`) は **LGTM スタンプに対して特別扱いをしない**。他のスタンプと同じく、6 必須スタイルパラメータ(font / color / animation / background / outline / outline_width)が揃っていれば pass する。block-image 形式でも inline HTML 形式でも同様。

「併用時はインラインに留める」という上記の編集ガイドラインは **runtime context(別 skill が同時に動いているか)を hook が知る手段が無い**ため、hook では enforce できない。これは人の判断 / SKILL.md 規約で運用する領域。

## 埋め込み vs 装飾

`inline` モードの中には**2 つのサブパターン**があり、ソース上は同じに見えるがレンダリングされた結果はまったく違って読める。ユーザーはこれを可読性失敗パターンの第 1 位として明示的に指摘している:

| パターン | 何 | 配置 | 文法的役割 |
|---|---|---|---|
| **埋め込み(embed)** | スタンプが文中の単語を置き換える | 文中 | **その文に合う**名詞・動詞・副詞の代わり |
| **装飾(decoration)** | 文法的役割なくムードや勢いを添える | 文の下に独立行、`→ ` を前置 | なし — 純粋に装飾 |

**ルール: 散文の文末に装飾スタンプを付け足してはいけない。** 文末の trailing 装飾(例: `…したい <マジで> <大事>。`)は埋め込みと視覚的に混ざり、読み手は文の終わりを認識できなくなる。trailing 装飾は専用行に移すこと:

```markdown
…したい。

→ <マジで> <大事>
```

見出し末の trailing 装飾は OK(見出しは散文と視覚的に区別される)。例: `## デプロイ順序 <大事>`。

### 埋め込みの文法的安全チェック

埋め込みを挿入する前に、**スタンプの `alt` テキストを文中に置いた状態で読み上げる**。自然な日本語として成立しないなら埋め込まない — スタンプを諦めるか、装飾行に移す。

- 悪い例: `カラムが <グッド> で <存在> する` — 「グッド」は名詞的な判定語で副詞スロットに合わない。文が壊れている。
- 良い例: `カラムが <存在> する` — 「存在」は元々そのスロットを埋めるサ変名詞の置換である。
- 良い修正(壊れた例の救済): `カラムが <存在> する。\n\n→ <グッド>`

このルールは下記の飽和モードのデフォルトより優先される: 飽和モードでも、埋め込みは依然として文法的に成立する必要がある。

### スタンプ対象: 文ではなく単語

mojiemoji は**単語レベルの一撃**であって、句や文の強調ではない。スイートスポットは**2 字の漢字熟語(二字熟語)** — コンパクトで意味密度が高く、視覚的にも際立つ。普通の日本語の文中で 1 つそういう単語に乗っかるとき、スタンプは最も光る。

| スタンプにする | スタンプしない |
|---|---|
| `歓迎` `修正` `確認` `完了` `重要` `緊急` `綺麗` `完璧` `要点` `対応` …(2 字熟語) | `気になりました` `お疲れさまでした`(完全な文 / 述語+丁寧語) |
| `PR` `OK` `NG` `WIP` `API` `LGTM` 等(2〜4 字の ASCII 略語 / ドメイン用語) | `〜していただきありがとうございます`(挨拶ブロック) |
| `マージ` `テスト` `バグ` `リファクタ`(2〜4 字のカタカナ語) | *単語*ではなく*文法的な節*に当たるもの |
| `綺麗` `素敵` `見事` `丁寧`(2 字の形容詞・形容動詞) | 動詞形(`書きました` `送ります` `読んでます`) |

候補テキストが文なら**スタンプ自体を諦める** — 同じ文の別の内容語を選ぶか、その箇所にはスタンプが乗らないと受け入れる。ユーザーは「文章は分割する以前に mojiemoji にしなくていい」「無理してまで mojiemoji にしなくて良い場面もある」と明示している。

### 長さ上限(スタンプ対象として選んだ*単語*に対して)

文字種別ごとのスタンプ長上限 — 文字種ごとにグリフ縮小特性が違うため、可読性閾値も違う:

| 文字種 | 1 スタンプあたり最大文字数 | 備考 |
|---|---|---|
| 漢字 | **2** | 画数が多い。インライン高で 3 字は潰れる。「漢字は2文字までじゃないと読めない」 |
| ひらがな | **5** | 3 字以上のときは、ほぼ中央で `%0A` 改行を入れて 2 行スタンプにする(各行≤3 ひらがな)。1〜2 字は単行。 |
| カタカナ | **3** | |
| ASCII | **3** | (例: `WIP`, `API`, `LGTM`) |

加えて、1 単語に対するスタンプ連続数の全体上限:

- **1 単語につきスタンプ ≤2 個。** 同一単語に 3 個以上連続するスタンプは密すぎる(ユーザーは 3 個を「きつい」、4 個を「無理」と評価)。3 連スタンプは禁止。

文字種が混ざる場合、**該当する文字種ごとの上限を全て**満たすこと。例: `お願い` = 漢字 1 + ひらがな 2 → 漢字 1 ≤2 ✓ / ひらがな 2 ≤4 ✓ → 単独スタンプ OK。`修正お願` = 漢字 3 + ひらがな 1 → 漢字 3 > 2 → 分割必須。

選んだ単語に対する判断フロー:

| 単語 | 単独スタンプに収まるか | そうでなければ |
|---|---|---|
| 漢字 ≤2、または カタカナ/ASCII ≤3、または ひらがな ≤4(4 字なら `%0A` 使用) | はい — 単独スタンプ | — |
| もう少し大きいが 2 スタンプ分の内容に収まる | 文字種境界 / 形態素境界で 2 スタンプに分割 | — |
| それより大きい | スタンプしない — 同じ文の別の短い単語を選ぶか、ここはスタンプしないと割り切る。「文章は分割する以前に mojiemoji にしなくていい」「無理してまで mojiemoji にしなくて良い場面もある」。 | — |

#### 境界ヒューリスティック(2 スタンプに分割するとき)

単純に 2 字ずつ切らないこと — それは `マージ歓迎` → `マー` + `ジ歓` + `迎` を生み、ユーザーから「単語の途中で切れているし、3 スタンプもダメ」と指摘されている。以下の優先順位で:

1. **文字種境界** — カタカナ ↔ 漢字 ↔ ひらがなの境目。
2. **複合語の形態素境界** — `修正お願い` → `修正` + `お願い`、`引き続き` → `引き` + `続き`。
3. **2 字フォールバック** — きれいな縫い目が無い場合、各チャンクが各文字種上限を満たすように 2+残り で割る。

実例:

| 単語 | 構成 | 処理 |
|---|---|---|
| `修正`             | 漢2 | 単独スタンプ ✓ |
| `歓迎`             | 漢2 | 単独スタンプ ✓ |
| `緊急対応`         | 漢4 | 分割: `緊急` + `対応` (漢2+漢2) — 単独スタンプだと漢≤2 を超える |
| `重要事項`         | 漢4 | 分割: `重要` + `事項` |
| `具体策`           | 漢3 | 分割: `具体` + `策` (漢2+漢1) |
| `マージ歓迎`       | カタ3+漢2 | 分割: `マージ` + `歓迎`(文字種境界) |
| `修正お願い`       | 漢2+ひら1+漢1+ひら1 (合計5) | 分割: `修正` + `お願い`(漢2 / 漢1+ひら2) |
| `引き続き`         | 漢1+ひら1+漢1+ひら1 (合計4) | 分割: `引き` + `続き`(形態素境界) |
| `よろしく` (ひら4) | ひら4 | 単独スタンプ `よろ\nしく` (%0A 2+2) |
| `おはよう` (ひら4) | ひら4 | 単独スタンプ `おは\nよう` |
| `ありがとう` (ひら5) | ひら5 | 単独スタンプ `ありが\nとう` (%0A 3+2) |
| `そうだね` (ひら4) | ひら4 | 単独スタンプ `そう\nだね` |
| `おつかれさま` (ひら6) | ひら6 | 分割: `おつかれ` (4, `%0A` 2+2) + `さま`(2, 単行) |

**ひらがな `%0A` ルール:** スタンプ内 `%0A` の形式は**ちょうど 3〜4 字の全ひらがな語**専用(4 字のときは `%0A` を入れる)。単語に漢字やカタカナが混ざる場合は複数スタンプ分割で、絶対に `%0A` を使わない — ひらがな以外のグリフは 2 行の狭いキャンバスで細部が潰れる。

### `%0A` 改行単独スタンプ(ひらがな限定、3〜5 字)

ヘルパースクリプトは `--text` 中のリテラル `\n` を URL パス内の `%0A` にエンコードする。全ひらがな 3〜5 字の単語に対して 2 行スタンプを作るのに使う(各行 ≤3 ひらがな):

```bash
python3 scripts/mojiemoji_markdown.py --text $'よろ\nしく' --inline \
  --font maru-bold --color 22c55e --animation poyoon \
  --outline triadic --outline-width 2

python3 scripts/mojiemoji_markdown.py --text $'ありが\nとう' --inline \
  --font hachimaru --color ec4899 --animation bane \
  --outline triadic --outline-width 2
```

`%0A` を**使わない**ケース:
- 単語に漢字やカタカナを含む(画数が潰れる)
- 1〜2 字のひらがな語(単行で収まるので不要)
- 6 字以上のひらがな語(代わりに 2 スタンプに分割)

### mojiemoji と Unicode 絵文字の組み合わせ — その場で工夫する

mojiemoji(漢字熟語 / 略語 / カタカナ語のテキストスタンプ)と絵文字(Unicode シンボル)は 2 つの層で、**組み合わせるための道具**である。ユーザーは「色々クリエイティブに」「どうしたら良いか自律的に創作して考えて」と言っている。固定テンプレートに頼らず、本文ごとにパターンを変え、読者を驚かせ、自由に混ぜる。`${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/references/` 配下の参照ファイル(もしあれば「Unicode emoji + mojiemoji — improvise」節を含むもの)は非網羅的な踏み台であって、レシピではない。

**絵文字側の選択肢** — 文末・段落末・見出し末の trailing 装飾に絵文字を置くとき:

- `data/emoji-catalog.yml` に登録された絵文字 (162 種) は **mojiemoji 化** された画像で出す。アニメ付きでパンチが増す。
- 未登録(例 🚀 = U+1F680、🪐 = U+1FA90)は**素の Unicode** に fallback。
- 判断フロー:
  1. VS16 を剥がす — `❤️` / `⚠️` のような emoji-presentation 形式は U+FE0F が末尾に付くが、catalog キーは base codepoint (`❤` / `⚠`) しか持たない。素朴に grep すると miss する。
  2. アンカー付きで lookup — `grep -E "^  $EMOJI:" data/emoji-catalog.yml`(行頭 2-space + key + `:`)で**実 YAML キー**にだけマッチさせる。`grep "<emoji>" data/emoji-catalog.yml` 単体は header コメント中の例 (`🚀` 等) にも当たって false positive になる。
  3. 居れば mojiemoji 化(catalog variant の params を字面通り使う — color-shift 系は outline 無し / `outline_width: "0"` なので、手書きテンプレで `outline=...&outline_width=2` を勝手に補わない)。
  4. 居なければ素の Unicode。
- どちらも文末/見出し末の「シンボル位置」専用 — 文中の単語置換 mojiemoji と役割を混ぜない。

```html
<!-- 悪い例: 5 字単独スタンプ、インライン高でグリフが判読不能 -->
<img src=".../emoji/%E3%83%9E%E3%83%BC%E3%82%B8%E6%AD%93%E8%BF%8E?..." alt="マージ歓迎" height="24" align="absmiddle">

<!-- 悪い例: 単純な 2 字切りで `マージ` が単語中央で割れる -->
<img src=".../emoji/%E3%83%9E%E3%83%BC?..." alt="マー" ...><img src=".../emoji/%E3%82%B8%E6%AD%93?..." alt="ジ歓" ...><img src=".../emoji/%E8%BF%8E?..." alt="迎" ...>

<!-- 良い例: カタカナ↔漢字の境界で分割 -->
<img src=".../emoji/%E3%83%9E%E3%83%BC%E3%82%B8?font=maru-bold&color=3b82f6&animation=bane&background=transparent&outline=triadic&outline_width=2" alt="マージ" height="24" align="absmiddle"><img src=".../emoji/%E6%AD%93%E8%BF%8E?font=gothic-bold&color=22c55e&animation=poyoon&background=transparent&outline=triadic&outline_width=2" alt="歓迎" height="24" align="absmiddle">
```

## 飽和モード(body surface のデフォルト)

body-class surface(issue / PR / リリース / コメント / 返信)が日本語の場合、**飽和がデフォルト** — トリガー語句は不要。ユーザーが明示的に「static」「plain」「スタンプなし」「少なめ」と言わない限り、この密度でレンダリングする。

### アンチパターン: 単一スタンプ本文(密度不足)

よくある**失敗パターン**は、本文の最上部(しばしばバッジ行より上)に mojiemoji を 1 つ置いて、残りはプレーンな日本語散文という構成。block でも inline でも同じ病。ユーザーは「モジエモジの使い方下手になった。埋め込み方が悪くなった。スキルに忠実にやってる?」とこれを誤ったデフォルトとして明示的に指摘している。

**過去の具体的な失敗例**:

- **issue #166**(block スタンプ + 単調): 本文中 15 スタンプを置いたが、全て `font=maru-bold color=60a5fa animation=spring speed=normal`。さらに `Promise.all` と `Green` という、そもそもスタンプすべきでない identifier まで含まれていた。多様性の無い量は失敗である。
- **issue #157**(先頭に単発インライン): shields 行は OK だが、その後 `## ステータス: post-POC <保留>` で `保留` が本文中唯一のスタンプ。残りはすべてプレーン散文。block ではなくインラインだが、同じ密度不足の症例。
- **2026-05-12 cross-repo-review batch**(7 PR で必須パラメータ欠落): `cross-repo-review` の Phase 6.5 で 7 PR 分のサマリー body を一括投稿した際、すべての URL が `background=transparent` だけで `font` / `color` / `animation` / `outline` / `outline_width` を欠落していた。当時の hook は `background` のみ検査していたため hook も通過、ダークモード GitHub 上で**全 7 PR 分のスタンプが黒不可視**で投稿された。以降 hook は 6 必須パラメータ全件チェックに強化されたが、行動側の原則は「**URL を手書きしない**」 — 構築は常にヘルパー / subagent 経由にすること。
- **2026-05-12 triage-review batch**(`mj()` Python helper 経由で 8 PR 分の不可視スタンプ): `triage-review` の reply batch で、body 組み立てを Python 側に任せ、`mj(text)` という short helper を実装して `mojiemoji.jozo.beer/emoji/<text>?text=<text>&background=transparent` だけ吐かせた。**`font` / `color` / `animation` / `outline` / `outline_width` の 5 必須パラメータが全部抜けた**結果、SP-ACL#1756 含む 8 件で黒不可視スタンプを投稿。以降 hook は `python3 X.py && gh api --input out.json` 形式の連結コマンドのスクリプト本文まで読みに行く (`mojiemoji-japanese-gate.py` の `SCRIPT_RE`) ように強化された。行動側の原則は「**Python / Ruby / Node 側で mojiemoji URL を文字列構築しない**」 — § Python / cross-boundary interop 参照。

飽和デフォルト下では、**本文中スタンプ ≤2 個は構成エラー**である — 出稿前に PHRASES 一覧をフルで作り直して再ディスパッチすること。

日本語の body-class surface を作りかけて「とりあえず最上部に 1 つ mojiemoji を貼って出すか」と思いかけたら、**止めること**。いずれかを取る:

1. **`mojiemoji-selector` にデリゲートする** — 本文中の強調すべき名詞・動詞をすべて含む PHRASES 一覧で、インライン飽和密度でレンダリングし、返ってきたスニペットの周りに散文を組み上げる(推奨経路)。
2. **mojiemoji を完全にスキップする** — 明示的な理由(謝罪 / セキュリティ / 法務 など — 装飾禁止リスト参照)を添えて。

### このデフォルト密度の具体像

- 事実ベースの語も、文法的に収まるならインライン埋め込みとしてスタンプして OK。多くの 2 字以上の技術系日本語の名詞・形容詞はスタンプ可能。スタンプ禁止リスト(コード、パス、識別子、リンク — 後述「絶対不変」参照)は狭い例外である。**以下は非網羅のスタンプ可能リスト** — selector がスキップ判定で迷ったときの即座のリファレンス:

  - **状態 / 完成度**: `完成`, `完了`, `終了`, `達成`, `実現`, `成功`, `着手`, `開始`, `進行`, `進捗`, `中止`, `中断`, `保留`, `未着手`, `未解決`, `未実施`, `判明`, `判断`, `決定`, `合意`, `仮置`
  - **バグ / 障害**: `バグ`, `不具合`, `障害`, `クラッシュ`, `リーク`, `漏洩`, `欠陥`, `欠落`, `致命`, `重大`, `軽微`, `異常`, `正常`, `発生`, `再現`, `再発`, `誤動作`, `誤検知`, `誤判定`, `破綻`, `破損`
  - **問題 / 課題**: `問題`, `課題`, `懸案`, `不足`, `不便`, `不備`, `不整合`, `矛盾`, `違反`, `重複`, `衝突`, `競合`, `干渉`, `齟齬`, `不明`, `不明点`, `疑問`, `疑念`
  - **改善 / 最適化**: `改善`, `改良`, `強化`, `最適`, `効率`, `高速`, `軽量`, `簡潔`, `簡素`, `整理`, `整備`, `整頓`, `整列`, `再編`, `再構成`, `削減`, `圧縮`, `刷新`, `洗練`
  - **同梱 / 連携**: `同梱`, `同期`, `同居`, `同様`, `同一`, `同等`, `同格`, `統一`, `共通`, `共有`, `連携`, `連動`, `包含`, `内包`, `付随`, `付帯`, `提供`, `配布`, `配信`, `配置`, `配備`
  - **検証 / 確認**: `検証`, `検査`, `検出`, `検知`, `確認`, `試験`, `計測`, `観測`, `監視`, `追跡`, `調査`, `分析`, `解析`, `精査`, `突合`
  - **安全 / 防御**: `安全`, `安定`, `信頼`, `堅牢`, `強固`, `保護`, `防止`, `防御`, `防壁`, `障壁`, `抑止`, `阻止`, `遮断`, `隔離`, `封鎖`
  - **危険 / 警告**: `危険`, `脅威`, `警告`, `注意`, `慎重`, `配慮`, `留意`, `警戒`, `危機`, `危惧`, `緊急`, `急務`, `急ぎ`, `要注意`
  - **評価**: `評価`, `価値`, `優秀`, `卓越`, `優位`, `不利`, `利点`, `欠点`, `長所`, `短所`, `美点`, `弱点`, `強み`, `弱み`, `見事`, `綺麗`, `完璧`
  - **動作 / 挙動**: `動作`, `挙動`, `振舞`, `反応`, `応答`, `出力`, `入力`, `通信`, `通知`, `通報`, `報告`, `伝播`, `伝達`
  - **範囲 / 限界**: `範囲`, `領域`, `対象`, `範疇`, `限界`, `境界`, `上限`, `下限`, `制限`, `規制`, `規模`, `規約`, `規則`
  - **結果 / 効果**: `結果`, `成果`, `効果`, `影響`, `余波`, `副作用`, `反映`, `波及`, `帰結`, `因果`
  - **概念 / 抽象**: `抽象`, `具体`, `本質`, `本筋`, `本来`, `概念`, `概要`, `趣旨`, `要旨`, `主旨`, `動機`, `意図`, `目的`, `観点`, `論点`, `要点`, `要諦`, `原則`, `原理`, `情報`
  - **必要性 / 許可**: `必要`, `不要`, `必須`, `任意`, `推奨`, `禁止`, `許可`, `拒否`, `拒絶`, `阻止`, `承認`, `却下`, `保留`
  - **既存 / 新規**: `既存`, `新規`, `新設`, `撤廃`, `廃止`, `廃棄`, `削除`, `除去`, `追加`, `排除`, `除外`, `包含`, `内包`, `継承`, `移植`, `移管`, `移行`, `引継`, `引き継ぎ`, `委譲`, `代替`, `代理`, `代行`
  - **比較 / 順序**: `比較`, `対比`, `対称`, `優先`, `劣後`, `上位`, `下位`, `異なる`, `同じ`, `相違`, `差分`, `差異`, `区別`, `識別`
  - **程度**: `軽微`, `重大`, `致命`, `些細`, `重要`, `重要度`, `優先度`, `重視`, `軽視`, `過小`, `過大`, `膨大`, `豊富`, `潤沢`
  - **時間性**: `即時`, `即座`, `直後`, `直前`, `緊急`, `急務`, `遅延`, `速報`, `早期`, `迅速`, `恒常`, `永続`, `一時`, `暫定`, `仮想`
  - **ドキュメント / 説明**: `説明`, `解説`, `注釈`, `補足`, `補完`, `詳細`, `概略`, `概観`, `全体像`, `全体`, `一部`, `部分`, `要約`, `抜粋`, `引用`, `参照`, `根拠`, `理由`
  - **変更 / 操作**: `変更`, `修正`, `更新`, `訂正`, `編集`, `加筆`, `推敲`, `差替`, `差し替え`, `置換`, `転送`, `転載`, `転記`, `転換`, `切替`, `切断`, `接続`, `接合`, `分離`, `分割`, `結合`, `統合`, `統廃合`, `合流`, `合算`
  - **データ / 構造**: `情報`, `仕様`, `要件`, `設計`, `実装`, `開発`, `構築`, `構成`, `構造`, `設定`, `初期化`, `紐付け`, `参照`, `保存`, `永続化`, `読込`, `書込`, `表示`, `非表示`
  - **テスト / 品質**: `テスト`, `ユニット`, `単体`, `結合`, `回帰`, `網羅`, `カバレッジ`, `健全`, `健全性`, `品質`, `信頼性`, `保守性`, `可読性`, `拡張性`
  - **判定 / 状態語**: `存在`, `不在`, `有効`, `無効`, `有害`, `無害`, `実質`, `形骸`, `準拠`, `逸脱`, `合致`, `不一致`, `妥当`, `不当`, `適切`, `不適切`
  - **頻出 ASCII / 略語**: `DB`, `E2E`, `API`, `URL`, `URI`, `UI`, `UX`, `OS`, `CI`, `CD`, `PR`, `MR`, `RFC`, `ADR`, `SLA`, `SLO`, `KPI`, `OKR`, `WIP`, `MVP`, `POC`
  - **頻出カタカナ (2-3 字)**: `バグ`, `ログ`, `テスト`, `タグ`, `パス`, `フラグ`, `フック`, `キー`, `ジョブ`, `タスク`, `スキル`, `モード`, `プラグ`, `スタブ`, `モック`
- AC チェックリスト、調査リストも、その散文にスタンプを埋め込める。
- 「1 文インラインスタンプ 2 個まで」の制約は緩和 — 文法が許す限り連ねてよい。
- セクション見出し: 見出しのキーワードをインライン埋め込みする(例 `## <デプロイ> 手順`)、または末尾に絵文字 trailing 装飾を付ける(catalog 登録済の絵文字なら mojiemoji 化、未登録なら素の Unicode。例 `## リリース 🎉` は catalog にあるので mojiemoji 化、`## デプロイ手順 🚀` は U+1F680 が catalog 外なので Unicode のまま)を推奨。見出し後の独立行 block 装飾は**撤回された** — 本文・レビュー surface での先頭/末尾 block スタンプと同じ破壊的パターンである。

### 絶対不変のもの

- **埋め込みの文法的安全性**: 埋め込みは常に成立する文でなければならない。
- **装飾は独立行**: 散文の文末に装飾を付け足さない。下に `→ <stamps>` 行を置く。
- **コード、パス、識別子、リンク**: 絶対にスタンプしない。
- **ダークモードに耐える色**(Tailwind 300〜500 域。`references/parameters.md` § Dark-mode-safe color palette 参照)。
- **アニメーション必須**。rotational 系 (`spin` / `kaiten`) は **`speed=step` または `slow` のみ可読** — `normal` / `fast` では回転が速すぎて読めなくなる。現行サービスでは `kaiten` が正準名 (`references/parameters.md` § Valid animation values 参照)。
- **アニメーション多様性**: 同じ animation を本文中で 3 回以上使わない。標準 34 種から **12 種以上の異なる値**を使う(`references/parameters.md` § Animation diversity 参照)。

### 飽和制約ブロック(mojiemoji-selector ディスパッチに貼り付ける)

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

## Surface ごとの top/closing 装飾ヒューリスティック

飽和インライン埋め込みは全 surface 共通だが、**先頭文と締めの文**(段落として独立して読まれやすい箇所)はトーンが surface タイプによって変わる。以下の表で「先頭文に埋め込みやすい語」と「締めに埋め込みやすい語」を引き当てる。装飾するのは独立行 block ではなく**その文の中の語**。

### Issue 本文(`gh issue create`)

| Issue タイプ | 先頭文に埋め込む語(例) | 締め文に埋め込む語(例) | トーン |
|---|---|---|---|
| Bug / 不具合 | `バグ` / `要対応` / `不具合` / `致命` | `修正` / `対応` / `お願い` | cautionary — 祝祭は避ける |
| Feature / 機能追加 | `機能` / `提案` / `新規` / `導入` | `よろしく` / `お願い` / `歓迎` | anticipatory neutral |
| Refactor / 整備 | `整備` / `整理` / `改善` / `刷新` | `お願い` / `レビュー` | neutral |
| Chore / 雑務 | `雑務` / `整備` / `更新` | (装飾控えめ) | minimal |
| Cosmetic / 軽微 | (装飾控えめ、1 スタンプで足る場合あり) | — | light |

### PR 本文(`gh pr create`)

| PR タイプ | 先頭文に埋め込む語(例) | 締め文に埋め込む語(例) | トーン |
|---|---|---|---|
| feat / 新機能 | `新機能` / `機能` / `実装` / `追加` | `レビュー` / `よろしく` / `歓迎` | positive momentum |
| fix / バグ修正 | `修正` / `対応` / `バグ` / `解決` | `確認` / `よろしく` | reassuring |
| refactor / 整備 | `整理` / `整備` / `綺麗` / `刷新` | `レビュー` / `よろしく` | clean / satisfied |
| chore / deps | `更新` / `整備` / `同期` | (装飾控えめ) | neutral |
| docs | `加筆` / `更新` / `整理` | `確認` | neutral / light |

### Review summary body(`gh pr review` / `gh api .../reviews`)

`verdict × finding-count` でトーンが決まる。**summary body(`body` フィールド)のみ装飾**し、inline `comments[]` の findings は素のままにする — findings は技術的引用なので装飾と干渉する。

| verdict | findings | 先頭文に埋め込む語(例) | 締め文に埋め込む語(例) | 注意 |
|---|---|---|---|---|
| `approve` | 0 (clean) | `完璧` / `綺麗` / `見事` / `LGTM` | `マージ` / `歓迎` / `お疲れさま` | celebratory。mojiemoji 単独なら inline / block どちらの LGTM も自由。他の LGTM-imagery skill と併用する場合のみ mojiemoji は inline に留める(§ LGTM 画像 参照)。 |
| `approve` | nits のみ | `綺麗` / `良い` / `軽微` | `感謝` / `お疲れさま` | thanks 寄り、celebrate しすぎない |
| `comment` | ≤2 | `確認` / `相談` / `提案` | `引き続き` / `よろしく` | tone-setter で軽く |
| `comment` | 3〜5 | `確認` / `指摘` / `検討` | `ご対応` / `よろしく` | neutral, business-like |
| `comment` | 6+ | `要点` / `観点` / `整理` | `確認` / `お願い` | matter-of-fact、スタンプ少なめでメリハリ |
| `request-changes` | — | `相談` / `観点` / `要修正` | `引き続き` / `よろしく` | cautious、pile-on しない |

`comments[]` フィールドの inline findings は**装飾しない**。findings は技術引用(コード行・対象シンボル・修正提案)であり、装飾が入ると読み手の grep 性を阻害する。

### Reply / コメント返信(`gh api .../comments`)

返信は短いので、**1 段落 1 個の punch-line スタンプ**で足りる。`address-review` / `triage-review` 系スキルが action バッジ(`action: fixed/by design/test added/deferred/wontfix`)を先頭に置くので、その下の説明文に inline 埋め込み。

- `action: fixed` の説明 → `修正` / `対応` を埋め込む
- `action: by design` の説明 → `意図` / `仕様` / `想定` を埋め込む
- `action: test added` → `追加` / `検証` を埋め込む
- `action: deferred` → `別件` / `分離` / `分割` を埋め込む
- `action: wontfix` で純粋に技術引用(test 名 / file path / spec ref)だけならスタンプを諦める

### リリースノート(`gh release create`)

`feat` / `fix` の比率に応じて feat 寄りの語(`機能` / `新規` / `追加`)か fix 寄り(`修正` / `解決`)を先頭に。締めは「みなさんありがとうございました」系を inline 埋め込み(独立行の closing block 画像は禁止 — § デフォルトのトーンとインライン飽和 § 「マントラ」参照)。

## ワークフロー

1. surface を特定する(issue / PR 本文 / レビューコメント / 返信 / リリースノート)。surface が **issue 本文 / PR 本文 / リリースノート**なら、まずバッジの有無を確認する(§ バッジと併用する を参照)。surface に応じた先頭/締め語の引き当ては § Surface ごとの top/closing 装飾ヒューリスティック を参照。
2. draft が日本語 markdown なら、まず `scripts/prestamp.py` を通す。高頻度語(修正/確認/対応/PR など)はここで決定論的に `<img>` 化し、code fence / inline code / `<img>` 既存タグ / mermaid / link target / shields.io badge などの safe-zone は保護される。
3. モードを決める(`block` vs `inline`。混在も可)。
4. **各スタンプを 3 字以内に切る**(inline・block 共通)。4 字以上のフレーズは左から 2 字ずつ厳密にチャンク化(末尾 1 字は許容)し、隣接する独立スタンプとしてセパレータ無しでレンダリングする。チャンクごとに font / color / animation を選ぶ。例と根拠は § "Phrase-length & line-break rules" 相当(上記の長さ上限・境界ヒューリスティック)を参照。
5. パラメータを選ぶ:
   - **単一フレーズ・単一の自明なプリセット**: まず `references/flavor-guide.md` でそのフレーズがスタンプ価値ありか確認し、次に `references/presets.md` で 1 行を引いて、スクリプトを直接呼ぶ。subagent は不要。
   - **それ以外**(2 フレーズ以上 / バリエーション / カタログ / 配置が曖昧 / トーン制約あり)は **必ず `mojiemoji-selector` subagent にデリゲート**する。references をメインスレッドに読み込まない。
   - **強い禁止: フラグを固定して直接スクリプトをフレーズごとにループ呼び出ししない。** ファストパスは単一フレーズ専用。`mojiemoji_markdown.py` を同じ `--font --color --animation --speed` で 2 回以上呼ぶのは、issue #166 の単調本文を生んだ仕組みそのもの(15 スタンプ全て `font=maru-bold color=60a5fa animation=spring speed=normal`)。複数フレーズの仕事は常に `mojiemoji-selector` にデリゲートし、Hard contract の多様性制約を本文全体に適用させる。
6. 返ってきたスニペットを核に最終的なメッセージを組み立てる。周辺の散文は自然に保ち、inline ではスタンプを強調として機能させる。
7. **本文構成(issue 本文 / PR 本文 / リリースノート、loud トーン)**:
   - **必須のデフォルト — インライン密度: 1 段落あたりスタンプ 1〜2 個。** 各段落で最も強調すべきキーワードを選ぶ。アイデアを担う箇条書き(要件 / 受け入れ条件)では、文法的に収まる名詞・動詞をすべて埋め込む。飽和は「全単語にスタンプする」という意味ではなく、「選択性を保ちつつ一貫した存在感を出す」こと。コードパス / 識別子 / リンクを含むセクション(関連ファイル、関連 PR、references)では、パス・識別子そのものはスタンプしないが、周辺の日本語散文(「差し替え対象」のような関係性記述、「変更不要の想定」のような括弧書き)は**スタンプして良いし、インライン飽和下ではすべき**。
   - ✗ **セクション末オチ装飾**(セクション後ろの独立行 `→ <stamp1>`)は**生成しない**。escape valve は、ユーザーがそのターン内で block 装飾意図(「→ つけて」 / 「盛大に」)と具体的な配置指示の両方を明示した場合のみ。
   - ✗ **締めの装飾**(本文末の `---` + 独立行ムードスタンプ)は**生成しない**。同じ escape valve のみ。
8. **貼り付け前に必ず検証する。** スニペット受け取り後、`references/verification.md` のスポットチェックブロックを本文全体に対して実行する。失敗があればローカルで直す(または再ディスパッチ)してから貼り付ける。
9. 本文が固まったら `scripts/coverage.py --surface <...>` で最低密度/文ヒット率/段落偏りを測る。警告が出たら装飾を足し、hook 経路で block したい時は `--mode block` を使う。
10. ユーザーが実際に投稿するよう依頼してきたら、まず文面を組み上げ、その後 `gh` コマンドを実行する。

## デリゲーション

`mojiemoji-selector` subagent を `Agent` ツールで `subagent_type: "mojiemoji-selector"` を指定してディスパッチする。入力は以下のコントラクト形式で渡す:

```
SURFACE: <issue-body|pr-body|review-comment|reply|release-note>
MODE:    <block|inline|mixed>
TONE:    <calm|neutral|loud>
PHRASES:
- <phrase> — <intent in one short clause>
- <phrase> — <intent>
CONSTRAINTS (optional):
- <e.g. "avoid red", "match thread tone">
SKILL_DIR: ${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github
```

`SKILL_DIR` は絶対パスで渡し、subagent が推測しなくて済むようにする。subagent はコンパクトな `phrase | mode | snippet` の表を返す。それ以外はコンテキストに入らない。

`model: opus` にエスカレートするのは、ユーザーが大型カタログや細かい趣味調整を求めるときだけ。多くのケースでデフォルトの `sonnet` で十分である。

### Python / cross-boundary interop

複数 PR / 複数 issue を batch で投稿するときに Python (or Ruby / Node) で body テンプレートを組み立てたくなる場面がある。**Python 側で mojiemoji URL を文字列構築してはいけない** — `?text=<text>&background=transparent` だけ並べた `mj(text)` ヘルパーは、6 必須パラメータを欠落して dark mode 不可視のスタンプを大量生産する(2026-05-12 triage-review の 7 PR で実例、§ 失敗パターン)。

2 つの安全経路:

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
   毎フレーズで font / color / animation を変えること(さもなくば issue #166 の単調本文と同じ轍を踏む)。
2. **`mojiemoji-selector` に先にバッチをレンダリングさせる**:
   subagent からスニペット表を受け取り、Python 側ではそれを*不透明な `<img>` 文字列*として変数展開のみする。Python は body 組み立ての糊にとどめ、URL 構築には触れない。

PreToolUse hook は `python3 X.py && gh api --input out.json` のような連結コマンドのスクリプト本体まで読みに行く(`mojiemoji-japanese-gate.py` の `SCRIPT_RE`)。出力 JSON がまだ存在しない瞬間でも、スクリプト中の URL テンプレートは検出される。手抜きしないこと。

### 各ディスパッチ向けの Hard contract

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

### 鉄則: スタンプ禁止 identifier(FLAVOR GATE OVERRIDE の例外)

飽和 / loud トーンで FLAVOR GATE OVERRIDE が効いていても、**以下は常にプレーンテキストのまま**。周囲がどれだけスタンプで埋まっていても、絶対にスタンプ化しない:

- **API 名 / 言語組み込み**: `Promise.all`, `Promise`, `useState`, `useEffect`, `Map`, `Map.from`, `Vec::new`, `Result`, `Option`, `Iterator::find`
- **英単語の identifier / 判定語**: `Green`, `Red`, `Blue`, `null`, `undefined`, `OK`, `NG`, `Yes`, `No`, `True`, `False`, `Success`, `Error`
- **ファイルパス**: `apps/api/src/...`, `packages/db/...`, `Sources/Foo.swift`
- **バージョン文字列**: `v1.2.3`, `0.4.0`, `Node 20`
- **コードシンボル / 型名**: `MatchingHistory`, `creativeIntegrity`, `WallpaperLoadingOverlay`
- **URL、ハッシュ、issue/PR 番号**: `#166`, `abc1234`, `https://...`
- **単位付き数値**: `100ms`, `200lines`, `5指標` の数字部分

これらはスタンプ飽和の文の中にあっても**スタンプスロットを持たない**。周りの日本語散文はスタンプして良い(飽和ではすべき)が、identifier 自体は素のまま。

**過去の具体的失敗(issue #166)**: `Promise.all` と `Green` がスタンプ化された。`Promise.all` は JavaScript の API 名、`Green` は英語の判定語。両方ともこのリストに入る — プレーンのままにすべきだった。

迷ったら問う: 「コードレビュアーがこの文字列を逐語 grep したくなるか?」 答えが Yes(identifier / API / パス)ならスタンプ不可。日本語散文としてのみ意味を持つもの(修正、検証、紐付け、保留、着地)ならスタンプ可。

スニペットを受け取った後は、`references/verification.md` § Post-dispatch spot-check の検証ブロックを実行する。失敗チェックが残った本文は出稿しない。

## 直接スクリプト(単一フレーズのファストパス)

```bash
# Block
scripts/mojiemoji_markdown.py --text 'レビュー歓迎' \
  --font maru-bold --color 3b82f6 --animation bane --speed slow

# Inline (height=24 align=absmiddle)
scripts/mojiemoji_markdown.py --text 'マジで' --inline \
  --font maru-bold --color ef4444 --animation bure --speed normal
```

フラグ: `--text`, `--alt`, `--html`, `--inline`, `--height`, `--width`, `--align`, `--font`, `--color`, `--animation`, `--speed`, `--gradient`, `--flip`, `--padding`, `--background`, `--outline`, `--outline-width`, `--path`, `--query`, `--base-url`。

`--background` のデフォルトは `transparent` で、明示的に上書きしない限りすべての URL に出力される。`--outline` はオプトイン(body-class surface では推奨)。

## デフォルト

- **デフォルトでアニメーション有り。** すべてのスタンプにアニメーションプリセットを付ける — 静止は例外であってルールではない。ムードに合うモーションを選ぶ(祝いなら `bane` / `kira` / `kirari` / `yatta`、緊迫なら `gatagata` / `bure` / `tenmetsu` / `shuchusen`、中立的なステータスなら `yurayura` / `mochimochi` / `nami`)。アニメーションを落とすのは、それがむしろ邪魔になるとき(インラインスタンプが多すぎる密な段落、または謝罪本文・障害ポストモーテムのような重いコンテキスト)のみ。
- `mojiemoji-selector` にデリゲートする場合、`TONE: calm` でもアニメーションは付く(ただし遅め・柔らかめのもの)。ユーザーが静止を求めたときに限り、明示的に `CONSTRAINTS: "no animation"` を指定する。
- **`background=transparent` を常時(意図的に設定しない限り)。** mojiemoji のデフォルト背景は白なので、未設定だとダークモードの GitHub で浮く。スクリプトはデフォルトですべての URL に `background=transparent` を吐く。`--background <color>` で上書きするのはユーザーが明示的に色付き背景を求めたときのみ。その場合はライト・ダーク両方で読めることを確認してから出稿する。
- **body-class surface でのアウトライン**: `outline=darker outline_width=2`。ライトな Tailwind 300〜400 フィルに `outline=ffffff` を組み合わせない。`references/parameters.md` § Outline 参照。

標準のアニメーション / フォント / 色の値、インラインの height 指針、「パラメータが効かなくなったとき」の復旧手順は `references/parameters.md` を参照。

サービス側のハードリミット(15 字上限、プリフライト HTTP チェック)、およびディスパッチ後検証 bash ブロックは `references/verification.md` を参照。

## 出力ルール

- そのまま貼れるスニペットを返す。説明的散文は返さない。
- issue 本文 / PR 本文 / リリースノートの場合、本文の最上部に shields.io バッジが存在することを確認する(スタンプとは別の段落)。バッジだけならまだ良い — このサーフェスでバッジ無しのスタンプは繰り返される失敗パターンである。
- block の場合、密な段落より見出し / コールアウト / チェックリスト / 締めの行を優先する。
- inline の場合、ホストの文を自然に保つ。日本語の body-class surface ではインライン飽和をデフォルトとする(1 段落最低 1〜2 個の埋め込み)。
- **コードパス、識別子、リンクはスタンプ対象外。ただし周辺の散文はスタンプ対象。** 箇条書きが `` `Sources/Foo.swift:40-55` — `WallpaperLoadingOverlay` (差し替え対象) `` のような形のとき、ファイルパスとシンボルは素のまま — だが括弧内の記述子(`差し替え対象`、`変更不要の想定`、`重点`、`導入`)は日本語散文なのでインライン飽和デフォルト下では**スタンプすべき**。「`WallpaperPresenter` の状態を *維持* する」のような文も同様 — シンボルは素のまま、記述子にスタンプが乗る。
- フレーズが flavor-guide のスタンプ禁止リストに引っかかる場合、黙って落とすか指摘する。API 名・バージョン・謝罪本文・セキュリティ/法務テキストは決して装飾しない。
- **スポットチェックは body-class surface でスタンプ数 ≥3 のとき必須、任意ではない。** 貼り付け前に `references/verification.md` § Post-dispatch spot-check(ステップ 1〜14)を本文全体に対して実行する。目視レビューでは多様性違反がすり抜ける — issue #166 は 15 スタンプで一見「装飾済み」に見えたが、スポットチェックなら捕捉できた: アニメーションが 1 種類、色が 1 種類、identifier スタンプチェックで `Promise.all` / `Green` が引っかかる。

<!--
  mojiemoji-schema-version: 2.0.0
  The hook (hooks/mojiemoji-japanese-gate.py § validate_schema_version)
  reads this marker AND each harness-local copy under
  $HOME/.config/<harness>/skills/mojiemoji-github/SKILL.md. When a
  harness copy is behind the host, the hook emits a warning to stderr
  (rc=0 by default; MOJIEMOJI_STRICT_VERSION=1 upgrades to block rc=2).

  When to bump:

    MAJOR (X.0.0)  — breaking changes to the skill contract (URL pattern
                     change, new mandatory parameter, removed parameter,
                     renamed canonical animation/font value, etc.).
                     Old harness copies *will* produce broken output
                     against the new hook — bump and treat drift as a
                     hard re-install requirement.

    MINOR (0.X.0)  — additive canonical changes (new animation, new
                     font, new optional parameter). Old harness copies
                     still produce valid output; they just miss the new
                     options.

    PATCH (0.0.X)  — wording / clarification / typo fixes. No drift
                     concern; ideally don't bump for these, but bumping
                     forces a re-pull and clears stale guidance.
-->
<!-- mojiemoji-schema-version: 2.0.0 -->
