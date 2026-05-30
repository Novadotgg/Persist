import json
import hashlib
import redis
import structlog
from typing import Dict, Any
from app.core.config import settings

logger = structlog.get_logger()

import time

class InMemoryRedisFallback:
    def __init__(self):
        self._store = {}
        self._expires = {}
        logger.warning("Initializing InMemoryRedisFallback as Redis is unreachable.")

    def _is_expired(self, key: str) -> bool:
        if key in self._expires:
            if time.time() > self._expires[key]:
                del self._store[key]
                del self._expires[key]
                return True
        return False

    def set(self, key: str, value: str, ex=None, nx=False) -> bool:
        self._is_expired(key)
        if nx and key in self._store:
            return False
        
        self._store[key] = value
        if ex:
            self._expires[key] = time.time() + ex
        elif key in self._expires:
            del self._expires[key]
        return True

    def get(self, key: str) -> bytes:
        if self._is_expired(key):
            return None
        val = self._store.get(key)
        if val is None:
            return None
        if isinstance(val, str):
            return val.encode('utf-8')
        return val

    def delete(self, *keys) -> int:
        count = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                if key in self._expires:
                    del self._expires[key]
                count += 1
        return count

    def ping(self) -> bool:
        return True

class RedisClientProxy:
    def __init__(self):
        self._local_redis = None
        self._fallback = None

    @property
    def client(self):
        if self._local_redis is not None:
            return self._local_redis
        if self._fallback is not None:
            return self._fallback

        # Try to connect to Redis
        try:
            client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Test connection
            client.ping()
            self._local_redis = client
            logger.info("Successfully connected to Redis.")
            return self._local_redis
        except Exception as e:
            logger.warning("Failed to connect to Redis, falling back to in-memory store", error=str(e))
            self._fallback = InMemoryRedisFallback()
            return self._fallback

    def set(self, *args, **kwargs):
        try:
            return self.client.set(*args, **kwargs)
        except Exception as e:
            logger.warning("Redis operation failed, switching to in-memory fallback", error=str(e))
            self._fallback = InMemoryRedisFallback()
            self._local_redis = None
            return self._fallback.set(*args, **kwargs)

    def get(self, *args, **kwargs):
        try:
            return self.client.get(*args, **kwargs)
        except Exception as e:
            logger.warning("Redis operation failed, switching to in-memory fallback", error=str(e))
            self._fallback = InMemoryRedisFallback()
            self._local_redis = None
            return self._fallback.get(*args, **kwargs)

    def delete(self, *args, **kwargs):
        try:
            return self.client.delete(*args, **kwargs)
        except Exception as e:
            logger.warning("Redis operation failed, switching to in-memory fallback", error=str(e))
            self._fallback = InMemoryRedisFallback()
            self._local_redis = None
            return self._fallback.delete(*args, **kwargs)

    def ping(self, *args, **kwargs):
        try:
            return self.client.ping(*args, **kwargs)
        except Exception as e:
            return False

    def __bool__(self):
        return True

redis_client = RedisClientProxy()


def get_event_id(source: str, payload: Dict[str, Any]) -> str:
    """
    Generate a stable, unique event identifier based on payload elements (id, message_id, etc.)
    or a SHA-256 hash of the payload content as a fallback.
    """
    # 1. Search for common unique ID keys
    for key in ["id", "message_id", "issue_id", "event_id", "uid"]:
        if key in payload and payload[key]:
            val = str(payload[key]).strip()
            if val:
                return f"{source}:{val}"
    
    # 2. Heuristic fallback: deterministic SHA-256 hash of payload
    try:
        serialized = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(serialized.encode()).hexdigest()
        return f"{source}:hash:{payload_hash}"
    except Exception as e:
        logger.error("Failed to serialize payload for hash ID generation", error=str(e))
        # Last resort fallback: random or timestamp-based, but we want de-duplication to be deterministic,
        # so return empty string (which means de-duplication is skipped)
        return ""

def is_duplicate_event(event_id: str, expiration_seconds: int = 86400) -> bool:
    """
    Checks if an event_id exists in Redis.
    If it does not exist, sets the key with expiration and returns False.
    If it exists, returns True.
    If Redis is unreachable, log error and allow the event (return False).
    """
    if not event_id:
        return False

    key = f"processed_event:{event_id}"
    
    if redis_client is None:
        logger.warning("Redis client is uninitialized. Skipping de-duplication.", key=key)
        return False

    try:
        # set with ex (expiry in seconds) and nx=True (set only if not exists)
        is_new = redis_client.set(key, "1", ex=expiration_seconds, nx=True)
        # set returns True/1 if set was successful (i.e. key did not exist)
        # if not is_new, it means key already exists (it is a duplicate)
        return not is_new
    except redis.RedisError as e:
        logger.error("Redis error during idempotency check", key=key, error=str(e))
        return False
