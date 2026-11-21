from __future__ import annotations

import asyncio
import json
import logging

import websockets

from backend.models import DriveCommand

logger = logging.getLogger(__name__)


class Esp32ControlClient:
    """Cliente WebSocket que encaminha comandos de direção e mantém estado seguro."""

    def __init__(self, ws_url: str, mock_mode: bool = True) -> None:
        self.ws_url = ws_url
        self.mock_mode = mock_mode
        self.connected = mock_mode
        self.last_command = DriveCommand(left=0, right=0)
        self._ws = None
        self._lock = asyncio.Lock()

    async def send_command(self, cmd: DriveCommand) -> None:
        self.last_command = cmd
        if self.mock_mode:
            self.connected = True
            return

        async with self._lock:
            try:
                if self._ws is None:
                    self._ws = await asyncio.wait_for(
                        websockets.connect(self.ws_url),
                        timeout=1.5,
                    )
                    self.connected = True
                await self._ws.send(json.dumps(cmd.model_dump()))
            except Exception as exc:
                logger.warning("Erro ao enviar comando para ESP32 (%s): %s", self.ws_url, exc)
                self.connected = False
                await self.close()

    async def emergency_stop(self) -> None:
        await self.send_command(DriveCommand(left=0, right=0))

    async def close(self) -> None:
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        if not self.mock_mode:
            self.connected = False
