"""Un vrai serveur MCP (le jumeau Python, en HTTP) pour les tests de la boucle."""

import socket
import threading
import time
from collections.abc import Iterator

import pytest
import uvicorn

from exp001_mcp_server.server import create_server


@pytest.fixture(scope="session")
def server_url(pytestconfig) -> Iterator[str]:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    app = create_server(pytestconfig.rootpath / "domains/magasin/data/v1").streamable_http_app(
        host="127.0.0.1"
    )
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/mcp"
    server.should_exit = True
    thread.join(timeout=5)
