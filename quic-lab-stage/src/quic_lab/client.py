"""QUIC echo client with handshake and per-message RTT measurements.

Run it repeatedly against the same server (`--runs N`) to see TLS 1.3
session resumption shorten later handships; the client stores the
session ticket in memory and offers it on every subsequent connection.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
import time

from aioquic.asyncio import QuicConnectionProtocol, connect
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import ConnectionTerminated, StreamDataReceived

from .protocol import FrameDecoder, encode_frame
from .server import ALPN

logger = logging.getLogger("quic-lab.client")


class EchoClientProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._decoders: dict[int, FrameDecoder] = {}
        self._waiters: dict[int, asyncio.Future] = {}

    def quic_event_received(self, event) -> None:
        if isinstance(event, StreamDataReceived):
            decoder = self._decoders.setdefault(event.stream_id, FrameDecoder())
            try:
                frames = decoder.feed(event.data)
            except ValueError as exc:
                logger.error("malformed frame from server: %s", exc)
                return
            for payload in frames:
                waiter = self._waiters.pop(event.stream_id, None)
                if waiter is not None and not waiter.done():
                    waiter.set_result(payload)
        elif isinstance(event, ConnectionTerminated):
            error = ConnectionError(
                f"connection closed (code={event.error_code}, {event.reason_phrase})"
            )
            for waiter in self._waiters.values():
                if not waiter.done():
                    waiter.set_exception(error)

    async def echo(self, payload: bytes) -> bytes:
        """Send one framed message on a fresh stream; resolve with the echo."""
        stream_id = self._quic.get_next_available_stream_id()
        loop = asyncio.get_running_loop()
        waiter = loop.create_future()
        self._waiters[stream_id] = waiter
        self._quic.send_stream_data(stream_id, encode_frame(payload), end_stream=False)
        self.transmit()
        return await waiter


async def run_client(
    host: str = "127.0.0.1",
    port: int = 4433,
    cafile: str | None = None,
    runs: int = 1,
    message_count: int = 5,
    size: int = 64,
    timeout: float = 5.0,
) -> int:
    """Run `runs` connections; return 0 when every echo matched."""
    ticket = None
    all_ok = True

    for run in range(1, runs + 1):
        configuration = QuicConfiguration(is_client=True, alpn_protocols=[ALPN])
        if cafile:
            configuration.load_verify_locations(cafile)
        else:
            configuration.verify_mode = ssl.CERT_NONE  # self-signed lab cert
        if ticket is not None:
            configuration.session_ticket = ticket

        def save_ticket(t) -> None:
            nonlocal ticket
            ticket = t

        start = time.perf_counter()
        async with connect(
            host,
            port,
            configuration=configuration,
            create_protocol=EchoClientProtocol,
            session_ticket_handler=save_ticket,
        ) as client:
            handshake_ms = (time.perf_counter() - start) * 1000
            resumed = ticket is not None

            rtts: list[float] = []
            for i in range(message_count):
                payload = (
                    f"run{run:02d}/msg{i:03d}/".encode() + b"x" * max(size - 16, 0)
                )
                t0 = time.perf_counter()
                echoed = await asyncio.wait_for(client.echo(payload), timeout=timeout)
                rtts.append((time.perf_counter() - t0) * 1000)
                if echoed != payload:
                    all_ok = False
                    print(f"  MISMATCH run={run} msg={i} ({len(echoed)}B echoed)")

            # Wait briefly for the server's session ticket so the next
            # connection can resume (shorter handshake).
            deadline = time.perf_counter() + 1.0
            while ticket is None and time.perf_counter() < deadline:
                await asyncio.sleep(0.05)

            avg = sum(rtts) / len(rtts) if rtts else 0.0
            print(
                f"run {run:>2} | {host}:{port} | handshake {handshake_ms:6.1f} ms"
                f" | {message_count} msgs | rtt min/avg/max"
                f" {min(rtts):.1f}/{avg:.1f}/{max(rtts):.1f} ms"
                f" | resumed ticket: {'yes' if resumed else 'no'}"
            )

    print("all echoes matched" if all_ok else "ECHO MISMATCHES DETECTED")
    return 0 if all_ok else 1
