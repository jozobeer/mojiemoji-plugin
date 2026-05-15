from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_COVERAGE = (
    REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "coverage.py"
).resolve()


def _shadows_coverage_package(path: str) -> bool:
    try:
        return (Path(path or ".").resolve() / "coverage.py") == LOCAL_COVERAGE
    except OSError:
        return False


original_path = sys.path[:]
sys.path[:] = [path for path in original_path if not _shadows_coverage_package(path)]

try:
    spec = importlib.util.find_spec("coverage")
    if spec is not None and spec.submodule_search_locations is not None:
        importlib.import_module("coverage").process_startup()
finally:
    sys.path[:] = original_path
