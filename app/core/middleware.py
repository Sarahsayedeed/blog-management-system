import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Log in structured JSON format via loguru
        logger.bind(
            http_method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2),
        ).info("API Request Processed")
        
        return response
