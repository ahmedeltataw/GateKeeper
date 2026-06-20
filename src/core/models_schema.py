"""Loader for ``models_schema.json`` — the central, hand-edited model catalog.

The schema is the ONE place you add a model. Instead of repeating provider,
limits, and metadata in every file, you write a short entry under ``models`` and
optionally lean on a ``category`` (for the provider) and shared ``defaults``.

``build_opencode_models()`` reads the schema and produces the object OpenCode
expects: a dict keyed by model id, each value carrying at least ``name``. The
category's ``provider_id`` and the top-level ``defaults`` are merged in so the
per-model entries stay tiny.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _PROJECT_ROOT / "models_schema.json"


def load_schema(path: Path | None = None) -> dict[str, Any]:
    """Read and return the raw schema document."""
    schema_path = path or _SCHEMA_PATH
    if not schema_path.exists():
        raise FileNotFoundError(f"Model schema not found: {schema_path}")
    with schema_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_entry(
    model_id: str,
    raw: dict[str, Any],
    categories: dict[str, Any],
    defaults: dict[str, Any],
) -> dict[str, Any]:
    """Merge defaults + category + per-model fields into one flat entry."""
    category_key = raw.get("category")
    category = categories.get(category_key, {}) if category_key else {}

    # Precedence: explicit per-model field > category > defaults.
    entry: dict[str, Any] = {**defaults}
    if "provider_id" in category:
        entry["provider"] = category["provider_id"]
    entry.update(raw)

    entry["id"] = model_id
    entry.setdefault("name", model_id)
    entry.setdefault("category", category_key or "general")
    entry.setdefault("fallback_order", [])
    return entry


def build_opencode_models(path: Path | None = None) -> dict[str, Any]:
    """Return ``{"models": {id: entry, ...}}`` in the shape OpenCode expects.

    ``models`` is an OBJECT keyed by id (not a list); an array there trips
    OpenCode's "Failed to load sessions" parser.
    """
    schema = load_schema(path)
    categories = schema.get("categories", {})
    defaults = schema.get("defaults", {})

    models = {
        model_id: _resolve_entry(model_id, raw, categories, defaults)
        for model_id, raw in schema.get("models", {}).items()
    }
    return {"models": models}


# Schema key -> ModelInfo field. Keys not listed here pass through unchanged
# when they are valid ModelInfo fields (see _OVERLAY_PASSTHROUGH).
_OVERLAY_RENAMES: dict[str, str] = {
    "name": "display_name",
    "fallback_order": "fallback_models",
}

# Explicit schema fields allowed to override a base registry entry.
_OVERLAY_PASSTHROUGH: frozenset[str] = frozenset(
    {
        "display_name",
        "provider_id",
        "provider_model_id",
        "strength",
        "strength_order",
        "use_cases",
        "category",
        "tier",
        "context_window",
        "max_output_tokens",
        "modalities",
        "pricing",
        "rate_limits",
        "enabled",
        "status",
        "fallback_models",
        "notes",
        "source_url",
        "added_at",
        "last_verified",
        "verification_source",
    }
)


def build_overlay(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return per-model OVERRIDES to layer on top of the base registry.

    Unlike :func:`build_opencode_models`, this does NOT bake in ``defaults`` —
    only fields a model explicitly declares are returned, so overlaying never
    clobbers a base entry's real values with schema defaults. Keys are renamed
    to ModelInfo fields (``name`` -> ``display_name`` etc.); a model's
    ``category`` also injects that category's ``provider_id``.
    """
    schema = load_schema(path)
    categories = schema.get("categories", {})

    overlay: dict[str, dict[str, Any]] = {}
    for model_id, raw in schema.get("models", {}).items():
        fields: dict[str, Any] = {}

        category_key = raw.get("category")
        category = categories.get(category_key, {}) if category_key else {}
        if "provider_id" in category:
            fields["provider_id"] = category["provider_id"]

        for key, value in raw.items():
            field = _OVERLAY_RENAMES.get(key, key)
            if field in _OVERLAY_PASSTHROUGH:
                fields[field] = value

        overlay[model_id] = fields
    return overlay


def models_by_category(path: Path | None = None) -> dict[str, list[str]]:
    """Group model ids by their category — handy for menus/diagnostics."""
    grouped: dict[str, list[str]] = {}
    for model_id, entry in build_opencode_models(path)["models"].items():
        grouped.setdefault(entry["category"], []).append(model_id)
    return grouped


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    print(json.dumps(build_opencode_models(), indent=2, ensure_ascii=False))
