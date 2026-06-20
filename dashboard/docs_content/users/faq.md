# FAQ

### Is GateKeeper compatible with the OpenAI SDK?

Yes. Point the SDK's `base_url` at your GateKeeper instance and use your
GateKeeper access key. No other code changes are needed.

---

### Which models can I use?

Any model listed in the [Model Cards](../models/overview.md). You select a model
by its id in the `model` field of your request.

---

### What happens if a model is down or rate-limited?

GateKeeper can automatically fall back to a compatible model so your request
still succeeds. The response tells you when a fallback was used.

---

### Do I need a paid account?

No. Many supported providers offer a free tier. You only need one provider key
to get started.

---

### How are my provider keys stored?

Provider keys are encrypted at rest inside GateKeeper and are never returned to
clients. Your apps only ever use your GateKeeper access key.

---

### Can I stream responses?

Yes. Set `stream: true` in your request to receive tokens as they are generated.
See [Making Requests](making_requests.md).

---

### How do I run it in Docker?

Provide configuration through environment variables (your encryption key and at
least one provider key). GateKeeper reads its configuration from the environment,
so it runs cleanly in containers without writing to disk.

---

### Where do I report issues or request features?

Open an issue in the project repository. Include the request you sent (with keys
removed) and the response or error you received.
