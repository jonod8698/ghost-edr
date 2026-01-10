"""Quarantine (network isolation) action."""
from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from ghost_enforcer.actions.base import BaseAction

if TYPE_CHECKING:
    from ghost_enforcer.alert_parser import FalcoAlert
    from ghost_enforcer.config import PolicyRule


class QuarantineAction(BaseAction):
    """Isolate a container by disconnecting it from all networks."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.logger = structlog.get_logger()

    async def execute(self, alert: FalcoAlert, policy: PolicyRule) -> bool:
        """Quarantine the container by disconnecting networks."""
        if not alert.container_id:
            self.logger.warning("No container ID in alert, cannot quarantine")
            return False

        self.logger.warning(
            "QUARANTINING CONTAINER",
            container_id=alert.container_id[:12],
            container_name=alert.container_name,
            rule=alert.rule,
            policy=policy.name,
        )

        success = self.runtime.disconnect_network(alert.container_id)

        if success:
            self.logger.info(
                "Container quarantined (networks disconnected)",
                container_id=alert.container_id[:12],
            )
        else:
            self.logger.error(
                "Failed to quarantine container",
                container_id=alert.container_id[:12],
            )

        return success
