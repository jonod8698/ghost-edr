"""Main daemon loop for Ghost EDR Enforcer."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog
from aiohttp import web

from ghost_enforcer.alert_parser import parse_falco_alert
from ghost_enforcer.config import EnforcerConfig, default_policies
from ghost_enforcer.policy_engine import PolicyEngine
from ghost_enforcer.runtime.detector import detect_container_runtime

if TYPE_CHECKING:
    from ghost_enforcer.runtime.base import ContainerRuntime


class EnforcerDaemon:
    """Main daemon that receives alerts and takes action."""

    def __init__(self, config: EnforcerConfig) -> None:
        self.config = config
        self.logger = structlog.get_logger()
        self.policy_engine = PolicyEngine(config)
        self.runtime: ContainerRuntime | None = None
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._shutdown_event = asyncio.Event()

        # Apply default policies if none configured
        if not config.policies:
            config.policies = default_policies()
            self.logger.info(
                "No policies configured, using defaults",
                policy_count=len(config.policies),
            )

    async def run(self) -> None:
        """Start the daemon."""
        # Detect and initialize container runtime
        self.runtime = detect_container_runtime(
            preferred=self.config.runtime_type,
            socket_path=self.config.docker_socket,
        )
        self.logger.info(
            "Container runtime detected",
            runtime=self.runtime.name,
            socket=self.runtime.socket_path,
        )

        # Initialize policy engine with runtime
        self.policy_engine.set_runtime(self.runtime)

        # Start HTTP receiver
        await self._start_http_receiver()

        self.logger.info(
            "Ghost EDR Enforcer running",
            port=self.config.receiver_port,
            policies=len(self.config.policies),
            dry_run=self.config.dry_run,
        )

        # Wait for shutdown signal
        await self._shutdown_event.wait()

    async def shutdown(self) -> None:
        """Gracefully shutdown the daemon."""
        if self._shutdown_event.is_set():
            return

        self.logger.info("Shutting down Ghost EDR Enforcer...")

        if self._runner:
            await self._runner.cleanup()

        self._shutdown_event.set()

    async def _start_http_receiver(self) -> None:
        """Start the HTTP webhook receiver."""
        self._app = web.Application()
        self._app.router.add_post("/falco", self._handle_falco_alert)
        self._app.router.add_get("/health", self._handle_health)
        self._app.router.add_get("/metrics", self._handle_metrics)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        site = web.TCPSite(
            self._runner,
            self.config.receiver.host,
            self.config.receiver_port,
        )
        await site.start()

    async def _handle_falco_alert(self, request: web.Request) -> web.Response:
        """Handle incoming Falco alert."""
        try:
            data = await request.json()
            alert = parse_falco_alert(data)

            self.logger.info(
                "Alert received",
                rule=alert.rule,
                priority=alert.priority,
                container_id=alert.container_id,
                container_name=alert.container_name,
            )

            # Process through policy engine
            await self.policy_engine.process_alert(alert)

            return web.Response(status=200, text="OK")

        except Exception as e:
            self.logger.error("Failed to process alert", error=str(e))
            return web.Response(status=500, text=str(e))

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response(
            {
                "status": "healthy",
                "runtime": self.runtime.name if self.runtime else "unknown",
                "policies": len(self.config.policies),
            }
        )

    async def _handle_metrics(self, request: web.Request) -> web.Response:
        """Prometheus-style metrics endpoint."""
        metrics = self.policy_engine.get_metrics()
        return web.json_response(metrics)
