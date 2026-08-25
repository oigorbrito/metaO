# Roadmap 8 — A04 Authoritative Freshness Primitives

Status: IMPLEMENTED / EXECUTABLE VALIDATION PENDING.

This slice introduces a framework-neutral trusted-clock freshness boundary without modifying the current terminal acceptance path.

Frozen rules:

```text
CALLER_TIMESTAMP = CLAIM
TRUSTED_CLOCK = AUTHORITATIVE TIME SOURCE
FUTURE EVIDENCE -> BLOCK
EXPIRED/OVER-AGE EVIDENCE -> STALE
FRESHNESS_PASS != METAO_ACCEPTED
```

No new dependency, no cryptography, no terminal-path integration, no merge authorization.
