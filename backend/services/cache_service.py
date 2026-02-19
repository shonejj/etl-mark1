"""Redis cache service for preview caching, rate limiting, pub/sub."""

import json
from typing import Optional, Any
import redis

from backend.core.config import settings


class CacheService:
    """Redis-backed caching service."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=100,
            )
        return self._client

    def get(self, key: str) -> Optional[str]:
        """Get a cached value by key."""
        try:
            return self.client.get(key)
        except redis.ConnectionError:
            return None

    def set(self, key: str, value: str, ttl_seconds: int = 600) -> None:
        """Set a cached value with TTL."""
        try:
            self.client.setex(key, ttl_seconds, value)
        except redis.ConnectionError:
            pass  # Cache failures are non-fatal

    def get_json(self, key: str) -> Optional[Any]:
        """Get and parse a JSON cached value."""
        raw = self.get(key)
        if raw:
            return json.loads(raw)
        return None

    def set_json(self, key: str, value: Any, ttl_seconds: int = 600) -> None:
        """Serialize and cache a JSON value."""
        self.set(key, json.dumps(value, default=str), ttl_seconds)

    def delete(self, key: str) -> None:
        """Delete a cached key."""
        try:
            self.client.delete(key)
        except redis.ConnectionError:
            pass

    def invalidate_pattern(self, pattern: str) -> None:
        """Delete all keys matching a pattern."""
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
        except redis.ConnectionError:
            pass

    def publish(self, channel: str, message: str) -> None:
        """Publish a message to a Redis channel (for WebSocket fanout)."""
        try:
            self.client.publish(channel, message)
        except redis.ConnectionError:
            pass

    def health_check(self) -> bool:
        """Check if Redis is reachable."""
        try:
            return self.client.ping()
        except redis.ConnectionError:
            return False


cache_service = CacheService()
