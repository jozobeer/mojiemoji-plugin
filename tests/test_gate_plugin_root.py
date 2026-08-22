"""Tests for `lib.plugin_root` and remediation path resolution (#147).

Claude Code injects `CLAUDE_PLUGIN_ROOT` into hook subprocesses but NOT
into the interactive Bash tool environment, so remediation text that the
gate emits for the agent must embed the *resolved* absolute path — a
literal `${CLAUDE_PLUGIN_ROOT}` degrades to `/skills/...` where the
agent would run it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from conftest import HOOK, REPO_ROOT

JP_BODY = "これは日本語の本文です。"


def _import_plugin_root_mod():
    import importlib

    scripts_dir = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    return importlib.import_module("lib.plugin_root")


class TestPluginRootResolution:
    def test_env_value_wins(self, monkeypatch):
        mod = _import_plugin_root_mod()
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/opt/claude/plugins/mojiemoji/")
        assert mod.plugin_root() == "/opt/claude/plugins/mojiemoji"

    def test_fallback_derives_from_module_location(self, monkeypatch):
        mod = _import_plugin_root_mod()
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        assert mod.plugin_root() == str(REPO_ROOT)


class TestRemediationPathEmbedding:
    """The hook's stderr must contain runnable absolute paths."""

    @staticmethod
    def _run_gate(env_overrides: dict[str, str | None], tmp_path):
        env = {**os.environ}
        for key, value in env_overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": f'gh issue create --title "x" --body "{JP_BODY}"'},
        }
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            env=env,
            timeout=10,
        )

    def test_without_env_embeds_derived_absolute_path(self, tmp_path):
        result = self._run_gate({"CLAUDE_PLUGIN_ROOT": None}, tmp_path)
        assert result.returncode == 2
        assert "${CLAUDE_PLUGIN_ROOT}" not in result.stderr
        assert f"{REPO_ROOT}/skills/mojiemoji-github" in result.stderr

    def test_with_env_embeds_injected_root(self, tmp_path):
        result = self._run_gate({"CLAUDE_PLUGIN_ROOT": "/tmp/fake-plugin-root"}, tmp_path)
        assert result.returncode == 2
        assert "${CLAUDE_PLUGIN_ROOT}" not in result.stderr
        assert "/tmp/fake-plugin-root/skills/mojiemoji-github" in result.stderr
