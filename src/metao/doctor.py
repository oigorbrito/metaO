from __future__ import annotations
import importlib
import os
import sys
from typing import Any

from .cli import FACTORY_ENV_VAR, resolve_factory_spec, CLIInputError
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
            except Exception as e:
                db_msg = f"Cannot create parent directory: {e}"
        else:
            if os.access(parent, os.W_OK):
                db_status = "PASS"
            else:
                db_msg = "Parent directory not writable"
    except Exception as e:
        db_msg = str(e)
    check_db = {"name": "DATABASE_PATH", "status": db_status}
    if db_msg: check_db["message"] = db_msg
    checks.append(check_db)
    
    # 3. FACTORY_CONFIG
    factory_spec = None
    try:
        factory_spec = resolve_factory_spec(explicit_factory_spec)
        checks.append({"name": "FACTORY_CONFIG", "status": "PASS", "details": factory_spec})
    except CLIInputError as e:
        checks.append({"name": "FACTORY_CONFIG", "status": "NOT_CONFIGURED", "message": str(e)})
    except Exception as e:
        checks.append({"name": "FACTORY_CONFIG", "status": "FAIL", "message": str(e)})

    # 4. FACTORY_IMPORT & 5. OPERATOR_CONSTRUCTION & 6. RUNTIME_CATALOG
    check_import = {"name": "FACTORY_IMPORT", "status": "NOT_CHECKED"}
    check_construct = {"name": "OPERATOR_CONSTRUCTION", "status": "NOT_CHECKED"}
    check_catalog = {"name": "RUNTIME_CATALOG", "status": "NOT_CHECKED"}

    if factory_spec:
        if ":" not in factory_spec:
            check_import = {"name": "FACTORY_IMPORT", "status": "FAIL", "message": "Syntax must be module:function"}
        else:
            module_name, attr = factory_spec.split(":", 1)
            try:
                module = importlib.import_module(module_name)
                factory_func = getattr(module, attr)
                if not callable(factory_func):
                    check_import = {"name": "FACTORY_IMPORT", "status": "FAIL", "message": "Target is not callable"}
                else:
                    check_import = {"name": "FACTORY_IMPORT", "status": "PASS"}
                    
                    # Try construct
                    try:
                        from .sqlite_store import SQLiteMissionStore
                        probe_store = SQLiteMissionStore(":memory:")
                        operator = factory_func(store=probe_store)
                        if not isinstance(operator, MissionOperator):
                            check_construct = {"name": "OPERATOR_CONSTRUCTION", "status": "FAIL", "message": "Factory did not return a MissionOperator"}
                        else:
                            check_construct = {"name": "OPERATOR_CONSTRUCTION", "status": "PASS"}
                            
                            # Catalog
                            if hasattr(operator, "runtime_entries") and callable(getattr(operator, "runtime_entries")):
                                try:
                                    entries = operator.runtime_entries()
                                    check_catalog = {"name": "RUNTIME_CATALOG", "status": "PASS", "details": f"count={len(list(entries))}"}
                                except Exception as e:
                                    check_catalog = {"name": "RUNTIME_CATALOG", "status": "FAIL", "message": f"runtime_entries() failed: {e}"}
                            else:
                                check_catalog = {"name": "RUNTIME_CATALOG", "status": "NOT_CONFIGURED", "message": "Operator does not expose runtime_entries"}
                                
                    except Exception as e:
                        check_construct = {"name": "OPERATOR_CONSTRUCTION", "status": "FAIL", "message": str(e)}
            except ImportError as e:
                check_import = {"name": "FACTORY_IMPORT", "status": "FAIL", "message": str(e)}
            except AttributeError as e:
                check_import = {"name": "FACTORY_IMPORT", "status": "FAIL", "message": str(e)}
            except Exception as e:
                check_import = {"name": "FACTORY_IMPORT", "status": "FAIL", "message": str(e)}
                
    checks.extend([check_import, check_construct, check_catalog])
    
    overall = "PASS"
    for c in checks:
        if c["status"] == "FAIL":
            overall = "FAIL"
            break
        if c["status"] == "NOT_CONFIGURED" and overall == "PASS":
            overall = "NOT_CONFIGURED"
            
    return {
        "overall_status": overall,
        "checks": checks
    }
