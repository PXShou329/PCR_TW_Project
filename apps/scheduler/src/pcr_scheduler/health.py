"""Dependency-free liveness/readiness endpoint."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Callable

from .state import HeartbeatState


class HealthServer:
    def __init__(self, host: str, port: int, state: HeartbeatState) -> None:
        self._state = state
        self._server = ThreadingHTTPServer((host, port), self._handler_factory())
        self._thread = Thread(
            target=self._server.serve_forever,
            name="scheduler-health",
            daemon=True,
        )

    def _handler_factory(self) -> type[BaseHTTPRequestHandler]:
        snapshot: Callable[[], dict[str, object]] = self._state.snapshot

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
                current = snapshot()
                if self.path == "/live":
                    self._json(HTTPStatus.OK, {"status": "alive"})
                elif self.path in {"/ready", "/health"}:
                    status = HTTPStatus.OK if current["ready"] else HTTPStatus.SERVICE_UNAVAILABLE
                    self._json(status, current)
                else:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

            def _json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
                encoded = json.dumps(
                    payload, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *_args: object) -> None:
                return

        return Handler

    @property
    def address(self) -> tuple[str, int]:
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
