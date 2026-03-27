"""Lazy dashboard exports for the KHIS toolkit web application."""

from __future__ import annotations

from typing import Any

__all__ = ["app", "create_app"]


def create_app(*args: Any, **kwargs: Any):
    """Import and return the Flask app factory only when needed."""
    from .app import create_app as _create_app

    return _create_app(*args, **kwargs)


def __getattr__(name: str):
    """Resolve the module-level ``app`` export lazily."""
    if name == "app":
        from .app import app as _app

        return _app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
