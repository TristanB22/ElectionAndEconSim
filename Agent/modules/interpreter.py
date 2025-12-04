#!/usr/bin/env python3
"""
Interpreter for typed actions.

- dry_run: validate schema/permissions/preconditions, return estimate
- commit: revalidate, apply effects to produce domain events, atomically:
  * append events to event bus
  * map events to accounting journal lines (placeholder hook)
  * write action record to action ledger

All world mutations must occur via reducers that consume emitted events.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import jsonschema  # type: ignore
    _HAS_JSONSCHEMA = True
except Exception:
    _HAS_JSONSCHEMA = False

from Agent.modules.actions.registry import ActionRegistry, ActionSpec


WorldT = Any


@dataclass
class DryRunResult:
    ok: bool
    estimate: Optional[Dict[str, float]] = None
    errors: Optional[List[str]] = None


class Interpreter:
    def __init__(self, registry: ActionRegistry, world: WorldT, event_bus: Any, accounting: Any, ledger: Any, rng_seed: Optional[int] = None) -> None:
        self.registry = registry
        self.world = world
        self.event_bus = event_bus
        self.accounting = accounting
        self.ledger = ledger
        self.rng_seed = rng_seed

    def _validate_schema(self, schema: Dict[str, Any], params: Dict[str, Any]) -> List[str]:
        if not _HAS_JSONSCHEMA:
            # Best-effort minimal validation
            required = schema.get("required", [])
            missing = [k for k in required if k not in params]
            return [f"Missing required param: {k}" for k in missing]
        try:
            jsonschema.validate(instance=params, schema=schema)  # type: ignore
            return []
        except Exception as e:
            return [str(e)]

    def dry_run(self, agent_id: str, action_name: str, params: Dict[str, Any], firm_id: Optional[str] = None) -> DryRunResult:
        spec: Optional[ActionSpec] = self.registry.get(action_name, firm_id)
        if spec is None:
            return DryRunResult(ok=False, errors=[f"Unknown action: {action_name}"])
        errors = self._validate_schema(spec.params_schema, params)
        if errors:
            return DryRunResult(ok=False, errors=errors)
        # TODO: permission checks (future roles system)
        for pre in spec.preconditions:
            try:
                if not pre(self.world, str(agent_id), params):
                    return DryRunResult(ok=False, errors=["precondition_failed"])
            except Exception as e:
                return DryRunResult(ok=False, errors=[f"precondition_error: {e}"])
        try:
            est = spec.estimate(self.world, str(agent_id), params)
            return DryRunResult(ok=True, estimate=est)
        except Exception as e:
            return DryRunResult(ok=False, errors=[f"estimate_error: {e}"])

    def commit(self, agent_id: str, action_name: str, params: Dict[str, Any], now: datetime, firm_id: Optional[str] = None) -> Dict[str, Any]:
        start_time = datetime.now()
        dr = self.dry_run(agent_id, action_name, params, firm_id=firm_id)
        if not dr.ok:
            return {"ok": False, "error": dr.errors}
        spec: ActionSpec = self.registry.get(action_name, firm_id)  # type: ignore
        # Generate domain events
        events = spec.effects(self.world, str(agent_id), params, now)
        # Normalize timestamps to simulation time if available
        try:
            from Environment.time_manager import get_current_simulation_timestamp
            sim_ts = get_current_simulation_timestamp()
            for evt in events:
                evt["timestamp"] = sim_ts
        except Exception:
            pass
        # Accounting mapping (optional placeholder)
        journal_lines: List[Dict[str, Any]] = []
        try:
            if self.accounting is not None and hasattr(self.accounting, "map_events_to_journal"):
                journal_lines = self.accounting.map_events_to_journal(firm_id, events, agent_id) or []
                if hasattr(self.accounting, "balanced") and not self.accounting.balanced(journal_lines):
                    return {"ok": False, "error": "unbalanced_journal"}
        except Exception as e:
            return {"ok": False, "error": f"accounting_error: {e}"}
        # Append events to event bus/queue
        try:
            if hasattr(self.event_bus, "append"):
                for evt in events:
                    self.event_bus.append(evt)
            elif hasattr(self.event_bus, "emit"):
                for evt in events:
                    self.event_bus.emit(evt)
        except Exception as e:
            return {"ok": False, "error": f"event_bus_error: {e}"}
        # Calculate execution time
        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        # Post to ledger (journal)
        try:
            if self.ledger is not None and hasattr(self.ledger, "record"):
                self.ledger.record(now, self.rng_seed, str(agent_id), action_name, params, events, journal_lines, execution_time_ms)
        except Exception as e:
            return {"ok": False, "error": f"ledger_error: {e}"}
        return {"ok": True, "events": events, "journal": journal_lines, "estimate": dr.estimate}


