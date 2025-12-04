#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from Agent.modules.actions.registry import ActionRegistry, ActionSpec
from .channel_registry import global_channel_registry


@dataclass
class ChannelSpec:
    id: str
    topology: str  # dm|feed|event
    targeting: Dict[str, Any]
    costs: Dict[str, float]  # money,time,social_capital,compute
    friction: Dict[str, Any]  # signup_steps, rate_limit_per_day
    credibility_baseline: float
    latency_s: float
    caps: Dict[str, int]  # daily_slots, group_size
    diffusion: Dict[str, Any]  # homophily, tail


def _make_preconditions_for_channel(op_kind: str, spec: ChannelSpec):
    def _pre(world, agent_id: str, params: Dict[str, Any]) -> bool:
        # require membership or access flag in world.state or channel registry
        reg = global_channel_registry.get(spec.id)
        if not reg:
            return False
        # simple rate cap: check per-agent usage in params context if provided
        usage = params.get("_usage_counters", {}).get(spec.id, 0)
        cap = int(spec.friction.get("rate_limit_per_day", spec.caps.get("daily_slots", 10)))
        if usage >= cap:
            return False
        return True
    return _pre


def _estimate_for_channel(op_kind: str, spec: ChannelSpec):
    def _est(world, agent_id: str, params: Dict[str, Any]) -> Dict[str, float]:
        return {
            "time_minutes": float(spec.costs.get("time", 1.0)),
            "money": float(spec.costs.get("money", 0.0)),
        }
    return _est


def _effects_for_channel(op_kind: str, spec: ChannelSpec):
    def _eff(world, agent_id: str, params: Dict[str, Any], now) -> List[Dict[str, Any]]:
        # introduce <=5% holdout randomly at delivery time
        import random
        holdout = random.random() < 0.05
        payload = {
            "channel_id": spec.id,
            "topology": spec.topology,
            "params": {k: v for k, v in (params or {}).items() if not k.startswith("_")},
            "holdout": holdout,
        }
        if op_kind == "post":
            et = "channel_post"
        elif op_kind == "dm":
            et = "channel_dm"
        else:
            et = "channel_event_org"
        return [{
            "event_type": et,
            "content": spec.id,
            "environment": "default",
            "source": str(agent_id),
            "target": params.get("target_id"),
            "metadata": payload,
            "timestamp": now.timestamp(),
        }]
    return _eff


def register_channel_actions(action_registry: ActionRegistry, spec: ChannelSpec) -> None:
    """
    generate actions for a channel: post_to_<id>, dm_on_<id>, organize_event_on_<id>.
    comments are lowercase.
    """
    # record in global registry
    global_channel_registry.register(spec.__dict__)

    actions: List[tuple[str, str]] = [
        (f"post_to_{spec.id}", "post"),
        (f"dm_on_{spec.id}", "dm"),
        (f"organize_event_on_{spec.id}", "event"),
    ]

    for name, kind in actions:
        params_schema = {"type": "object", "properties": {"text": {"type": "string"}, "target_id": {"type": ["string", "null"]}}, "additionalProperties": True}
        pre = _make_preconditions_for_channel(kind, spec)
        est = _estimate_for_channel(kind, spec)
        eff = _effects_for_channel(kind, spec)
        action_registry.register(ActionSpec(
            name=name,
            description=f"{kind} via {spec.id}",
            params_schema=params_schema,
            preconditions=[pre],
            effects=eff,
            estimate=est,
            permissions=[],
        ))



