# Model Cards

Each model has different strengths. Use these cards to pick the right one for
your task. You select a model by putting its **id** in the `model` field of your
request.

| Model | Best for | Context | Vision |
| --- | --- | --- | --- |
| [GLM-4.7-Flash](glm-4.7-flash.md) | Coding, reasoning, long documents | 200K | No |
| [GLM-4.5-Flash](glm-4.5-flash.md) | Fast everyday chat & coding | 128K | No |
| [GLM-4.6V-Flash](glm-4.6v-flash.md) | Images + text (vision) | 128K | Yes |

---

## How to choose

- **Need to read a large document or codebase?** Pick a model with a big
  context window, like **GLM-4.7-Flash**.
- **Want fast, lightweight answers?** **GLM-4.5-Flash** is a great default.
- **Working with images?** Use a vision model like **GLM-4.6V-Flash**.

> **Tip:** Switching models is a one-line change. Start with a fast model and
> move up only if you need more capability.
