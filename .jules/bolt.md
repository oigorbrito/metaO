## 2026-03-30 - Deferred Process-Parallelism Optimizations in Release Cycles
**Learning:** Parallelizing sequential child process calls (`cli(...)`) with `Promise.all` alters operational failure semantics (starting both subprocesses instead of aborting after the first fails) and requires reproducible benchmark artifacts and failure-semantics tests prior to release convergence.
**Action:** When introducing process concurrency in Express/Node control-plane CLI endpoints, include explicit failure-semantics tests and empirical process-pressure benchmarks.
