"""Core module containing exceptions and system foundation."""

from app.core.exceptions import (
    AppValidationError,
    ConfigurationError,
    ResourceNotFoundError,
    UntangleError,
    register_exception_handlers,
)

__all__ = [
    "AppValidationError",
    "ConfigurationError",
    "ResourceNotFoundError",
    "UntangleError",
    "register_exception_handlers",
]
