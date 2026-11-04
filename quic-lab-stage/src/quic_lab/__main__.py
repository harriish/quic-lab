"""CLI entry points: `python -m quic_lab server|client`."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from .client import run_client
from .server import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quic-lab",
        description="A minimal QUIC echo lab: server, client, metrics.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    server = sub.add_parser("server", help="run the QUIC echo server")
    server.add_argument("--host", default="0.0.0.0")
    server.add_argument("--port", type=int, default=4433)
    server.add_argument("--cert", default="certs/server.crt")
    server.add_argument("--key", default="certs/server.key")
    server.add_argument("--metrics", default="metrics.jsonl")
    server.add_argument("--log-level", default="INFO")

    client = sub.add_parser("client", help="run the QUIC echo client")
    client.add_argument("--host", default="127.0.0.1")
    client.add_argument("--port", type=int, default=4433)
    client.add_argument(
        "--ca",
        default=None,
        help="CA bundle to verify the server cert (default: skip verification)",
    )
    client.add_argument("--runs", type=int, default=1, help="sequential connections")
    client.add_argument("--messages", type=int, default=5)
    client.add_argument("--size", type=int, default=64, help="payload bytes")
    client.add_argument("--timeout", type=float, default=5.0)
    client.add_argument("--log-level", default="WARNING")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    if args.command == "server":
        asyncio.run(
            run_server(
                host=args.host,
                port=args.port,
                certfile=args.cert,
                keyfile=args.key,
                metrics_path=args.metrics,
            )
        )
        return 0
    return asyncio.run(
        run_client(
            host=args.host,
            port=args.port,
            cafile=args.ca,
            runs=args.runs,
            message_count=args.messages,
            size=args.size,
            timeout=args.timeout,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
