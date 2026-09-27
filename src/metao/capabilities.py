from __future__ import annotations
from enum import StrEnum

class Capability(StrEnum):
    """Authoritative list of executor capabilities supported by metaO."""
    # File System
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    
    # Execution
    SHELL_EXECUTION = "shell_execution"
    PROCESS_MANAGEMENT = "process_management"
    
    # External Integration
    NETWORK_ACCESS = "network_access"
    HTTP_REQUESTS = "http_requests"
    BROWSER_CONTROL = "browser_control"
    
    # Git/VCS
    GIT_OPERATIONS = "git_operations"
    
    # High-level Logic
    PLANNING = "planning"
    REPLANNING = "replanning"
    SELF_CORRECTION = "self_correction"

__all__ = ["Capability"]
