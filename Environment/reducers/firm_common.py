#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, Any, List

from Environment.core.world_state import WorldState


def apply_retail_order_placed(world: WorldState, event: Dict[str, Any]):
    """Applies retail_order_placed event to firm's orders and cash (immediate payment)."""
    meta = event.get('metadata', {})
    firm_id = meta.get('firm_id')
    if not firm_id:
        return
    
    order_id = meta.get('order_id')
    total_price = float(meta.get('total_price', 0.0))
    items = meta.get('items', [])
    
    firm_state = world.get_firm_state(firm_id)
    
    # Record the order
    orders = firm_state.setdefault('orders', {})
    orders[order_id] = meta
    
    # For immediate cash transaction, update cash and inventory
    firm_state['cash'] = float(firm_state.get('cash', 0.0)) + total_price
    
    # Update inventory
    inventory = firm_state.setdefault('inventory', {})
    for item in items:
        sku = item.get('sku')
        qty = int(item.get('qty', 0))
        if sku:
            inventory[sku] = max(0, int(inventory.get(sku, 0)) - qty)

def apply_retail_order_fulfilled(world: WorldState, event: Dict[str, Any]):
    """Applies retail_order_fulfilled event."""
    meta = event.get('metadata', {})
    firm_id = meta.get('firm_id')
    order_id = meta.get('order_id')
    
    if firm_id and order_id:
        firm_state = world.get_firm_state(firm_id)
        if 'orders' in firm_state and order_id in firm_state['orders']:
            firm_state['orders'][order_id]['status'] = 'fulfilled'

def apply_retail_invoice_issued(world: WorldState, event: Dict[str, Any]):
    """Applies retail_invoice_issued event to update AR."""
    meta = event.get('metadata', {})
    firm_id = meta.get('firm_id')
    order_id = meta.get('order_id')
    ar_amount = float(meta.get('ar_amount', 0.0))
    
    if firm_id:
        firm_state = world.get_firm_state(firm_id)
        firm_state['ar'] = float(firm_state.get('ar', 0.0)) + ar_amount
        
        if 'orders' in firm_state and order_id in firm_state['orders']:
            firm_state['orders'][order_id]['status'] = 'invoiced'

def apply_retail_payment_received(world: WorldState, event: Dict[str, Any]):
    """Applies retail_payment_received event to update cash and AR."""
    meta = event.get('metadata', {})
    firm_id = meta.get('firm_id')
    amount = float(meta.get('amount', 0.0))
    
    if firm_id:
        firm_state = world.get_firm_state(firm_id)
        firm_state['ar'] = max(0.0, float(firm_state.get('ar', 0.0)) - amount)
        # Don't double-add cash since we already did it in order_placed for immediate payment

def apply_retail_stock_received(world: WorldState, event: Dict[str, Any]):
    """Applies retail_stock_received event to update inventory."""
    meta = event.get('metadata', {})
    firm_id = meta.get('firm_id')
    sku = meta.get('sku')
    qty = int(meta.get('qty', 0))
    cost = float(meta.get('cost', 0.0))
    
    if firm_id and sku:
        firm_state = world.get_firm_state(firm_id)
        inventory = firm_state.setdefault('inventory', {})
        inventory[sku] = int(inventory.get(sku, 0)) + qty
        
        # Update cash for stock purchase
        firm_state['cash'] = float(firm_state.get('cash', 0.0)) - (cost * qty)

# Map event types to their respective reducer functions
FIRM_COMMON_REDUCERS = {
    "retail_order_placed": apply_retail_order_placed,
    "retail_order_fulfilled": apply_retail_order_fulfilled,
    "retail_invoice_issued": apply_retail_invoice_issued,
    "retail_payment_received": apply_retail_payment_received,
    "retail_stock_received": apply_retail_stock_received,
}


