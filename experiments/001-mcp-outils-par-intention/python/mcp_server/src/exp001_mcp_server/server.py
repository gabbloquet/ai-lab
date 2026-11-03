import argparse
import logging
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from exp001_mcp_server.catalog.infra.inbound.mcp.intent.intent_tools import register_intent_tools
from exp001_mcp_server.catalog.infra.outbound.data.catalog_loader import load_catalog

DEFAULT_DATA_DIR = Path("domains/magasin/data/v1")
# Le serveur Java écoute sur 8080 : le jumeau prend le port suivant pour tourner à côté.
DEFAULT_PORT = 8081


def create_server(data_dir: Path) -> MCPServer:
    server = MCPServer(name="magasin-mcp", version="0.1.0")
    register_intent_tools(server, load_catalog(data_dir))
    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Jumeau Python de la variante intent de la 001")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    # 127.0.0.1 : le SDK active alors la validation des en-têtes Origin et Host.
    create_server(args.data_dir).run("streamable-http", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
