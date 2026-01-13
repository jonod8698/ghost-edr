"""Configuration management for Ghost EDR Enforcer."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Enforcement action types."""

    ALERT = "alert"
    WEBHOOK = "webhook"


class Priority(str, Enum):
    """Alert priority levels (matches Falco priorities)."""

    EMERGENCY = "emergency"
    ALERT = "alert"
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    NOTICE = "notice"
    INFORMATIONAL = "informational"
    DEBUG = "debug"


# Priority ordering for comparison (higher = more severe)
PRIORITY_ORDER: dict[Priority, int] = {
    Priority.DEBUG: 0,
    Priority.INFORMATIONAL: 1,
    Priority.NOTICE: 2,
    Priority.WARNING: 3,
    Priority.ERROR: 4,
    Priority.CRITICAL: 5,
    Priority.ALERT: 6,
    Priority.EMERGENCY: 7,
}


class PolicyRule(BaseModel):
    """A single policy rule."""

    name: str
    description: str | None = None

    # Matching conditions
    rule_patterns: list[str] = Field(default_factory=list)
    priority_min: Priority = Priority.WARNING
    container_patterns: list[str] = Field(default_factory=list)
    image_patterns: list[str] = Field(default_factory=list)
    exclude_containers: list[str] = Field(default_factory=list)

    # Actions
    action: ActionType = ActionType.ALERT
    webhook_url: str | None = None

    # Rate limiting
    cooldown_seconds: int = 60


class ReceiverConfig(BaseModel):
    """Receiver configuration."""

    type: str = "http"
    port: int = 8766
    host: str = "0.0.0.0"


class EnforcerConfig(BaseModel):
    """Main configuration for Ghost EDR Enforcer."""

    # General settings
    log_level: str = "info"
    dry_run: bool = False

    # Receiver settings
    receiver: ReceiverConfig = Field(default_factory=ReceiverConfig)
    receiver_port: int = 8766

    # Runtime detection
    runtime_auto_detect: bool = True
    runtime_type: str | None = None
    docker_socket: str | None = None

    # Default policy
    default_action: ActionType = ActionType.ALERT

    # Policy rules (evaluated in order)
    policies: list[PolicyRule] = Field(default_factory=list)

    # Webhook for all alerts
    global_webhook_url: str | None = None

    # Excluded containers (never take action on these)
    excluded_containers: list[str] = Field(
        default_factory=lambda: ["ghost-mole"]
    )

    # Metrics
    enable_metrics: bool = False
    metrics_port: int = 9090


def load_config(path: Path) -> EnforcerConfig:
    """Load configuration from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    # Handle policies
    if "policies" in data:
        data["policies"] = [
            PolicyRule(**p) if isinstance(p, dict) else p for p in data["policies"]
        ]

    # Handle receiver
    if "receiver" in data and isinstance(data["receiver"], dict):
        data["receiver"] = ReceiverConfig(**data["receiver"])

    return EnforcerConfig(**data)


def default_policies() -> list[PolicyRule]:
    """Return default policy rules."""
    return [
        PolicyRule(
            name="critical-threats",
            description="Alert on critical security threats",
            priority_min=Priority.CRITICAL,
            rule_patterns=[
                "Ghost EDR - Reverse Shell*",
                "Ghost EDR - Crypto Miner*",
                "Ghost EDR - Container Escape*",
                "Ghost EDR - Nsenter*",
                "Ghost EDR - Kernel Module*",
                "Ghost EDR - Netcat Reverse Shell*",
                "Ghost EDR - Download and Execute*",
                "Ghost EDR - Process Injection*",
            ],
            action=ActionType.ALERT,
            cooldown_seconds=0,
        ),
        PolicyRule(
            name="high-threats",
            description="Alert on high priority threats",
            priority_min=Priority.ERROR,
            rule_patterns=[
                "Ghost EDR - Mining Pool Connection*",
                "Ghost EDR - Mount in Privileged*",
                "Ghost EDR - Shell Spawned from Web*",
                "Ghost EDR - Docker Socket Access*",
            ],
            action=ActionType.ALERT,
            cooldown_seconds=30,
        ),
        PolicyRule(
            name="suspicious-activity",
            description="Alert on suspicious activity",
            priority_min=Priority.WARNING,
            action=ActionType.ALERT,
            cooldown_seconds=60,
        ),
    ]
