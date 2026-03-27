"""Minimal Flask dashboard scaffold for the KHIS toolkit."""

from __future__ import annotations

from flask import Flask, jsonify


def create_app() -> Flask:
    """Create the Flask application used for local and deployed demos."""
    app = Flask(__name__)

    @app.get("/")
    def index():
        """Return a simple status payload for the dashboard scaffold."""
        return jsonify(
            {
                "project": "khis-toolkit",
                "status": "scaffold-ready",
                "message": "Dashboard scaffold created. Build analytics views next.",
            }
        )

    return app


app = create_app()
