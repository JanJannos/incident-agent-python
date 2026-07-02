---
name: caching-strategy
description: >
  Implement efficient caching strategies using Redis, Memcached, CDN, and cache
  invalidation patterns. Use when optimizing application performance, reducing
  database load, or improving response times.
---

# Caching Strategy

## Table of Contents

- [Overview](#overview)
- [When to Use](#when-to-use)
- [Quick Start](#quick-start)
- [Reference Guides](#reference-guides)
- [Best Practices](#best-practices)

## Overview

Implement effective caching strategies to improve application performance, reduce latency, and decrease load on backend systems.

## When to Use

- Reducing database query load
- Improving API response times
- Handling high traffic loads
- Caching expensive computations
- Storing session data
- CDN integration for static assets
- Implementing distributed caching
- Rate limiting and throttling

## Quick Start

Minimal working example (Python + Redis):

```python
import json
import redis.asyncio as redis

class CacheService:
    def __init__(self, redis_url: str = "redis://localhost:6379", default_ttl: int = 3600):
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._default_ttl = default_ttl

    async def get(self, key: str) -> dict | None:
        raw = await self._redis.get(key)
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: dict, ttl: int | None = None) -> None:
        await self._redis.set(key, json.dumps(value), ex=ttl or self._default_ttl)
```

## Reference Guides

| Guide | Contents |
|---|---|
| [Cache Decorator (Python)](references/cache-decorator-python.md) | Cache Decorator (Python) |
| [Multi-Level Cache](references/multi-level-cache.md) | Multi-Level Cache |
| [Cache Invalidation Strategies](references/cache-invalidation-strategies.md) | Cache Invalidation Strategies |
| [HTTP Caching Headers](references/http-caching-headers.md) | HTTP Caching Headers |

## Best Practices

### ✅ DO

- Set appropriate TTL values
- Implement cache warming for critical data
- Use cache-aside pattern for reads
- Monitor cache hit rates
- Implement graceful degradation on cache failure
- Use compression for large cached values
- Namespace cache keys properly
- Implement cache stampede prevention
- Use consistent hashing for distributed caching
- Monitor cache memory usage

### ❌ DON'T

- Cache everything indiscriminately
- Use caching as a fix for poor database design
- Store sensitive data without encryption
- Forget to handle cache misses
- Set TTL too long for frequently changing data
- Ignore cache invalidation strategies
- Cache without monitoring
- Store large objects without consideration
