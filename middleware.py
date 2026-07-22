import time
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Límite máximo de IPs rastreadas para prevenir memory exhaustion
MAX_TRACKED_IPS = 10_000
# Cada cuántas requests se ejecuta la limpieza de IPs expiradas
CLEANUP_EVERY = 500


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_history: dict[str, list[float]] = {}
        self._request_counter = 0

    def _extract_client_ip(self, request: Request) -> str:
        """Extrae la IP real del cliente, respetando proxies reverso."""
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_expired(self, now: float) -> None:
        """Elimina IPs cuyas ventanas de tiempo ya expiraron."""
        expired_ips = [
            ip for ip, timestamps in self.request_history.items()
            if not timestamps or (now - timestamps[-1]) >= self.window_seconds
        ]
        for ip in expired_ips:
            del self.request_history[ip]

    def _enforce_max_tracked_ips(self) -> None:
        """Si se supera el límite de IPs rastreadas, elimina las más antiguas."""
        if len(self.request_history) <= MAX_TRACKED_IPS:
            return
        # Ordenar por último timestamp y quedarse con el 80%
        sorted_ips = sorted(
            self.request_history.keys(),
            key=lambda ip: self.request_history[ip][-1] if self.request_history[ip] else 0
        )
        to_remove = sorted_ips[:len(self.request_history) - int(MAX_TRACKED_IPS * 0.8)]
        for ip in to_remove:
            del self.request_history[ip]
        logger.warning(
            "Rate limiter: %d IPs expiradas limpiadas por exceso de memoria", len(to_remove)
        )

    async def dispatch(self, request: Request, call_next):
        # Omitir el límite para la raíz
        if request.url.path == "/":
            return await call_next(request)

        client_ip = self._extract_client_ip(request)
        now = time.time()

        # Limpieza periódica de registros expirados
        self._request_counter += 1
        if self._request_counter % CLEANUP_EVERY == 0:
            self._cleanup_expired(now)
            self._enforce_max_tracked_ips()

        # Obtener o inicializar la ventana del cliente
        timestamps = self.request_history.get(client_ip)
        if timestamps is None:
            self.request_history[client_ip] = timestamps = []
        else:
            # Filtrar timestamps fuera de la ventana
            self.request_history[client_ip] = timestamps = [
                t for t in timestamps if now - t < self.window_seconds
            ]

        # Verificar límite
        if len(timestamps) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - timestamps[0]))
            logger.warning(
                "Rate limit bloqueado: IP=%s rutas_recientes=%d",
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
        return await call_next(request)
