"""A bounded, in-memory map from scan_id to the result it produced.

`scan_id` is the idempotency key for both endpoints (docs/DESIGN.md section
8.3). A dropped connection on a mountain plot means retries are normal, and a
retry must not produce a second diagnosis or a second history entry.

**This does not survive a restart, and that is deliberate for Phase 1**: there
is no database. The client is the durable record and dedupes locally as well.
This covers the common case of a retry seconds after a dropped connection,
which is the case that actually happens.

Least-recently-used eviction, because the entry a client is retrying is the
entry it reads, so reading has to keep it alive.
"""

from __future__ import annotations

import copy
from collections import OrderedDict
from typing import Any


class ResultCache:
    """Recently completed results, keyed by scan_id, oldest evicted first."""

    def __init__(self, *, max_entries: int) -> None:
        if max_entries < 0:
            raise ValueError(f"max_entries must not be negative, got {max_entries}")
        self._max_entries = max_entries
        self._entries: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, scan_id: str) -> dict[str, Any] | None:
        """The stored result, or None. A hit becomes the most recent entry.

        Returns a deep copy: the caller hands this to the serialiser and may
        add fields to it, and a mutation leaking back would change what every
        later replay returns.
        """
        stored = self._entries.get(scan_id)
        if stored is None:
            return None
        self._entries.move_to_end(scan_id)
        return copy.deepcopy(stored)

    def put(self, scan_id: str, result: dict[str, Any]) -> None:
        """Store a result, evicting the least recently used if full."""
        if self._max_entries == 0:
            return
        self._entries[scan_id] = copy.deepcopy(result)
        self._entries.move_to_end(scan_id)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)
