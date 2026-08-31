## 2025-05-18 - Avoid micro-optimizing low-level loops without profiling bottlenecks
**Learning:** In python-based control plane evaluations like `evaluate_acceptance`, per-item gate evaluation allocation overhead (e.g. tuple construction vs individual gate checks) accounts for ~6-16% speedup. Avoid premature or unreadable micro-optimizations that don't maintain explicit semantics.
**Action:** Focus optimizations on clean reductions of unnecessary intermediate allocations and redundant iterations while keeping code perfectly readable.
