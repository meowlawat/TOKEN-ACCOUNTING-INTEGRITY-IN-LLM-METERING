"""One-shot patch: wire the real serving stack into the M1 stream and the M2 route.

Kept as a file (not an inline heredoc) because the replacement blocks contain SSE
newline escapes that shells mangle. Idempotent: re-running is a no-op.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "app" / "m_routes.py"
s = p.read_text(encoding="utf-8")
changed = []

OLD_GEN = '''    async def gen():
        try:
            for i in range(n_out):
                if await request.is_disconnected():
                    state["disconnect_ns"] = time.perf_counter_ns()
                    break
                word = mock._det_int(f"{req.prompt}:{i}", seed, 0, 21)  # noqa: SLF001 - deterministic index
                yield f"data: token_{word}\\n\\n".encode()
                state["delivered"] += 1
                if delay_s:
                    await asyncio.sleep(delay_s)
            else:
                state["completed"] = True
            yield b"data: [DONE]\\n\\n"
'''

NEW_GEN = '''    async def gen():
        try:
            if use_real:
                # Real SSE from the upstream serving stack. On a client disconnect we
                # stop consuming and the upstream stream is torn down, so the usage
                # record never arrives -- the M1 condition occurring for real rather
                # than by construction.
                async for delta, usage in real_server.stream(req.prompt, seed, n_out):
                    if await request.is_disconnected():
                        state["disconnect_ns"] = time.perf_counter_ns()
                        break
                    if usage is not None:
                        state["upstream_usage"] = usage.raw
                        continue
                    yield f"data: {delta}\\n\\n".encode()
                    state["delivered"] += 1
                else:
                    state["completed"] = True
            else:
                for i in range(n_out):
                    if await request.is_disconnected():
                        state["disconnect_ns"] = time.perf_counter_ns()
                        break
                    word = mock._det_int(f"{req.prompt}:{i}", seed, 0, 21)  # noqa: SLF001 - deterministic index
                    yield f"data: token_{word}\\n\\n".encode()
                    state["delivered"] += 1
                    if delay_s:
                        await asyncio.sleep(delay_s)
                else:
                    state["completed"] = True
            yield b"data: [DONE]\\n\\n"
'''

OLD_M2 = '''    input_tokens, output_tokens, reasoning_tokens = _server_truth(req.prompt, seed)
    true_usage = Usage(input_tokens=input_tokens, output_tokens=output_tokens, reasoning_tokens=reasoning_tokens)
'''

NEW_M2 = '''    upstream_raw = None
    if req.generator == "real":
        # Ground truth is the serving stack's OWN usage record: a real BPE prompt count,
        # whatever the model actually emitted, and a real prefix-cache split. SmolLM2
        # reports no reasoning tokens, so that category is genuinely 0 here rather than a
        # deterministic stand-in -- which makes the K2 `drop_reasoning` manipulation
        # inert against this stack. That is reported, not hidden.
        _text, ru = await real_server.complete(req.prompt, seed, req.max_tokens)
        input_tokens, output_tokens, reasoning_tokens = ru.input_tokens, ru.output_tokens, 0
        upstream_raw = ru.raw
        true_usage = Usage(input_tokens=input_tokens, output_tokens=output_tokens,
                           cached_input_tokens=ru.cached_input_tokens, reasoning_tokens=0)
    else:
        input_tokens, output_tokens, reasoning_tokens = _server_truth(req.prompt, seed)
        true_usage = Usage(input_tokens=input_tokens, output_tokens=output_tokens, reasoning_tokens=reasoning_tokens)
'''

if OLD_GEN in s:
    s = s.replace(OLD_GEN, NEW_GEN, 1)
    changed.append("M1 stream")
if OLD_M2 in s:
    s = s.replace(OLD_M2, NEW_M2, 1)
    changed.append("M2 truth")

p.write_text(s, encoding="utf-8")
print("patched:", ", ".join(changed) if changed else "nothing (already applied)")
