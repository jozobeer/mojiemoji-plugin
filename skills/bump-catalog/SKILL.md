---
name: bump-catalog
description: >-
  Promote frequently used mojiemoji variants from the local usage cache into
  prestamp-catalog.yml and open a deterministic catalog update pull request.
allowed-tools:
  # bump_catalog.py 本体。`--dry-run` / `--apply` / `--pr` <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%A2%E3%83%BC%E3%83%89?font=hachimaru&amp;color=4ade80&amp;animation=bane&amp;background=transparent&amp;outline=4a16a3&amp;outline_width=2" alt="モード" height="24" align="absmiddle">全てで使用。
  # `--pr` <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%A2%E3%83%BC%E3%83%89?font=noto&amp;color=22c55e&amp;animation=kage_neon&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="モード" height="24" align="absmiddle">では内部から `git` / `gh pr create` を `system()` で呼ぶが、
  # Ruby プロセス内 subprocess なので外側の Bash gate 1 つで通る。
  - Bash(python3 skills/mojiemoji-github/scripts/bump_catalog.py*)
  - Bash(python3 */skills/mojiemoji-github/scripts/bump_catalog.py*)
---

# Bump Catalog

`mojiemoji-github` <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%97%E3%83%A9%E3%82%B0?font=kurobara&amp;color=60a5fa&amp;animation=psycho&amp;background=transparent&amp;outline_width=0" alt="プラグ" height="24" align="absmiddle">インの catalog をローカル usage cache から
<img src="https://mojiemoji.jozo.beer/emoji/%E8%87%AA%E5%8B%95?font=kurobara&amp;color=4ade80&amp;animation=zairu&amp;background=transparent&amp;outline=4a16a3&amp;outline_width=2" alt="自動" height="24" align="absmiddle">的に育てる skill。selector subagent が catalog miss した term に
flavor を選定したとき、`cache_record.py` が JSONL に<img src="https://mojiemoji.jozo.beer/emoji/%E8%BF%BD%E8%A8%98?font=zero&amp;color=f59e0b&amp;animation=yatta&amp;background=transparent&amp;outline=0bf59e&amp;outline_width=2" alt="追記" height="24" align="absmiddle">する。
この skill はその cache を集計して、しきい値を満たした variant を
`prestamp-catalog.yml` に昇格させる <img src="https://mojiemoji.jozo.beer/emoji/PR?font=hachimaru&amp;color=ef4444&amp;animation=bure&amp;background=transparent&amp;outline=44ef44&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> を 1 件作る。

**全工程はトークン<img src="https://mojiemoji.jozo.beer/emoji/%E4%B8%8D%E8%A6%81?font=hachimaru&amp;color=3b82f6&amp;animation=tatemoya&amp;background=transparent&amp;outline=f63b82&amp;outline_width=2" alt="不要" height="24" align="absmiddle">・LLM <img src="https://mojiemoji.jozo.beer/emoji/%E4%B8%8D%E8%A6%81?font=mincho&amp;color=8b5cf6&amp;animation=gatagata&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="不要" height="24" align="absmiddle">・<img src="https://mojiemoji.jozo.beer/emoji/%E6%B1%BA%E5%AE%9A?font=zero&amp;color=10b981&amp;animation=mozaiku&amp;background=transparent&amp;outline=8110b9&amp;outline_width=2" alt="決定" height="24" align="absmiddle">論的。**
この<img src="https://mojiemoji.jozo.beer/emoji/%E3%82%B9%E3%82%AD%E3%83%AB?font=hachimaru&amp;color=60a5fa&amp;animation=kage_neon&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="スキル" height="24" align="absmiddle">本体は単にスクリプトを呼ぶだけ。

## 起動条件

ユーザーが明示的に「catalog を育てて」「bump-catalog 走らせて」など
要求したとき。あるいは `/bump-catalog` を叩いたとき。

## <img src="https://mojiemoji.jozo.beer/emoji/%E6%89%8B%E9%A0%86?font=kurobara&amp;color=c084fc&amp;animation=kaiten&amp;speed=slow&amp;background=transparent&amp;outline=fcc084&amp;outline_width=2" alt="手順" height="24" align="absmiddle">

1. まず引数なしで dry-run して何が<img src="https://mojiemoji.jozo.beer/emoji/%E8%BF%BD%E5%8A%A0?font=maru&amp;color=3b82f6&amp;animation=chirichiri&amp;background=transparent&amp;outline=f63b82&amp;outline_width=2" alt="追加" height="24" align="absmiddle">されるか<img src="https://mojiemoji.jozo.beer/emoji/%E7%A2%BA%E8%AA%8D?font=toge&amp;color=f59e0b&amp;animation=zanzo&amp;background=transparent&amp;outline=0bf59e&amp;outline_width=2" alt="確認" height="24" align="absmiddle">する(デフォルトが
   `--dry-run` なので破壊的操作は起きない):

   ```bash
   python3 skills/mojiemoji-github/scripts/bump_catalog.py
   ```

   <img src="https://mojiemoji.jozo.beer/emoji/%E5%87%BA%E5%8A%9B?font=tamanegi&amp;color=22c55e&amp;animation=kage_bokashi&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="出力" height="24" align="absmiddle">に「would add N variant(s) ...」が出たら次へ。「no new variants
   to add」だけならその回はスキップして終わり。

2. <img src="https://mojiemoji.jozo.beer/emoji/%E5%86%85%E5%AE%B9?font=maru-bold&amp;color=a855f7&amp;animation=mochimochi&amp;background=transparent&amp;outline=f7a855&amp;outline_width=2" alt="内容" height="24" align="absmiddle">に<img src="https://mojiemoji.jozo.beer/emoji/%E5%95%8F%E9%A1%8C?font=chikara&amp;color=10b981&amp;animation=kage_kaiten&amp;speed=slow&amp;background=transparent&amp;outline=8110b9&amp;outline_width=2" alt="問題" height="24" align="absmiddle">なければ `--pr` を付けて本実行する:

   ```bash
   python3 skills/mojiemoji-github/scripts/bump_catalog.py --pr
   ```

   `--pr` <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%A2%E3%83%BC%E3%83%89?font=noto&amp;color=22c55e&amp;animation=kage_neon&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="モード" height="24" align="absmiddle">がやること:
   - `usage.jsonl` を読む(`$MOJIEMOJI_CACHE_FILE` または
     `${XDG_DATA_HOME:-~/.local/share}/mojiemoji-plugin/usage.jsonl`)
   - 閾値(デフォルト 2)を満たした variant を diff として抽出
   - <img src="https://mojiemoji.jozo.beer/emoji/%E6%97%A2%E5%AD%98?font=maru-bold&amp;color=c084fc&amp;animation=ekken&amp;background=transparent&amp;outline=fcc084&amp;outline_width=2" alt="既存" height="24" align="absmiddle"> variant とまったく<img src="https://mojiemoji.jozo.beer/emoji/%E5%90%8C%E4%B8%80?font=maru&amp;color=fb923c&amp;animation=neruneru&amp;background=transparent&amp;outline=0cea58&amp;outline_width=2" alt="同一" height="24" align="absmiddle">の flavor はスキップ
   - `prestamp-catalog.yml` をマージ
   - `plugin.json` の patch version を bump
   - clean tree <img src="https://mojiemoji.jozo.beer/emoji/%E6%A4%9C%E8%A8%BC?font=gothic&amp;color=22c55e&amp;animation=nami&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="検証" height="24" align="absmiddle"> + `git fetch origin main && git checkout main && git pull`
   - `feat/auto-catalog-grow-<yyyymmdd>` ブランチを切って commit + push
   - `gh pr create --assignee @me` で <img src="https://mojiemoji.jozo.beer/emoji/PR?font=maru&amp;color=34d399&amp;animation=gatagata&amp;background=transparent&amp;outline=9934d3&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> を作成
   - <img src="https://mojiemoji.jozo.beer/emoji/PR?font=hachimaru&amp;color=ef4444&amp;animation=bure&amp;background=transparent&amp;outline=44ef44&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> <img src="https://mojiemoji.jozo.beer/emoji/URL?font=kurobara&amp;color=facc15&amp;animation=mozaiku&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="URL" height="24" align="absmiddle"> を stdout に出す

3. <img src="https://mojiemoji.jozo.beer/emoji/PR?font=toge&amp;color=3b82f6&amp;animation=zairu&amp;background=transparent&amp;outline=f63b82&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> <img src="https://mojiemoji.jozo.beer/emoji/URL?font=pixel&amp;color=f87171&amp;animation=ekken&amp;background=transparent&amp;outline=26dc26&amp;outline_width=2" alt="URL" height="24" align="absmiddle"> をユーザーに<img src="https://mojiemoji.jozo.beer/emoji/%E5%A0%B1%E5%91%8A?font=hachimaru&amp;color=60a5fa&amp;animation=yoko_scroll&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="報告" height="24" align="absmiddle">する。それだけ。

## オプション

- catalog だけ<img src="https://mojiemoji.jozo.beer/emoji/%E6%9B%B4%E6%96%B0?font=toge&amp;color=facc15&amp;animation=neruneru&amp;background=transparent&amp;outline=04ca8a&amp;outline_width=2" alt="更新" height="24" align="absmiddle">したい(<img src="https://mojiemoji.jozo.beer/emoji/PR?font=toge&amp;color=3b82f6&amp;animation=zairu&amp;background=transparent&amp;outline=f63b82&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> は手で出す)なら `--apply`:

  ```bash
  python3 skills/mojiemoji-github/scripts/bump_catalog.py --apply
  ```

  これは `prestamp-catalog.yml` のマージのみ。`plugin.json` も触らず git
  操作もしない。

- 閾値を変えたいなら `--threshold N` (デフォルト 2)。1 件単位でも
  複利が効くという<img src="https://mojiemoji.jozo.beer/emoji/%E8%A6%B3%E7%82%B9?font=noto&amp;color=ef4444&amp;animation=yatta&amp;background=transparent&amp;outline=44ef44&amp;outline_width=2" alt="観点" height="24" align="absmiddle">で、しきい値は低めに保つのが<img src="https://mojiemoji.jozo.beer/emoji/%E6%8E%A8%E5%A5%A8?font=chikara&amp;color=f43f5e&amp;animation=mochimochi&amp;background=transparent&amp;outline=5ef43f&amp;outline_width=2" alt="推奨" height="24" align="absmiddle">。

## <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%A2%E3%83%BC%E3%83%89?font=noto&amp;color=22c55e&amp;animation=kage_neon&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="モード" height="24" align="absmiddle">まとめ

| <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%A2%E3%83%BC%E3%83%89?font=noto&amp;color=22c55e&amp;animation=kage_neon&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="モード" height="24" align="absmiddle"> | catalog | plugin.json | git/<img src="https://mojiemoji.jozo.beer/emoji/PR?font=toge&amp;color=3b82f6&amp;animation=zairu&amp;background=transparent&amp;outline=f63b82&amp;outline_width=2" alt="PR" height="24" align="absmiddle"> |
|---|---|---|---|
| `--dry-run` (default) | — | — | — |
| `--apply` | ✓ | — | — |
| `--pr` | ✓ | ✓ (patch bump) | ✓ |

## <img src="https://mojiemoji.jozo.beer/emoji/%E6%B3%A8%E6%84%8F?font=toge&amp;color=f472b6&amp;animation=kage_kaiten&amp;speed=slow&amp;background=transparent&amp;outline=77db27&amp;outline_width=2" alt="注意" height="24" align="absmiddle">

- この<img src="https://mojiemoji.jozo.beer/emoji/%E3%82%B9%E3%82%AD%E3%83%AB?font=akzk&amp;color=22c55e&amp;animation=chirichiri&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="スキル" height="24" align="absmiddle">は catalog の<img src="https://mojiemoji.jozo.beer/emoji/%E8%87%AA%E5%8B%95?font=kurobara&amp;color=4ade80&amp;animation=zairu&amp;background=transparent&amp;outline=4a16a3&amp;outline_width=2" alt="自動" height="24" align="absmiddle">マージのみを担当する。**人間レビューは
  <img src="https://mojiemoji.jozo.beer/emoji/%E5%BF%85%E9%A0%88?font=dela&amp;color=22c55e&amp;animation=patapata&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="必須" height="24" align="absmiddle">** — auto-merge は<img src="https://mojiemoji.jozo.beer/emoji/%E7%A6%81%E6%AD%A2?font=maru&amp;color=8b5cf6&amp;animation=nami&amp;background=transparent&amp;outline=f68b5c&amp;outline_width=2" alt="禁止" height="24" align="absmiddle">。
- スクリプトは Phase 1 <img src="https://mojiemoji.jozo.beer/emoji/%E5%AE%9F%E8%A3%85?font=chikara&amp;color=ef4444&amp;animation=zanzo&amp;background=transparent&amp;outline=44ef44&amp;outline_width=2" alt="実装" height="24" align="absmiddle">(<img src="https://mojiemoji.jozo.beer/emoji/%E5%8F%82%E7%85%A7?font=mincho&amp;color=60a5fa&amp;animation=tate_scroll&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="参照" height="24" align="absmiddle">: GitHub Issue #46)。今後の Phase で
  GitHub Actions による週次 cron、公開 cache 集約方法などを<img src="https://mojiemoji.jozo.beer/emoji/%E8%BF%BD%E5%8A%A0?font=maru&amp;color=3b82f6&amp;animation=chirichiri&amp;background=transparent&amp;outline=f63b82&amp;outline_width=2" alt="追加" height="24" align="absmiddle">する予定。

## <img src="https://mojiemoji.jozo.beer/emoji/%E5%85%A5%E5%8A%9B?font=akzk&amp;color=f97316&amp;animation=nami&amp;background=transparent&amp;outline=16f973&amp;outline_width=2" alt="入力" height="24" align="absmiddle">枯渇時 (#92 / #93)

`usage.jsonl` が空 / ほぼ空のときは `bump-catalog` を回しても "no
new variants to add" しか出ない。これは selector subagent が
起動していないサイン (prestamp 過剰<img src="https://mojiemoji.jozo.beer/emoji/%E5%8A%B9%E7%8E%87?font=toge&amp;color=fb923c&amp;animation=mozaiku&amp;background=transparent&amp;outline=0cea58&amp;outline_width=2" alt="効率" height="24" align="absmiddle">化による)。draft markdown が
あるなら `/mojiemoji-propose <path>` を先に回して、未 stamp の 2-8 字
<img src="https://mojiemoji.jozo.beer/emoji/%E6%97%A5?font=tamanegi&amp;color=f87171&amp;animation=kage_neon&amp;background=transparent&amp;outline=26dc26&amp;outline_width=2" alt="日" height="24" align="absmiddle">本語連続を selector に投げて cache に<img src="https://mojiemoji.jozo.beer/emoji/%E8%BF%BD%E8%A8%98?font=akzk&amp;color=c084fc&amp;animation=chirichiri&amp;background=transparent&amp;outline=fcc084&amp;outline_width=2" alt="追記" height="24" align="absmiddle">してから `bump-catalog` を
呼ぶ。
