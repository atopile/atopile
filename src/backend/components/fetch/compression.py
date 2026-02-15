from __future__ import annotations

import hashlib
import json
from typing import Any

import zstd


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compress_zstd(data: bytes, *, level: int = 10) -> bytes:
    return zstd.compress(data, level)


def decompress_zstd(data: bytes) -> bytes:
    return zstd.decompress(data)


def canonicalize_json_obj(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonicalize_json_bytes(data: bytes) -> bytes:
    return canonicalize_json_obj(json.loads(data.decode("utf-8")))


def compare_bytes(expected: bytes, actual: bytes) -> bool:
    return expected == actual


def compare_json_semantic(expected: bytes, actual: bytes) -> bool:
    return json.loads(expected.decode("utf-8")) == json.loads(actual.decode("utf-8"))


def verify_round_trip_bytes(raw: bytes, compressed: bytes) -> bool:
    return compare_bytes(raw, decompress_zstd(compressed))


def test_zstd_round_trip_preserves_bytes() -> None:
    raw = b"example payload"
    compressed = compress_zstd(raw)
    assert verify_round_trip_bytes(raw, compressed)
    assert sha256_hex(raw) == sha256_hex(decompress_zstd(compressed))


def test_canonicalize_json_is_stable() -> None:
    first = b'{"b":2,"a":1}'
    second = b'{"a":1,"b":2}'
    assert canonicalize_json_bytes(first) == canonicalize_json_bytes(second)
    assert compare_json_semantic(first, second)
