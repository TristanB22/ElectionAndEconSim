#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ActionLedger:
    def __init__(self, path: str = "logs/action_ledger.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, now: datetime, seed: Optional[int], agent_id: str, action: str, params: Dict[str, Any], events: List[Dict[str, Any]], journal: List[Dict[str, Any]]) -> None:
        rec = {
            "ts": now.isoformat(),
            "seed": seed,
            "agent_id": agent_id,
            "action": action,
            "params": params,
            "events": events,
            "journal": journal,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def read_all(self) -> List[Dict[str, Any]]:
        """Reads all records from the ledger."""
        if not self.path.exists():
            return []
        records = []
        with self.path.open('r', encoding='utf-8') as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not parse ledger line: {line.strip()} - {e}")
        return records


