# Making Requests

GateKeeper implements the OpenAI **Chat Completions** API. If your tooling
already targets OpenAI, just change the base URL and key.

---

## Endpoint

```
POST /v1/chat/completions
```

Base URL (local): `http://127.0.0.1:8000`

---

## Request body

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `model` | string | — | Model id (see [Model Cards](../models/overview.md)) |
| `messages` | array | — | Conversation turns (`role` + `content`) |
| `temperature` | number | `0.7` | Creativity, `0.0`–`2.0` |
| `max_tokens` | integer | `2048` | Max tokens to generate |
| `top_p` | number | `1.0` | Nucleus sampling |
| `stream` | boolean | `false` | Stream tokens as they are produced |
| `stop` | string \| array | `null` | Stop sequence(s) |

---

## Basic example

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="YOUR_GATEKEEPER_KEY",
)

resp = client.chat.completions.create(
    model="glm-4.7-flash",
    messages=[
        {"role": "system", "content": "You are concise."},
        {"role": "user", "content": "Explain HTTP in one line."},
    ],
)

print(resp.choices[0].message.content)
```

---

## Streaming

Set `stream: true` to receive tokens incrementally:

```python
stream = client.chat.completions.create(
    model="glm-4.7-flash",
    messages=[{"role": "user", "content": "Count to five."}],
    stream=True,
)

for chunk in stream:
    delta = chunk.choices[0].delta.content or ""
    print(delta, end="", flush=True)
```

---

## Switching models

Changing models is a one-line change — the request shape stays identical:

```diff
- model="glm-4.7-flash",
+ model="glm-4.6v-flash",
```

Browse the [Model Cards](../models/overview.md) to choose the best fit for your
task (coding, reasoning, vision, and more).

---

## Automatic fallback

If your chosen model is rate-limited or temporarily unavailable, GateKeeper can
route the request to a compatible alternative so your application keeps
responding. Responses indicate when a fallback was used, so you always know what
served your request.

---

## Good practices

- **Send a system message** to set tone and constraints.
- **Cap `max_tokens`** to control latency and cost.
- **Handle `429`** with a short backoff and retry.
- **Stream** long responses for a snappier user experience.
