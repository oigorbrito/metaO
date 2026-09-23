"""Declarative, framework-neutral runtime catalog factory."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Callable, Mapping

from .benchmark_routing import BenchmarkRoutingPolicy
from .benchmark_selection import BenchmarkSelectionPolicy
from .benchmark_store import SQLiteBenchmarkEvidenceStore
from .catalog import OrchestratorCatalog
from .control_plane import EvidenceNormalizer, SelectionPolicy
from .core import ExecutionRequest, Mission, OrchestratorContract, OrchestratorRegistry
from .feedback_catalog import HistoricalFeedbackCatalog
from .governed_catalog import GovernedOrchestratorCatalog
from .mission_store import MissionStorePort
from .operator import MissionOperator
from .runtime_admission import (
    RuntimeAdmissionError,
    RuntimeAdmissionGate,
    RuntimeCertificateAdmissionError,
)
from .runtime_certification import (
    RuntimeCertification,
    RuntimeCertificationStorePort,
    is_certificate_fresh,
    latest_certificate,
)
from .runtime_certification_revocation import (
    RuntimeCertificationRevocationStorePort,
    is_certificate_revoked,
)
from .runtime_control import RuntimeControlStorePort
from .runtime_feedback import RuntimeFeedbackStorePort, record_outcome
from .runtime_health import RuntimeHealthStorePort
from .sqlite_runtime_certification import SQLiteRuntimeCertificationStore
from .sqlite_runtime_certification_revocation import SQLiteRuntimeCertificationRevocationStore
from .sqlite_runtime_control import SQLiteRuntimeControlStore
from .sqlite_runtime_feedback import SQLiteRuntimeFeedbackStore
from .sqlite_runtime_health import SQLiteRuntimeHealthStore


RUNTIME_CATALOG_ENV = "METAO_RUNTIME_CATALOG"
RUNTIME_CONTROL_DB_ENV = "METAO_RUNTIME_CONTROL_DB"
RUNTIME_FEEDBACK_DB_ENV = "METAO_RUNTIME_FEEDBACK_DB"
RUNTIME_HEALTH_DB_ENV = "METAO_RUNTIME_HEALTH_DB"
RUNTIME_CERTIFICATION_DB_ENV = "METAO_RUNTIME_CERTIFICATION_DB"
RUNTIME_CERTIFICATION_REVOCATION_DB_ENV = "METAO_RUNTIME_CERTIFICATION_REVOCATION_DB"
BENCHMARK_EVIDENCE_DB_ENV = "METAO_BENCHMARK_EVIDENCE_DB"
BENCHMARK_ROUTING_POLICY_ENV = "METAO_BENCHMARK_ROUTING_POLICY"


class RuntimeCatalogConfigError(ValueError):
    """Raised when a declarative runtime catalog is invalid or unsafe to use."""


def _benchmark_routing_policy_from_env(value: str | None) -> BenchmarkRoutingPolicy | None:
    if value is None:
        return None
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeCatalogConfigError(
            f"{BENCHMARK_ROUTING_POLICY_ENV} must contain valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeCatalogConfigError(
            f"{BENCHMARK_ROUTING_POLICY_ENV} must contain a JSON object"
        )
    try:
        return BenchmarkRoutingPolicy(
            benchmark_id=str(payload["benchmark_id"]),
            benchmark_version=str(payload["benchmark_version"]),
            task_set=str(payload["task_set"]),
            metric_name=str(payload["metric_name"]),
            base_weight=float(payload.get("base_weight", 1.0)),
            benchmark_weight=float(payload.get("benchmark_weight", 1.0)),
            require_fresh=bool(payload.get("require_fresh", True)),
            max_age_seconds=float(payload.get("max_age_seconds", 86_400.0)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeCatalogConfigError(
            f"{BENCHMARK_ROUTING_POLICY_ENV} is invalid"
        ) from exc


@dataclass(frozen=True)
class RuntimePlugin:
    orchestrator: OrchestratorContract
    normalizer: EvidenceNormalizer

    def __post_init__(self) -> None:
        if not isinstance(self.orchestrator, OrchestratorContract):
            raise RuntimeCatalogConfigError("runtime plugin must provide OrchestratorContract")
        if not callable(self.normalizer):
            raise RuntimeCatalogConfigError("runtime plugin normalizer must be callable")


class RuntimeCatalogOperator(MissionOperator):
    """MissionOperator with catalog visibility and advisory runtime feedback."""

    def __init__(
        self,
        *,
        registry,
        catalog,
        store: MissionStorePort,
        feedback: RuntimeFeedbackStorePort | None = None,
        selection_policy: SelectionPolicy | None = None,
    ) -> None:
        super().__init__(
            registry=registry,
            catalog=catalog,
            store=store,
            selection_policy=selection_policy,
        )
        self._runtime_catalog_view = catalog
        self._runtime_feedback = feedback
        self._last_feedback_error: Exception | None = None

    def runtime_entries(self):
        return self._runtime_catalog_view.entries()

    def feedback_error(self) -> Exception | None:
        return self._last_feedback_error

    def _record_runtime_feedback(self, outcome) -> None:
        if self._runtime_feedback is None:
            return
        try:
            record_outcome(self._runtime_feedback, outcome)
            self._last_feedback_error = None
        except Exception as exc:  # feedback is advisory after mission commit
            self._last_feedback_error = exc

    def run(self, *args, **kwargs):
        outcome = super().run(*args, **kwargs)
        self._record_runtime_feedback(outcome)
        return outcome

    def resume(self, *args, **kwargs):
        outcome = super().resume(*args, **kwargs)
        self._record_runtime_feedback(outcome)
        return outcome


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


def _configure_runtime_health(
    plugin: RuntimePlugin,
    health: RuntimeHealthStorePort | None,
) -> None:
    if health is None:
        return
    configure = getattr(plugin.orchestrator, "configure_runtime_health_store", None)
    if not callable(configure):
        return
    try:
        configure(health)
    except Exception as exc:
        orchestrator_id = plugin.orchestrator.descriptor.orchestrator_id
        raise RuntimeCatalogConfigError(
            f"runtime health store configuration failed: {orchestrator_id}"
        ) from exc


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


def _certification_config(entry: Mapping[str, Any]) -> Mapping[str, Any] | None:
    certification = entry.get("certification")
    if certification is None:
        return None
    return _as_object(certification, "certification")


def _probe_request(entry: Mapping[str, Any], plugin: RuntimePlugin) -> ExecutionRequest | None:
    config = _certification_config(entry)
    if config is None:
        return None
    mode = config.get("mode", "required")
    if mode == "legacy":
        return None
    if mode != "required":
        raise RuntimeCatalogConfigError("certification.mode must be required or legacy")
    probe = _as_object(config.get("probe"), "certification.probe")
    execution_id = _required_string(probe, "execution_id")
    objective = _required_string(probe, "objective")
    mission_id = probe.get("mission_id", f"certify-{plugin.orchestrator.descriptor.orchestrator_id}")
    if not isinstance(mission_id, str) or not mission_id:
        raise RuntimeCatalogConfigError("certification.probe.mission_id must be a non-empty string")
    capabilities = probe.get(
        "required_capabilities",
        sorted(plugin.orchestrator.descriptor.capabilities),
    )
    if not isinstance(capabilities, list) or not capabilities or not all(
        isinstance(item, str) and item for item in capabilities
    ):
        raise RuntimeCatalogConfigError(
            "certification.probe.required_capabilities must be a non-empty string list"
        )
    context = probe.get("context", {})
    if not isinstance(context, dict):
        raise RuntimeCatalogConfigError("certification.probe.context must be a JSON object")
    return ExecutionRequest(
        execution_id,
        Mission(mission_id, objective, frozenset(capabilities)),
        context,
    )


def _reuse_passed_certificate(entry: Mapping[str, Any]) -> bool:
    config = _certification_config(entry)
    if config is None or config.get("mode", "required") == "legacy":
        return False
    value = config.get("reuse_passed", False)
    if not isinstance(value, bool):
        raise RuntimeCatalogConfigError("certification.reuse_passed must be boolean")
    return value


def _certificate_max_age_seconds(entry: Mapping[str, Any]) -> float | None:
    config = _certification_config(entry)
    if config is None or config.get("mode", "required") == "legacy":
        return None
    value = config.get("max_age_seconds")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeCatalogConfigError("certification.max_age_seconds must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise RuntimeCatalogConfigError("certification.max_age_seconds must be finite")
    if result <= 0:
        raise RuntimeCatalogConfigError("certification.max_age_seconds must be positive")
    return result


def _certification_now_epoch(value: float | None) -> float:
    result = time.time() if value is None else float(value)
    if not math.isfinite(result):
        raise RuntimeCatalogConfigError("certification current time must be finite")
    if result < 0:
        raise RuntimeCatalogConfigError("certification current time must be non-negative")
    return result


def _latest_reusable_certificate(
    certifications: RuntimeCertificationStorePort,
    revocations: RuntimeCertificationRevocationStorePort | None,
    *,
    orchestrator_id: str,
    runtime_version: str,
    probe_execution_id: str,
    now_epoch: float | None,
    max_age_seconds: float | None,
) -> RuntimeCertification | None:
    """Return the latest exact verdict only when that generation is reusable."""

    current = latest_certificate(
        certifications,
        orchestrator_id=orchestrator_id,
        runtime_version=runtime_version,
        probe_execution_id=probe_execution_id,
    )
    if current is None or not current.passed:
        return None
    if is_certificate_revoked(revocations, current.certificate_id):
        return None
    if max_age_seconds is not None:
        assert now_epoch is not None
        if not is_certificate_fresh(
            current,
            now_epoch=now_epoch,
            max_age_seconds=max_age_seconds,
        ):
            return None
    return current


def create_operator_from_catalog(
    path: str | Path,
    *,
    store: MissionStorePort,
    controls: RuntimeControlStorePort | None = None,
    feedback: RuntimeFeedbackStorePort | None = None,
    health: RuntimeHealthStorePort | None = None,
    certifications: RuntimeCertificationStorePort | None = None,
    certification_revocations: RuntimeCertificationRevocationStorePort | None = None,
    certification_now_epoch: float | None = None,
    selection_policy: SelectionPolicy | None = None,
) -> MissionOperator:
    """Build one operator, optionally certifying entries before admission."""

    registry = OrchestratorRegistry()
    catalog = OrchestratorCatalog(registry)
    admission = RuntimeAdmissionGate(
        registry,
        catalog,
        certifications,
        certification_revocations,
    )

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
        _configure_runtime_health(plugin, health)

        metrics = dict(
            cost=_number(entry, "cost", 0.0),
            latency_ms=_number(entry, "latency_ms", 1000.0),
            trust_profile=str(entry.get("trust_profile", "local")),
            success_rate=_unit_interval(entry, "success_rate", 0.5),
            quality=_unit_interval(entry, "quality", 0.5),
            reliability=_unit_interval(entry, "reliability", 0.5),
        )
        probe = _probe_request(entry, plugin)
        if probe is None:
            registry.register(plugin.orchestrator)
            catalog.register(
                plugin.orchestrator.descriptor.orchestrator_id,
                normalizer=plugin.normalizer,
                **metrics,
            )
            continue
        if certifications is None:
            raise RuntimeCatalogConfigError(
                "certification.mode=required needs a runtime certification store"
            )

        orchestrator_id = plugin.orchestrator.descriptor.orchestrator_id
        runtime_version = plugin.orchestrator.descriptor.version
        reuse_passed = _reuse_passed_certificate(entry)
        max_age_seconds = _certificate_max_age_seconds(entry)
        current_verdict = latest_certificate(
            certifications,
            orchestrator_id=orchestrator_id,
            runtime_version=runtime_version,
            probe_execution_id=probe.execution_id,
        )
        already_generational = (
            current_verdict is not None and current_verdict.certified_at_epoch > 0
        )
        needs_generation_time = (
            max_age_seconds is not None
            or certification_revocations is not None
            or already_generational
        )
        now_epoch = (
            _certification_now_epoch(certification_now_epoch)
            if needs_generation_time
            else None
        )

        if reuse_passed:
            existing = _latest_reusable_certificate(
                certifications,
                certification_revocations,
                orchestrator_id=orchestrator_id,
                runtime_version=runtime_version,
                probe_execution_id=probe.execution_id,
                now_epoch=now_epoch,
                max_age_seconds=max_age_seconds,
            )
            if existing is not None:
                try:
                    admission.admit_certified(
                        plugin.orchestrator,
                        plugin.normalizer,
                        existing,
                        expected_probe_execution_id=probe.execution_id,
                        now_epoch=now_epoch if max_age_seconds is not None else None,
                        max_age_seconds=max_age_seconds,
                        **metrics,
                    )
                except RuntimeCertificateAdmissionError as exc:
                    raise RuntimeCatalogConfigError(
                        f"runtime certificate reuse failed: {orchestrator_id}"
                    ) from exc
                continue

        try:
            admission.admit(
                plugin.orchestrator,
                plugin.normalizer,
                probe,
                certified_at_epoch=now_epoch if now_epoch is not None else 0.0,
                **metrics,
            )
        except RuntimeAdmissionError as exc:
            failed = ",".join(exc.report.failed_checks)
            raise RuntimeCatalogConfigError(
                f"runtime certification failed: {orchestrator_id}: {failed}"
            ) from exc
        except RuntimeCatalogConfigError:
            raise
        except Exception as exc:
            raise RuntimeCatalogConfigError(
                f"runtime certified admission failed: {orchestrator_id}"
            ) from exc

    operational_catalog = (
        GovernedOrchestratorCatalog(catalog, controls) if controls is not None else catalog
    )
    if feedback is not None:
        operational_catalog = HistoricalFeedbackCatalog(operational_catalog, feedback)
    return RuntimeCatalogOperator(
        registry=registry,
        catalog=operational_catalog,
        store=store,
        feedback=feedback,
        selection_policy=selection_policy,
    )


def create_operator(
    *,
    store: MissionStorePort,
    runtime_control_db: str | Path | None = None,
    runtime_feedback_db: str | Path | None = None,
    runtime_health_db: str | Path | None = None,
    runtime_certification_db: str | Path | None = None,
    runtime_certification_revocation_db: str | Path | None = None,
    certification_now_epoch: float | None = None,
    benchmark_evidence_db: str | Path | None = None,
    benchmark_routing_policy: BenchmarkRoutingPolicy | None = None,
) -> MissionOperator:
    """CLI-compatible factory using environment-backed runtime configuration."""

    path = os.environ.get(RUNTIME_CATALOG_ENV)
    if not path:
        raise RuntimeCatalogConfigError(
            f"{RUNTIME_CATALOG_ENV} must point to a trusted runtime catalog JSON file"
        )
    control_path = runtime_control_db or os.environ.get(RUNTIME_CONTROL_DB_ENV)
    feedback_path = runtime_feedback_db or os.environ.get(RUNTIME_FEEDBACK_DB_ENV) or control_path
    health_path = runtime_health_db or os.environ.get(RUNTIME_HEALTH_DB_ENV) or control_path
    certification_path = (
        runtime_certification_db
        or os.environ.get(RUNTIME_CERTIFICATION_DB_ENV)
        or control_path
    )
    revocation_path = (
        runtime_certification_revocation_db
        or os.environ.get(RUNTIME_CERTIFICATION_REVOCATION_DB_ENV)
        or certification_path
    )
    controls = SQLiteRuntimeControlStore(control_path) if control_path else None
    feedback = SQLiteRuntimeFeedbackStore(feedback_path) if feedback_path else None
    health = SQLiteRuntimeHealthStore(health_path) if health_path else None
    certifications = (
        SQLiteRuntimeCertificationStore(certification_path) if certification_path else None
    )
    certification_revocations = (
        SQLiteRuntimeCertificationRevocationStore(revocation_path)
        if revocation_path
        else None
    )

    benchmark_path = benchmark_evidence_db or os.environ.get(BENCHMARK_EVIDENCE_DB_ENV)
    resolved_benchmark_policy = benchmark_routing_policy or _benchmark_routing_policy_from_env(
        os.environ.get(BENCHMARK_ROUTING_POLICY_ENV)
    )
    if (benchmark_path is None) != (resolved_benchmark_policy is None):
        raise RuntimeCatalogConfigError(
            f"{BENCHMARK_EVIDENCE_DB_ENV} and {BENCHMARK_ROUTING_POLICY_ENV} "
            "must be configured together"
        )
    selection_policy = None
    if benchmark_path is not None and resolved_benchmark_policy is not None:
        selection_policy = BenchmarkSelectionPolicy(
            SQLiteBenchmarkEvidenceStore(benchmark_path),
            resolved_benchmark_policy,
        )

    return create_operator_from_catalog(
        path,
        store=store,
        controls=controls,
        feedback=feedback,
        health=health,
        certifications=certifications,
        certification_revocations=certification_revocations,
        certification_now_epoch=certification_now_epoch,
        selection_policy=selection_policy,
    )


__all__ = [
    "RUNTIME_CATALOG_ENV",
    "RUNTIME_CONTROL_DB_ENV",
    "RUNTIME_FEEDBACK_DB_ENV",
    "RUNTIME_HEALTH_DB_ENV",
    "RUNTIME_CERTIFICATION_DB_ENV",
    "RUNTIME_CERTIFICATION_REVOCATION_DB_ENV",
    "BENCHMARK_EVIDENCE_DB_ENV",
    "BENCHMARK_ROUTING_POLICY_ENV",
    "RuntimeCatalogConfigError",
    "RuntimePlugin",
    "RuntimeCatalogOperator",
    "create_operator",
    "create_operator_from_catalog",
]
