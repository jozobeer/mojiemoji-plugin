# mojiemoji

Turn Japanese Markdown into [mojiemoji](https://mojiemoji.jozo.beer) image
stamps — deterministic, idempotent, and safe-zone aware.

```bash
uvx mojiemoji < body.md > decorated.md
```

Catalog terms become inline `<img>` stamps; everything else passes through
untouched. Code fences, inline code, link targets, and shields.io badge rows
are left alone, and running it twice changes nothing the first run already
stamped.

## Library

```python
from mojiemoji import transform, report_unstamped

stamped = transform(markdown_text)
gaps = report_unstamped(stamped)
```

`transform` is a pure function: it reads the bundled catalogs, renders stamp
URLs, and returns the result. It performs no network calls, reads no
repository settings, and touches no cache — deciding *when* to decorate is the
caller's job.

## Configuration

| Knob | Effect |
|---|---|
| `--base-url` / `MOJIEMOJI_BASE_URL` | Render against another instance. Argument wins over the variable, which wins over the hosted default. |
| `--intensity` | `aggressive` (default), `normal`, or `minimal` substitution density. |
| `--catalog` / `--emoji-catalog` | Use catalogs from disk instead of the bundled ones. |
| `--report-unstamped` | Emit a JSON report of Japanese runs the catalog missed, instead of the markdown. |

## Related

The [mojiemoji-plugin](https://github.com/jozobeer/mojiemoji-plugin)
repository wraps this package for AI coding harnesses, adding the GitHub
posting policy, the catalog-growth pipeline, and per-harness skills.
