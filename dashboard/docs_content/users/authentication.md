# Authentication

Every request to GateKeeper is authenticated with a **Bearer token**, exactly
like the OpenAI API.

```http
Authorization: Bearer YOUR_GATEKEEPER_KEY
```

---

## Your access key

On first run, GateKeeper helps you mint a strong access key from the dashboard.
Keep this key secret — anyone with it can make requests on your behalf.

- Treat the key like a password.
- Never commit it to source control.
- Store it in an environment variable or a secrets manager.

---

## Provider keys vs. your access key

There are **two kinds** of keys, and it helps to keep them straight:

| Key | Who uses it | Where it lives |
| --- | --- | --- |
| **Your access key** | Your apps, to call GateKeeper | Your app's environment |
| **Provider keys** | GateKeeper, to call upstream models | Encrypted inside GateKeeper |

You only ever send your **access key**. GateKeeper manages the provider keys for
you and never exposes them back to clients.

---

## Rotating keys

If a key is leaked or you simply want to rotate:

1. Issue a new access key from the dashboard.
2. Update your apps to use the new key.
3. Revoke the old key.

Provider keys can be added, replaced, or removed from the dashboard at any time
without restarting your apps.

---

## Errors

| Status | Meaning | What to do |
| --- | --- | --- |
| `401` | Missing or invalid key | Check the `Authorization` header |
| `403` | Action not allowed for this key | Use a key with the right access |
| `429` | Too many requests | Back off and retry shortly |

> **Security tip:** Run GateKeeper behind HTTPS in production so keys are never
> sent in clear text.
