"""Webhook notification action."""
from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp
import structlog

from ghost_enforcer.actions.base import BaseAction

if TYPE_CHECKING:
    from ghost_enforcer.alert_parser import FalcoAlert
    from ghost_enforcer.config import PolicyRule


class WebhookAction(BaseAction):
    """Send alert to external webhook."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.logger = structlog.get_logger()

    async def execute(self, alert: FalcoAlert, policy: PolicyRule) -> bool:
        """Send alert to webhook."""
        # Determine webhook URL
        url = policy.webhook_url or self.config.global_webhook_url

        if not url:
            self.logger.warning("No webhook URL configured")
            return False

        payload = {
            "source": "ghost-edr",
            "alert": {
                "rule": alert.rule,
                "priority": alert.priority,
                "output": alert.output,
                "time": alert.time.isoformat(),
                "container_id": alert.container_id,
                "container_name": alert.container_name,
                "container_image": alert.container_image,
                "process": alert.proc_name,
                "cmdline": alert.proc_cmdline,
                "user": alert.user_name,
                "tags": alert.tags,
            },
            "policy": {
                "name": policy.name,
                "action": policy.action.value,
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if 200 <= response.status < 300:
                        self.logger.info(
                            "Webhook notification sent",
                            url=url,
                            status=response.status,
                        )
                        return True
                    else:
                        self.logger.error(
                            "Webhook returned error",
                            url=url,
                            status=response.status,
                        )
                        return False
        except Exception as e:
            self.logger.error(
                "Webhook request failed",
                url=url,
                error=str(e),
            )
            return False
