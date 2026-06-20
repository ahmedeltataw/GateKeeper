# GLM-4.6V-Flash

**Model id:** `glm-4.6v-flash`

A vision-capable model that understands **both images and text**. Use it when
your task involves pictures, screenshots, diagrams, or documents with visuals.

---

## At a glance

| Property | Value |
| --- | --- |
| Strength | Medium |
| Context window | 128K tokens |
| Max output | Standard |
| Modalities | Text + Image |
| Cost tier | Free |

---

## Best use cases

- ✅ **Vision** — describe, analyze, or answer questions about images.
- ✅ **Screenshots & UI** — explain what is on screen.
- ✅ **Diagrams & charts** — interpret visual content.
- ✅ **Light coding** — code paired with visual context.

## Less ideal for

- ❌ Heavy text-only reasoning — prefer [GLM-4.7-Flash](glm-4.7-flash.md).

---

## Example

```python
client.chat.completions.create(
    model="glm-4.6v-flash",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What is in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/cat.jpg"}},
        ],
    }],
)
```

> **Why pick this one?** It is the right choice whenever an image is part of the
> question. For pure text, a text model will usually be faster and stronger.
