from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    def __init__(self, limit: int = 90, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, request: Request) -> None:
        forwarded = request.headers.get("x-forwarded-for", "")
        client_id = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
        now = monotonic()
        entries = self.requests[client_id]
        while entries and entries[0] < now - self.window_seconds:
            entries.popleft()
        if len(entries) >= self.limit:
            raise HTTPException(status_code=429, detail="Too many requests. Please retry shortly.")
        entries.append(now)

