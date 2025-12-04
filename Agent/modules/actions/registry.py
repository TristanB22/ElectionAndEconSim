#!/usr/bin/env python3
"""
Action Registry and Specifications

Defines typed, parametric actions and a registry that supports both global and
firm-namespaced actions. Actions are declarative:
- params_schema: JSONSchema dict used for validation
- preconditions: pure functions (world, agent_id, params) -> bool
- effects: pure function (world, agent_id, params, now) -> List[DomainEvent]
- estimate: pure function (world, agent_id, params) -> {time_minutes, cost, risk, success_prob}

DomainEvent is represented as a plain dict to keep the interpreter decoupled
from the concrete Event dataclass. Reducers and the interpreter convert/route
these to Environment.events.Event instances as needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional
import json


# Type aliases for clarity
WorldT = Any  # Will be Environment.core.world_state.WorldState at runtime
DomainEvent = Dict[str, Any]


@dataclass
class ActionSpec:
    name: str
    description: str
    params_schema: Dict[str, Any]
    preconditions: List[Callable[[WorldT, str, Dict[str, Any]], bool]]
    effects: Callable[[WorldT, str, Dict[str, Any], datetime], List[DomainEvent]]
    estimate: Callable[[WorldT, str, Dict[str, Any]], Dict[str, float]]
    permissions: List[str] = field(default_factory=list)


class ActionRegistry:
    """
    Registry for actions with optional firm scoping.

    - Global actions are stored under firm_id=None
    - Firm-scoped actions are stored under their firm_id
    """

    def __init__(self) -> None:
        # Mapping: (firm_id or None) -> {action_name -> ActionSpec}
        self._actions: Dict[Optional[str], Dict[str, ActionSpec]] = {}

    def register(self, spec: ActionSpec, firm_id: Optional[str] = None) -> None:
        if firm_id not in self._actions:
            self._actions[firm_id] = {}
        self._actions[firm_id][spec.name] = spec

    def get(self, name: str, firm_id: Optional[str] = None) -> Optional[ActionSpec]:
        # Firm namespace has priority if provided
        if firm_id is not None and firm_id in self._actions and name in self._actions[firm_id]:
            return self._actions[firm_id][name]
        # Fallback to global
        if None in self._actions and name in self._actions[None]:
            return self._actions[None][name]
        return None

    def list(self, firm_id: Optional[str] = None) -> List[ActionSpec]:
        out: List[ActionSpec] = []
        if None in self._actions:
            out.extend(self._actions[None].values())
        if firm_id is not None and firm_id in self._actions:
            out.extend(self._actions[firm_id].values())
        return out


# ---------------------------------
# Baseline environment/global actions
# ---------------------------------

def _evt(event_type: str, content: str, environment: str, source: str, target: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, timestamp: Optional[float] = None) -> DomainEvent:
    return {
        "event_type": event_type,
        "content": content,
        "environment": environment,
        "source": source,
        "target": target,
        "metadata": metadata or {},
        "timestamp": timestamp,
    }


def register_baseline_actions(registry: ActionRegistry) -> None:
    """
    Register a set of baseline global actions to enable end-to-end agent
    loops without pre-scripted events.
    """

    # move_to(place_id)
    def move_to_pre(world: WorldT, agent_id: str, params: Dict[str, Any]) -> bool:
        place_id = params.get("place_id")
        return isinstance(place_id, str) and len(place_id) > 0

    def move_to_est(world: WorldT, agent_id: str, params: Dict[str, Any]) -> Dict[str, float]:
        duration = 5.0
        return {"time_minutes": duration, "time": duration, "money": 0.0, "risk": 0.01, "success_prob": 0.99}

    def move_to_eff(world: WorldT, agent_id: str, params: Dict[str, Any], now: datetime) -> List[DomainEvent]:
        place_id = params["place_id"]
        # Mutate world via reducer by emitting an interaction event
        return [
            _evt(
                event_type="interaction",
                content=f"agent {agent_id} moves to {place_id}",
                environment="default",
                source=str(agent_id),
                target=None,
                metadata={"action": "move_to", "place_id": place_id},
                timestamp=now.timestamp(),
            )
        ]

    registry.register(
        ActionSpec(
            name="move_to",
            description="Move the agent to a place by id",
            params_schema={"type": "object", "properties": {"place_id": {"type": "string"}}, "required": ["place_id"]},
            preconditions=[move_to_pre],
            effects=move_to_eff,
            estimate=move_to_est,
            permissions=[],
        )
    )

    # message(target_id, text)
    def message_pre(world: WorldT, agent_id: str, params: Dict[str, Any]) -> bool:
        return isinstance(params.get("text"), str) and len(params["text"].strip()) > 0

    def message_est(world: WorldT, agent_id: str, params: Dict[str, Any]) -> Dict[str, float]:
        duration = 1.0
        return {"time_minutes": duration, "time": duration, "money": 0.0, "risk": 0.0, "success_prob": 0.999}

    def message_eff(world: WorldT, agent_id: str, params: Dict[str, Any], now: datetime) -> List[DomainEvent]:
        target_id = params.get("target_id")
        text = params.get("text", "")
        return [
            _evt(
                event_type="message",
                content=text,
                environment="default",
                source=str(agent_id),
                target=str(target_id) if target_id is not None else None,
                metadata={"action": "message"},
                timestamp=now.timestamp(),
            )
        ]

    registry.register(
        ActionSpec(
            name="message",
            description="Send a message to another agent",
            params_schema={
                "type": "object",
                "properties": {"target_id": {"type": ["string", "integer", "null"]}, "text": {"type": "string", "maxLength": 512}},
                "required": ["text"],
            },
            preconditions=[message_pre],
            effects=message_eff,
            estimate=message_est,
            permissions=[],
        )
    )

    # schedule_task(task_json)
    def schedule_pre(world: WorldT, agent_id: str, params: Dict[str, Any]) -> bool:
        return isinstance(params.get("task"), dict)

    def schedule_est(world: WorldT, agent_id: str, params: Dict[str, Any]) -> Dict[str, float]:
        duration = 0.5
        return {"time_minutes": duration, "time": duration, "money": 0.0, "risk": 0.0, "success_prob": 1.0}

    def schedule_eff(world: WorldT, agent_id: str, params: Dict[str, Any], now: datetime) -> List[DomainEvent]:
        return [
            _evt(
                event_type="system_notification",
                content="task_scheduled",
                environment="default",
                source=str(agent_id),
                target=str(agent_id),
                metadata={"action": "schedule_task", "task": params.get("task", {})},
                timestamp=now.timestamp(),
            )
        ]

    registry.register(
        ActionSpec(
            name="schedule_task",
            description="Schedule a task for future execution",
            params_schema={"type": "object", "properties": {"task": {"type": "object"}}, "required": ["task"]},
            preconditions=[schedule_pre],
            effects=schedule_eff,
            estimate=schedule_est,
            permissions=[],
        )
    )

    # open_close(object_id)
    def open_close_pre(world: WorldT, agent_id: str, params: Dict[str, Any]) -> bool:
        return isinstance(params.get("object_id"), str)

    def open_close_est(world: WorldT, agent_id: str, params: Dict[str, Any]) -> Dict[str, float]:
        duration = 0.5
        return {"time_minutes": duration, "time": duration, "money": 0.0, "risk": 0.0, "success_prob": 0.99}

    def open_close_eff(world: WorldT, agent_id: str, params: Dict[str, Any], now: datetime) -> List[DomainEvent]:
        object_id = params.get("object_id")
        return [
            _evt(
                event_type="interaction",
                content=f"agent {agent_id} toggles {object_id}",
                environment="default",
                source=str(agent_id),
                target=None,
                metadata={"action": "open_close", "object_id": object_id},
                timestamp=now.timestamp(),
            )
        ]

    registry.register(
        ActionSpec(
            name="open_close",
            description="Open or close a simple object",
            params_schema={"type": "object", "properties": {"object_id": {"type": "string"}}, "required": ["object_id"]},
            preconditions=[open_close_pre],
            effects=open_close_eff,
            estimate=open_close_est,
            permissions=[],
        )
    )

    # use(object_id, intent, modifiers?)
    def use_pre(world: WorldT, agent_id: str, params: Dict[str, Any]) -> bool:
        return isinstance(params.get("object_id"), str) and isinstance(params.get("intent"), str)

    def use_est(world: WorldT, agent_id: str, params: Dict[str, Any]) -> Dict[str, float]:
        duration = 3.0
        return {"time_minutes": duration, "time": duration, "money": 0.0, "risk": 0.02, "success_prob": 0.95}

    def use_eff(world: WorldT, agent_id: str, params: Dict[str, Any], now: datetime) -> List[DomainEvent]:
        object_id = params.get("object_id")
        intent = params.get("intent")
        modifiers = params.get("modifiers", {})
        return [
            _evt(
                event_type="interaction",
                content=f"agent {agent_id} uses {object_id} with intent {intent}",
                environment="default",
                source=str(agent_id),
                target=None,
                metadata={"action": "use", "object_id": object_id, "intent": intent, "modifiers": modifiers},
                timestamp=now.timestamp(),
            )
        ]

    registry.register(
        ActionSpec(
            name="use",
            description="Use an object with a specified intent and optional modifiers",
            params_schema={
                "type": "object",
                "properties": {"object_id": {"type": "string"}, "intent": {"type": "string"}, "modifiers": {"type": "object"}},
                "required": ["object_id", "intent"],
            },
            preconditions=[use_pre],
            effects=use_eff,
            estimate=use_est,
            permissions=[],
        )
    )

    # travel(to, route?, mode?)
    def travel_pre(world: WorldT, agent_id: str, params: Dict[str, Any]) -> bool:
        destination = params.get("to")
        if isinstance(destination, dict):
            return bool(destination.get("id"))
        return isinstance(destination, str) and len(destination.strip()) > 0

    def travel_est(world: WorldT, agent_id: str, params: Dict[str, Any]) -> Dict[str, float]:
        route = params.get("route") or {}
        duration = float(route.get("duration_minutes") or route.get("time_minutes") or 10.0)
        distance = float(route.get("distance_km") or 0.0)
        cost = float(route.get("cost") or 0.0)
        return {
            "time_minutes": duration,
            "time": duration,
            "distance_km": distance,
            "money": cost,
            "risk": float(route.get("risk", 0.01)),
            "success_prob": float(route.get("success_prob", 0.995)),
        }

    def travel_eff(world: WorldT, agent_id: str, params: Dict[str, Any], now: datetime) -> List[DomainEvent]:
        destination = params.get("to")
        if isinstance(destination, dict):
            destination_id = destination.get("id") or destination.get("label") or "unknown"
        else:
            destination_id = destination
        route = params.get("route") or {}
        metadata = {
            "action": "Travel",
            "agent_id": str(agent_id),
            "to": destination_id,
            "mode": params.get("mode"),
            "distance_km": route.get("distance_km"),
            "duration_minutes": route.get("duration_minutes"),
            "provider": route.get("provider"),
            "polyline": route.get("polyline"),
        }
        return [
            {
                "event_type": "interaction",
                "content": f"agent {agent_id} travels to {destination_id}",
                "environment": "default",
                "source": str(agent_id),
                "target": None,
                "metadata": metadata,
                "timestamp": now.timestamp(),
            }
        ]

    registry.register(
        ActionSpec(
            name="Travel",
            description="Travel to a known location using the provided route information",
            params_schema={
                "type": "object",
                "properties": {
                    "to": {"oneOf": [{"type": "string"}, {"type": "object"}]},
                    "mode": {"type": ["string", "null"]},
                    "route": {"type": ["object", "null"]},
                },
                "required": ["to"],
            },
            preconditions=[travel_pre],
            effects=travel_eff,
            estimate=travel_est,
            permissions=[],
        )
    )

    # exchange(counterparty, receive, give?)
    def exchange_pre(world: WorldT, agent_id: str, params: Dict[str, Any]) -> bool:
        counterparty = params.get("counterparty")
        receive = params.get("receive")
        return isinstance(counterparty, str) and isinstance(receive, dict) and len(receive) > 0

    def exchange_est(world: WorldT, agent_id: str, params: Dict[str, Any]) -> Dict[str, float]:
        receive = params.get("receive") or {}
        item_count = sum(float(v) for v in receive.values() if isinstance(v, (int, float)))
        duration = max(2.0, min(20.0, 3.0 + item_count * 1.5))
        spend = float(params.get("spend") or 0.0)
        return {
            "time_minutes": duration,
            "time": duration,
            "money": spend,
            "risk": 0.02,
            "success_prob": 0.98,
        }

    def exchange_eff(world: WorldT, agent_id: str, params: Dict[str, Any], now: datetime) -> List[DomainEvent]:
        counterparty = params.get("counterparty")
        receive = params.get("receive") or {}
        items = [{"sku": sku, "qty": int(qty)} for sku, qty in receive.items()]
        events: List[DomainEvent] = []

        try:
            firm_state = world.state.get_firm_state(counterparty)
            priced_items = []
            total_price = 0.0
            total_cost = 0.0
            for item in items:
                sku = item["sku"]
                qty = item["qty"]
                unit_price = float(firm_state.get("prices", {}).get(sku, 0.0))
                unit_cost = float(firm_state.get("costs", {}).get(sku, 0.0))
                priced_items.append(
                    {
                        "sku": sku,
                        "qty": qty,
                        "unit_price": unit_price,
                        "unit_cost": unit_cost,
                    }
                )
                total_price += unit_price * qty
                total_cost += unit_cost * qty

            order_id = world.state.get_next_firm_order_id(counterparty)
            base_meta = {"order_id": order_id, "customer_id": str(agent_id), "firm_id": counterparty}
            events.append(
                {
                    "event_type": "retail_order_placed",
                    "content": f"order {order_id}",
                    "environment": "default",
                    "source": str(agent_id),
                    "target": None,
                    "metadata": {**base_meta, "items": priced_items, "total_price": total_price, "total_cost": total_cost},
                    "timestamp": now.timestamp(),
                }
            )
            events.append(
                {
                    "event_type": "retail_order_fulfilled",
                    "content": f"fulfill {order_id}",
                    "environment": "default",
                    "source": str(agent_id),
                    "target": None,
                    "metadata": {"order_id": order_id, "firm_id": counterparty, "items": priced_items},
                    "timestamp": now.timestamp(),
                }
            )
            events.append(
                {
                    "event_type": "retail_invoice_issued",
                    "content": f"invoice for {order_id}",
                    "environment": "default",
                    "source": str(agent_id),
                    "target": None,
                    "metadata": {"order_id": order_id, "firm_id": counterparty, "ar_amount": total_price},
                    "timestamp": now.timestamp(),
                }
            )
            events.append(
                {
                    "event_type": "retail_payment_received",
                    "content": f"payment for {order_id}",
                    "environment": "default",
                    "source": str(agent_id),
                    "target": None,
                    "metadata": {"order_id": order_id, "firm_id": counterparty, "amount": total_price},
                    "timestamp": now.timestamp(),
                }
            )
        except Exception:
            events.append(
                {
                    "event_type": "payment",
                    "content": json.dumps({"counterparty": counterparty, "receive": receive}),
                    "environment": "default",
                    "source": str(agent_id),
                    "target": None,
                    "metadata": {},
                    "timestamp": now.timestamp(),
                }
            )

        return events

    registry.register(
        ActionSpec(
            name="Exchange",
            description="Purchase goods or services from a counterparty firm",
            params_schema={
                "type": "object",
                "properties": {
                    "counterparty": {"type": "string"},
                    "receive": {"type": "object"},
                    "give": {"type": ["object", "null"]},
                    "spend": {"type": ["number", "null"]},
                },
                "required": ["counterparty", "receive"],
            },
            preconditions=[exchange_pre],
            effects=exchange_eff,
            estimate=exchange_est,
            permissions=[],
        )
    )

    # consume(items)
    def consume_pre(world: WorldT, agent_id: str, params: Dict[str, Any]) -> bool:
        items = params.get("items")
        return isinstance(items, dict) and len(items) > 0

    def consume_est(world: WorldT, agent_id: str, params: Dict[str, Any]) -> Dict[str, float]:
        items = params.get("items") or {}
        duration = max(1.0, min(10.0, 2.0 + len(items) * 1.0))
        return {
            "time_minutes": duration,
            "time": duration,
            "money": 0.0,
            "risk": 0.01,
            "success_prob": 0.995,
        }

    def consume_eff(world: WorldT, agent_id: str, params: Dict[str, Any], now: datetime) -> List[DomainEvent]:
        return [
            {
                "event_type": "inventory_removed",
                "content": "consume",
                "environment": "default",
                "source": str(agent_id),
                "target": None,
                "metadata": {"items": params.get("items", {})},
                "timestamp": now.timestamp(),
            }
        ]

    registry.register(
        ActionSpec(
            name="Consume",
            description="Consume items from the agent's personal inventory",
            params_schema={
                "type": "object",
                "properties": {"items": {"type": "object"}},
                "required": ["items"],
            },
            preconditions=[consume_pre],
            effects=consume_eff,
            estimate=consume_est,
            permissions=[],
        )
    )

    # communicate(to, message)
    def communicate_pre(world: WorldT, agent_id: str, params: Dict[str, Any]) -> bool:
        msg = params.get("message")
        return isinstance(msg, str) and len(msg.strip()) > 0

    def communicate_est(world: WorldT, agent_id: str, params: Dict[str, Any]) -> Dict[str, float]:
        duration = 1.0
        return {
            "time_minutes": duration,
            "time": duration,
            "money": 0.0,
            "risk": 0.01,
            "success_prob": 0.995,
        }

    def communicate_eff(world: WorldT, agent_id: str, params: Dict[str, Any], now: datetime) -> List[DomainEvent]:
        return [
            {
                "event_type": "message",
                "content": params.get("message", ""),
                "environment": "default",
                "source": str(agent_id),
                "target": params.get("to"),
                "metadata": {"action": "Communicate"},
                "timestamp": now.timestamp(),
            }
        ]

    registry.register(
        ActionSpec(
            name="Communicate",
            description="Communicate with another entity",
            params_schema={
                "type": "object",
                "properties": {
                    "to": {"type": ["string", "null"]},
                    "message": {"type": "string"},
                },
                "required": ["message"],
            },
            preconditions=[communicate_pre],
            effects=communicate_eff,
            estimate=communicate_est,
            permissions=[],
        )
    )

    # transfer(asset, amount, counterparty)
    def transfer_pre(world: WorldT, agent_id: str, params: Dict[str, Any]) -> bool:
        asset = params.get("asset")
        amount = params.get("amount")
        counterparty = params.get("counterparty")
        return (
            isinstance(asset, str)
            and isinstance(counterparty, str)
            and isinstance(amount, (int, float))
            and amount >= 0
        )

    def transfer_est(world: WorldT, agent_id: str, params: Dict[str, Any]) -> Dict[str, float]:
        duration = 1.0
        return {
            "time_minutes": duration,
            "time": duration,
            "money": float(params.get("amount") or 0.0),
            "risk": 0.01,
            "success_prob": 0.99,
        }

    def transfer_eff(world: WorldT, agent_id: str, params: Dict[str, Any], now: datetime) -> List[DomainEvent]:
        metadata = {
            "asset": params.get("asset"),
            "amount": params.get("amount"),
            "counterparty": params.get("counterparty"),
        }
        return [
            {
                "event_type": "asset_transferred",
                "content": json.dumps(metadata),
                "environment": "default",
                "source": str(agent_id),
                "target": params.get("counterparty"),
                "metadata": metadata,
                "timestamp": now.timestamp(),
            }
        ]

    registry.register(
        ActionSpec(
            name="Transfer",
            description="Transfer an asset or currency to a counterparty",
            params_schema={
                "type": "object",
                "properties": {
                    "asset": {"type": "string"},
                    "amount": {"type": "number"},
                    "counterparty": {"type": "string"},
                },
                "required": ["asset", "amount", "counterparty"],
            },
            preconditions=[transfer_pre],
            effects=transfer_eff,
            estimate=transfer_est,
            permissions=[],
        )
    )
