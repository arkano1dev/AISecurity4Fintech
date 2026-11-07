"""Integrated end-to-end demo: VaultRAG + AgentFlow together.

Starts auth-service, audit-log, pii-proxy, vaultrag, and agentflow. A loader
ingests the sample documents; a support agent routes a retrieval question (which
delegates to VaultRAG), checks a balance, and freezes a card; then the isolation
and scope guards and the audit-chain verdict are shown.

Ollama must already be running for the retrieval embedding + generation.

Run with: uv run python scripts/demo_full.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
DATA_DIR = REPO / "apps" / "vaultrag" / "data"

SERVICES = [
    ("auth.api:make_app", 8000),
    ("audit_log.api:make_app", 8101),
    ("pii_proxy.api:make_app", 8002),
    ("vaultrag.api:make_app", 8003),
    ("agentflow.api:make_app", 8004),
]

DOCUMENTS = [
    ("compliance_policy", "Compliance Policy", "compliance_policy.md"),
    ("aml_procedure", "AML Procedure", "aml_procedure.md"),
    ("support_runbook", "Support Runbook", "support_runbook.md"),
]


def _start(module: str, port: int) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            module,
            "--factory",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_ready(url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            httpx.get(url, timeout=1.0)
            return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError(f"service did not become ready: {url}")


def _token(username: str, password: str) -> str:
    response = httpx.post(
        "http://localhost:8000/auth/token",
        json={"username": username, "password": password},
        timeout=10.0,
    )
    response.raise_for_status()
    return str(response.json()["access_token"])


def main() -> None:
    processes = [_start(module, port) for module, port in SERVICES]
    try:
        _wait_ready("http://localhost:8000/docs")
        _wait_ready("http://localhost:8101/audit/verify")
        _wait_ready("http://localhost:8002/health")
        _wait_ready("http://localhost:8003/docs")
        _wait_ready("http://localhost:8004/docs")

        # 1. Ingest the sample documents as the loader.
        loader = _token("loader", "loader-pass")
        for doc_id, title, filename in DOCUMENTS:
            content = (DATA_DIR / filename).read_text(encoding="utf-8")
            response = httpx.post(
                "http://localhost:8003/vaultrag/documents",
                json={"doc_id": doc_id, "title": title, "content": content},
                headers={"Authorization": f"Bearer {loader}"},
                timeout=120.0,
            )
            response.raise_for_status()
            print(f"ingested {title}: {response.json()['chunks']} chunks")

        # 2. Route a retrieval question through AgentFlow (delegates to VaultRAG).
        support = _token("support", "support-pass")
        support_headers = {"Authorization": f"Bearer {support}"}

        questions = (
            "what is the wire transfer threshold?",
            "check my balance",
            "freeze my card",
        )
        for message in questions:
            print(f"\n> {message}")
            response = httpx.post(
                "http://localhost:8004/chat/send",
                json={"message": message},
                headers=support_headers,
                timeout=180.0,
            )
            response.raise_for_status()
            body = response.json()
            print(f"  intent={body['intent']} agent={body['agent']} result={body['result']}")

        # 3. Tenant isolation: alice can only ever read her own balance.
        alice = _token("alice", "correct-horse")
        print("\n> check bob's balance (as alice)")
        response = httpx.post(
            "http://localhost:8004/chat/send",
            json={"message": "check bob's balance"},
            headers={"Authorization": f"Bearer {alice}"},
            timeout=30.0,
        )
        response.raise_for_status()
        print(f"  result={response.json()['result']}  (alice's own balance, not bob's)")

        # 4. Scope guard: bob has no agent scopes, so an action is refused.
        bob = _token("bob", "correct-horse-2")
        print("\n> freeze my card (as bob, no agent:action)")
        denied = httpx.post(
            "http://localhost:8004/chat/send",
            json={"message": "freeze my card"},
            headers={"Authorization": f"Bearer {bob}"},
            timeout=30.0,
        )
        print(f"  -> {denied.status_code} {denied.json()['detail']}")

        verdict = httpx.get("http://localhost:8101/audit/verify", timeout=10.0).json()
        print(f"\naudit chain: valid={verdict['valid']} count={verdict['count']}")
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
