---
trigger: always_on
---

---
trigger: model_decision
description: "Apply async, concurrency, and performance guidelines for Python code."
---

# Python Performance & Async Guidelines

## 1. Asynchronous Code (`asyncio`)
- Do not call blocking operations (synchronous HTTP clients like `requests`, `time.sleep()`, heavy disk I/O) inside async functions; use `aiohttp`/`httpx`, `asyncio.sleep()`, or offload to thread pools via `asyncio.to_thread()`.
- Explicitly handle timeouts for every remote request (`asyncio.timeout`).

## 2. Memory & Computations
- Use generator expressions (`(x for x in iterable)`) when streaming large datasets instead of instantiating full lists in memory.
- Prefer built-in collections and operations (`set` for lookups, `collections.deque` for FIFO queues) rather than custom implementations.