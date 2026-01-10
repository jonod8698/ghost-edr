"""Kill container action."""
from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from ghost_enforcer.actions.base import BaseAction

if TYPE_CHECKING:
    from ghost_enforcer.alert_parser import FalcoAlert
    from ghost_enforcer.config import PolicyRule


class KillAction(BaseAction):
    """Kill a container."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.logger = structlog.get_logger()

    async def execute(self, alert: FalcoAlert, policy: PolicyRule) -> bool:
        """Kill the container that triggered the alert."""
        if not alert.container_id:
            self.logger.warning("No container ID in alert, cannot kill")
            return False

        self.logger.critical(
            "KILLING CONTAINER",
            container_id=alert.container_id[:12],
            container_name=alert.container_name,
            rule=alert.rule,
            policy=policy.name,
        )

        success = self.runtime.kill_container(alert.container_id)

        if success:
            self.logger.info(
                "Container killed successfully",
                container_id=alert.container_id[:12],
            )
        else:
            self.logger.error(
                "Failed to kill container",
                container_id=alert.container_id[:12],
            )

        return success
