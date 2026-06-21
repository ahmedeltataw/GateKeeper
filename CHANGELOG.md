# 📝 Changelog

All notable changes to GateKeeper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Model Cards** doc section — 32 live-verified models with tier, context, and best-use
- **Integrate with OpenCode & AI Agents** doc section — `/v1/connection-info`, `setup_agents.py`, manual OpenCode config
- **Live Health Check** doc section + `scripts/live_smoke_report.py` one-shot per-model smoke report
- Docker Compose support for one-command deployment

### Fixed
- Provider keys added to `.env` after the first run are now imported — `key_manager`
  bootstrap was all-or-nothing and silently skipped new keys once the vault was non-empty
  (activated cloudflare, huggingface, oc_zen, zai)
- `smoke` probe no longer crashes on list-shaped (multimodal) completion content;
  `content` is normalised to text so the probe honours its "never raises" contract
- `setup_agents.py` no longer crashes on legacy Windows consoles (cp1252) — stdout is forced to UTF-8
- Streamlit dashboard with dark mode
- Multi-tenant API key support
- Smart diagnostics engine (413 shrink, 5xx backoff)
- Quality router with per-task model selection
- Sticky sessions for conversation continuity
- Cache hit rate tracking
- Background benchmark runner
- Auto-generated models catalog

### Changed
- Improved fallback engine with 4-tier cascade
- Health probes now use passive-first strategy
- Circuit breaker now persists state to SQLite

## [0.1.0] - 2026-01-01

### Added
- Initial release
- 12 provider adapters (Groq, Gemini, OpenRouter, Mistral, GitHub Models, NVIDIA, Cerebras, Cloudflare, Zhipu, Hugging Face, Aion, Cohere)
- OpenAI-compatible API (`/v1/chat/completions`, `/v1/models`)
- Encrypted key vault (AES-256-GCM)
- Token-bucket rate limiter
- Circuit breaker with auto-blacklist
- Background health monitoring
- Response cache with TTL
- Windows one-click launcher (`run.bat`)
- pytest test suite
- MIT License
