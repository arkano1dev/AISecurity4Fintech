"""End-to-end AgentFlow demo.

Starts auth-service, audit-log, and agentflow; logs in as alice; routes a
retrieval message and an action message; shows the 403 on a token without the
action scope; and prints the audit-chain verdict.

Run with: uv run python scripts/demo_agentflow.py
"""

from __future__ import annotations

import subprocess
import sys
import time

import httpx

SERVICES = [
    ("auth.api:make_app", 8000),
    ("audit_log.api:make_app", 8101),
    ("agentflow.api:make_app", 8004),
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


def main() -> None:
    processes = [_start(module, port) for module, port in SERVICES]
    try:
        _wait_ready("http://localhost:8000/docs")
        _wait_ready("http://localhost:8101/audit/verify")
        _wait_ready("http://localhost:8004/docs")

        login = httpx.post(
            "http://localhost:8004/chat/session",
            json={"username": "support", "password": "support-pass"},
            timeout=10.0,
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        for question in ("what is the wire transfer threshold?", "please freeze my card"):
            print(f"\n> {question}")
            response = httpx.post(
                "http://localhost:8004/chat/send",
                json={"message": question},
                headers=headers,
                timeout=10.0,
            )
            response.raise_for_status()
            body = response.json()
            print(f"  intent={body['intent']} agent={body['agent']} result={body['result']}")

        # A token without agent:action must be refused.
        bob = httpx.post(
            "http://localhost:8004/chat/session",
            json={"username": "bob", "password": "correct-horse-2"},
            timeout=10.0,
        )
        bob.raise_for_status()
        bob_headers = {"Authorization": f"Bearer {bob.json()['access_token']}"}
        denied = httpx.post(
            "http://localhost:8004/chat/send",
            json={"message": "freeze my card"},
            headers=bob_headers,
            timeout=10.0,
        )
        print(
            f"\n> freeze my card (as bob, no agent:action) -> {denied.status_code} "
            f"{denied.json()['detail']}"
        )

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
