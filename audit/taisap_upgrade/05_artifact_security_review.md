# Artifact security review

Date: 2026-11-06

Scope: local reproducibility and the dormant two-machine profiles. No service was started,
no external host was contacted, and no network target was probed. Static findings were
confirmed against configuration and code; all Compose files were parsed with
`docker compose config --quiet` using temporary non-production values.

## Confirmed findings and changes

### S1 — Published services and default credentials (fixed)

The primary Compose file published PostgreSQL, Redis, and the gateway on every host
interface, used `postgres:postgres`, and ran Redis without authentication. The alternate
topologies repeated the credentials and exposed their gateway proxies on every interface.
The application also started in the intentionally vulnerable B0 posture by default.

The local profiles now:

- bind all published ports to `127.0.0.1`;
- require explicit PostgreSQL and Redis secrets via Compose's `:?` fail-closed syntax;
- enable Redis password authentication and append-only persistence;
- pass authenticated connection URLs only inside the Compose network; and
- default B0 to `hardened`, while preserving `CLASS6_CREDIT_RACE=vulnerable` as an
  explicit experimental selection and preserving the runtime A/B endpoint.

The example environment file contains blank secret/URL fields rather than working default
credentials. Secrets containing URL-special characters must be URL-encoded.

### S2 — Unsafe two-machine connection defaults (fixed as a launch gate)

The Host A profile constructed plaintext PostgreSQL and Redis URLs to a public IP with
default credentials. An IP allowlist does not provide transport encryption or service
authentication. The profile now refuses to render unless the operator supplies complete
`MACHINE_A_DATABASE_URL` and `MACHINE_A_REDIS_URL` values. Its documentation requires
service TLS or an authorized SSH tunnel. Host B requires explicit credentials and an
explicit private/tunnel bind address.

This change is a fail-closed launch gate, not a claim that TLS was configured or tested.
E4 remains unexecuted and requires human approval. The Azure helper scripts have not been
certified against the new gate and must not be used until an operator supplies and verifies
the tunnel/TLS setup.

### S3 — Cross-tenant request-ID join (fixed)

Optional worker instrumentation looked up an `MRecord` using only the client-supplied
`request_id`. Two accounts may legally choose the same value, allowing timestamps from one
tenant's settlement event to be written to another tenant's audit row. The lookup now uses
both `account_id` and `request_id`. The associated comment was also corrected: the durable
outbox and record commit precede Redis emission in the current implementation.

## Existing controls independently checked

- Settlement replay suppression uses a unique random `event_id` and a transactional
  `pending -> applied` claim coupled to the debit. A duplicate claim returns without a
  second debit.
- The standalone worker closes its Redis client in `finally` on normal cancellation or
  signal-driven shutdown.
- The hardened synchronous completion path refunds and commits the reservation if
  generation raises before completion.

These are source-level checks in this phase. E3's fault matrix was not executed because
the Docker daemon was unavailable.

## Deliberate experimental exposure versus safe default

The vulnerable B0, M1, M2, and async variants remain in the artifact because they are the
experimental independent variables. They are not removed or silently changed. Safe launch
defaults reduce accidental exposure; experiments must select a vulnerable posture
explicitly and should run only on the loopback-bound local testbed.

## Unresolved security limitations

- Administrative setup/configuration routes have no separate administrator credential.
  Loopback binding is the current boundary. Do not publish the gateway or place it behind
  an untrusted reverse proxy without adding authentication and authorization.
- Client `request_id` values are correlation identifiers, not general API idempotency
  keys. Replaying a completed synchronous request can repeat service and billing. The
  misleading model comment was corrected, but production-grade idempotency would require
  a tenant-scoped uniqueness constraint, response-state design, and migration testing.
- Secrets are passed as container environment values and may be visible to local Docker
  administrators. Docker secrets or an external secret manager are out of scope for this
  local artifact.
- Cross-host TLS/tunnel operation has not been exercised. Required URLs prevent the old
  insecure default but do not validate a user-supplied URL's certificate or tunnel.
- No container image digest pinning or vulnerability scan was performed in this offline,
  daemon-unavailable phase.

## Verification

```text
python -m pytest audit/taisap_upgrade/tests/test_artifact_security.py -q
8 passed

python -m pytest -q
27 passed

docker compose -f <each of five compose files> config --quiet
PASS for docker-compose.yml, docker-compose.multiworker.yml,
docker-compose.distributed.yml, docker-compose.machineA.yml, and
docker-compose.machineB.yml
```

The Compose validation used temporary values only and started no containers.
