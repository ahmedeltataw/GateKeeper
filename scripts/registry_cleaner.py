#!/usr/bin/env python3
"""Registry cleaner — quarantine models that no longer exist upstream.

Runs the same live smoke probe as ``live_smoke_report.py`` (registry + key vault
+ circuit breaker, real ``smoke.smoke_test_model`` per active model), collects
every model that came back with a ``404`` (Model Not Found), and then edits
``models_registry.json`` to take those dead models out of rotation.

Two modes:

* ``--disable`` (default) — set ``"enabled": false`` on each 404 model. Reversible:
  the record stays, so you can flip it back on if the provider restores the model.
* ``--delete`` — remove the model record from the file entirely.

Safety:

* Nothing is written until you confirm (type ``yes``). ``--yes`` skips the prompt
  for automation; ``--dry-run`` reports what *would* change and writes nothing.
* A timestamped backup of ``models_registry.json`` is written next to it before
  any edit, so a bad run is always recoverable.

Usage::

    python scripts/registry_cleaner.py              # probe, confirm, disable 404s
    python scripts/registry_cleaner.py --delete     # remove 404 records instead
    python scripts/registry_cleaner.py --dry-run     # show 404s, change nothing
    python scripts/registry_cleaner.py --yes         # no interactive confirmation
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

_REGISTRY_PATH = _ROOT / "models_registry.json"


def _load_env() -> None:
    env = _ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


async def _probe_for_404s() -> list[tuple[str, str, str]]:
    """Run the live smoke probe and return ``(model_id, provider_id, detail)``
    for every active model that failed with a ``404``."""
    from src.core import circuit, key_manager
    from src.core.config_loader import get_config
    from src.core.registry import get_registry
    from src.core.smoke import smoke_test_model

    registry = await get_registry()
    await key_manager.init()
    await circuit.init()

    active = registry.get_active()
    cfg = get_config().probe
    sem = asyncio.Semaphore(max(1, cfg.concurrency))

    print(f"active models       : {len(active)}")
    print(f"probe concurrency   : {cfg.concurrency}   timeout: {cfg.timeout_seconds}s")
    print("-" * 78)

    async def one(m):
        async with sem:
            res = await smoke_test_model(
                m, prompt=cfg.prompt, max_tokens=cfg.max_tokens, timeout=cfg.timeout_seconds
            )
        return m, res

    results = await asyncio.gather(*(one(m) for m in active))

    dead: list[tuple[str, str, str]] = []
    healthy = 0
    for m, res in results:
        if res["ok"]:
            healthy += 1
        elif res.get("code") == "404":
            dead.append((m.id, m.provider_id, res.get("detail", "")))

    failed = len(results) - healthy
    print(f"SUMMARY: probed={len(results)} healthy={healthy} failed={failed} "
          f"not_found(404)={len(dead)}")
    print("-" * 78)
    return dead


def _backup_registry() -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    backup = _REGISTRY_PATH.with_suffix(f".json.bak-{stamp}")
    shutil.copy2(_REGISTRY_PATH, backup)
    return backup


def _apply(dead_ids: set[str], *, delete: bool) -> int:
    """Edit ``models_registry.json`` in place. Returns the number of records
    changed. Assumes a backup has already been taken."""
    with _REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        models: list[dict] = json.load(handle)

    changed = 0
    if delete:
        kept = [m for m in models if m.get("id") not in dead_ids]
        changed = len(models) - len(kept)
        models = kept
    else:
        for m in models:
            if m.get("id") in dead_ids and m.get("enabled", True) is not False:
                m["enabled"] = False
                changed += 1

    with _REGISTRY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(models, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return changed


def _confirm(action: str, count: int) -> bool:
    answer = input(f"\n{action} {count} model(s) in models_registry.json? type 'yes' to proceed: ")
    return answer.strip().lower() == "yes"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Quarantine 404 models from the registry.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--disable", action="store_true",
                      help="set enabled:false on 404 models (default)")
    mode.add_argument("--delete", action="store_true",
                      help="remove 404 model records entirely")
    parser.add_argument("--dry-run", action="store_true",
                        help="report 404 models but change nothing")
    parser.add_argument("--yes", action="store_true",
                        help="skip the interactive confirmation prompt")
    args = parser.parse_args()
    delete = args.delete  # disable is the default when neither flag is given

    _load_env()
    dead = await _probe_for_404s()

    if not dead:
        print("No 404 (Model Not Found) models. Registry already clean.")
        return 0

    action = "DELETE" if delete else "DISABLE"
    print(f"{len(dead)} model(s) returned 404 -> will {action}:")
    for mid, prov, detail in dead:
        print(f"  - {mid:<28} {prov:<14} {detail[:40]}")

    if args.dry_run:
        print("\n--dry-run: no changes written.")
        return 0

    if not args.yes and not _confirm(action, len(dead)):
        print("Aborted. No changes written.")
        return 1

    backup = _backup_registry()
    changed = _apply({mid for mid, _, _ in dead}, delete=delete)
    print(f"\nBackup written : {backup.name}")
    print(f"{action.title()}d {changed} model(s) in {_REGISTRY_PATH.name}.")
    print("Restart the gateway (or rerun live_smoke_report.py) to pick up the cleaned catalog.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
