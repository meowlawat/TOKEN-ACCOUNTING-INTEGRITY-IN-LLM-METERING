"""M2 attack harness — usage-record under-reporting under a dishonest client.

The client sends a named manipulation strategy (the server applies it to the true
usage to form the declared usage vector — equivalent to a client that computed the
manipulated vector itself). Whether it pays off depends on the trial's
usage-authority architecture.

ETHICS: local testbed only.
"""

from __future__ import annotations

import uuid

import httpx


async def send(
    client: httpx.AsyncClient, api_key: str, prompt: str, seed: int, trial_id: str, manipulation: str
) -> dict:
    request_id = uuid.uuid4().hex
    resp = await client.post(
        "/m2/complete",
        headers={"X-API-Key": api_key},
        json={"prompt": prompt, "seed": seed, "trial_id": trial_id,
              "request_id": request_id, "manipulation": manipulation},
    )
    resp.raise_for_status()
    return resp.json()
