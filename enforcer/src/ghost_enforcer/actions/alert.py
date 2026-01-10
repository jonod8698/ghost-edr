"""Alert-only action (logging)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from ghost_enforcer.actions.base import BaseAction

if TYPE_CHECKING:
    from ghost_enforcer.alert_parser import FalcoAlert
    from ghost_enforcer.config import PolicyRule


class AlertAction(BaseAction):
    """Log an alert without taking enforcement action."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.logger = structlog.get_logger()

    async def execute(self, alert: FalcoAlert, policy: PolicyRule) -> bool:
        """Log the alert."""
        self.logger.warning(
            "SECURITY ALERT",
            rule=alert.rule,
            priority=alert.priority,
            container_id=alert.container_id[:12] if alert.container_id else None,
            container_name=alert.container_name,
            container_image=alert.container_image,
            process=alert.proc_name,
            cmdline=alert.proc_cmdline,
            user=alert.user_name,
            connection=alert.fd_name,
            tags=alert.tags,
            policy=policy.name,
        )

        return True
