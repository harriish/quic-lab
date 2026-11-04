"""Per-connection counters and JSONL metrics output.

The server appends one JSON object per QUIC connection, which keeps the
output trivially parseable by `jq`, Prometheus file exporters, or a
CloudWatch agent — the same pattern used in production services.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ConnectionStats:
    connection_id: str
    started_at: float = field(default_factory=time.time)
    frames_in: int = 0
    frames_out: int = 0
    bytes_in: int = 0
    bytes_out: int = 0

    def record_in(self, nbytes: int) -> None:
        self.frames_in += 1
        self.bytes_in += nbytes

    def record_out(self, nbytes: int) -> None:
        self.frames_out += 1
        self.bytes_out += nbytes

    @property
    def duration_s(self) -> float:
        return round(time.time() - self.started_at, 3)

    def to_dict(self) -> dict[str, object]:
        return {
            "connection_id": self.connection_id,
            "started_at": int(self.started_at),
            "duration_s": self.duration_s,
            "frames_in": self.frames_in,
            "frames_out": self.frames_out,
            "bytes_in": self.bytes_in,
            "bytes_out": self.bytes_out,
        }


class MetricsWriter:
    """Append-only JSONL metrics sink."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, stats: ConnectionStats) -> None:
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(stats.to_dict(), sort_keys=True) + "\n")
