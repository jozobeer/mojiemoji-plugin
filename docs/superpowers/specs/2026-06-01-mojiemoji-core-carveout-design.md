<!-- mojiemoji:off -->

# mojiemoji core 切り出し設計 — uv workspace + PyPI 配布

- 関連 issue: [#141](https://github.com/jozobeer/mojiemoji-plugin/issues/141)（discuss）
- ステータス: **decision**（方向性合意済み）→ 次は writing-plans で実装計画
- 日付: 2026-06-01（decision）/ 2026-08-23（main へ着地、§ 決定後の差分反映 を追記）

> このドキュメントはレビューしやすさを優先して prestamp 装飾を施していない（plain）。
> GitHub に投稿する #141 decision コメント側は dogfood gate に従い prestamp 装飾する。

## 決定サマリ

| 軸 | 決定 |
|---|---|
| 第一目的 | **PyPI で第三者配布まで今回スコープに入れる** |
| トポロジ | **同リポ内 uv workspace でパッケージ化（issue 案 A/C）** |
| 命名 | 配布名 = import 名 = CLI 名を **`mojiemoji`** に統一 |
| build backend | hatchling |
| publish | GitHub Actions + PyPI trusted publisher（OIDC、トークン保存なし） |
| タグ規約 | `core-vX.Y.Z`（PyPI publish trigger）/ `plugin-vX.Y.Z` |
| `coverage.py` | plugin 側に残置 |

この組み合わせ（同リポ workspace から `core` だけを PyPI publish）を採る理由:

- 切り出しが既存 hook / skill / agent / CI を破壊しない（互換 shim を残せる）
- catalog 育成パイプライン（#46 / #92 / #93 の自動 PR）が `data/*.yml` の同リポ内移動だけで温存される
- 配布到達は PyPI で最大化しつつ、2 リポ運用の cross-repo CI オーバーヘッドを負わない
- 実利用が積み上がれば、後から互換性を保って別リポ（issue 案 B）へ昇格できる

## 命名の根拠

PyPI / npm の空き状況を確認済み（2026-06-01 時点）:

| 候補 | PyPI | npm |
|---|---|---|
| **`mojiemoji`** | 空き | 空き |
| `mojiemoji-core` | 空き | — |
| `moji` | 取得済み | 取得済み |
| `prestamp` | 空き | 空き |

`mojiemoji` は PyPI / npm 双方が空きで、サービス `mojiemoji.jozo.beer` とブランドが一致する。
配布名・import 名・CLI 名を `mojiemoji` に揃え、npm 名前空間も予約しておく（将来の JS ラッパー用）。

- ライブラリ: `from mojiemoji import transform, render, load_catalog, report_unstamped`
- CLI: `mojiemoji`（stdin → stdout）
- 現リポ `mojiemoji-plugin` は **Claude Code プラグイン**として継続し、`mojiemoji` を依存に取る

## トポロジ（同リポ uv workspace）

```
mojiemoji-plugin/                    ← repo root = plugin（workspace root）
├─ pyproject.toml                    ← workspace 定義 + plugin dev deps + coverage 設定
├─ packages/mojiemoji-core/
│   ├─ pyproject.toml                ← name="mojiemoji", build=hatchling, deps=[pyyaml]
│   ├─ src/mojiemoji/                ← src-layout
│   │   ├─ __init__.py               ← public API 再エクスポート
│   │   ├─ cli.py                    ← [project.scripts] mojiemoji
│   │   ├─ （prestamp pipeline 一式）
│   │   ├─ （lib core subset）
│   │   └─ data/*.yml                ← ★パッケージ内へ移動
│   └─ tests/                        ← core テスト
├─ skills/ hooks/ agents/ scripts/   ← plugin 固有（core を依存）
└─ pyproject.toml [tool.uv.sources] mojiemoji = { workspace = true }
```

ローカル開発では plugin 側が `mojiemoji` を workspace 依存として解決する。
PyPI に publish するのは `mojiemoji`（core）のみで、plugin は publish しない。

## core / plugin 境界

| → core（`mojiemoji`, PyPI 公開） | → plugin（現リポに残す） |
|---|---|
| prestamp pipeline: `boundaries` / `catalog` / `render` / `emoji_pass` / `text_pass` / `lines` / `masker` / `unstamped_report` / `incremental` | `hooks/`（PreToolUse gate, PostToolUse warn） |
| `mojiemoji_markdown.py`（単発 URL 生成） | `agents/mojiemoji-selector`（cache 育成） |
| lib core subset: `term_boundaries` / `japanese_ranges` / `sentence` / `forbidden_colors` / `constants` | `skills/mojiemoji-github/SKILL.md` |
| `lib/config.py`（intensity 既定 = core CLI のユーザー設定） | `scripts/bump_catalog.py` / `cache_record.py` / `cache_stats.py` / `generate_catalog.py` |
| `data/*.yml` + `stampable-terms.txt`（package data 同梱） | **`lib/repo_policy.py`**（GitHub PR-body 政策） / `lib/cache_path.py`（cache） / `coverage.py` |

判定基準: 「呼んでも何も変えない純粋変換」＝ core、「GitHub / cache / 自動 PR / Claude 経路に依存」＝ plugin。

## load-bearing リファクタ（設計の肝）

### 1. データ解決を `importlib.resources` 化

現状 `prestamp/catalog.py` は `__file__` 相対でパッケージ**外**を辿る:

```python
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG_PATH = _SCRIPTS_DIR.parent / "data" / "prestamp-catalog.yml"
```

インストール済み wheel / `uvx` ではパッケージ外の `data/` を確実には見つけられない。
`data/*.yml` をパッケージ内（`src/mojiemoji/data/`）へ移し、以下へ変更する:

```python
from importlib.resources import files
DEFAULT_CATALOG_PATH = files("mojiemoji.data") / "prestamp-catalog.yml"
```

**実証済み**（2026-06-01, throwaway sandbox）: hatchling の src-layout は
`src/mojiemoji/data/*.yml` を wheel に追加設定なしで同梱し、
`importlib.resources.files("mojiemoji.data")` がインストール済み wheel で解決でき、
`uvx --from <wheel> mojiemoji` で console entry が走ることを確認した。
uv-runnability はこのリファクタのクリティカルパス上にある（=「フォルダ移動」ではない）。

### 2. 政策（PR-body skip）の切断

core の `prestamp/cli.py` が plugin 政策を import している:

```python
from lib.repo_policy import should_skip_pr_body   # GitHub 固有
...
skip = args.surface == "pr-body" and should_skip_pr_body()
```

`should_skip_pr_body()` は GitHub の squash/merge 設定を `gh` で読む GitHub 固有ゲートであり、
純粋 core が依存してはならない。**決定: core は PR-body 概念を一切持たない純粋変換にし、
PR-body skip 判定は plugin の hook / skill 層へ移す**（plugin が `should_skip_pr_body()` を呼び、
skip なら core を通さない）。

- 残す: `get_intensity()`（`~/.config/mojiemoji/config.json` 由来の intensity 既定）は GitHub 非依存の
  CLI ユーザー設定なので core に残す。
- 代替案（不採用）: core が純粋 `--skip` boolean だけを honor し、plugin が値を計算して渡す。
  subprocess 経路でも動くが、core に PR-body 由来のフラグ意味論が薄く残るため不採用。

これは「移動」ではなく境界設計の本丸。実装時に `--surface pr-body` の全呼び出し元
（hook / skill / CI drift check）を洗い出して移送する。

### 3. base URL 上書き経路

`lib/constants.DEFAULT_BASE_URL = "https://mojiemoji.jozo.beer"` を
`MOJIEMOJI_BASE_URL` 環境変数 + `--base-url` フラグ + 関数 kwarg で上書け状態にする
（issue 論点 2、self-host instance 用途を塞がない）。優先順位: kwarg/CLI > env > 既定。

## 配布・バージョン

- build backend は **hatchling**（非 Python データ同梱が枯れている）。
- **PyPI trusted publisher（OIDC）** を GitHub Actions の release workflow に設定し、API トークンを保存しない。
- publish 対象は `mojiemoji`（core）のみ。
- タグ規約: `core-vX.Y.Z`（PyPI publish を trigger）/ `plugin-vX.Y.Z`（Claude Code プラグイン）。
  `vX` 単体は曖昧なので使わない。
- core public API の SemVer 約束（issue 論点 9）:
  - catalog への用語追加 = patch または minor
  - public API（`transform` / `render` 等のシグネチャ）の削除・破壊 = major
- publish 前の利用経路:
  `uvx --from "git+https://github.com/jozobeer/mojiemoji-plugin#subdirectory=packages/mojiemoji-core" mojiemoji`
- publish 後:
  `uvx mojiemoji` / `uv tool install mojiemoji` / `uv run mojiemoji`

## 互換 shim と移行影響

既存パイプラインを壊さないため、以下の互換層を残す:

- `skills/mojiemoji-github/scripts/prestamp.py` shim は core の `main` を re-export し、
  `python3 prestamp.py < in.md > out.md` の文書化済みエントリを維持する。
  → CI drift check / `mojiemoji_md_edit_warn` hook / coverage がパス変更なしで動く。
- hooks の `from lib.constants import ...`（#101）を `from mojiemoji...` へ移行する。
- catalog 育成は `data/*.yml` が同リポ内に残るため、`bump_catalog.py` / `generate_catalog.py` の
  対象パス更新のみで #46 / #92 / #93 の自動 PR 経路を温存する。

### 実装時に洗い出す移行影響（writing-plans フェーズで並列に確定）

- CI drift check の prestamp 呼び出しパス
- `mojiemoji_md_edit_warn` hook の prestamp サブプロセス呼び出し
- root `pyproject.toml` の coverage source root（core / plugin で分割）
- `generate_catalog.py` / `verify-lists-vs-service.sh` の data パス
- #101 の hook `from lib.constants` 直 import の core 切り出し後の成立性
- `--surface pr-body` の全呼び出し元（政策切断に伴う移送先）

## テスト方針

- core テストを `packages/mojiemoji-core/tests/` へ分離する。
- plugin テスト（hooks / bump_catalog / repo_policy 政策）は現リポに残す。
- coverage の source root を core / plugin で分割する。
- `coverage.py`（密度メトリクス）は plugin 側に残置し、core が吐いた装飾済みテキストを後段で計測する。

## スコープ外（今回やらない）

- 別リポ `jozobeer/mojiemoji-core` への物理分離（issue 案 B）— 実利用が積み上がってから昇格。
- HTTP API（issue 案 D）— 別 issue。ローカル動作の package を先に出す。
- 他言語ポート（issue 案 E）— long-term roadmap の目印のみ。
- catalog を別パッケージ `mojiemoji-catalog` に分離する案 — 今回は core 同梱で十分。

## 検証エビデンス（2026-06-01）

throwaway sandbox（`HOME` / `XDG_*` を /tmp に隔離、live config 非接触）で次を実機確認:

1. hatchling src-layout が `mojiemoji/data/prestamp-catalog.yml` を wheel に同梱（追加設定不要）
2. `importlib.resources.files("mojiemoji.data")` がインストール済み wheel で YAML を解決
3. `uvx --from <wheel> mojiemoji --selftest` が `[project.scripts]` console entry を実行
4. `printf '...' | uvx --from <wheel> mojiemoji` の stdin → stdout 変換が成立

## 決定後の差分反映（2026-08-23 追記）

decision（2026-06-01）から main 着地までの間に入った変更のうち、切り出しの前提・影響範囲に
関わるものを反映する。**上の決定内容は変更していない** — 影響範囲の棚卸しの追記のみ。

### 技術的前提の再確認

決定当時に引用した現状コードは、いずれも現在の main と一致していることを確認済み:

- `prestamp/catalog.py:45` の `__file__` 相対パッケージ外パス解決（→ リファクタ 1 の対象）
- `prestamp/cli.py:22` の `from lib.repo_policy import should_skip_pr_body` と
  `cli.py:224` の `skip = args.surface == "pr-body" and should_skip_pr_body()`（→ リファクタ 2 の対象）

政策結合は実質この 2 行だけで、core 候補の lib モジュール
（`term_boundaries` / `japanese_ranges` / `constants` / `sentence` / `forbidden_colors`）は
いずれも stdlib のみに依存する純粋モジュールである。境界は設計どおり素直に切れる。

`packages/` ディレクトリはまだ存在せず、実装は未着手。

### 境界表に載っていなかったファイルの分類

| ファイル | 分類 | 根拠 |
|---|---|---|
| `prestamp/incremental.py` | **core** | prestamp pipeline の一部（`lib.sentence` 依存）。境界表に個別列挙が漏れていたため上表に追記した |
| `lib/plugin_root.py` | plugin | `CLAUDE_PLUGIN_ROOT` を解決する Claude Code 固有ロジック（#147）。`prestamp/*` からは未 import |
| `lib/yaml_helpers.py` | plugin | catalog 整形ヘルパー。`cache_stats.py` / `bump_catalog.py` のみが使用 |
| `lib/flavor.py` | plugin | catalog 育成系スクリプトの YAML シリアライズ |
| `cache_stats.py` | plugin | `lib.cache_path` / `lib.flavor` / `lib.yaml_helpers` 依存 |
| `lint_rendered_body.py` | plugin | mojiemoji サービスへの HTTP 検証（stdlib のみだが plugin 運用ツール） |
| `normalize_catalog_colors.py` | plugin | catalog メンテナンス（`lib.forbidden_colors` を core から import する形になる） |
| `verify-lists-vs-service.sh` | plugin | data パスの追随が必要（既出） |

### 追加された移行影響（実装時に洗い出す対象へ追加）

decision 後に `scripts/prestamp.py` への参照経路が大きく増えた。パス変更・shim 維持の判断は
これら全経路を通す必要がある:

- **`harnesses/` リファレンスアダプタ 7 種**（#150 / #157）— grok / codex / opencode /
  copilot-cli / gemini / cursor / windsurf のすべてが
  `python3 /path/to/mojiemoji-plugin/skills/mojiemoji-github/scripts/prestamp.py --surface ...`
  を fallback 経路として記載。core publish 後は `uvx mojiemoji` へ切り替える主対象
- **`harnesses/README.md` / `docs/harnesses/agy.md` / `docs/harnesses/codex.md`**
- **`README.md` の「他 AI ハーネスでの利用」節**（#158）— `uvx mojiemoji` を「core 公開後の推奨経路」と
  明記済みなので、publish 時にここを実体化する
- **Codex パッケージ**（#151 / #152）— `plugins/mojiemoji-plugin/` へ `skills/` を丸ごとコピーする
  `scripts/sync-codex-plugin-package.sh` があり、core 切り出しでコピー対象が変わる。
  `tests/test_codex_package.py` の version parity 契約も追随が必要
- **`scripts/audit-harness-skills.sh` の契約 5**（`prestamp.py` 参照の必須化）と
  **契約 6**（schema マーカー一致）— 呼び出し経路が `uvx mojiemoji` に変わると契約 5 の
  検出パターンを更新する必要がある
- **`hooks/gate/validators/catalog_leftovers.py`** の remediation メッセージが
  `{plugin_root()}/skills/mojiemoji-github/scripts/prestamp.py` を案内（#147）

### 段階的移行の方針（追加決定）

上記の参照経路が 20 箇所超に増えたため、**互換 shim（`scripts/prestamp.py`）の維持は
publish 後もしばらく継続する**。アダプタ / docs の推奨経路を `uvx mojiemoji` に切り替える作業は
core が PyPI に出てから別 PR で行い、切り出し PR 自体はパス互換を壊さないことを条件とする。

<!-- mojiemoji:on -->
