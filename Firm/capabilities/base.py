from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# Forward declarations for type hints
ActionRegistry = Any
AccountingAdapter = Any
WorldState = Any
MechanismEngine = Any

@dataclass
class CapabilitySpec:
    """
    Defines a firm capability, which is a pluggable set of features
    (actions, reducers, accounting mappers, mechanisms).
    """
    id: str
    version: str
    description: str
    config_schema: Dict[str, Any] = field(default_factory=dict) # jsonschema for capability-specific config
    depends_on: List[str] = field(default_factory=list) # Other capabilities this one depends on
    conflicts_with: List[str] = field(default_factory=list) # Capabilities this one cannot coexist with

    # Functions/lists provided by this capability
    # These will be registered with the respective central systems
    provide_actions: Optional[Callable[[ActionRegistry, str, Dict[str, Any]], None]] = None # (registry, firm_id, config) -> None
    provide_reducers: Optional[Dict[str, Callable[[WorldState, Dict[str, Any]], None]]] = None # event_type -> reducer_func
    provide_journal_mappers: Optional[Callable[[AccountingAdapter], None]] = None # (accounting_adapter) -> None
    provide_mechanisms: Optional[Callable[[MechanismEngine, str, Dict[str, Any]], None]] = None # (mechanism_engine, firm_id, config) -> None

class CapabilityRegistry:
    """
    Manages and resolves firm capabilities.
    """
    def __init__(self):
        self._capabilities: Dict[str, CapabilitySpec] = {}

    def register(self, capability: CapabilitySpec):
        """Registers a new capability."""
        capability_key = f"{capability.id}.{capability.version}"
        if capability_key in self._capabilities:
            logger.warning(f"Overwriting capability '{capability_key}'")
        self._capabilities[capability_key] = capability
        logger.info(f"Registered capability: {capability_key}")

    def get(self, capability_id: str) -> Optional[CapabilitySpec]:
        """Retrieves a registered capability."""
        return self._capabilities.get(capability_id)

    def resolve_capabilities(self, capability_ids: List[str]) -> List[CapabilitySpec]:
        """
        Resolves a list of capability IDs into a topologically sorted list of CapabilitySpecs,
        checking dependencies and conflicts.
        """
        resolved: List[CapabilitySpec] = []
        resolved_ids = set()
        
        def resolve_recursive(cap_id: str):
            if cap_id in resolved_ids:
                return
                
            cap = self.get(cap_id)
            if not cap:
                raise ValueError(f"Capability '{cap_id}' not found in registry")
            
            # First resolve dependencies
            for dep_id in cap.depends_on:
                resolve_recursive(dep_id)
            
            # Check for conflicts with already resolved capabilities
            for resolved_cap in resolved:
                if cap.id in resolved_cap.conflicts_with or resolved_cap.id in cap.conflicts_with:
                    raise ValueError(f"Conflicting capabilities: {cap.id} and {resolved_cap.id}")
            
            resolved.append(cap)
            resolved_ids.add(cap_id)
        
        for cap_id in capability_ids:
            resolve_recursive(cap_id)
        
        return resolved

    def list_all(self) -> List[str]:
        """Returns all registered capability IDs."""
        return list(self._capabilities.keys())

# Global registry instance
_global_capability_registry = CapabilityRegistry()

def get_capability_registry() -> CapabilityRegistry:
    """Returns the global capability registry."""
    return _global_capability_registry