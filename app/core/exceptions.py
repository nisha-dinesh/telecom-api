# app/core/exceptions.py
# Job of this file: our own error types. Services RAISE them; one central
# handler in main.py (added later) catches them and returns a clean JSON reply.


class AppError(Exception):
    """Parent of all our errors. Carries an HTTP status code and a message."""

    status_code: int = 500
    default_message: str = "Something went wrong"

    def __init__(self, message: str | None = None):
        # Use the given message, or the class's default one.
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(AppError):
    """The thing the client asked for does not exist."""

    status_code = 404
    default_message = "Resource not found"


class ConflictError(AppError):
    """It would create a duplicate (same email, phone number, circle name...)."""

    status_code = 409
    default_message = "Resource already exists"


class ForbiddenError(AppError):
    """Logged in, but not allowed to do this (wrong role or someone else's data)."""

    status_code = 403
    default_message = "You are not allowed to do this"


class UnauthorizedError(AppError):
    """Not logged in, wrong password, or the token is missing/expired."""

    status_code = 401
    default_message = "Invalid or missing credentials"


class BusinessRuleError(AppError):
    """The request is well-formed but breaks a business rule
    (for example: recharging a ported-out number)."""

    status_code = 422
    default_message = "Request breaks a business rule"