from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


class CapabilityAuthority(StrEnum):
    PYTHON = "PYTHON"
    RUST_SHADOW = "RUST_SHADOW"
    RUST_ACTIVE = "RUST_ACTIVE"


PHASE7_QUALIFIED_CAPABILITIES = frozenset(
    {
        "acceptance",
        "policy",
        "approval",
        "budget",
        "authority_provenance",
        "proof_replay",
    }
)

PHASE7_SHADOW_CAPABILITIES = frozenset({"runtime"})
PHASE8_QUALIFIED_CAPABILITIES = PHASE7_QUALIFIED_CAPABILITIES | frozenset({"runtime"})


@dataclass(frozen=True, slots=True)
class CapabilityCutoverState:
    qualified_capabilities: frozenset[str] = PHASE7_QUALIFIED_CAPABILITIES
    shadow_capabilities: frozenset[str] = PHASE7_SHADOW_CAPABILITIES
    active_capabilities: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        for field_name, values in (
            ("qualified_capabilities", self.qualified_capabilities),
            ("shadow_capabilities", self.shadow_capabilities),
            ("active_capabilities", self.active_capabilities),
        ):
            if any(not capability for capability in values):
                raise ValueError(f"{field_name} cannot contain empty capabilities")

    def authority_for(self, capability: str) -> CapabilityAuthority:
        if capability in self.active_capabilities:
            return CapabilityAuthority.RUST_ACTIVE
        if capability in self.shadow_capabilities:
            return CapabilityAuthority.RUST_SHADOW
        return CapabilityAuthority.PYTHON

    def promote(self, capability: str) -> CapabilityCutoverState:
        if capability not in self.qualified_capabilities:
            return self
        return replace(
            self,
            active_capabilities=self.active_capabilities | frozenset({capability}),
            shadow_capabilities=self.shadow_capabilities - frozenset({capability}),
        )

    def shadow(self, capability: str) -> CapabilityCutoverState:
        if capability not in self.shadow_capabilities and capability not in self.qualified_capabilities:
            return self
        return replace(
            self,
            active_capabilities=self.active_capabilities - frozenset({capability}),
            shadow_capabilities=self.shadow_capabilities | frozenset({capability}),
        )

    def rollback(self, capability: str) -> CapabilityCutoverState:
        return replace(
            self,
            active_capabilities=self.active_capabilities - frozenset({capability}),
            shadow_capabilities=self.shadow_capabilities - frozenset({capability}),
        )

    def promote_qualified(self) -> CapabilityCutoverState:
        state = self
        for capability in sorted(self.qualified_capabilities):
            state = state.promote(capability)
        return state


def default_phase7_cutover_state() -> CapabilityCutoverState:
    return CapabilityCutoverState()


def default_phase8_cutover_state() -> CapabilityCutoverState:
    return CapabilityCutoverState(
        qualified_capabilities=PHASE8_QUALIFIED_CAPABILITIES,
        shadow_capabilities=frozenset(),
        active_capabilities=frozenset(),
    ).promote_qualified()
