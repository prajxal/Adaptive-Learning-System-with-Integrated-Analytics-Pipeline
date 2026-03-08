import time
from fastapi import Request, HTTPException

class RateLimiter:
    """
    In-memory fixed window rate limiter dependency.
    """
    def __init__(self, calls: int, period: int):
        self.calls = calls
        self.period = period
        self.history = {}

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        if client_ip not in self.history:
            self.history[client_ip] = []
            
        # Optional: cleanup loop to prevent memory leaks in production
        # For MVP, clean up when this IP accesses.
        self.history[client_ip] = [t for t in self.history[client_ip] if now - t < self.period]
        
        if len(self.history[client_ip]) >= self.calls:
            raise HTTPException(status_code=429, detail="Too Many Requests")
            
        self.history[client_ip].append(now)
