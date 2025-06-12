from cachetools import TTLCache

# Simple in-memory caches for API responses. TTL defaults to 1 hour.
EMPLOYEE_CACHE = TTLCache(maxsize=64, ttl=3600)
LEAVE_TYPES_CACHE = TTLCache(maxsize=64, ttl=3600)
LEAVE_HISTORY_CACHE = TTLCache(maxsize=64, ttl=3600)
LEAVE_BALANCE_CACHE = TTLCache(maxsize=256, ttl=3600)
