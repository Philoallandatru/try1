from __future__ import annotations

import hmac


class PortalRunnerAuthError(PermissionError):
    pass


def verify_bearer_token(authorization: str | None, expected_token: str) -> None:
    if not expected_token:
        raise PortalRunnerAuthError("Runner token is not configured.")
    if not authorization:
        raise PortalRunnerAuthError("Missing Authorization header.")

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise PortalRunnerAuthError("Authorization header must use Bearer token.")

    supplied = authorization[len(prefix) :].strip()
    if not hmac.compare_digest(supplied, expected_token):
        raise PortalRunnerAuthError("Invalid runner token.")
