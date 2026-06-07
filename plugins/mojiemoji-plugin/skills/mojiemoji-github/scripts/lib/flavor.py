"""Flavor: a single mojiemoji rendering variant.

Used by `bump_catalog.py`, `cache_stats.py`, and `generate_catalog.py`
to serialise catalog variants into YAML. Previously each script had
its own `render_variant*` function with subtly different signatures
and key orderings — adding a new field (e.g. `flip`) required three
synchronous edits.

A `Flavor` is a thin wrapper around the dict literal selectors record;
keep dict access via `Flavor.fields` for callers that still need
raw mutation. Use `Flavor.from_dict(...).to_yaml_lines(indent="    ")`
to render to YAML.
"""

from __future__ import annotations

from dataclasses import dataclass

from lib.yaml_helpers import yaml_value


# Canonical YAML key order. Adding a new field: append here so all
# renderers pick it up automatically.
_FIELD_ORDER: tuple[str, ...] = (
    "font",
    "color",
    "outline",
    "outline_width",
    "animation",
    "speed",
)


@dataclass(frozen=True)
class Flavor:
    fields: dict

    @classmethod
    def from_dict(cls, raw: dict) -> "Flavor":
        return cls(fields=dict(raw))

    def to_yaml_lines(self, indent: str = "    ") -> list[str]:
        """Render to a YAML list item.

        The first field (`font`) gets the `- ` prefix; subsequent
        fields are indented to the same column. Optional fields
        (`outline`, `outline_width`, `speed`) are omitted when the
        flavor dict has no value for them.
        """
        if "font" not in self.fields:
            raise ValueError("Flavor.to_yaml_lines requires a `font` field")
        lines = [f"{indent}- font: {self.fields['font']}"]
        for key in _FIELD_ORDER:
            if key == "font":
                continue
            value = self.fields.get(key)
            if value is None or value == "":
                continue
            lines.append(f"{indent}  {key}: {yaml_value(value)}")
        return lines
