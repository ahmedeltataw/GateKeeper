"""Smart Diagnostic / remediation engine (gateway -> provider edge).

When a provider call fails, this decides whether the failure is *programmatically
recoverable* before the circuit breaker counts it against the model:

- ``413`` Payload Too Large -> shrink the request (lower ``max_tokens``, drop the
  oldest non-system turns) and retry.
- ``5xx`` / ``timeout`` -> bounded exponential backoff, then retry (transient
  server hiccup; the same provider usually recovers within a second).
- ``429`` -> NOT retried on the same provider. With many providers available,
  immediate failover (plus the provider cooldown) beats sleeping on a rate-limit
  that will not clear in a second. The fallback engine handles it.
- anything else (``401`` bad key, ``404`` model gone) -> not recoverable here.

This is deliberately NOT FastAPI/ASGI middleware: ASGI middleware only sees the
client->gateway edge, while these errors occur on the gateway->provider edge.
The fallback engine calls ``diagnose`` around each provider attempt.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.types import ChatRequest, ModelInfo

_MIN_MAX_TOKENS = 256
_RECOVERABLE_BACKOFF_CODES = {"5xx", "timeout"}


def preflight_clamp(request: ChatRequest, model: ModelInfo) -> ChatRequest:
    """Proactively shrink a request to fit a model's limits *before* sending.

    Many 413/400 "payload too large" errors are avoidable: callers (and OpenCode)
    often ask for more output tokens than a model allows. Capping ``max_tokens``
    to the model's ``max_output_tokens`` up front prevents the round-trip failure
    entirely — important for tight-limit providers like GitHub Models.
    """
    if request.max_tokens <= model.max_output_tokens:
        return request
    return request.model_copy(update={"max_tokens": model.max_output_tokens})


@dataclass(frozen=True)
class Remediation:
    """The engine's verdict for one failed attempt."""

    action: str  # "retry_modified" | "retry_after" | "none"
    request: ChatRequest | None  # modified request for "retry_modified"
    delay_seconds: float  # backoff for "retry_after"
    explanation: str  # human-readable "[problem] -> [fix]"; empty when action == "none"

    @property
    def will_retry(self) -> bool:
        return self.action != "none"


def _shrink_request(request: ChatRequest) -> ChatRequest:
    """Reduce a request's footprint for a 413 retry.

    Halve ``max_tokens`` (floor ``_MIN_MAX_TOKENS``) and drop the oldest
    non-system messages, always keeping any leading system message and the most
    recent user turn so the conversation still makes sense.
    """
    new_max_tokens = max(_MIN_MAX_TOKENS, request.max_tokens // 2)

    messages = request.messages
    system = [m for m in messages[:1] if m.role == "system"]
    body = messages[len(system):]
    # Keep the last turn; drop the oldest half of the remainder.
    if len(body) > 1:
        keep_from = len(body) // 2
        body = body[keep_from:]
    new_messages = [*system, *body] or list(messages)

    return request.model_copy(
        update={"messages": new_messages, "max_tokens": new_max_tokens}
    )


def diagnose(
    code: str,
    request: ChatRequest,
    attempt: int,
    *,
    max_backoff_seconds: float = 8.0,
) -> Remediation:
    """Return a remediation plan for a failed attempt.

    ``attempt`` is the zero-based remediation attempt count for this model on
    this request; callers cap how many times they re-invoke after a retry.
    """
    if code == "413":
        shrunk = _shrink_request(request)
        # If shrinking changed nothing, there is nothing left to try.
        if (
            shrunk.max_tokens == request.max_tokens
            and len(shrunk.messages) == len(request.messages)
        ):
            return Remediation("none", None, 0.0, "")
        return Remediation(
            "retry_modified",
            shrunk,
            0.0,
            f"413 Payload Too Large -> shrank request to max_tokens="
            f"{shrunk.max_tokens}, {len(shrunk.messages)} message(s), and retried",
        )

    if code in _RECOVERABLE_BACKOFF_CODES:
        delay = min(max_backoff_seconds, 0.5 * (2**attempt))
        return Remediation(
            "retry_after",
            None,
            delay,
            f"{code} -> exponential backoff {delay:.1f}s, then retried",
        )

    return Remediation("none", None, 0.0, "")
