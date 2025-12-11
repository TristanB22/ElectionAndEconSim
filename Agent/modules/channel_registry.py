#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict


class ChannelRegistry:
    """
    global channel registry for active channel specs.
    comments are lowercase.
    """

    def __init__(self) -> None:
        self._specs: Dict[str, dict] = {}

    def register(self, spec: dict) -> None:
        cid = spec.get("id")
        if not cid:
            raise ValueError("channel spec missing id")
        self._specs[cid] = spec

    def get(self, channel_id: str) -> dict | None:
        return self._specs.get(channel_id)

    def list(self) -> Dict[str, dict]:
        return dict(self._specs)


# singleton instance
global_channel_registry = ChannelRegistry()

def get_global_channel_registry() -> ChannelRegistry:
    """Get the global channel registry instance."""
    return global_channel_registry


