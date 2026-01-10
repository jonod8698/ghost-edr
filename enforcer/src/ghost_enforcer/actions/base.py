"""Base action class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ghost_enforcer.alert_parser import FalcoAlert
    from ghost_enforcer.config import EnforcerConfig, PolicyRule
    from ghost_enforcer.runtime.base import ContainerRuntime


class BaseAction(ABC):
    """Base class for enforcement actions."""

    def __init__(self, config: EnforcerConfig, runtime: ContainerRuntime) -> None:
        self.config = config
        self.runtime = runtime

    @abstractmethod
    async def execute(self, alert: FalcoAlert, policy: PolicyRule) -> bool:
        """Execute the action.

        Args:
            alert: The Falco alert that triggered this action
            policy: The policy rule that matched

        Returns:
            True if action was successful, False otherwise
        """
        pass
