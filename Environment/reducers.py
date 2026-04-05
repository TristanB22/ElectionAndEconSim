#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, Any


def reduce_event(world, evt: Dict[str, Any]) -> None:
    t = evt.get("event_type")
    meta = evt.get("metadata", {})
    agent_id = str(evt.get("source")) if evt.get("source") is not None else None

    if t == "interaction" and meta.get("action") == "Travel":
        to = meta.get("to")
        if agent_id and to:
            world.state.set_agent_position(agent_id, to)

    elif t == "retail_order_fulfilled":
        firm_id = meta.get("firm_id") or None
        items = meta.get("items", [])
        if firm_id:
            fs = world.state.get_firm_state(firm_id)
            inv = fs.setdefault("inventory", {})
            for it in items:
                sku = it.get("sku")
                qty = int(it.get("qty", 0))
                if sku:
                    inv[sku] = max(0, int(inv.get(sku, 0)) - qty)

    elif t == "retail_invoice_issued":
        firm_id = meta.get("firm_id") or None
        amt = float(meta.get("ar_amount", 0.0))
        if firm_id and amt:
            fs = world.state.get_firm_state(firm_id)
            fs["ar"] = float(fs.get("ar", 0.0)) + amt

    elif t == "retail_payment_received":
        firm_id = meta.get("firm_id") or None
        amt = float(meta.get("amount", 0.0))
        if firm_id and amt:
            fs = world.state.get_firm_state(firm_id)
            fs["cash"] = float(fs.get("cash", 0.0)) + amt
            fs["ar"] = max(0.0, float(fs.get("ar", 0.0)) - amt)


