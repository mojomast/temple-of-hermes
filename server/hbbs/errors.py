"""Structured HBBS/1 errors.

The wire format keeps the flat ``ok``/``error``/``code``/``fix`` shape used by
the rest of the Hermes tooling, and mirrors the machine-readable code inside
``details`` for clients that prefer a nested error object.
"""

from __future__ import annotations

from typing import Any


class BBS1Error(Exception):
    """A structured HBBS/1 error.

    ``code`` and ``message`` are server-controlled. User content, tokens,
    endpoints, and paths must never be interpolated into either value.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)
        self.field = field
        self.retry_after = retry_after
        self.details = dict(details or {})

    def error_object(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.field is not None:
            error["field"] = self.field
        if self.retry_after is not None:
            error["retry_after"] = max(1, min(86_400, int(self.retry_after)))
        if self.details:
            error["details"] = {key: value for key, value in list(self.details.items())[:8]}
        return error

    def envelope(self, command: str) -> dict[str, Any]:
        return {"v": 1, "ok": False, "command": command, "error": self.error_object()}


class HBBSError(Exception):
    """An error that is safe to return to a client."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        *,
        fix: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = int(status)
        self.code = str(code)
        self.message = str(message)
        self.fix = fix
        self.details = details or {}

    def envelope(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "ok": False,
            "data": None,
            "error": self.message,
            "code": self.code,
            "fix": self.fix,
            "details": dict(self.details),
        }
        if self.details:
            # A nested copy is useful for clients that do not know HBBS/1 yet.
            body["error_object"] = {
                "code": self.code,
                "message": self.message,
                "details": dict(self.details),
            }
        return body


def bad_request(message: str, *, code: str = "invalid_request", details: dict[str, Any] | None = None) -> HBBSError:
    return HBBSError(400, code, message, fix="Correct the request and try again.", details=details)


def unauthorized(message: str = "Authentication required.", *, code: str = "unauthorized") -> HBBSError:
    return HBBSError(401, code, message, fix="Present a valid AUTH token.", details=None)


def forbidden(message: str = "Not allowed.", *, code: str = "forbidden") -> HBBSError:
    return HBBSError(403, code, message, fix="Use an account with the required role.", details=None)


def not_found(message: str = "Not found.", *, code: str = "not_found") -> HBBSError:
    return HBBSError(404, code, message, fix="Check the identifier.", details=None)


def conflict(message: str, *, code: str = "conflict", details: dict[str, Any] | None = None) -> HBBSError:
    return HBBSError(409, code, message, fix="Choose another value or resolve the existing resource.", details=details)


def too_large(message: str = "Request body is too large.") -> HBBSError:
    return HBBSError(413, "payload_too_large", message, fix="Send a smaller request.")


def unsupported_media(message: str = "Content-Type must be application/json.") -> HBBSError:
    return HBBSError(415, "unsupported_media_type", message, fix="Send JSON with Content-Type: application/json.")


def rate_limited(retry_after: int, *, action: str) -> HBBSError:
    return HBBSError(
        429,
        "rate_limited",
        f"Rate limit exceeded for {action}.",
        fix="Wait, then retry.",
        details={
            "retry_after_seconds": max(0, int(retry_after)),
            "retry_after": max(0, int(retry_after)),
            "action": action,
        },
    )
