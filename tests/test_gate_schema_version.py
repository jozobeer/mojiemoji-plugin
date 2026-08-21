"""Tests for `validators/schema_version.py` (issue #80 drift detection).

Verify validate_schema_version's behaviour across the 4 cases:
marker present + match / mismatch / missing on harness file, strict
mode block, host-marker-missing no-op, and absent harness file skip.

These tests import the validator module directly and monkeypatch the
file-lookup hooks — they don't shell out through the full
PreToolUse pipeline because we want to exercise the per-case stderr
output, not the integrated exit code path.
"""

from __future__ import annotations


class TestSchemaVersionDrift:
    """Verify validate_schema_version's behaviour across the 4 cases:
    marker present + match / mismatch / missing on harness file, and
    strict mode block.
    """

    @staticmethod
    def _import_schema_version_mod():
        # The schema-version drift validator lives in
        # `hooks/gate/validators/schema_version.py`. We splice the
        # `hooks/` directory onto sys.path so the import works
        # regardless of pytest invocation cwd, then return the module
        # for monkeypatch.setattr to mutate. `monkeypatch` already
        # restores patched attributes between tests, so we rely on
        # the import cache rather than reloading the module each time.
        import importlib
        import sys
        from conftest import HOOK
        hooks_dir = HOOK.parent
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        return importlib.import_module("gate.validators.schema_version")

    @staticmethod
    def _write_skill(path, version):
        path.parent.mkdir(parents=True, exist_ok=True)
        if version is None:
            path.write_text("# SKILL.md (no marker)\n")
        else:
            path.write_text(f"# SKILL.md\n\n<!-- mojiemoji-schema-version: {version} -->\n")

    def test_match_emits_nothing(self, tmp_path, monkeypatch, capsys):
        mod = self._import_schema_version_mod()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "host.md")
        # Re-cache by clearing the sentinel.
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "host.md", "2.0.0")
        # Point all harness paths at one matching file.
        harness_path = tmp_path / "claude" / "SKILL.md"
        self._write_skill(harness_path, "2.0.0")
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("claude", harness_path),)
        )

        rc = mod.validate_schema_version("ダミー")

        captured = capsys.readouterr()
        assert rc == 0
        assert captured.err == ""

    def test_mismatch_warns_but_does_not_block(self, tmp_path, monkeypatch, capsys):
        mod = self._import_schema_version_mod()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "host.md")
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "host.md", "2.0.0")
        stale = tmp_path / "codex" / "SKILL.md"
        self._write_skill(stale, "1.5.0")
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("codex", stale),)
        )

        rc = mod.validate_schema_version("ダミー")

        captured = capsys.readouterr()
        assert rc == 0  # warn-only by default
        assert "expected: 2.0.0" in captured.err
        assert "found:    1.5.0" in captured.err
        assert "codex" in captured.err

    def test_missing_marker_on_harness_warns(self, tmp_path, monkeypatch, capsys):
        mod = self._import_schema_version_mod()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "host.md")
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "host.md", "2.0.0")
        no_marker = tmp_path / "gemini" / "SKILL.md"
        self._write_skill(no_marker, None)
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("gemini", no_marker),)
        )

        rc = mod.validate_schema_version("ダミー")

        captured = capsys.readouterr()
        assert rc == 0
        assert "(marker missing)" in captured.err
        assert "gemini" in captured.err

    def test_strict_mode_mismatch_blocks(self, tmp_path, monkeypatch, capsys):
        mod = self._import_schema_version_mod()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "host.md")
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "host.md", "2.0.0")
        stale = tmp_path / "opencode" / "SKILL.md"
        self._write_skill(stale, "1.0.0")
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("opencode", stale),)
        )
        monkeypatch.setenv("MOJIEMOJI_STRICT_VERSION", "1")

        rc = mod.validate_schema_version("ダミー")

        assert rc == 2

    def test_host_marker_missing_is_noop(self, tmp_path, monkeypatch, capsys):
        # When the host SKILL.md has no marker (drift-check disabled),
        # the stage must not emit anything regardless of harness state.
        mod = self._import_schema_version_mod()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "no-marker-host.md")
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "no-marker-host.md", None)
        stale = tmp_path / "codex" / "SKILL.md"
        self._write_skill(stale, "1.0.0")
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("codex", stale),)
        )

        rc = mod.validate_schema_version("ダミー")

        captured = capsys.readouterr()
        assert rc == 0
        assert captured.err == ""

    def test_absent_harness_files_are_skipped(self, tmp_path, monkeypatch, capsys):
        # Harness path doesn't exist — should silently skip, not warn.
        mod = self._import_schema_version_mod()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "host.md")
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "host.md", "2.0.0")
        nonexistent = tmp_path / "windsurf" / "never-existed.md"
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("windsurf", nonexistent),)
        )

        rc = mod.validate_schema_version("ダミー")

        captured = capsys.readouterr()
        assert rc == 0
        assert captured.err == ""

    def test_default_harness_paths_include_agy(self, monkeypatch, tmp_path):
        mod = self._import_schema_version_mod()
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path / "home")
        paths = mod._harness_skill_paths()
        labels = [label for label, _ in paths]
        assert "agy (global skill)" in labels
        assert "agy (skill)" in labels
        assert "agy (config skill)" in labels
        assert "agy (rule)" in labels
        assert "agy (config rule)" in labels

    def test_agy_mismatch_warns(self, tmp_path, monkeypatch, capsys):
        mod = self._import_schema_version_mod()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "host.md")
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "host.md", "2.0.0")
        stale = tmp_path / "agy" / "SKILL.md"
        self._write_skill(stale, "1.0.0")
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("agy (global skill)", stale),)
        )

        rc = mod.validate_schema_version("ダミー")

        captured = capsys.readouterr()
        assert rc == 0
        assert "expected: 2.0.0" in captured.err
        assert "found:    1.0.0" in captured.err
        assert "agy (global skill)" in captured.err

