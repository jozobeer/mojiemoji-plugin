"""Repository merge-message policy for PR body stamping.

GitHub can copy the PR body into squash / merge commit messages. When
either setting uses ``PR_BODY``, mojiemoji HTML in the PR body leaks into
commit history, so PR body decoration defaults to skip.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional
from urllib.parse import urlparse

FORCE_PR_BODY_ENV = "MOJIEMOJI_FORCE_PR_BODY"
POLICY_SAFE = "safe"
POLICY_LEAKS = "leaks"
POLICY_UNKNOWN = "unknown"
PR_BODY = "PR_BODY"
TTL_SECONDS = 60 * 60

Runner = Callable[..., subprocess.CompletedProcess[str]]
PolicyState = str


def force_pr_body_enabled(env: Optional[Mapping[str, str]] = None) -> bool:
    """True when users explicitly opt back into PR body decoration."""
    return (env or os.environ).get(FORCE_PR_BODY_ENV) == "1"


def repo_from_remote_url(url: str) -> Optional[tuple[str, str]]:
    """Parse GitHub owner/repo from common git remote URL forms."""
    cleaned = url.strip()
    if not cleaned:
        return None
    if cleaned.startswith("git@github.com:"):
        return _owner_repo_from_path(cleaned.removeprefix("git@github.com:"))

    parsed = urlparse(cleaned)
    # `hostname` strips any `user@` / `:port` so `ssh://git@github.com/o/r`
    # resolves to `github.com`; `netloc` would keep the `git@` userinfo and
    # never match.
    if parsed.hostname != "github.com":
        return None
    return _owner_repo_from_path(parsed.path.lstrip("/"))


def current_repo(
    *,
    cwd: Optional[Path] = None,
    runner: Runner = subprocess.run,
) -> Optional[tuple[str, str]]:
    """Resolve owner/repo from the current git remote without network."""
    try:
        proc = runner(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(cwd) if cwd is not None else None,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return repo_from_remote_url(proc.stdout)


def policy_state(data: Mapping[str, Any]) -> PolicyState:
    """Classify a GitHub repo API response / cache payload.

    A merge method only leaks the PR body if that method copies the body
    into the commit message AND the method is actually enabled. Absent
    ``allow_*`` flags (pre-existing cache entries written before this
    field was tracked) default to True so classification stays
    conservative rather than silently downgrading to SAFE.
    """
    if data.get("squash_merge_commit_message") == PR_BODY and data.get("allow_squash_merge", True):
        return POLICY_LEAKS
    if data.get("merge_commit_message") == PR_BODY and data.get("allow_merge_commit", True):
        return POLICY_LEAKS
    return POLICY_SAFE


def repo_policy_state(
    *,
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    now: Optional[datetime] = None,
    runner: Runner = subprocess.run,
) -> PolicyState:
    """Return safe / leaks / unknown, reading fresh cache before gh API."""
    resolved = _resolved_repo(owner=owner, repo=repo, cwd=cwd, runner=runner)
    if resolved is None:
        return POLICY_UNKNOWN
    owner, repo = resolved

    cached = _read_fresh_cache(_cache_path(owner, repo, env=env), now=now)
    if cached is not None:
        return policy_state(cached)

    fetched = _fetch_repo_policy(owner, repo, runner=runner)
    if fetched is None:
        return POLICY_UNKNOWN
    _write_cache(_cache_path(owner, repo, env=env), fetched)
    return policy_state(fetched)


def should_skip_pr_body(
    *,
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    runner: Runner = subprocess.run,
) -> bool:
    """True when PR body decoration should be skipped by default."""
    if force_pr_body_enabled(env):
        return False
    return repo_policy_state(owner=owner, repo=repo, cwd=cwd, env=env, runner=runner) in {
        POLICY_LEAKS,
        POLICY_UNKNOWN,
    }


def _owner_repo_from_path(path: str) -> Optional[tuple[str, str]]:
    stripped = path.strip().removesuffix(".git")
    parts = [part for part in stripped.split("/") if part]
    if len(parts) < 2:
        return None
    return parts[-2], parts[-1]


def _resolved_repo(
    *,
    owner: Optional[str],
    repo: Optional[str],
    cwd: Optional[Path],
    runner: Runner,
) -> Optional[tuple[str, str]]:
    if owner and repo:
        return owner, repo
    return current_repo(cwd=cwd, runner=runner)


def _cache_path(
    owner: str,
    repo: str,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> Path:
    values = env or os.environ
    base = Path(values.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "mojiemoji" / "repo-policy" / f"{owner}--{repo}.json"


def _read_fresh_cache(path: Path, *, now: Optional[datetime] = None) -> Optional[dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None

    fetched_at = _parsed_datetime(data.get("fetched_at"))
    if fetched_at is None:
        return None
    current = now or datetime.now(timezone.utc)
    if (current - fetched_at).total_seconds() > TTL_SECONDS:
        return None
    if not _has_policy_fields(data):
        return None
    return data


def _fetch_repo_policy(
    owner: str,
    repo: str,
    *,
    runner: Runner = subprocess.run,
) -> Optional[dict[str, Any]]:
    try:
        proc = runner(
            ["gh", "api", f"repos/{owner}/{repo}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not _has_policy_fields(data):
        return None
    return {
        "squash_merge_commit_message": data["squash_merge_commit_message"],
        "merge_commit_message": data["merge_commit_message"],
        "allow_squash_merge": data.get("allow_squash_merge", True),
        "allow_merge_commit": data.get("allow_merge_commit", True),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _write_cache(path: Path, data: Mapping[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError:
        return


def _has_policy_fields(data: Mapping[str, Any]) -> bool:
    return isinstance(data.get("squash_merge_commit_message"), str) and isinstance(
        data.get("merge_commit_message"), str
    )


def _parsed_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


__all__ = [
    "FORCE_PR_BODY_ENV",
    "POLICY_LEAKS",
    "POLICY_SAFE",
    "POLICY_UNKNOWN",
    "force_pr_body_enabled",
    "policy_state",
    "repo_from_remote_url",
    "repo_policy_state",
    "should_skip_pr_body",
]
