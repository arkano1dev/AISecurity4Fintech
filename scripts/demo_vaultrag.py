"""End-to-end VaultRAG demo.

Starts the shared services (audit-log, pii-proxy, vaultrag) as local processes,
ingests the three sample documents, runs queries, and prints the audit-chain
verdict. Ollama must already be running.

Run with: uv run python scripts/demo_vaultrag.py
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
    ("audit_log.api:make_app", 8101),
    ("pii_proxy.api:make_app", 8002),
    ("vaultrag.api:make_app", 8003),
]
DOCUMENTS = [
    ("compliance_policy", "Compliance Policy", "compliance_policy.md"),
    ("aml_procedure", "AML Procedure", "aml_procedure.md"),
    ("support_runbook", "Support Runbook", "support_runbook.md"),
]
QUESTIONS = [
    "What is the wire transfer escalation threshold and who must approve it?",
    "How long are customer transaction records retained?",
    "What should an agent do when a customer reports a fraudulent charge?",
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
        _wait_ready("http://localhost:8101/audit/verify")
        _wait_ready("http://localhost:8002/health")
        _wait_ready("http://localhost:8003/docs")

        for doc_id, title, filename in DOCUMENTS:
            content = (DATA_DIR / filename).read_text(encoding="utf-8")
            response = httpx.post(
                "http://localhost:8003/vaultrag/documents",
                json={"doc_id": doc_id, "title": title, "content": content},
                timeout=120.0,
            )
            response.raise_for_status()
            print(f"ingested {title}: {response.json()['chunks']} chunks")

        for question in QUESTIONS:
            print(f"\nQ: {question}")
            response = httpx.post(
                "http://localhost:8003/vaultrag/query",
                json={"question": question},
                timeout=180.0,
            )
            response.raise_for_status()
            body = response.json()
            print(f"A: {body['answer'].strip()}")
            print("Citations:")
            for citation in body["citations"]:
                snippet = citation["text"].replace("\n", " ")[:110]
                print(f"  - {citation['doc_id']}: {snippet}")

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
