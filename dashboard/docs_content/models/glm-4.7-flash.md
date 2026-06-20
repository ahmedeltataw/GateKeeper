# GLM-4.7-Flash

**Model id:** `glm-4.7-flash`

A strong, fast model with a very large context window. A great default for
coding and reasoning tasks that involve a lot of input.

---

## At a glance

| Property | Value |
| --- | --- |
| Strength | High |
| Context window | 200K tokens |
| Max output | Large |
| Modalities | Text |
| Cost tier | Free |

---

## Best use cases

- ✅ **Coding** — generation, refactoring, and explanation.
- ✅ **Reasoning** — multi-step problems and analysis.
- ✅ **Long inputs** — large documents, transcripts, or codebases.
- ✅ **Data tasks** — structured extraction and transformation.

## Less ideal for

- ❌ Image understanding — use a [vision model](glm-4.6v-flash.md) instead.

---

## Example

```python
client.chat.completions.create(
    model="glm-4.7-flash",
    messages=[{"role": "user", "content": "Refactor this function for clarity..."}],
)
```

> **Why pick this one?** When your prompt is big or the task needs careful
> reasoning, the large context and high capability make this a safe default.
