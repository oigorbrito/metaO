"""Declarative, framework-neutral runtime catalog factory.

This module turns the existing CLI ``--factory module:function`` hook into a
reusable multi-runtime configuration surface. Runtime-specific construction
remains delegated to trusted local plugin factories; this module imports no
orchestrator SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

from .catalog import OrchestratorCatalog
from .control_plane import EvidenceNormalizer
from .core import OrchestratorContract, OrchestratorRegistry
from .mission_store import MissionStorePort
from .operator import MissionOperator


RUNTIME_CATALOG_ENV = "METAO_RUNTIME_CATALOG"


class RuntimeCatalogConfigError(ValueError):
    """Raised when a declarative runtime catalog is invalid or unsafe to use."""


@dataclass(frozen=True)
class RuntimePlugin:
    """Framework-neutral product returned by a trusted runtime plugin factory."""

    orchestrator: OrchestratorContract
    normalizer: EvidenceNormalizer

    def __post_init__(self) -> None:
        if not isinstance(self.orchestrator, OrchestratorContract):
            raise RuntimeCatalogConfigError("runtime plugin must provide OrchestratorContract")
        if not callable(self.normalizer):
            raise RuntimeCatalogConfigError("runtime plugin normalizer must be callable")


def _as_object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeCatalogConfigError(f"{name} must be a JSON object")
    return value


def _required_string(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeCatalogConfigError(f"{key} must be a non-empty string")
    return value


def _number(data: Mapping[str, Any], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeCatalogConfigError(f"{key} must be numeric")
    result = float(value)
    if result < 0:
        raise RuntimeCatalogConfigError(f"{key} must be non-negative")
    return result


def _unit_interval(data: Mapping[str, Any], key: str, default: float) -> float:
    value = _number(data, key, default)
    if value > 1.0:
        raise RuntimeCatalogConfigError(f"{key} must be within [0, 1]")
    return value


def _load_callable(spec: str) -> Callable[..., Any]:
    if ":" not in spec:
        raise RuntimeCatalogConfigError("runtime factory must use module:function syntax")
    module_name, attribute = spec.split(":", 1)
    if not module_name or not attribute:
        raise RuntimeCatalogConfigError("runtime factory must use module:function syntax")
    try:
        target: Any = importlib.import_module(module_name)
        for part in attribute.split("."):
            target = getattr(target, part)
    except (ImportError, AttributeError) as exc:
        raise RuntimeCatalogConfigError(f"cannot load runtime factory: {spec}") from exc
    if not callable(target):
        raise RuntimeCatalogConfigError(f"runtime factory is not callable: {spec}")
    return target


def _read_manifest(path: str | Path) -> tuple[Mapping[str, Any], ...]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeCatalogConfigError(f"cannot read runtime catalog: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeCatalogConfigError(f"invalid runtime catalog JSON: {path}") from exc

    root = _as_object(payload, "runtime catalog")
    runtimes = root.get("runtimes")
    if not isinstance(runtimes, list) or not runtimes:
        raise RuntimeCatalogConfigError("runtime catalog requires a non-empty runtimes list")
    return tuple(_as_object(item, "runtime entry") for item in runtimes)


def create_operator_from_catalog(
    path: str | Path,
    *,
    store: MissionStorePort,
) -> MissionOperator:
    """Build one configured MissionOperator from a trusted local manifest.

    The manifest itself contains only framework-neutral routing metadata and a
    Python plugin-factory reference. The referenced plugin code is trusted local
    code and is responsible for importing/configuring any orchestrator SDK.
    """

    registry = OrchestratorRegistry()
    catalog = OrchestratorCatalog(registry)

    for entry in _read_manifest(path):
        factory_spec = _required_string(entry, "factory")
        try:
            plugin = _load_callable(factory_spec)()
        except RuntimeCatalogConfigError:
            raise
        except Exception as exc:
            raise RuntimeCatalogConfigError(f"runtime factory failed: {factory_spec}") from exc
        if not isinstance(plugin, RuntimePlugin):
            raise RuntimeCatalogConfigError(
                f"runtime factory must return RuntimePlugin: {factory_spec}"
            )

        registry.register(plugin.orchestrator)
        catalog.register(
            plugin.orchestrator.descriptor.orchestrator_id,
            normalizer=plugin.normalizer,
            cost=_number(entry, "cost", 0.0),
            latency_ms=_number(entry, "latency_ms", 1000.0),
            trust_profile=str(entry.get("trust_profile", "local")),
            success_rate=_unit_interval(entry, "success_rate", 0.5),
            quality=_unit_interval(entry, "quality", 0.5),
            reliability=_unit_interval(entry, "reliability", 0.5),
        )

    return MissionOperator(registry=registry, catalog=catalog, store=store)


def create_operator(*, store: MissionStorePort) -> MissionOperator:
    """CLI-compatible factory using ``METAO_RUNTIME_CATALOG`` as manifest path."""

    path = os.environ.get(RUNTIME_CATALOG_ENV)
    if not path:
        raise RuntimeCatalogConfigError(
            f"{RUNTIME_CATALOG_ENV} must point to a trusted runtime catalog JSON file"
        )
    return create_operator_from_catalog(path, store=store)


__all__ = [
    "RUNTIME_CATALOG_ENV",
    "RuntimeCatalogConfigError",
    "RuntimePlugin",
    "create_operator",
    "create_operator_from_catalog",
]
