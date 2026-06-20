# 🔒 Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in GateKeeper, please report it responsibly.

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email: **security@GateKeeper.dev** (or contact [@ahmedeltataw](https://github.com/ahmedeltataw) directly)

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response timeline

| Stage | Timeline |
|-------|----------|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 1 week |
| Fix or mitigation | Within 2 weeks (critical) / 1 month (moderate) |
| Public disclosure | After fix is released |

## Security Measures

GateKeeper is designed with security as a core principle:

### 🔐 Data Protection

- **Provider API keys** are encrypted at rest using **AES-256-GCM**
- **Client API keys** are stored as **SHA-256 hashes** — raw keys never touch disk
- The encryption key (`ENCRYPTION_KEY`) is held only in memory
- `.env`, `*.key`, and `*.db` files are git-ignored by default

### 🏠 Local-First Architecture

- The gateway binds to `127.0.0.1` by default — **no external network access**
- All data (prompts, responses, keys, usage) stays on your machine
- Zero telemetry — no analytics, no phone-home, no cloud dependency
- The only outbound traffic is to LLM providers **you** explicitly configured

### 🔑 Authentication

- API key authentication is enabled by default
- Multi-tenant mode scopes each client key to its plan's models
- Admin endpoints require a separate admin token

### 🛡️ Resilience

- Circuit breaker prevents cascading failures
- Rate limiter respects provider quotas
- Auto-blacklist for repeatedly failing models
- Graceful degradation — single provider failure never breaks the gateway

## Scope

The following are **in scope**:

- Authentication bypass
- Authorization bypass
- Remote code execution
- Data exposure (keys, prompts, responses)
- Denial of service
- Cryptographic weaknesses

The following are **out of scope**:

- Social engineering
- Physical access attacks
- Issues in third-party providers (report those to the provider)
- Issues requiring modification of `config.yaml` with admin access

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x | ✅ Yes |
| < 1.0 | ❌ No |

## Best Practices for Deployment

1. **Never expose the gateway to the internet** without proper authentication
2. **Use strong, unique `ENCRYPTION_KEY`** values (auto-generated is fine)
3. **Rotate API keys** periodically via the dashboard
4. **Enable `auth.enabled: true`** (default) — never disable auth in production
5. **Monitor the dashboard** for unusual usage patterns
6. **Keep `.env` out of version control** (git-ignored by default)

---

Thank you for helping keep GateKeeper and its users secure! 🙏
