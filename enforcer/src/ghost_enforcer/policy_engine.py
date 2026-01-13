"""Policy evaluation and enforcement engine."""
from __future__ import annotations

import fnmatch
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

from ghost_enforcer.config import ActionType, EnforcerConfig, PolicyRule, Priority, PRIORITY_ORDER

if TYPE_CHECKING:
    from ghost_enforcer.alert_parser import FalcoAlert
    from ghost_enforcer.runtime.base import ContainerRuntime


@dataclass
class PolicyMetrics:
    """Metrics for policy engine."""

    alerts_received: int = 0
    alerts_matched: int = 0
    actions_executed: dict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    actions_skipped_cooldown: int = 0
    actions_skipped_excluded: int = 0
    actions_failed: int = 0


class PolicyEngine:
    """Evaluates alerts against policies and executes actions."""

    def __init__(self, config: EnforcerConfig) -> None:
        self.config = config
        self.logger = structlog.get_logger()
        self.runtime: ContainerRuntime | None = None
        self.metrics = PolicyMetrics()

        # Cooldown tracking: (container_id, policy_name) -> last_action_time
        self._cooldowns: dict[str, float] = {}

        # Action handlers (initialized in set_runtime)
        self._actions: dict[ActionType, Any] = {}

    def set_runtime(self, runtime: ContainerRuntime) -> None:
        """Set the container runtime for action execution."""
        self.runtime = runtime

        # Import here to avoid circular imports
        from ghost_enforcer.actions.alert import AlertAction
        from ghost_enforcer.actions.webhook import WebhookAction

        self._actions = {
            ActionType.ALERT: AlertAction(self.config, runtime),
            ActionType.WEBHOOK: WebhookAction(self.config, runtime),
        }

    async def process_alert(self, alert: FalcoAlert) -> None:
        """Process an alert through the policy engine."""
        self.metrics.alerts_received += 1

        # Check if container is excluded
        if self._is_excluded(alert):
            self.metrics.actions_skipped_excluded += 1
            self.logger.debug(
                "Container excluded from enforcement",
                container_name=alert.container_name,
            )
            return

        # Find matching policy
        policy = self._find_matching_policy(alert)

        if not policy:
            self.logger.debug(
                "No policy matched",
                rule=alert.rule,
                priority=alert.priority,
            )
            return

        self.metrics.alerts_matched += 1

        # Check cooldown
        if not self._check_cooldown(alert, policy):
            self.metrics.actions_skipped_cooldown += 1
            self.logger.debug(
                "Action skipped due to cooldown",
                container_id=alert.container_id[:12] if alert.container_id else None,
                policy=policy.name,
            )
            return

        # Execute action
        await self._execute_action(alert, policy)

    def _is_excluded(self, alert: FalcoAlert) -> bool:
        """Check if container is in the exclusion list."""
        if not alert.container_name:
            return False

        for pattern in self.config.excluded_containers:
            if fnmatch.fnmatch(alert.container_name, pattern):
                return True

        return False

    def _find_matching_policy(self, alert: FalcoAlert) -> PolicyRule | None:
        """Find the first matching policy for an alert."""
        for policy in self.config.policies:
            if self._matches_policy(alert, policy):
                return policy
        return None

    def _matches_policy(self, alert: FalcoAlert, policy: PolicyRule) -> bool:
        """Check if an alert matches a policy."""
        # Check priority
        try:
            alert_priority = Priority(alert.priority.lower())
        except ValueError:
            alert_priority = Priority.WARNING

        alert_order = PRIORITY_ORDER.get(alert_priority, 0)
        policy_order = PRIORITY_ORDER.get(policy.priority_min, 0)

        if alert_order < policy_order:
            return False

        # Check rule patterns (if specified)
        if policy.rule_patterns:
            matched = any(
                fnmatch.fnmatch(alert.rule, pattern)
                for pattern in policy.rule_patterns
            )
            if not matched:
                return False

        # Check container patterns (if specified)
        if policy.container_patterns and alert.container_name:
            matched = any(
                fnmatch.fnmatch(alert.container_name, pattern)
                for pattern in policy.container_patterns
            )
            if not matched:
                return False

        # Check image patterns (if specified)
        if policy.image_patterns and alert.container_image:
            matched = any(
                fnmatch.fnmatch(alert.container_image, pattern)
                for pattern in policy.image_patterns
            )
            if not matched:
                return False

        # Check exclusions within policy
        if policy.exclude_containers and alert.container_name:
            if any(
                fnmatch.fnmatch(alert.container_name, pattern)
                for pattern in policy.exclude_containers
            ):
                return False

        return True

    def _check_cooldown(self, alert: FalcoAlert, policy: PolicyRule) -> bool:
        """Check if action is allowed based on cooldown."""
        if not alert.container_id:
            return True

        if policy.cooldown_seconds <= 0:
            return True

        key = f"{alert.container_id}:{policy.name}"
        last_action = self._cooldowns.get(key, 0)
        now = time.time()

        if now - last_action < policy.cooldown_seconds:
            return False

        # Update cooldown
        self._cooldowns[key] = now
        return True

    async def _execute_action(self, alert: FalcoAlert, policy: PolicyRule) -> None:
        """Execute the action specified by the policy."""
        action_type = policy.action

        self.logger.warning(
            "Executing policy action",
            policy=policy.name,
            action=action_type.value,
            container_id=alert.container_id[:12] if alert.container_id else None,
            container_name=alert.container_name,
            rule=alert.rule,
        )

        if self.config.dry_run:
            self.logger.info(
                "DRY RUN: Would execute action",
                action=action_type.value,
                container_id=alert.container_id[:12] if alert.container_id else None,
            )
            self.metrics.actions_executed[action_type.value] += 1
            return

        # Get action handler
        handler = self._actions.get(action_type)
        if not handler:
            self.logger.error("Unknown action type", action=action_type)
            return

        try:
            success = await handler.execute(alert, policy)
            if success:
                self.metrics.actions_executed[action_type.value] += 1
            else:
                self.metrics.actions_failed += 1
        except Exception as e:
            self.logger.error(
                "Action execution failed",
                action=action_type.value,
                error=str(e),
            )
            self.metrics.actions_failed += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics."""
        return {
            "alerts_received": self.metrics.alerts_received,
            "alerts_matched": self.metrics.alerts_matched,
            "actions_executed": dict(self.metrics.actions_executed),
            "actions_skipped_cooldown": self.metrics.actions_skipped_cooldown,
            "actions_skipped_excluded": self.metrics.actions_skipped_excluded,
            "actions_failed": self.metrics.actions_failed,
        }
