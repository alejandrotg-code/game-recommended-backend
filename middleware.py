import time
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_history = {}  # IP -> lista de marcas de tiempo

    async def dispatch(self, request: Request, call_next):
        # Omitir el límite de peticiones para la raíz "/"
        if request.url.path == "/":
            return await call_next(request)
            
        # Detectar la IP real del cliente
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        # Limpiar registros antiguos
        if client_ip in self.request_history:
            self.request_history[client_ip] = [
                t for t in self.request_history[client_ip]
                if now - t < self.window_seconds
            ]
        else:
            self.request_history[client_ip] = []
            
        # Verificar límite
        if len(self.request_history[client_ip]) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - self.request_history[client_ip][0]))
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Demasiadas peticiones. Por favor, intentalo de nuevo mas tarde.",
                    "retry_after_seconds": retry_after
                }
            )
            
        self.request_history[client_ip].append(now)
        return await call_next(request)
