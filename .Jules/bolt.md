# Bolt's Journal

## 2026-03-30 - Sub-process Fanout Bottlenecks in CLI-backed Web Backends
**Learning:** In architectures where an Express server delegates CLI operations to Python scripts via `execFile`, querying sub-resources per item sequentially multiplies cold-start process spawning overhead ($O(N)$ serial process spawns).
**Action:** Always batch sub-process calls or execute per-item sub-process calls concurrently using `Promise.all` when querying per-entity details from CLI backends.
