"""OpenAPI contract check.

Each service must expose the routes its story promises. Fails (non-zero exit) if
a route is missing, so a breaking API change cannot land unnoticed.

Run with: uv run python scripts/check_contract.py
"""

from __future__ import annotations

from agentflow.api import make_app as agentflow_app
from audit_log.api import make_app as audit_app
from auth.api import make_app as auth_app
from pii_proxy.api import make_app as pii_app

EXPECTED: dict[str, list[str]] = {
    "audit": ["/audit/append", "/audit/verify"],
    "auth": ["/auth/token", "/auth/verify", "/auth/.well-known/jwks.json"],
    "pii": ["/pii/mask", "/pii/vault", "/pii/receipt/{receipt}"],
    "agentflow": ["/chat/session", "/chat/whoami", "/chat/account", "/chat/send"],
}


def main() -> None:
    apps = {
        "audit": audit_app(),
        "auth": auth_app(),
        "pii": pii_app(),
        "agentflow": agentflow_app(),
    }
    failed = False
    for name, app in apps.items():
        paths = set(app.openapi()["paths"])
        missing = [p for p in EXPECTED[name] if p not in paths]
        if missing:
            failed = True
            print(f"{name}: MISSING routes {missing}")
        else:
            print(f"{name}: OK ({len(paths)} routes)")
    if failed:
        raise SystemExit("contract check failed")
    print("contract OK")


if __name__ == "__main__":
    main()
