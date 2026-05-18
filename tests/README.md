# tests/

`hooks/mojiemoji_japanese_gate.py` の pytest スイート。

## 走らせ方

```bash
pip install pytest
python3 -m pytest
```

ルートから `python3 -m pytest tests/ -v` でも可。

## 構成

- `conftest.py` — `run_hook` fixture (PreToolUse JSON を hook の stdin に流して `CompletedProcess` を返す)、`stamp_url` / `stamp_img` ヘルパー
- `test_gate.py` — クラス単位でゲートの段階別にケースをグループ化:
  - `TestToolFiltering` — 対象外ツールはすべて exit 0
  - `TestLanguageFiltering` — 英語 body はパス
  - `TestBypass` — `MOJIEMOJI_HOOK_DISABLED=1` の Bash プレフィックス / MCP body 内、旧名 `HOOK_DISABLE=1` がもう bypass しないこと
  - `TestBashHappyPath` — 装飾完備の `gh pr create` / `gh api .../reviews` はパス
  - `TestBashBlocking` — zero stamps / 必須パラ欠落 / 非 canonical font / 非 canonical animation / named color
  - `TestAnimationConflicts` — disco × outline / kaiten + 速度
  - `TestOutlineValidity` — outline の値検証
  - `TestFileInspection` — `--body-file` / `--input` / インタプリタ起動スクリプト
  - `TestMcpPath` — MCP 経路 (aliased server も含む)、read-only ツール、review body / `comments[].body` の個別検査

## 設計メモ

- subprocess で hook 本体を実プロセスとして起動して exit code を確認する形式 — 内部ロジックを import せず、production と同じ stdin/stdout/stderr/exit-code 契約だけを検証
- JSON ペイロードは Python dict を `run_hook` 内で `json.dumps` して stdin に流す。fixture ファイルは増やさない (case がコードに残るほうが diff レビュー時の意図が明瞭なため)
- body file / script file のテストは `tmp_path` 上に実ファイルを作り、cwd をそこに向けて hook の path resolution を本物の I/O 込みで検証する
