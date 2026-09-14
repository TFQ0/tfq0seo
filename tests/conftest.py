"""Deterministic HTTP fixtures. The suite must never contact public sites."""

import ipaddress
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


@pytest.fixture(autouse=True)
def isolate_network_and_configuration(monkeypatch):
    for name in os.environ:
        if name.startswith('TFQ0SEO_'):
            monkeypatch.delenv(name)
    original = socket.socket.connect
    original_ex = socket.socket.connect_ex

    def check(address):
        if isinstance(address, tuple):
            host = address[0]
            if host != 'localhost' and not ipaddress.ip_address(host).is_loopback:
                raise AssertionError('Tests may connect only to loopback addresses')

    def connect(sock, address):
        check(address)
        return original(sock, address)

    def connect_ex(sock, address):
        check(address)
        return original_ex(sock, address)

    monkeypatch.setattr(socket.socket, 'connect', connect)
    monkeypatch.setattr(socket.socket, 'connect_ex', connect_ex)


@pytest.fixture
def http_site():
    """Route map values are (status, headers, body); no implicit charset."""
    routes, requests = {}, []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            status, headers, body = routes.get(self.path, (404, {}, 'Not found'))
            body = body.encode('utf-8') if isinstance(body, str) else body
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:' + str(server.server_port), routes, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
