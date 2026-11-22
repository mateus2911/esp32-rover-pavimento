import asyncio
import json
from typing import Any
import websockets
from websockets.protocol import State


class RoverBridge:
    """Ponte entre o FastAPI e o servidor WebSocket da ESP32 (porta 82)."""

    def __init__(
        self,
        simulation_mode: bool = True,
        esp32_ws_url: str = "ws://192.168.4.1:82",
        connect_timeout: float = 0.5,
    ):
        self.simulation_mode = simulation_mode
        self.esp32_ws_url = esp32_ws_url
        self.connect_timeout = connect_timeout
        self._last_logged: tuple[int, int] | None = None
        self._ws: Any = None
        self._ws_lock: asyncio.Lock | None = None
        self._connection_error_logged = False

    def _get_lock(self) -> asyncio.Lock:
        if self._ws_lock is None:
            self._ws_lock = asyncio.Lock()
        return self._ws_lock

    @staticmethod
    def _is_ws_open(ws: Any) -> bool:
        if ws is None:
            return False
        state = getattr(ws, "state", None)
        if state is not None:
            return state is State.OPEN
        open_attr = getattr(ws, "open", None)
        if open_attr is not None:
            return bool(open_attr)
        return True

    @staticmethod
    def clamp_pwm(value: int) -> int:
        try:
            int_value = int(value)
        except (TypeError, ValueError):
            return 0
        return max(-255, min(255, int_value))

    async def _ensure_connected(self) -> Any:
        if self._is_ws_open(self._ws):
            return self._ws

        await self._discard_connection()
        self._ws = await websockets.connect(
            self.esp32_ws_url,
            open_timeout=self.connect_timeout,
            close_timeout=self.connect_timeout,
            ping_interval=None,
        )
        self._connection_error_logged = False
        return self._ws

    async def _discard_connection(self) -> None:
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            finally:
                self._ws = None

    async def close(self) -> None:
        """Fecha a conexão WebSocket persistente com a ESP32."""
        async with self._get_lock():
            await self._discard_connection()

    async def send_command(self, left: int, right: int) -> dict[str, int]:
        safe_left = self.clamp_pwm(left)
        safe_right = self.clamp_pwm(right)
        payload = {"left": safe_left, "right": safe_right}

        if self.simulation_mode:
            # Imprime no terminal apenas quando os valores mudarem (evita poluir o log a cada 150ms)
            if (safe_left, safe_right) != self._last_logged:
                print(f"[SIMULAÇÃO MOTOR] Enviando para ESP32: {payload}")
                self._last_logged = (safe_left, safe_right)
            return payload

        # Etapa 2 (hardware real): reutiliza conexão WebSocket persistente com reconexão automática
        message = json.dumps(payload)
        async with self._get_lock():
            for attempt in range(2):
                try:
                    ws = await self._ensure_connected()
                    await ws.send(message)
                    self._connection_error_logged = False
                    break
                except Exception as exc:
                    await self._discard_connection()
                    if attempt == 1 and not self._connection_error_logged:
                        print(f"[AVISO ESP32] Falha ao enviar comando: {exc}")
                        self._connection_error_logged = True

        return payload
