"""Tests for issue #138 PR body repo-policy gate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from conftest import COVERAGE, PRESTAMP, REPO_ROOT

SCRIPTS = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from lib import repo_policy  # noqa: E402

BODY = "これは修正と確認を含むPR本文です。\n"


def _completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def _runner_for(*, remote: str, api: dict | None = None, api_returncode: int = 0):
    def _run(args, **kwargs):
        if args[:4] == ["git", "config", "--get", "remote.origin.url"]:
            return _completed(remote)
        if args[:3] == ["gh", "api", "repos/o/r"]:
            return _completed(json.dumps(api or {}), api_returncode)
        return _completed("", 1)

    return _run


def _write_policy_cache(
    xdg_cache_home: Path,
    *,
    owner: str = "jozobeer",
    repo: str = "mojiemoji-plugin",
    squash: str,
    merge: str,
    fetched_at: datetime | None = None,
) -> None:
    path = xdg_cache_home / "mojiemoji" / "repo-policy" / f"{owner}--{repo}.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "squash_merge_commit_message": squash,
                "merge_commit_message": merge,
                "fetched_at": (fetched_at or datetime.now(timezone.utc)).isoformat(),
            }
        ),
        encoding="utf-8",
    )


def _run_py(script: Path, text: str, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged_env = {**os.environ, **env}
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=text,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=merged_env,
        timeout=10,
    )


def test_repo_policy_fetches_and_classifies_safe(tmp_path: Path) -> None:
    state = repo_policy.repo_policy_state(
        owner="o",
        repo="r",
        env={"XDG_CACHE_HOME": str(tmp_path)},
        runner=_runner_for(
            remote="git@github.com:o/r.git",
            api={
                "squash_merge_commit_message": "COMMIT_MESSAGES",
                "merge_commit_message": "PR_TITLE",
            },
        ),
    )

    assert state == repo_policy.POLICY_SAFE


@pytest.mark.parametrize(
    ("squash", "merge"),
    [
        ("PR_BODY", "PR_TITLE"),
        ("COMMIT_MESSAGES", "PR_BODY"),
    ],
)
def test_repo_policy_classifies_pr_body_leaks_from_cache(
    tmp_path: Path, squash: str, merge: str
) -> None:
    _write_policy_cache(tmp_path, squash=squash, merge=merge)

    state = repo_policy.repo_policy_state(
        owner="jozobeer",
        repo="mojiemoji-plugin",
        env={"XDG_CACHE_HOME": str(tmp_path)},
        runner=_runner_for(remote=""),
    )

    assert state == repo_policy.POLICY_LEAKS


def test_policy_state_defaults_absent_allow_flags_to_true() -> None:
    # Pre-existing cache entries carry no allow_* flags; classification
    # must stay conservative (LEAKS) rather than silently downgrade.
    assert (
        repo_policy.policy_state(
            {"squash_merge_commit_message": "PR_BODY", "merge_commit_message": "PR_TITLE"}
        )
        == repo_policy.POLICY_LEAKS
    )


@pytest.mark.parametrize(
    ("squash", "merge", "allow_squash", "allow_merge"),
    [
        ("PR_BODY", "PR_TITLE", False, True),
        ("COMMIT_MESSAGES", "PR_BODY", True, False),
        ("PR_BODY", "PR_BODY", False, False),
    ],
)
def test_policy_state_safe_when_pr_body_method_disabled(
    squash: str, merge: str, allow_squash: bool, allow_merge: bool
) -> None:
    assert (
        repo_policy.policy_state(
            {
                "squash_merge_commit_message": squash,
                "merge_commit_message": merge,
                "allow_squash_merge": allow_squash,
                "allow_merge_commit": allow_merge,
            }
        )
        == repo_policy.POLICY_SAFE
    )


def test_policy_state_leaks_when_pr_body_method_enabled() -> None:
    assert (
        repo_policy.policy_state(
            {
                "squash_merge_commit_message": "PR_BODY",
                "merge_commit_message": "PR_TITLE",
                "allow_squash_merge": True,
                "allow_merge_commit": False,
            }
        )
        == repo_policy.POLICY_LEAKS
    )


def test_repo_policy_safe_when_fetched_pr_body_method_disabled(tmp_path: Path) -> None:
    state = repo_policy.repo_policy_state(
        owner="o",
        repo="r",
        env={"XDG_CACHE_HOME": str(tmp_path)},
        runner=_runner_for(
            remote="git@github.com:o/r.git",
            api={
                "squash_merge_commit_message": "PR_BODY",
                "merge_commit_message": "PR_TITLE",
                "allow_squash_merge": False,
                "allow_merge_commit": True,
            },
        ),
    )

    assert state == repo_policy.POLICY_SAFE


def test_repo_policy_unknown_when_fetch_fails(tmp_path: Path) -> None:
    state = repo_policy.repo_policy_state(
        owner="o",
        repo="r",
        env={"XDG_CACHE_HOME": str(tmp_path)},
        runner=_runner_for(remote="git@github.com:o/r.git", api_returncode=1),
    )

    assert state == repo_policy.POLICY_UNKNOWN


def test_repo_policy_re_fetches_stale_or_corrupt_cache(tmp_path: Path) -> None:
    _write_policy_cache(
        tmp_path,
        owner="o",
        repo="r",
        squash="PR_BODY",
        merge="PR_TITLE",
        fetched_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )

    state = repo_policy.repo_policy_state(
        owner="o",
        repo="r",
        env={"XDG_CACHE_HOME": str(tmp_path)},
        runner=_runner_for(
            remote="git@github.com:o/r.git",
            api={
                "squash_merge_commit_message": "BLANK",
                "merge_commit_message": "PR_TITLE",
            },
        ),
    )

    assert state == repo_policy.POLICY_SAFE


def test_repo_policy_re_fetches_broken_json_cache(tmp_path: Path) -> None:
    path = tmp_path / "mojiemoji" / "repo-policy" / "o--r.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")

    state = repo_policy.repo_policy_state(
        owner="o",
        repo="r",
        env={"XDG_CACHE_HOME": str(tmp_path)},
        runner=_runner_for(
            remote="git@github.com:o/r.git",
            api={
                "squash_merge_commit_message": "BLANK",
                "merge_commit_message": "PR_TITLE",
            },
        ),
    )

    assert state == repo_policy.POLICY_SAFE


@pytest.mark.parametrize(
    "url",
    [
        "ssh://git@github.com/o/r.git",
        "ssh://git@github.com/o/r",
        "git@github.com:o/r.git",
        "https://github.com/o/r.git",
        "https://user@github.com/o/r",
    ],
)
def test_repo_from_remote_url_parses_github_forms(url: str) -> None:
    assert repo_policy.repo_from_remote_url(url) == ("o", "r")


@pytest.mark.parametrize(
    "url",
    [
        "ssh://git@gitlab.com/o/r.git",
        "https://example.com/o/r",
        "",
    ],
)
def test_repo_from_remote_url_rejects_non_github(url: str) -> None:
    assert repo_policy.repo_from_remote_url(url) is None


def test_force_env_disables_skip_even_for_unknown_repo() -> None:
    assert not repo_policy.should_skip_pr_body(
        env={"MOJIEMOJI_FORCE_PR_BODY": "1"},
        runner=_runner_for(remote="", api_returncode=1),
    )


def test_prestamp_pr_body_skips_when_repo_policy_leaks(tmp_path: Path) -> None:
    _write_policy_cache(tmp_path, squash="PR_BODY", merge="PR_TITLE")
    proc = _run_py(
        PRESTAMP,
        BODY,
        "--surface",
        "pr-body",
        env={"XDG_CACHE_HOME": str(tmp_path)},
    )

    assert proc.returncode == 0
    assert proc.stdout == BODY


def test_prestamp_pr_body_decorates_when_repo_policy_safe(tmp_path: Path) -> None:
    _write_policy_cache(tmp_path, squash="BLANK", merge="PR_TITLE")
    proc = _run_py(
        PRESTAMP,
        BODY,
        "--surface",
        "pr-body",
        env={"XDG_CACHE_HOME": str(tmp_path)},
    )

    assert proc.returncode == 0
    assert "<img" in proc.stdout


def test_prestamp_pr_body_force_decorates_even_when_policy_leaks(tmp_path: Path) -> None:
    _write_policy_cache(tmp_path, squash="PR_BODY", merge="PR_TITLE")
    proc = _run_py(
        PRESTAMP,
        BODY,
        "--surface",
        "pr-body",
        env={
            "XDG_CACHE_HOME": str(tmp_path),
            "MOJIEMOJI_FORCE_PR_BODY": "1",
        },
    )

    assert proc.returncode == 0
    assert "<img" in proc.stdout


def test_coverage_pr_body_skips_when_policy_leaks(tmp_path: Path) -> None:
    _write_policy_cache(tmp_path, squash="COMMIT_MESSAGES", merge="PR_BODY")
    proc = _run_py(
        COVERAGE,
        BODY,
        "--surface",
        "pr-body",
        "--mode",
        "block",
        env={"XDG_CACHE_HOME": str(tmp_path)},
    )

    assert proc.returncode == 0
    assert "policy=skip" in proc.stdout
