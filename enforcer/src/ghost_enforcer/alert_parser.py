"""Parse Falco JSON alerts into structured objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FalcoAlert:
    """Structured representation of a Falco alert."""

    # Core fields
    uuid: str
    rule: str
    priority: str
    output: str
    time: datetime

    # Container information
    container_id: str | None = None
    container_name: str | None = None
    container_image: str | None = None

    # Process information
    proc_name: str | None = None
    proc_cmdline: str | None = None
    proc_pid: int | None = None
    proc_ppid: int | None = None
    parent_name: str | None = None

    # User information
    user_name: str | None = None
    user_uid: int | None = None

    # Network information
    fd_name: str | None = None
    fd_type: str | None = None

    # Raw output fields
    output_fields: dict[str, Any] = field(default_factory=dict)

    # Tags
    tags: list[str] = field(default_factory=list)

    # Source
    source: str = "syscall"
    hostname: str | None = None

    def is_ghost_edr_rule(self) -> bool:
        """Check if this alert is from a Ghost EDR rule."""
        return self.rule.startswith("Ghost EDR")

    def get_mitre_tactics(self) -> list[str]:
        """Extract MITRE ATT&CK tactics from tags."""
        return [t for t in self.tags if t.startswith("mitre_")]

    def get_technique_ids(self) -> list[str]:
        """Extract MITRE ATT&CK technique IDs from tags."""
        return [t for t in self.tags if t.startswith("T")]


def parse_falco_alert(data: dict[str, Any]) -> FalcoAlert:
    """Parse a Falco JSON alert into a FalcoAlert object."""
    output_fields = data.get("output_fields", {})

    # Parse timestamp
    time_str = data.get("time", "")
    try:
        time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        time = datetime.now()

    return FalcoAlert(
        uuid=data.get("uuid", ""),
        rule=data.get("rule", "Unknown"),
        priority=data.get("priority", "WARNING").upper(),
        output=data.get("output", ""),
        time=time,
        # Container fields
        container_id=_get_field(output_fields, "container.id", "container_id"),
        container_name=_get_field(output_fields, "container.name", "container_name"),
        container_image=_get_field(
            output_fields, "container.image.repository", "container.image", "image"
        ),
        # Process fields
        proc_name=_get_field(output_fields, "proc.name", "process"),
        proc_cmdline=_get_field(output_fields, "proc.cmdline", "cmdline"),
        proc_pid=_get_int_field(output_fields, "proc.pid"),
        proc_ppid=_get_int_field(output_fields, "proc.ppid"),
        parent_name=_get_field(output_fields, "proc.pname", "parent"),
        # User fields
        user_name=_get_field(output_fields, "user.name", "user"),
        user_uid=_get_int_field(output_fields, "user.uid"),
        # Network fields
        fd_name=_get_field(output_fields, "fd.name", "connection"),
        fd_type=_get_field(output_fields, "fd.type"),
        output_fields=output_fields,
        tags=data.get("tags", []),
        source=data.get("source", "syscall"),
        hostname=data.get("hostname"),
    )


def _get_field(data: dict[str, Any], *keys: str) -> str | None:
    """Get the first matching field from data."""
    for key in keys:
        if key in data and data[key]:
            return str(data[key])
    return None


def _get_int_field(data: dict[str, Any], *keys: str) -> int | None:
    """Get the first matching integer field from data."""
    for key in keys:
        if key in data and data[key] is not None:
            try:
                return int(data[key])
            except (ValueError, TypeError):
                pass
    return None
