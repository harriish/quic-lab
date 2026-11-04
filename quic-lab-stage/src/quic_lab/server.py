"""A minimal QUIC echo server built on aioquic.

Each bidirectional stream is an independent request/response channel:
framed messages are echoed back on the same stream, and per-connection
stats are appended to a JSONL metrics file when the connection ends.
"""

from __future__ import annotations

import asyncio
import logging

from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import ConnectionTerminated, StreamDataReceived

from .protocol import FrameDecoder, encode_frame
from .stats import ConnectionStats, MetricsWriter

logger = logging.getLogger("quic-lab.server")
ALPN = "quic-lab/1"


class EchoServerProtocol(QuicConnectionProtocol):
    """Echo framed messages back on the stream they arrived on."""

    def __init__(self, *args, **kwargs) -> None:
        self._metrics: MetricsWriter | None = kwargs.pop("metrics", None)
        super().__init__(*args, **kwargs)
        self._decoders: dict[int, FrameDecoder] = {}
        self._stats_written = False
        self.stats = ConnectionStats(connection_id=self._quic.host_cid.hex())

    def quic_event_received(self, event) -> None:
        if isinstance(event, StreamDataReceived):
            decoder = self._decoders.setdefault(event.stream_id, FrameDecoder())
            try:
                frames = decoder.feed(event.data)
            except ValueError as exc:
                logger.warning("malformed frame on stream %d: %s", event.stream_id, exc)
                self._quic.close(error_code=1, reason_phrase="malformed frame")
                return
            for payload in frames:
                self.stats.record_in(len(payload))
                self._quic.send_stream_data(
                    event.stream_id, encode_frame(payload), end_stream=False
                )
                self.stats.record_out(len(payload))
                self.transmit()
        elif isinstance(event, ConnectionTerminated):
            logger.info(
                "connection %s closed (code=%d reason=%s)",
                self.stats.connection_id,
                event.error_code,
                event.reason_phrase,
            )
            self._write_stats()

    def connection_lost(self, exc) -> None:
        self._write_stats()
        super().connection_lost(exc)

    def _write_stats(self) -> None:
        if self._metrics is not None and not self._stats_written:
            self._metrics.write(self.stats)
            self._stats_written = True


async def run_server(
    host: str = "0.0.0.0",
    port: int = 4433,
    certfile: str = "certs/server.crt",
    keyfile: str = "certs/server.key",
    metrics_path: str = "metrics.jsonl",
) -> None:
    configuration = QuicConfiguration(is_client=False, alpn_protocols=[ALPN])
    configuration.load_cert_chain(certfile, keyfile)
    metrics = MetricsWriter(metrics_path)

    def create_protocol(*args, **kwargs) -> EchoServerProtocol:
        return EchoServerProtocol(*args, metrics=metrics, **kwargs)

    logger.info(
        "QUIC echo server listening on udp://%s:%d (alpn=%s)", host, port, ALPN
    )
    # A ticket handler is what makes the server send NEW_SESSION_TICKET
    # frames at all (see aioquic's Tls._server_handle_finished).
    await serve(
        host,
        port,
        configuration=configuration,
        create_protocol=create_protocol,
        session_ticket_handler=lambda ticket: None,
    )
    await asyncio.Future()  # serve forever
