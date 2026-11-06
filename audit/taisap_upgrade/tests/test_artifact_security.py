from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[3]


def read(name: str) -> str:
    return (REPO / name).read_text(encoding="utf-8")


def test_local_compose_is_loopback_only_and_requires_secrets() -> None:
    compose = read("docker-compose.yml")
    assert '"127.0.0.1:5432:5432"' in compose
    assert '"127.0.0.1:6379:6379"' in compose
    assert '"127.0.0.1:8000:8000"' in compose
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in compose
    assert "--requirepass" in compose
    assert "${REDIS_PASSWORD:?" in compose
    assert "CLASS6_CREDIT_RACE: ${CLASS6_CREDIT_RACE:-hardened}" in compose
    assert "POSTGRES_PASSWORD: postgres" not in compose


def test_alternate_local_topologies_publish_only_gateway_on_loopback() -> None:
    for name, port in (
        ("docker-compose.multiworker.yml", "8001"),
        ("docker-compose.distributed.yml", "8002"),
    ):
        compose = read(name)
        assert f'"127.0.0.1:{port}:80"' in compose
        assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in compose
        assert "${REDIS_PASSWORD:?" in compose
        assert "CLASS6_CREDIT_RACE: ${CLASS6_CREDIT_RACE:-hardened}" in compose


def test_two_machine_profile_has_no_hard_coded_public_plaintext_urls() -> None:
    host_a = read("docker-compose.machineA.yml")
    host_b = read("docker-compose.machineB.yml")
    assert "HOSTB_PUBLIC_IP" not in host_a
    assert "DATABASE_URL: ${MACHINE_A_DATABASE_URL:?" in host_a
    assert "REDIS_URL: ${MACHINE_A_REDIS_URL:?" in host_a
    assert '"127.0.0.1:8000:8000"' in host_a
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in host_b
    assert "${REDIS_PASSWORD:?" in host_b
    assert "${HOSTB_BIND_IP:?" in host_b


def test_application_defaults_to_hardened_posture() -> None:
    config = read("app/config.py")
    assert "class6_credit_race: Mode = Mode.hardened" in config


def test_worker_instrumentation_scopes_request_id_to_account() -> None:
    worker = read("app/accounting/worker_main.py")
    assert "MRecord.account_id == ev.account_id" in worker


def test_env_example_does_not_ship_default_credentials() -> None:
    example = read(".env.example")
    assert "postgres:postgres" not in example
    assert "REDIS_PASSWORD=" in example
    assert "POSTGRES_PASSWORD=" in example


def test_settlement_replay_is_claimed_once_and_cleanup_closes_redis() -> None:
    models = read("app/models/models.py")
    ledger = read("app/accounting/ledger.py")
    worker = read("app/accounting/worker_main.py")
    assert "event_id: Mapped[str] = mapped_column(String(64), unique=True" in models
    assert 'OutboxEvent.status == "pending"' in ledger
    assert '.values(status="applied"' in ledger
    assert "await redis_client.aclose()" in worker


def test_hardened_completion_refunds_when_generation_fails() -> None:
    main = read("app/main.py")
    hardened = main.split("async def _complete_hardened", 1)[1]
    assert "except Exception:" in hardened
    assert "await debit_ops.refund_hardened" in hardened
    assert "await session.commit()" in hardened
