"""Wire framing shared by the QUIC lab server and client.

Every application message travels inside a QUIC stream as one frame:

    +--------+-------------------+
    | length |      payload      |
    | 4 B BE |   `length` bytes  |
    +--------+-------------------+

`length` is a big-endian unsigned 32-bit integer. Frames larger than
MAX_FRAME_SIZE are rejected so a malformed peer cannot exhaust memory.
"""

from __future__ import annotations

import struct

HEADER = struct.Struct("!I")
MAX_FRAME_SIZE = 1 << 20  # 1 MiB


def encode_frame(payload: bytes) -> bytes:
    """Return one wire frame carrying `payload`."""
    if not payload:
        raise ValueError("cannot encode an empty payload")
    if len(payload) > MAX_FRAME_SIZE:
        raise ValueError(
            f"payload of {len(payload)} bytes exceeds MAX_FRAME_SIZE ({MAX_FRAME_SIZE})"
        )
    return HEADER.pack(len(payload)) + payload


class FrameDecoder:
    """Incremental decoder: feed raw stream bytes, get complete frames."""

    def __init__(self) -> None:
        self._buffer = b""

    def feed(self, data: bytes) -> list[bytes]:
        """Append `data` and return every frame that is now complete."""
        self._buffer += data
        frames: list[bytes] = []
        while True:
            if len(self._buffer) < HEADER.size:
                break
            (length,) = HEADER.unpack_from(self._buffer)
            if length == 0 or length > MAX_FRAME_SIZE:
                raise ValueError(f"invalid frame length {length}")
            end = HEADER.size + length
            if len(self._buffer) < end:
                break
            frames.append(self._buffer[HEADER.size : end])
            self._buffer = self._buffer[end:]
        return frames
