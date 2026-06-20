GateKeeper puts the power of AI at your fingertips in under 5 minutes.

# Getting Started

GateKeeper is a single, OpenAI-compatible gateway in front of many AI model
providers. You point your app at **one** endpoint with **one** API key, and
GateKeeper handles routing, fallback, and health behind the scenes.

If you have ever called the OpenAI API, you already know how to use GateKeeper.

---

## What you get

- **One endpoint, many models** — switch models by changing a single string.
- **Drop-in OpenAI compatibility** — works with existing OpenAI SDKs and tools.
- **Automatic fallback** — if one model is busy or down, your request keeps working.
- **Streaming support** — token-by-token responses out of the box.

---

## 1. Install

```bash
git clone <your-gatekeeper-repo-url>
cd gatekeeper
pip install -r requirements.txt
```

> **Tip:** Use a virtual environment (`python -m venv .venv`) to keep
> dependencies isolated.

---

## 2. Configure

Copy the example environment file and fill in the essentials:

```bash
cp .env.example .env
```

You need two things to start:

1. An **encryption key** (used to store provider keys securely at rest).
2. At least **one provider API key**.

```bash
# .env
ENCRYPTION_KEY=your_generated_key_here
ZAI_API_KEY=your_provider_key_here
```

Generate an encryption key with the command printed in `.env.example`. Most
providers offer a free tier — pick any one to begin.

---

## 3. Run

```bash
python -m src.api.server
```

The gateway starts on `http://127.0.0.1:8000`. On first run, open the dashboard
and follow the prompt to create your access key.

---

## 4. Your first request

GateKeeper speaks the OpenAI Chat Completions format:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_GATEKEEPER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "model": "glm-4.7-flash",
        "messages": [{"role": "user", "content": "Say hello in one sentence."}]
      }'
```

You will get back a standard OpenAI-shaped response. That is it — you are live.

---

## Next steps

- [Authentication](authentication.md) — how keys work and how to rotate them.
- [Making Requests](making_requests.md) — parameters, streaming, and examples.
- [Model Cards](../models/overview.md) — pick the right model for your task.
- [FAQ](faq.md) — common questions answered.
