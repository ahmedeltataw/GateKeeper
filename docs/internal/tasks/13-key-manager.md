# Task 13 — Key Manager (AES-256-GCM + SQLite)

> **Phase 3** · depends on: 01 · Reference: `IMPLEMENTATION_PLAN.md` §9, §19

## Objective
Securely store and retrieve provider API keys, encrypted at rest, decrypted only in memory at request time.

## Files to create/modify
- `src/core/key_manager.py`

## Detailed spec
- Encryption per §9 using `cryptography.hazmat.primitives.ciphers.aead.AESGCM`:
  - `generate_encryption_key()` → 32-byte key.
  - `encrypt_key(plain, key)` → `base64(nonce[12] + ciphertext)`.
  - `decrypt_key(b64, key)` → plain.
- `ENCRYPTION_KEY` loaded from `.env` (32-byte base64). Fail clearly if missing/wrong length.
- SQLite (`aiosqlite`) table `keys(id PK, encrypted_key, created_at, last_used, health_status default 'unknown')` per §9. DB path from config `database.path` (`server/data/gateway.db`).
- API: `init()` (create table, load index), `set_key(provider_id, plain)` (encrypt+store), `get_key(provider_id) -> plain` (decrypt in memory), `delete_key(provider_id)`, `list_providers_with_keys()`, `update_health(provider_id, status)`.
- Optional bootstrap: if `.env` contains `*_KEY` vars and DB has none, import them encrypted.
- Never log plaintext keys; dashboard will show masked.

## Acceptance criteria
- [ ] Round-trip: `set_key`→`get_key` returns the original plaintext.
- [ ] Stored value is `base64(nonce+ciphertext)`, not plaintext (verify in DB).
- [ ] Wrong/short `ENCRYPTION_KEY` raises a clear error.
- [ ] Tampered ciphertext fails GCM auth (decrypt raises).
- [ ] DB created at `server/data/gateway.db`; table schema matches §9.

## Review checklist
- 12-byte nonce, 256-bit key, GCM (AEAD) — not Fernet/CBC.
- No plaintext key logged or returned in API responses.
- Provider modules receive decrypted key only at call time.
