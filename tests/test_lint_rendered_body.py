"""Tests for the rendered-body mojiemoji URL linter."""

from __future__ import annotations

import importlib.util
import sys

from conftest import LINT_RENDERED_BODY, stamp_img, run_py


def load_module():
    spec = importlib.util.spec_from_file_location("lint_rendered_body", LINT_RENDERED_BODY)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_named_color_blocks_before_http() -> None:
    mod = load_module()

    def fail_if_called(url: str) -> int:
        raise AssertionError(f"HTTP should not be called for local color failure: {url}")

    findings = mod.lint_text(stamp_img(color="red"), status_for_url=fail_if_called)

    assert len(findings) == 1
    assert "color must be 6-digit hex" in findings[0].message
    assert "color=red" in findings[0].url


def test_http_non_200_blocks() -> None:
    mod = load_module()
    findings = mod.lint_text(stamp_img(color="3b82f6"), status_for_url=lambda _url: 400)

    assert len(findings) == 1
    assert findings[0].message == "HTTP 400"


def test_head_status_uses_linter_user_agent(monkeypatch) -> None:
    mod = load_module()
    requests = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout):
        requests.append(request)
        return Response()

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)

    assert mod.head_status("https://mojiemoji.jozo.beer/emoji/test", 5.0) == 200
    assert requests[0].get_method() == "HEAD"
    assert requests[0].get_header("User-agent") == "mojiemoji-plugin-lint/1.0"


def test_html_escaped_url_is_normalized_before_http() -> None:
    mod = load_module()
    calls: list[str] = []

    def ok(url: str) -> int:
        calls.append(url)
        return 200

    findings = mod.lint_text(stamp_img().replace("&", "&amp;"), status_for_url=ok)

    assert findings == []
    assert len(calls) == 1
    assert "&amp;" not in calls[0]
    assert "&background=transparent" in calls[0]


def test_cli_exits_2_for_named_color_without_http() -> None:
    proc = run_py(LINT_RENDERED_BODY, stamp_img(color="red"))

    assert proc.returncode == 2
    assert "color must be 6-digit hex" in proc.stderr
    assert "color=red" in proc.stderr
