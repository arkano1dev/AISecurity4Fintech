from __future__ import annotations

from audit_log.chain import canonical_json, compute_hash


def test_hash_is_hex_sha256() -> None:
    value = compute_hash("0" * 64, {"q": "hi"})
    assert len(value) == 64
    assert value.isalnum()


def test_prev_hash_of_first_is_zeros() -> None:
    assert canonical_json({"q": "hi"}) == '{"q":"hi"}'


def test_chain_links_are_consistent() -> None:
    first = compute_hash("0" * 64, {"q": "hi"})
    second = compute_hash(first, {"q": "bye"})
    assert first != second


def test_canonical_json_order_independence() -> None:
    left = canonical_json({"b": 2, "a": 1})
    right = canonical_json({"a": 1, "b": 2})
    assert left == right
