from __future__ import annotations

import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlparse

from node_health_watcher.state import HealthState

logger = logging.getLogger(__name__)


def make_handler(health_state: HealthState) -> type[BaseHTTPRequestHandler]:
    class NodeHealthHandler(BaseHTTPRequestHandler):
        server_version = "node-health-watcher"

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/api/v1/node-health":
                self._write_json(health_state.snapshot())
                return
            if path == "/metrics":
                self._write_text(health_state.render_metrics(), content_type="text/plain; version=0.0.4")
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            logger.debug("api %s", format % args)

        def _write_json(self, payload: dict) -> None:
            body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _write_text(self, payload: str, content_type: str) -> None:
            body = payload.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return NodeHealthHandler


def start_api_server(health_state: HealthState, host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), make_handler(health_state))
    thread = Thread(target=server.serve_forever, name="nhw-api", daemon=True)
    thread.start()
    logger.info("Node Health Watcher API listening on %s:%d", host, port)
    return server
