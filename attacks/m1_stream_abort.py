"""M1 attack harness — stream-abort under the dishonest-client threat model.

A single client opens an SSE stream to `/m1/stream` and, after receiving
``abort_after`` tokens, closes the connection (aborts). If ``abort_after`` is None
it reads to completion. The server settles the account per the trial's commit-timing
architecture; whether the client keeps the delivered inference for free depends on
that architecture.

ETHICS: local testbed only.
"""

from __future__ import annotations

import uuid

import httpx


async def stream_and_abort(
    client: httpx.AsyncClient, api_key: str, prompt: str, seed: int, trial_id: str,
    abort_after: int | None,
) -> tuple[str, int]:
    """Return (request_id, tokens_the_client_read). abort_after=None => complete."""
    request_id = uuid.uuid4().hex
    payload = {"prompt": prompt, "seed": seed, "trial_id": trial_id, "request_id": request_id}
    read = 0
    try:
        async with client.stream("POST", "/m1/stream", headers={"X-API-Key": api_key}, json=payload) as resp:
            if abort_after is not None and abort_after <= 0:
                return request_id, 0  # abort immediately
            async for line in resp.aiter_lines():
                if line.startswith("data: token_"):
                    read += 1
                    if abort_after is not None and read >= abort_after:
                        break  # abort: exiting the context closes the connection
                elif line.startswith("data: [DONE]"):
                    break
    except httpx.HTTPError:
        pass
    return request_id, read
