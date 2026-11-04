"""Unit tests for per-connection stats and the JSONL metrics sink."""

import json

from quic_lab.stats import ConnectionStats, MetricsWriter


def test_stats_counts_frames_and_bytes():
    stats = ConnectionStats(connection_id="abc123")
    stats.record_in(10)
    stats.record_in(5)
    stats.record_out(15)
    assert stats.frames_in == 2
    assert stats.bytes_in == 15
    assert stats.frames_out == 1
    assert stats.bytes_out == 15
    assert stats.duration_s >= 0


def test_stats_to_dict_shape():
    data = ConnectionStats(connection_id="cid").to_dict()
    assert data["connection_id"] == "cid"
    assert data["frames_in"] == 0
    assert data["bytes_out"] == 0
    assert isinstance(data["started_at"], int)
    assert isinstance(data["duration_s"], float)


def test_metrics_writer_appends_jsonl(tmp_path):
    path = tmp_path / "metrics.jsonl"
    writer = MetricsWriter(path)
    first = ConnectionStats(connection_id="c1")
    first.record_out(3)
    second = ConnectionStats(connection_id="c2")
    writer.write(first)
    writer.write(second)

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["connection_id"] == "c1"
    assert parsed[0]["frames_out"] == 1
    assert parsed[1]["connection_id"] == "c2"


def test_metrics_writer_creates_parent_dirs(tmp_path):
    writer = MetricsWriter(tmp_path / "nested" / "dir" / "metrics.jsonl")
    writer.write(ConnectionStats(connection_id="c1"))
    assert (tmp_path / "nested" / "dir" / "metrics.jsonl").exists()
