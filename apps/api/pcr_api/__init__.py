"""FastAPI application package for the PCR TW read-only strategy API."""

from typing import Any


def create_app(*args: Any, **kwargs: Any) -> Any:
    """Load the application factory without side effects on submodule imports."""

    from .main import create_app as factory

    return factory(*args, **kwargs)

__all__ = ["create_app"]
