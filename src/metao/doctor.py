from __future__ import annotations

import os
from typing import Any

from .cli import CLIInputError, load_factory_callable, resolve_factory_spec
from .mission_store import InMemoryMissionStore
from .operator import MissionOperator


def run_doctor(db_path: str, explicit_factory_spec: str | None = None) -> dict[str, Any]:
    checks = []

    # 1. CLI_PACKAGE
    checks.append({"name": "CLI_PACKAGE", "status": "PASS"})

    # 2. DATABASE_PATH
    db_status = "FAIL"
    db_msg = ""
    try:
        parent = os.path.dirname(os.path.abspath(db_path))
        if not os.path.exists(parent):
            try:
                os.makedirs(parent, exist_ok=True)
                db_status = "PASS"
            except Exception as exc:
                db_msg = f"Cannot create parent directory: {exc}"
        elif os.access(parent, os.W_OK):
            db_status = "PASS"
        else:
            db_msg = "Parent directory not writable"
    except Exception as exc:
        db_msg = str(exc)
    check_db = {"name": "DATABASE_PATH", "status": db_status}
    if db_msg:
        check_db["message"] = db_msg
    checks.append(check_db)

    # 3. FACTORY_CONFIG
    factory_spec = None
    try:
        factory_spec = resolve_factory_spec(explicit_factory_spec)
        checks.append({"name": "FACTORY_CONFIG", "status": "PASS", "details": factory_spec})
    except CLIInputError as exc:
        checks.append({"name": "FACTORY_CONFIG", "status": "NOT_CONFIGURED", "message": str(exc)})
    except Exception as exc:
        checks.append({"name": "FACTORY_CONFIG", "status": "FAIL", "message": str(exc)})

    # 4. FACTORY_IMPORT & 5. OPERATOR_CONSTRUCTION & 6. RUNTIME_CATALOG
    check_import = {"name": "FACTORY_IMPORT", "status": "NOT_CHECKED"}
    check_construct = {"name": "OPERATOR_CONSTRUCTION", "status": "NOT_CHECKED"}
    check_catalog = {"name": "RUNTIME_CATALOG", "status": "NOT_CHECKED"}

    if factory_spec:
        try:
            factory_func = load_factory_callable(factory_spec)
            check_import = {"name": "FACTORY_IMPORT", "status": "PASS"}

            try:
                probe_store = InMemoryMissionStore()
                operator = factory_func(store=probe_store)
                if not isinstance(operator, MissionOperator):
                    check_construct = {
                        "name": "OPERATOR_CONSTRUCTION",
                        "status": "FAIL",
                        "message": "Factory did not return a MissionOperator",
                    }
                else:
                    check_construct = {"name": "OPERATOR_CONSTRUCTION", "status": "PASS"}

                    runtime_entries = getattr(operator, "runtime_entries", None)
                    if callable(runtime_entries):
                        try:
                            entries = runtime_entries()
                            check_catalog = {
                                "name": "RUNTIME_CATALOG",
                                "status": "PASS",
                                "details": f"count={len(list(entries))}",
                            }
                        except Exception as exc:
                            check_catalog = {
                                "name": "RUNTIME_CATALOG",
                                "status": "FAIL",
                                "message": f"runtime_entries() failed: {exc}",
                            }
                    else:
                        check_catalog = {
                            "name": "RUNTIME_CATALOG",
                            "status": "NOT_CONFIGURED",
                            "message": "Operator does not expose runtime_entries",
                        }
            except Exception as exc:
                check_construct = {
                    "name": "OPERATOR_CONSTRUCTION",
                    "status": "FAIL",
                    "message": str(exc),
                }
        except (CLIInputError, ImportError, AttributeError) as exc:
            check_import = {"name": "FACTORY_IMPORT", "status": "FAIL", "message": str(exc)}
        except Exception as exc:
            check_import = {"name": "FACTORY_IMPORT", "status": "FAIL", "message": str(exc)}

    checks.extend([check_import, check_construct, check_catalog])

    overall = "PASS"
    for check in checks:
        if check["status"] == "FAIL":
            overall = "FAIL"
            break
        if check["status"] == "NOT_CONFIGURED" and overall == "PASS":
            overall = "NOT_CONFIGURED"

    return {
        "overall_status": overall,
        "checks": checks,
    }
