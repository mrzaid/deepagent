"""Thin OpenAI wrapper: tool-calling, token accounting, retry, and a cassette
layer for deterministic/offline replay.

Design choice: we do NOT use the multi-turn tool-message protocol. Each turn the
loop hands us a freshly *reconstructed* prompt (system + a rendered state
header) and we return the model's chosen tool call. This keeps every LLM call
effectively stateless and is what lets the agent run many steps without the
context growing unbounded (see context.py).

The cassette layer keys each request by a hash of its content. In `record` mode
we call the API and save the normalised response; in `replay` mode we serve it
from disk with no network. The eval harness uses replay for free, deterministic
reruns.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import config

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(api_key=config.OPENAI_API_KEY or None)
    return _client


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class LLMResponse:
    content: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


# --- cassette ------------------------------------------------------------
def _cassette_key(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def _cassette_path(key: str):
    config.CASSETTES_DIR.mkdir(parents=True, exist_ok=True)
    return config.CASSETTES_DIR / f"{key}.json"


def _load_cassette(key: str) -> Optional[dict]:
    p = _cassette_path(key)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _save_cassette(key: str, resp_dict: dict) -> None:
    _cassette_path(key).write_text(json.dumps(resp_dict, indent=2), encoding="utf-8")


# --- normalisation -------------------------------------------------------
def _normalise(raw) -> LLMResponse:
    msg = raw.choices[0].message
    calls = []
    for tc in (msg.tool_calls or []):
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {"_raw": tc.function.arguments}
        calls.append(ToolCall(id=tc.id, name=tc.function.name, args=args))
    usage = {}
    if getattr(raw, "usage", None):
        usage = {
            "prompt_tokens": raw.usage.prompt_tokens,
            "completion_tokens": raw.usage.completion_tokens,
            "total_tokens": raw.usage.total_tokens,
        }
    return LLMResponse(content=msg.content, tool_calls=calls, usage=usage)


def _to_dict(r: LLMResponse) -> dict:
    return {
        "content": r.content,
        "tool_calls": [{"id": c.id, "name": c.name, "args": c.args} for c in r.tool_calls],
        "usage": r.usage,
    }


def _from_dict(d: dict) -> LLMResponse:
    return LLMResponse(
        content=d.get("content"),
        tool_calls=[ToolCall(**c) for c in d.get("tool_calls", [])],
        usage=d.get("usage", {}),
    )


# --- streaming helpers ---------------------------------------------------
_REPORT_RE = re.compile(r'"report"\s*:\s*"')
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f"}


def _decode_report_value(args_so_far: str) -> Optional[str]:
    """Decode the (possibly partial) value of the "report" field from a streaming
    tool-call arguments string, so we can surface clean report text token-by-token
    instead of raw JSON. Returns None until the value has started."""
    m = _REPORT_RE.search(args_so_far)
    if not m:
        return None
    i, n = m.end(), len(args_so_far)
    out = []
    while i < n:
        c = args_so_far[i]
        if c == "\\" and i + 1 < n:
            nxt = args_so_far[i + 1]
            if nxt == "u" and i + 5 < n:
                try:
                    out.append(chr(int(args_so_far[i + 2:i + 6], 16)))
                except ValueError:
                    pass
                i += 6
                continue
            out.append(_ESCAPES.get(nxt, nxt))
            i += 2
            continue
        if c == '"':  # unescaped closing quote -> end of value
            break
        out.append(c)
        i += 1
    return "".join(out)


class _ReportStreamer:
    """Emits only the newly-arrived report text on each streamed args delta."""

    def __init__(self, cb: Callable[[str], None]):
        self.cb = cb
        self.emitted = 0

    def feed(self, args_so_far: str) -> None:
        val = _decode_report_value(args_so_far)
        if val is not None and len(val) > self.emitted:
            self.cb(val[self.emitted:])
            self.emitted = len(val)


def _stream_call(kwargs: dict, has_tools: bool, on_report_delta: Callable[[str], None]) -> LLMResponse:
    """Make a streaming completion, surface report/synthesis text via the callback,
    and reassemble the same normalised LLMResponse the non-streaming path returns."""
    kwargs = dict(kwargs, stream=True, stream_options={"include_usage": True})
    content_parts: list[str] = []
    tool_acc: dict[int, dict] = {}
    usage: dict = {}
    streamer = _ReportStreamer(on_report_delta)

    for chunk in _get_client().chat.completions.create(**kwargs):
        if getattr(chunk, "usage", None):
            usage = {"prompt_tokens": chunk.usage.prompt_tokens,
                     "completion_tokens": chunk.usage.completion_tokens,
                     "total_tokens": chunk.usage.total_tokens}
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None):
            content_parts.append(delta.content)
            if not has_tools:  # plain text completion (synthesis) -> stream it directly
                on_report_delta(delta.content)
        for tc in (getattr(delta, "tool_calls", None) or []):
            acc = tool_acc.setdefault(tc.index, {"id": None, "name": None, "args": ""})
            if tc.id:
                acc["id"] = tc.id
            if tc.function:
                if tc.function.name:
                    acc["name"] = tc.function.name
                if tc.function.arguments:
                    acc["args"] += tc.function.arguments
                    if acc["name"] == "finish":  # stream the final report as it forms
                        streamer.feed(acc["args"])

    calls = []
    for i in sorted(tool_acc):
        acc = tool_acc[i]
        try:
            args = json.loads(acc["args"] or "{}")
        except json.JSONDecodeError:
            args = {"_raw": acc["args"]}
        calls.append(ToolCall(id=acc["id"] or f"call_{i}", name=acc["name"] or "", args=args))
    return LLMResponse(content=("".join(content_parts) or None), tool_calls=calls, usage=usage)


# --- public API ----------------------------------------------------------
def chat(
    messages: list[dict],
    tools: Optional[list[dict]] = None,
    tool_choice: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_retries: int = 4,
    on_report_delta: Optional[Callable[[str], None]] = None,
) -> LLMResponse:
    model = model or config.AGENT_MODEL
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": tool_choice,
        "temperature": temperature,
    }
    key = _cassette_key(payload)

    # record + replay both read an existing cassette first. record is therefore
    # WRITE-ONCE (never clobbers), so repeated identical prompts in one run return
    # the same value — essential because the model isn't perfectly deterministic
    # even at temperature 0, and summary prompts can recur.
    if config.LLM_MODE in ("replay", "record"):
        cached = _load_cassette(key)
        if cached is not None:
            return _from_dict(cached)
        if config.LLM_MODE == "replay":
            raise RuntimeError(
                f"No cassette for request {key} (LLM_MODE=replay). "
                f"Record it first with LLM_MODE=record."
            )

    kwargs = {"model": model, "messages": messages, "temperature": temperature}
    if tools:
        kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

    # Stream only when a delta callback is supplied (the finish/synthesis report);
    # everything else uses the plain call so token accounting is unchanged. Streaming
    # does not affect the cassette key, so recorded eval runs stay reproducible.
    stream = on_report_delta is not None

    last_err = None
    for attempt in range(max_retries):
        try:
            if stream:
                resp = _stream_call(kwargs, bool(tools), on_report_delta)
            else:
                resp = _normalise(_get_client().chat.completions.create(**kwargs))
            if config.LLM_MODE == "record":
                _save_cassette(key, _to_dict(resp))
            return resp
        except Exception as e:  # noqa: BLE001 - broad on purpose for transient retry
            last_err = e
            if not _is_transient(e) or attempt == max_retries - 1:
                raise
            # full jitter: avoids synchronised retry storms against a rate limit
            time.sleep(random.uniform(0, min(2 ** attempt, 8)))
    raise last_err  # pragma: no cover


def _is_transient(e: Exception) -> bool:
    name = type(e).__name__
    transient = {"RateLimitError", "APITimeoutError", "APIConnectionError", "InternalServerError"}
    if name in transient:
        return True
    status = getattr(e, "status_code", None)
    return status in (429, 500, 502, 503, 504)


def simple(system: str, user: str, model: Optional[str] = None, temperature: float = 0.0,
           on_report_delta: Optional[Callable[[str], None]] = None) -> LLMResponse:
    """Convenience for plain text completions (summaries, judging, synthesis).
    Pass on_report_delta to stream the text (used for force-synthesis)."""
    return chat(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=model,
        temperature=temperature,
        on_report_delta=on_report_delta,
    )


class StructuredOutputError(RuntimeError):
    """Raised when the model's output can't be validated against the schema after
    the allowed retries — callers can then fall back gracefully."""


def structured(system: str, user: str, schema, model: Optional[str] = None,
               temperature: float = 0.0, max_validation_retries: int = 2,
               on_retry: Optional[Callable[[int, Exception], None]] = None):
    """Ask the model for JSON, validate it against a pydantic model, and treat a
    malformed/invalid response as a *transient* error — retry the call rather than
    accept degraded data (the pattern from the reference docex app). Returns the
    validated model instance + the usage dict; raises StructuredOutputError if it
    never validates.

    Retrying only yields a different result on a LIVE call — under record/replay the
    response is fixed by the cassette, so we don't loop pointlessly there.
    """
    from pydantic import ValidationError  # local import keeps pydantic optional at import time

    last_err: Exception | None = None
    attempts = max_validation_retries + 1
    for attempt in range(1, attempts + 1):
        resp = simple(system, user, model=model, temperature=temperature)
        m = re.search(r"\{.*\}", resp.content or "", re.S)
        if m:
            try:
                return schema.model_validate_json(m.group(0)), resp.usage
            except ValidationError as e:
                last_err = e
        else:
            last_err = ValueError("no JSON object found in model output")

        if attempt < attempts and config.LLM_MODE not in ("replay", "record"):
            if on_retry:
                on_retry(attempt, last_err)
            continue
        break

    raise StructuredOutputError(f"output failed schema validation after {attempt} attempt(s): {last_err}")
