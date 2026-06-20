# GLM-4.5-Flash

**Model id:** `glm-4.5-flash`

A balanced, fast model for everyday chat and coding. A good default when you
want quick responses without sacrificing quality.

---

## At a glance

| Property | Value |
| --- | --- |
| Strength | High |
| Context window | 128K tokens |
| Max output | Standard |
| Modalities | Text |
| Cost tier | Free |

---

## Best use cases

- ✅ **Everyday chat** — assistants and Q&A.
- ✅ **Coding** — quick generation and fixes.
- ✅ **Reasoning** — solid step-by-step answers.
- ✅ **Search-style queries** — concise, helpful responses.

## Less ideal for

- ❌ Extremely large inputs — prefer [GLM-4.7-Flash](glm-4.7-flash.md) (200K).
- ❌ Images — use a [vision model](glm-4.6v-flash.md).

---

## Example

```python
client.chat.completions.create(
    model="glm-4.5-flash",
    messages=[{"role": "user", "content": "Summarize this email in two lines."}],
)
```

> **Why pick this one?** It is a strong, snappy default for most tasks. Start
> here and only move up if you hit a limit.
