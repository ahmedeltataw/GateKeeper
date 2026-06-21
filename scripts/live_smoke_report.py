#!/usr/bin/env python3
"""One-shot live health check for the activated catalog.

Boots the minimum subsystems (registry, key vault, circuit breaker), loads the
provider keys from ``.env``, runs the real boot probe (``probe.probe_all_models``
-> ``smoke.smoke_test_model`` per model), and prints a pass/fail table plus the
quarantine state. This is the same code path the gateway runs at startup when
``probe.enabled`` is true, just driven standalone so we can read the results.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


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


async def main() -> int:
    _load_env()

    from src.core import circuit, key_manager
    from src.core.config_loader import get_config
    from src.core.registry import get_registry
    from src.core.smoke import smoke_test_model

    registry = await get_registry()
    await key_manager.init()
    await circuit.init()

    keyed = await key_manager.list_providers_with_keys()
    active = registry.get_active()
    print(f"providers with keys : {len(keyed)} -> {', '.join(sorted(keyed))}")
    print(f"active models       : {len(active)}")
    print("-" * 78)

    cfg = get_config().probe
    sem = asyncio.Semaphore(4)

    async def one(m):
        async with sem:
            res = await smoke_test_model(
                m, prompt=cfg.prompt, max_tokens=cfg.max_tokens, timeout=cfg.timeout_seconds
            )
        # Feed the breaker exactly like probe.py does, so quarantine state is real.
        if res["ok"]:
            await circuit.record_success(m.id)
        else:
            await circuit.record_failure(m.id, res.get("code", "5xx"), res.get("detail", ""))
        return m, res

    results = await asyncio.gather(*(one(m) for m in active))

    rows = []
    for m, res in results:
        ok = res["ok"]
        detail = "" if ok else f"{res.get('code', '?')}: {res.get('detail', '')}"
        lat = res.get("latency_ms", "")
        rows.append((ok, m.id, m.provider_id, lat, detail))

    rows.sort(key=lambda r: (not r[0], r[2], r[1]))
    print(f"{'RESULT':<6} {'MODEL':<28} {'PROVIDER':<14} {'ms':<7} DETAIL")
    for ok, mid, prov, lat, detail in rows:
        mark = "PASS" if ok else "FAIL"
        print(f"{mark:<6} {mid:<28} {prov:<14} {str(lat):<7} {detail[:34]}")

    healthy = sum(1 for ok, *_ in rows if ok)
    blacklisted = sum(
        1 for b in circuit.snapshot().values() if b.get("state") == circuit.STATE_BLACKLISTED
    )
    print("-" * 78)
    print(
        f"SUMMARY: probed={len(rows)} healthy={healthy} "
        f"failed={len(rows) - healthy} blacklisted={blacklisted}"
    )
    by_prov: dict[str, list[int]] = {}
    for ok, _mid, prov, *_ in rows:
        s = by_prov.setdefault(prov, [0, 0])
        s[0] += int(ok)
        s[1] += 1
    print("BY PROVIDER:")
    for prov in sorted(by_prov):
        p, t = by_prov[prov]
        print(f"  {prov:<14} {p}/{t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
