"""mojiemoji Japanese-gate hook decomposition (#101).

Submodules:
  - `patterns` — hook-specific regex / constant definitions
  - `extract`  — Bash / MCP routing + body / script extraction
  - `validators` — per-stage validators (URL presence, required params,
                   outline, canonical values, catalog leftovers, schema
                   version drift)

The hook entry point (`hooks/mojiemoji_japanese_gate.py`) glues these
together via `VALIDATION_PIPELINE` and the standalone-validator
callables exported here.

Package name is `gate`, not `lib`, to avoid shadowing the shared
`skills/mojiemoji-github/scripts/lib/` package that we splice onto
sys.path for `lib.constants`, `lib.term_boundaries`, etc. — the two
names had collided under a single-import-name regime.
"""
