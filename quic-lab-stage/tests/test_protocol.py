"""Unit tests for the wire framing used by the QUIC lab."""

import struct

import pytest

from quic_lab.protocol import HEADER, MAX_FRAME_SIZE, FrameDecoder, encode_frame


def test_roundtrip_single_frame():
    frame = encode_frame(b"hello quic")
    assert HEADER.unpack_from(frame)[0] == len(b"hello quic")
    assert FrameDecoder().feed(frame) == [b"hello quic"]


def test_multiple_frames_in_one_feed():
    wire = encode_frame(b"one") + encode_frame(b"two") + encode_frame(b"three")
    assert FrameDecoder().feed(wire) == [b"one", b"two", b"three"]


def test_partial_feed_yields_nothing_then_completes():
    decoder = FrameDecoder()
    frame = encode_frame(b"payload")
    split = len(frame) // 2
    assert decoder.feed(frame[:split]) == []
    assert decoder.feed(frame[split:]) == [b"payload"]


def test_decode_is_stateful_across_calls():
    decoder = FrameDecoder()
    assert decoder.feed(encode_frame(b"a") + encode_frame(b"b")[:3]) == [b"a"]
    assert decoder.feed(encode_frame(b"b")[3:] + encode_frame(b"c")) == [b"b", b"c"]


def test_rejects_empty_payload():
    with pytest.raises(ValueError):
        encode_frame(b"")


def test_rejects_oversized_payload():
    with pytest.raises(ValueError):
        encode_frame(b"x" * (MAX_FRAME_SIZE + 1))


def test_decoder_rejects_zero_length_frame():
    decoder = FrameDecoder()
    with pytest.raises(ValueError):
        decoder.feed(struct.pack("!I", 0))


def test_decoder_rejects_absurd_length():
    decoder = FrameDecoder()
    with pytest.raises(ValueError):
        decoder.feed(struct.pack("!I", MAX_FRAME_SIZE + 1) + b"x" * 8)
