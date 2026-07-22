import time
import logging
from cachetools import TTLCache
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 30, window_seconds: int = 60, max_ips: int = 10_000):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Utiliza TTLCache para limitar el número máximo de IPs rastreadas y su tiempo de vida
        self.request_history: TTLCache[str, list[float]] = TTLCache(maxsize=max_ips, ttl=window_seconds)

    def _extract_client_ip(self, request: Request) -> str:
        """Extrae la IP real del cliente, respetando proxies reverso."""
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        # Omitir el límite para la raíz
        if request.url.path == "/":
            return await call_next(request)

        client_ip = self._extract_client_ip(request)
        now = time.time()

        # Obtener timestamps del cliente o crear nueva lista
        timestamps = self.request_history.get(client_ip)
        if timestamps is None:
            timestamps = []
        else:
            # Filtrar marcas de tiempo fuera de la ventana activa
            timestamps = [t for t in timestamps if now - t < self.window_seconds]

        # Verificar límite
        if len(timestamps) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - timestamps[0]))
            logger.warning(
                "Rate limit bloqueado: IP=%s peticiones_recientes=%d",
                client_ip, len(timestamps),
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Demasiadas peticiones. Por favor, intentalo de nuevo mas tarde.",
                    "retry_after_seconds": max(retry_after, 1),
                },
            )

        timestamps.append(now)
        self.request_history[client_ip] = timestamps
        return await call_next(request)

