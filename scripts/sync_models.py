"""Sync the model catalog → ``models_registry.json``.

This script materialises the authoritative free-model catalog into a validated
JSON registry that the gateway loads at startup.

All models below were **doc-verified June 2026** against each provider's current
documentation as genuinely FREE and **requiring no payment card**. They are NOT
live-call verified — open-weight menus rotate often, so run a startup health
check and prune anything that 401s/404s. See ``docs/STATUS_AND_SETUP.md``.

Provider order is preserved from ``models-classification.md``.
Aion (no permanently-free model) and Cohere (non-commercial, not
OpenAI-compatible) are intentionally excluded from the active catalog.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path so ``src`` is importable when running as a script.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from src.core.types import ModelInfo

_OUTPUT_PATH = _PROJECT_ROOT / "models_registry.json"


def _model(
    *,
    id: str,
    display_name: str,
    provider_id: str,
    provider_model_id: str,
    strength: str,
    use_cases: list[str],
    context_window: int,
    max_output_tokens: int,
    rate_limits: dict[str, Any],
    category: str = "general",
    modalities: list[str] | None = None,
    notes: str | None = None,
    fallback_models: list[str] | None = None,
    added_at: str = "2026-06-17",
    last_verified: str = "2026-06-17",
) -> dict[str, Any]:
    """Build a normalised model record matching ``ModelInfo``."""
    return {
        "id": id,
        "display_name": display_name,
        "provider_id": provider_id,
        "provider_model_id": provider_model_id,
        "strength": strength,
        "use_cases": use_cases,
        "category": category,
        "context_window": context_window,
        "max_output_tokens": max_output_tokens,
        "modalities": modalities or ["text"],
        "pricing": {"input": 0, "output": 0},
        "rate_limits": rate_limits,
        "enabled": True,
        "status": "active",
        "fallback_models": fallback_models or [],
        "notes": notes,
        "added_at": added_at,
        "last_verified": last_verified,
        "verification_source": "doc_verified",
    }


_MODELS: list[dict[str, Any]] = [
    # ---------------------------------------------------------------------
    # Provider 1 — OpenRouter (Bearer; :free models; no card)
    # base: https://openrouter.ai/api/v1  | OpenAI-compatible
    # ---------------------------------------------------------------------
    _model(
        id="or-gpt-oss-120b",
        display_name="GPT-OSS 120B (OpenRouter)",
        provider_id="openrouter",
        provider_model_id="openai/gpt-oss-120b:free",
        strength="A",
        use_cases=["coding", "search", "reasoning"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"rpm": 20, "rpd": 50},
        notes="50 RPD until you've ever bought >=10 credits, then 1000 RPD.",
    ),
    _model(
        id="or-qwen3-coder",
        display_name="Qwen3 Coder (OpenRouter)",
        provider_id="openrouter",
        provider_model_id="qwen/qwen3-coder:free",
        strength="A",
        use_cases=["coding"],
        context_window=256_000,
        max_output_tokens=8192,
        rate_limits={"rpm": 20, "rpd": 50},
        category="coding",
    ),
    _model(
        id="or-llama-3.3-70b",
        display_name="Llama 3.3 70B (OpenRouter)",
        provider_id="openrouter",
        provider_model_id="meta-llama/llama-3.3-70b-instruct:free",
        strength="A",
        use_cases=["search", "coding", "creative", "reasoning"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"rpm": 20, "rpd": 50},
    ),
    _model(
        id="or-glm-4.5-air",
        display_name="GLM 4.5 Air (OpenRouter)",
        provider_id="openrouter",
        provider_model_id="z-ai/glm-4.5-air:free",
        strength="A",
        use_cases=["reasoning", "coding"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"rpm": 20, "rpd": 50},
    ),
    _model(
        id="or-gemma-4-31b",
        display_name="Gemma 4 31B (OpenRouter)",
        provider_id="openrouter",
        provider_model_id="google/gemma-4-31b-it:free",
        strength="B",
        use_cases=["creative", "search"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"rpm": 20, "rpd": 50},
    ),
    _model(
        id="or-auto",
        display_name="OpenRouter Auto (free)",
        provider_id="openrouter",
        provider_model_id="openrouter/free",
        strength="B",
        use_cases=["default", "coding", "search"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"rpm": 20, "rpd": 50},
        notes="Auto-router that picks any available free model.",
    ),
    # ---------------------------------------------------------------------
    # Provider 2 — Google Gemini / AI Studio (query-param or Bearer; no card)
    # base: .../v1beta  | translated  | FREE TIER TRAINS ON YOUR DATA
    # ---------------------------------------------------------------------
    _model(
        id="gemini-2.5-pro",
        display_name="Gemini 2.5 Pro",
        provider_id="gemini",
        provider_model_id="gemini-2.5-pro",
        strength="S",
        use_cases=["coding", "search", "reasoning", "creative", "data", "vision"],
        context_window=1_000_000,
        max_output_tokens=65_000,
        rate_limits={"rpm": 5, "rpd": 100},
        modalities=["text", "image"],
        notes="Free tier may use prompts for training. Limits cut ~Dec 2025; verify live.",
    ),
    _model(
        id="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        provider_id="gemini",
        provider_model_id="gemini-2.5-flash",
        strength="A",
        use_cases=["coding", "search", "creative", "data", "vision"],
        context_window=1_000_000,
        max_output_tokens=65_000,
        rate_limits={"rpm": 10, "rpd": 250},
        modalities=["text", "image"],
        notes="Best all-round free default. Free tier may train on data.",
    ),
    _model(
        id="gemini-2.5-flash-lite",
        display_name="Gemini 2.5 Flash-Lite",
        provider_id="gemini",
        provider_model_id="gemini-2.5-flash-lite",
        strength="B",
        use_cases=["coding", "search", "vision"],
        context_window=1_000_000,
        max_output_tokens=65_000,
        rate_limits={"rpm": 15, "rpd": 1000},
        modalities=["text", "image"],
    ),
    _model(
        id="gemini-2.0-flash",
        display_name="Gemini 2.0 Flash",
        provider_id="gemini",
        provider_model_id="gemini-2.0-flash",
        strength="B",
        use_cases=["search", "coding", "vision"],
        context_window=1_000_000,
        max_output_tokens=8192,
        rate_limits={"rpm": 15, "rpd": 1500},
        modalities=["text", "image"],
    ),
    # ---------------------------------------------------------------------
    # Provider 3 — Groq (Bearer; no card; fastest)
    # base: https://api.groq.com/openai/v1  | OpenAI-compatible
    # ---------------------------------------------------------------------
    _model(
        id="groq-gpt-oss-120b",
        display_name="GPT-OSS 120B (Groq)",
        provider_id="groq",
        provider_model_id="openai/gpt-oss-120b",
        strength="A",
        use_cases=["coding", "search", "reasoning"],
        context_window=128_000,
        max_output_tokens=32_000,
        rate_limits={"rpm": 30, "rpd": 1000, "tpm": 8000},
        notes="Best Groq pick. Fast.",
    ),
    _model(
        id="groq-gpt-oss-20b",
        display_name="GPT-OSS 20B (Groq)",
        provider_id="groq",
        provider_model_id="openai/gpt-oss-20b",
        strength="B",
        use_cases=["coding", "reasoning", "search"],
        context_window=128_000,
        max_output_tokens=32_000,
        rate_limits={"rpm": 30, "rpd": 1000, "tpm": 8000},
    ),
    _model(
        id="groq-llama-3.3-70b",
        display_name="Llama 3.3 70B (Groq)",
        provider_id="groq",
        provider_model_id="llama-3.3-70b-versatile",
        strength="A",
        use_cases=["coding", "search", "reasoning", "data"],
        context_window=128_000,
        max_output_tokens=32_000,
        rate_limits={"rpm": 30, "rpd": 1000, "tpm": 12_000},
    ),
    _model(
        id="groq-llama-3.1-8b",
        display_name="Llama 3.1 8B Instant (Groq)",
        provider_id="groq",
        provider_model_id="llama-3.1-8b-instant",
        strength="C",
        use_cases=["search", "coding"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"rpm": 30, "rpd": 14_400, "tpm": 6000},
    ),
    _model(
        id="groq-qwen3-32b",
        display_name="Qwen3 32B (Groq, preview)",
        provider_id="groq",
        provider_model_id="qwen/qwen3-32b",
        strength="A",
        use_cases=["reasoning", "coding", "search"],
        context_window=128_000,
        max_output_tokens=16_000,
        rate_limits={"rpm": 30, "rpd": 1000, "tpm": 6000},
        notes="Preview model; not for production.",
    ),
    _model(
        id="groq-llama-4-scout",
        display_name="Llama 4 Scout (Groq, preview)",
        provider_id="groq",
        provider_model_id="meta-llama/llama-4-scout-17b-16e-instruct",
        strength="B",
        use_cases=["search", "vision", "coding"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"rpm": 30, "rpd": 1000, "tpm": 6000},
        modalities=["text", "image"],
        notes="Preview; vision + long context.",
    ),
    # ---------------------------------------------------------------------
    # Provider 4 — Mistral AI (Bearer; no card but phone verify; trains on data)
    # base: https://api.mistral.ai/v1  | OpenAI-compatible (mostly)
    # ---------------------------------------------------------------------
    _model(
        id="mistral-large",
        display_name="Mistral Large",
        provider_id="mistral",
        provider_model_id="mistral-large-latest",
        strength="S",
        use_cases=["coding", "search", "reasoning", "data"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"rps": 1, "tpm": 500_000},
        notes="Free Experiment tier opts INTO training by default; opt out in console.",
    ),
    _model(
        id="mistral-medium",
        display_name="Mistral Medium",
        provider_id="mistral",
        provider_model_id="mistral-medium-latest",
        strength="A",
        use_cases=["coding", "search", "reasoning"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"rps": 1, "tpm": 500_000},
    ),
    _model(
        id="mistral-magistral",
        display_name="Magistral Medium",
        provider_id="mistral",
        provider_model_id="magistral-medium-latest",
        strength="A",
        use_cases=["reasoning", "coding"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"rps": 1, "tpm": 500_000},
        category="reasoning",
    ),
    _model(
        id="mistral-small",
        display_name="Mistral Small",
        provider_id="mistral",
        provider_model_id="mistral-small-latest",
        strength="B",
        use_cases=["coding", "search", "creative"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"rps": 1, "tpm": 500_000},
    ),
    _model(
        id="mistral-pixtral",
        display_name="Pixtral Large",
        provider_id="mistral",
        provider_model_id="pixtral-large-latest",
        strength="A",
        use_cases=["vision", "coding"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"rps": 1, "tpm": 500_000},
        modalities=["text", "image"],
    ),
    _model(
        id="mistral-codestral",
        display_name="Codestral",
        provider_id="mistral",
        provider_model_id="codestral-latest",
        strength="A",
        use_cases=["coding"],
        context_window=256_000,
        max_output_tokens=8192,
        rate_limits={"rps": 1, "tpm": 500_000},
        category="coding",
        notes="UNCERTAIN: Codestral may require billing attached (Premier-tagged).",
    ),
    # ---------------------------------------------------------------------
    # Provider 5 — GitHub Models (Bearer PAT models:read; no card)
    # base: https://models.github.ai/inference  | OpenAI-compatible
    # ---------------------------------------------------------------------
    _model(
        id="gh-gpt-4.1",
        display_name="GPT-4.1 (GitHub Models)",
        provider_id="github_models",
        provider_model_id="openai/gpt-4.1",
        strength="A",
        use_cases=["coding", "search", "reasoning", "data"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"rpm": 10, "rpd": 50},
        notes="Only no-card source of proprietary GPT. High tier: tight limits.",
    ),
    _model(
        id="gh-gpt-4o",
        display_name="GPT-4o (GitHub Models)",
        provider_id="github_models",
        provider_model_id="openai/gpt-4o",
        strength="A",
        use_cases=["coding", "search", "creative", "data", "vision"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"rpm": 15, "rpd": 150},
        modalities=["text", "image"],
    ),
    _model(
        id="gh-gpt-4o-mini",
        display_name="GPT-4o Mini (GitHub Models)",
        provider_id="github_models",
        provider_model_id="openai/gpt-4o-mini",
        strength="B",
        use_cases=["coding", "search", "data"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"rpm": 15, "rpd": 150},
    ),
    _model(
        id="gh-llama-3.3-70b",
        display_name="Llama 3.3 70B (GitHub Models)",
        provider_id="github_models",
        provider_model_id="meta/llama-3.3-70b-instruct",
        strength="A",
        use_cases=["coding", "search", "data"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"rpm": 15, "rpd": 150},
    ),
    _model(
        id="gh-deepseek-r1",
        display_name="DeepSeek R1 (GitHub Models)",
        provider_id="github_models",
        provider_model_id="deepseek/DeepSeek-R1",
        strength="A",
        use_cases=["reasoning", "coding"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"rpm": 1, "rpd": 8},
        category="reasoning",
        notes="Reasoning model: very tight limits (~1 RPM / ~8 RPD).",
    ),
    # ---------------------------------------------------------------------
    # Provider 6 — NVIDIA NIM (Bearer nvapi-; no card; prototyping only)
    # base: https://integrate.api.nvidia.com/v1  | OpenAI-compatible
    # ---------------------------------------------------------------------
    _model(
        id="nv-llama-3.1-405b",
        display_name="Llama 3.1 405B (NVIDIA)",
        provider_id="nvidia",
        provider_model_id="meta/llama-3.1-405b-instruct",
        strength="S",
        use_cases=["reasoning", "coding", "search"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"rpm": 40},
    ),
    _model(
        id="nv-deepseek-r1",
        display_name="DeepSeek R1 (NVIDIA)",
        provider_id="nvidia",
        provider_model_id="deepseek-ai/deepseek-r1",
        strength="S",
        use_cases=["reasoning", "coding"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"rpm": 40},
        category="reasoning",
    ),
    _model(
        id="nv-llama-3.3-70b",
        display_name="Llama 3.3 70B (NVIDIA)",
        provider_id="nvidia",
        provider_model_id="meta/llama-3.3-70b-instruct",
        strength="A",
        use_cases=["coding", "search", "data"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"rpm": 40},
    ),
    _model(
        id="nv-qwen2.5-coder-32b",
        display_name="Qwen2.5 Coder 32B (NVIDIA)",
        provider_id="nvidia",
        provider_model_id="qwen/qwen2.5-coder-32b-instruct",
        strength="A",
        use_cases=["coding"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"rpm": 40},
        category="coding",
    ),
    _model(
        id="nv-nemotron-70b",
        display_name="Llama 3.1 Nemotron 70B (NVIDIA)",
        provider_id="nvidia",
        provider_model_id="nvidia/llama-3.1-nemotron-70b-instruct",
        strength="A",
        use_cases=["reasoning", "coding"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"rpm": 40},
    ),
    # ---------------------------------------------------------------------
    # Provider 7 — Cerebras (Bearer; no card; fastest; 8K context cap on free)
    # base: https://api.cerebras.ai/v1  | OpenAI-compatible
    # ---------------------------------------------------------------------
    _model(
        id="cb-gpt-oss-120b",
        display_name="GPT-OSS 120B (Cerebras)",
        provider_id="cerebras",
        provider_model_id="gpt-oss-120b",
        strength="A",
        use_cases=["coding", "search", "reasoning"],
        context_window=8192,
        max_output_tokens=8192,
        rate_limits={"rpm": 30, "tpd": 1_000_000},
        notes="Free tier caps context at 8K. ~2000+ tok/s. Menu rotates.",
    ),
    _model(
        id="cb-glm-4.7",
        display_name="ZAI GLM-4.7 (Cerebras, preview)",
        provider_id="cerebras",
        provider_model_id="zai-glm-4.7",
        strength="A",
        use_cases=["reasoning", "coding"],
        context_window=8192,
        max_output_tokens=8192,
        rate_limits={"rpm": 30, "tpd": 1_000_000},
        notes="Preview; 8K context cap on free tier.",
    ),
    # ---------------------------------------------------------------------
    # Provider 8 — Cloudflare Workers AI (Bearer + account_id; no card; no training)
    # base: .../accounts/{account_id}/ai/run  | translated  | 10k neurons/day
    # ---------------------------------------------------------------------
    _model(
        id="cf-gpt-oss-120b",
        display_name="GPT-OSS 120B (Cloudflare)",
        provider_id="cloudflare",
        provider_model_id="@cf/openai/gpt-oss-120b",
        strength="A",
        use_cases=["coding", "search", "reasoning"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"neurons": 10_000},
    ),
    _model(
        id="cf-llama-3.3-70b",
        display_name="Llama 3.3 70B (Cloudflare)",
        provider_id="cloudflare",
        provider_model_id="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        strength="A",
        use_cases=["coding", "search"],
        context_window=131_000,
        max_output_tokens=4096,
        rate_limits={"neurons": 10_000},
        notes="Best quality/Neuron value.",
    ),
    _model(
        id="cf-qwen2.5-coder-32b",
        display_name="Qwen2.5 Coder 32B (Cloudflare)",
        provider_id="cloudflare",
        provider_model_id="@cf/qwen/qwen2.5-coder-32b-instruct",
        strength="A",
        use_cases=["coding"],
        context_window=32_000,
        max_output_tokens=4096,
        rate_limits={"neurons": 10_000},
        category="coding",
    ),
    _model(
        id="cf-qwq-32b",
        display_name="QwQ 32B (Cloudflare)",
        provider_id="cloudflare",
        provider_model_id="@cf/qwen/qwq-32b",
        strength="A",
        use_cases=["reasoning"],
        context_window=32_000,
        max_output_tokens=4096,
        rate_limits={"neurons": 10_000},
        category="reasoning",
    ),
    _model(
        id="cf-llama-4-scout",
        display_name="Llama 4 Scout (Cloudflare)",
        provider_id="cloudflare",
        provider_model_id="@cf/meta/llama-4-scout-17b-16e-instruct",
        strength="A",
        use_cases=["search", "coding"],
        context_window=131_000,
        max_output_tokens=4096,
        rate_limits={"neurons": 10_000},
    ),
    _model(
        id="cf-llama-3.2-11b-vision",
        display_name="Llama 3.2 11B Vision (Cloudflare)",
        provider_id="cloudflare",
        provider_model_id="@cf/meta/llama-3.2-11b-vision-instruct",
        strength="B",
        use_cases=["vision"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"neurons": 10_000},
        modalities=["text", "image"],
    ),
    _model(
        id="cf-llama-3.1-8b",
        display_name="Llama 3.1 8B Fast (Cloudflare)",
        provider_id="cloudflare",
        provider_model_id="@cf/meta/llama-3.1-8b-instruct-fp8-fast",
        strength="B",
        use_cases=["search", "coding"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"neurons": 10_000},
        notes="Cheapest/fastest; best Neuron value.",
    ),
    # ---------------------------------------------------------------------
    # Provider 9 — Z.ai / Zhipu GLM (Bearer; no card)
    # base: https://api.z.ai/api/paas/v4  | OpenAI-compatible | ~1 concurrent
    # ---------------------------------------------------------------------
    _model(
        id="glm-4.7-flash",
        display_name="GLM-4.7-Flash",
        provider_id="zai",
        provider_model_id="glm-4.7-flash",
        strength="A",
        use_cases=["coding", "search", "reasoning", "data"],
        context_window=200_000,
        max_output_tokens=128_000,
        rate_limits={"concurrent": 1},
    ),
    _model(
        id="glm-4.5-flash",
        display_name="GLM-4.5-Flash",
        provider_id="zai",
        provider_model_id="glm-4.5-flash",
        strength="A",
        use_cases=["coding", "reasoning", "search"],
        context_window=128_000,
        max_output_tokens=8192,
        rate_limits={"concurrent": 1},
    ),
    _model(
        id="glm-4.6v-flash",
        display_name="GLM-4.6V-Flash",
        provider_id="zai",
        provider_model_id="glm-4.6v-flash",
        strength="B",
        use_cases=["vision", "coding"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"concurrent": 1},
        modalities=["text", "image"],
    ),
    # ---------------------------------------------------------------------
    # Provider 10 — HuggingFace Inference Providers (Bearer; no card)
    # base: https://router.huggingface.co/v1  | OpenAI-compatible
    # NOTE: only ~$0.10/month free credit — evaluation only.
    # ---------------------------------------------------------------------
    _model(
        id="hf-deepseek-r1",
        display_name="DeepSeek R1 (HuggingFace)",
        provider_id="huggingface",
        provider_model_id="deepseek-ai/DeepSeek-R1",
        strength="A",
        use_cases=["reasoning", "coding"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"rpm": 10},
        category="reasoning",
        notes="Eval only: ~$0.10/month free credit, then PRO needed.",
    ),
    _model(
        id="hf-llama-3.3-70b",
        display_name="Llama 3.3 70B (HuggingFace)",
        provider_id="huggingface",
        provider_model_id="meta-llama/Llama-3.3-70B-Instruct",
        strength="A",
        use_cases=["coding", "search", "data"],
        context_window=128_000,
        max_output_tokens=4096,
        rate_limits={"rpm": 10},
        notes="Eval only: ~$0.10/month free credit.",
    ),
]


def _validate_and_serialise() -> list[dict[str, Any]]:
    """Validate every record against ``ModelInfo`` and return JSON-safe dicts."""
    seen_ids: set[str] = set()
    output: list[dict[str, Any]] = []

    for raw in _MODELS:
        model = ModelInfo.model_validate(raw)
        if model.id in seen_ids:
            raise ValueError(f"Duplicate model id: {model.id}")
        seen_ids.add(model.id)
        output.append(model.model_dump(mode="json", exclude_none=True))

    return output


def main() -> None:
    records = _validate_and_serialise()
    _OUTPUT_PATH.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} models to {_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
