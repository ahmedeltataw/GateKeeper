"""In-memory model registry loaded from ``models_registry.json``."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from src.core.models_schema import build_overlay
from src.core.types import ModelInfo

logger = logging.getLogger("gateway.registry")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_REGISTRY_PATH = _PROJECT_ROOT / "models_registry.json"

# The authoritative catalog (IMPLEMENTATION_PLAN.md §13) uses dots in ids such
# as "gemini-3.5-flash", so the pattern must allow them.
_ID_PATTERN = re.compile(r"^[a-z0-9.-]+$")


class Registry:
    """Stores and queries the gateway's model catalog."""

    def __init__(self, registry_path: Path | None = None) -> None:
        self._path = registry_path or _REGISTRY_PATH
        self._models: dict[str, ModelInfo] = {}

    async def load(self) -> None:
        """Load models from the JSON registry file."""
        if not self._path.exists():
            raise FileNotFoundError(f"Model registry not found: {self._path}")

        with self._path.open("r", encoding="utf-8") as handle:
            raw_models: list[dict[str, Any]] = json.load(handle)

        # Base data comes from models_registry.json; models_schema.json overlays
        # metadata (display name, category, fallback order, any explicit field)
        # on top. The schema is the single place to tweak a model without
        # editing the full registry record.
        base: dict[str, dict[str, Any]] = {}
        for raw in raw_models:
            model_id = raw.get("id")
            if model_id in base:
                raise ValueError(f"Duplicate model id: {model_id}")
            base[model_id] = raw

        overlay = build_overlay()
        for model_id, fields in overlay.items():
            if model_id in base:
                base[model_id].update(fields)
            else:
                # Schema-only model: only usable if it carries every required
                # ModelInfo field. Skip (don't crash startup) if it doesn't.
                base[model_id] = {"id": model_id, **fields}

        self._models = {}
        for model_id, raw in base.items():
            try:
                model = ModelInfo.model_validate(raw)
            except Exception as exc:
                if model_id in {m.get("id") for m in raw_models}:
                    raise  # a base/overlay combo must always be valid
                logger.warning("skipping invalid schema-only model %s: %s", model_id, exc)
                continue
            if not _ID_PATTERN.match(model.id):
                raise ValueError(f"Invalid model id: {model.id}")
            self._models[model.id] = model

    def get(self, model_id: str) -> ModelInfo | None:
        return self._models.get(model_id)

    def get_active(self) -> list[ModelInfo]:
        return [m for m in self._models.values() if m.enabled and m.status == "active"]

    def get_by_strength(self, strength: str) -> list[ModelInfo]:
        return [
            m
            for m in self.get_active()
            if m.strength == strength
        ]

    def get_by_use_case(self, use_case: str) -> list[ModelInfo]:
        return [
            m
            for m in self.get_active()
            if use_case in m.use_cases
        ]

    def get_best_for_task(self, use_case: str) -> list[ModelInfo]:
        """Return active models for a use case sorted by strength (S first)."""
        return sorted(
            self.get_by_use_case(use_case),
            key=lambda m: (m.strength_order, m.id),
        )

    def get_by_provider(self, provider_id: str) -> list[ModelInfo]:
        return [m for m in self._models.values() if m.provider_id == provider_id]

    def get_providers_for_model(self, model_id: str) -> list[str]:
        """Return provider_ids that offer a model with the given gateway id."""
        model = self.get(model_id)
        if model is None:
            return []
        return [
            m.provider_id
            for m in self._models.values()
            if m.provider_model_id == model.provider_model_id
        ]

    def get_models_sharing(self, model_id: str) -> list[ModelInfo]:
        """Return active models that share the same ``provider_model_id``.

        The requested model comes first, followed by siblings on *other*
        providers. Each sibling keeps its own gateway id, so callers can invoke
        the right provider with an id it actually recognises.
        """
        model = self.get(model_id)
        if model is None:
            return []
        siblings = [
            m
            for m in self._models.values()
            if m.provider_model_id == model.provider_model_id
            and m.id != model.id
            and m.enabled
            and m.status == "active"
        ]
        return [model, *siblings]

    def mark_removed(self, model_id: str) -> None:
        """Mark a single model as removed (model-scoped, e.g. after a 404)."""
        model = self._models.get(model_id)
        if model is not None:
            model.status = "removed"

    def set_enabled(self, model_id: str, enabled: bool) -> bool:
        """Toggle a model's ``enabled`` flag at runtime (admin control).

        Returns True if the model exists. The change is in-memory only — it does
        not rewrite ``models_registry.json`` — so a restart restores the
        catalog's declared state. A disabled model drops out of ``get_active``
        and therefore out of routing and ``/v1/models``.
        """
        model = self._models.get(model_id)
        if model is None:
            return False
        model.enabled = enabled
        return True

    def search(self, term: str) -> list[ModelInfo]:
        term_lower = term.lower()
        return [
            m
            for m in self._models.values()
            if term_lower in m.id.lower()
            or term_lower in m.display_name.lower()
            or term_lower in m.provider_id.lower()
        ]

    def all_models(self) -> list[ModelInfo]:
        return list(self._models.values())


# Module-level singleton for application use.
_registry: Registry | None = None


async def get_registry() -> Registry:
    """Return the loaded module-level registry singleton."""
    global _registry
    if _registry is None:
        _registry = Registry()
        await _registry.load()
    return _registry


def reset_registry() -> None:
    """Clear the module-level registry singleton (useful in tests)."""
    global _registry
    _registry = None


def get_registry_sync() -> Registry:
    """Return the already-loaded registry; raise if not loaded yet."""
    if _registry is None:
        raise RuntimeError("Registry has not been loaded. Call load() first.")
    return _registry
