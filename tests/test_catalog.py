"""Tests for the generated models.json catalog."""

from __future__ import annotations

import pytest

from src.core import catalog
from src.core.registry import get_registry


@pytest.mark.asyncio
async def test_catalog_models_is_object_keyed_by_id(loaded_registry):
    """models must be an object keyed by id (OpenCode shape), not an array."""
    await get_registry()  # populate the module singleton catalog reads from
    document = catalog.build_catalog()

    assert isinstance(document["models"], dict)
    sample_id = next(iter(document["models"]))
    assert document["models"][sample_id]["id"] == sample_id
    assert document["total"] == len(document["models"])
    assert document["usable"] <= document["total"]
