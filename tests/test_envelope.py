"""Tests for the wire envelope protocol."""

import json

import pytest

from src.core.network import Envelope, PROTOCOL_VERSION, parse_envelope


def test_to_line_is_valid_json_with_all_fields() -> None:
    env = Envelope(sender_id="alice", payload="hello")
    data = json.loads(env.to_line())
    assert data == {
        "sender_id": "alice",
        "payload": "hello",
        "kind": "message",
        "version": PROTOCOL_VERSION,
    }


def test_hello_handshake_round_trip() -> None:
    env = Envelope(sender_id="alice", payload="", kind="hello")
    parsed = parse_envelope(env.to_line())
    assert parsed == env


def test_parse_rejects_garbage() -> None:
    assert parse_envelope("not json at all") is None
    assert parse_envelope("") is None
    assert parse_envelope('{"sender_id": "", "payload": "x"}') is None  # no sender
    assert parse_envelope('"just a string"') is None


def test_parse_accepts_extra_fields() -> None:
    line = json.dumps({"sender_id": "x", "payload": "y", "future_feature": True})
    env = parse_envelope(line)
    assert env is not None
    assert env.sender_id == "x"
    assert env.payload == "y"
