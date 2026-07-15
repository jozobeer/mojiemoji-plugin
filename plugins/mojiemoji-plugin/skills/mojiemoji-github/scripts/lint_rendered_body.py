#!/usr/bin/env python3
"""Lint rendered mojiemoji URLs in a markdown body."""

from __future__ import annotations

import argparse
import bisect
import html
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

MOJI_URL_RE = re.compile(r"https?://mojiemoji\.jozo\.beer/[^\s\"<>)]+")
HEX6_RE = re.compile(r"\A#?[0-9a-fA-F]{6}\Z")
StatusChecker = Callable[[str], int]


@dataclass(frozen=True)
class Finding:
    source: str
    line: int
    url: str
    message: str


def line_offsets(text: str) -> list[int]:
    return [match.start() for match in re.finditer("\n", text)]


def line_for_offset(offsets: Sequence[int], position: int) -> int:
    return bisect.bisect_left(offsets, position) + 1


def iter_mojiemoji_urls(
    text: str,
    offsets: Sequence[int] | None = None,
) -> Iterable[tuple[int, str]]:
    line_starts = offsets if offsets is not None else line_offsets(text)
    for match in MOJI_URL_RE.finditer(text):
        line = line_for_offset(line_starts, match.start())
        yield line, html.unescape(match.group(0))


def color_finding(source: str, line: int, url: str) -> Finding | None:
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query, keep_blank_values=True)
    color_values = query.get("color", [])
    if not color_values:
        return None

    color = color_values[-1]
    if HEX6_RE.match(color):
        return None

    return Finding(
        source=source,
        line=line,
        url=url,
        message=f"color must be 6-digit hex, got {color!r}",
    )


def head_status(url: str, timeout: float) -> int:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "mojiemoji-plugin-lint/1.0"},
        method="HEAD",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def lint_urls(
    urls: Iterable[tuple[int, str]],
    *,
    source: str = "<stdin>",
    timeout: float = 5.0,
    status_for_url: StatusChecker | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    status = status_for_url or (lambda url: head_status(url, timeout))

    for line, url in urls:
        local_finding = color_finding(source, line, url)
        if local_finding is not None:
            findings.append(local_finding)
            continue

        try:
            code = status(url)
        except RuntimeError as exc:
            findings.append(
                Finding(source=source, line=line, url=url, message=f"request failed: {exc}")
            )
            continue

        if code != 200:
            findings.append(
                Finding(source=source, line=line, url=url, message=f"HTTP {code}")
            )

    return findings


def lint_text(
    text: str,
    *,
    source: str = "<stdin>",
    timeout: float = 5.0,
    status_for_url: StatusChecker | None = None,
) -> list[Finding]:
    return lint_urls(
        iter_mojiemoji_urls(text),
        source=source,
        timeout=timeout,
        status_for_url=status_for_url,
    )


def documents(paths: Sequence[str]) -> Iterable[tuple[str, str]]:
    if not paths:
        yield "<stdin>", sys.stdin.read()
        return

    stdin_used = False
    for raw_path in paths:
        if raw_path == "-":
            if stdin_used:
                raise SystemExit("error: stdin marker '-' can only be used once")
            stdin_used = True
            yield "<stdin>", sys.stdin.read()
            continue

        path = Path(raw_path)
        try:
            yield str(path), path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise SystemExit(f"error: cannot read {path}: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lint rendered mojiemoji URLs in markdown bodies.",
        usage="lint_rendered_body.py [--timeout SECONDS] [body.md ...]",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Markdown body files to lint. Reads stdin when omitted or when '-' is used.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="HTTP HEAD timeout in seconds (default: 5)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    opts = build_parser().parse_args(argv)
    all_findings: list[Finding] = []
    url_count = 0

    for source, text in documents(opts.paths):
        urls = list(iter_mojiemoji_urls(text, line_offsets(text)))
        url_count += len(urls)
        all_findings.extend(lint_urls(urls, source=source, timeout=opts.timeout))

    if all_findings:
        for finding in all_findings:
            print(
                f"mojiemoji lint: {finding.source}:{finding.line}: {finding.message}\n"
                f"  {finding.url}",
                file=sys.stderr,
            )
        return 2

    print(f"[ok] {url_count} mojiemoji URL(s) linted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
