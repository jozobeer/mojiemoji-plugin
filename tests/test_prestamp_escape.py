"""Tests for prestamp.py's `<!-- mojiemoji:off -->` / `:on` escape markers.

When `:off` appears on its own line, prestamp skips both the term and
emoji passes until a matching `:on` (or EOF). Redundant markers no-op,
markers survive verbatim in output (GitHub renders HTML comments as
nothing), and the off region also freezes the emoji pass.
"""

from __future__ import annotations

from conftest import PRESTAMP, run_py


def test_prestamp_skips_transform_inside_off_on_markers() -> None:
    body = (
        "修正の確認。\n"
        "\n"
        "<!-- mojiemoji:off -->\n"
        "> プレーンな例: これは修正と確認と対応がそのまま。\n"
        "<!-- mojiemoji:on -->\n"
        "\n"
        "ここからまた修正。\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "3")

    assert proc.returncode == 0
    before, rest = proc.stdout.split("<!-- mojiemoji:off -->", 1)
    disabled, after = rest.split("<!-- mojiemoji:on -->", 1)

    assert "<img" in before
    assert "<img" not in disabled
    assert "修正" in disabled and "確認" in disabled and "対応" in disabled
    assert "<img" in after


def test_prestamp_off_without_on_extends_to_eof() -> None:
    body = (
        "修正前のスタンプ。\n"
        "<!-- mojiemoji:off -->\n"
        "ここから先は修正も確認も対応もスタンプにならない。\n"
        "ファイル末尾まで継続。\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "1")

    assert proc.returncode == 0
    _, disabled = proc.stdout.split("<!-- mojiemoji:off -->", 1)
    assert "<img" not in disabled


def test_prestamp_redundant_off_and_on_are_no_ops() -> None:
    body = (
        "<!-- mojiemoji:off -->\n"
        "内側 off も no-op、確認 raw。\n"
        "<!-- mojiemoji:off -->\n"
        "ここも修正 raw。\n"
        "<!-- mojiemoji:on -->\n"
        "ここから修正は stamp。\n"
        "<!-- mojiemoji:on -->\n"
        "redundant on の後も対応はそのまま stamp。\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "2")

    assert proc.returncode == 0
    head, tail = proc.stdout.split("<!-- mojiemoji:on -->", 1)
    assert "<img" not in head
    assert "<img" in tail


def test_prestamp_off_on_freezes_emoji_pass_too() -> None:
    body = (
        "🎉 はスタンプされる\n"
        "<!-- mojiemoji:off -->\n"
        "🎉 はそのまま\n"
        "<!-- mojiemoji:on -->\n"
        "🎉 もう一度スタンプ\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "4")

    assert proc.returncode == 0
    # 2 stamps total — outside the off-region only.
    assert proc.stdout.count("<img") == 2


def test_prestamp_off_on_markers_render_invisibly() -> None:
    # GitHub renders HTML comments as nothing — the markers must survive
    # verbatim in the output so author intent is preserved.
    body = (
        "<!-- mojiemoji:off -->\n"
        "raw line\n"
        "<!-- mojiemoji:on -->\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "1")

    assert proc.returncode == 0
    assert "<!-- mojiemoji:off -->" in proc.stdout
    assert "<!-- mojiemoji:on -->" in proc.stdout
