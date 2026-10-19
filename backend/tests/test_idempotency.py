"""The bounded result cache behind scan_id.

Phase 1 has no database, so this is an in-memory map that does not survive a
restart. That is a deliberate limit, not an oversight: the client is the
durable record and dedupes locally too, and this only has to cover the common
case of a retry seconds after a dropped connection.
"""

import pytest

from app.services.idempotency import ResultCache


def test_a_stored_result_comes_back() -> None:
    cache = ResultCache(max_entries=4)
    cache.put("a", {"scan_id": "a", "value": 1})

    assert cache.get("a") == {"scan_id": "a", "value": 1}
    assert cache.get("b") is None


def test_the_oldest_entry_is_dropped_when_full() -> None:
    cache = ResultCache(max_entries=3)
    for key in "abcd":
        cache.put(key, {"scan_id": key})

    assert cache.get("a") is None
    assert [cache.get(key)["scan_id"] for key in "bcd"] == ["b", "c", "d"]
    assert len(cache) == 3


def test_reading_an_entry_keeps_it_alive() -> None:
    # A client retrying one scan repeatedly must not have its own result
    # evicted by its own retries.
    cache = ResultCache(max_entries=3)
    for key in "abc":
        cache.put(key, {"scan_id": key})

    cache.get("a")
    cache.put("d", {"scan_id": "d"})

    assert cache.get("a") is not None
    assert cache.get("b") is None


def test_storing_the_same_key_twice_replaces_rather_than_grows() -> None:
    cache = ResultCache(max_entries=2)
    cache.put("a", {"scan_id": "a", "v": 1})
    cache.put("a", {"scan_id": "a", "v": 2})

    assert len(cache) == 1
    assert cache.get("a")["v"] == 2


def test_a_stored_result_cannot_be_mutated_through_the_cache() -> None:
    # The endpoint hands the stored dict straight to the serialiser. If a
    # caller could mutate it, the next replay would return the mutation.
    cache = ResultCache(max_entries=2)
    cache.put("a", {"scan_id": "a", "prediction": {"confidence": 0.9}})

    first = cache.get("a")
    first["prediction"]["confidence"] = 0.1

    assert cache.get("a")["prediction"]["confidence"] == 0.9


def test_a_cache_with_no_room_stores_nothing_rather_than_failing() -> None:
    # Reachable by setting idempotency_cache_size to 0 to turn the feature off.
    cache = ResultCache(max_entries=0)
    cache.put("a", {"scan_id": "a"})

    assert cache.get("a") is None
    assert len(cache) == 0


def test_a_negative_size_is_refused() -> None:
    with pytest.raises(ValueError):
        ResultCache(max_entries=-1)
