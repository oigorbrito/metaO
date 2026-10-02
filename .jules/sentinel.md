## 2025-03-30 - CLI Option Argument Injection Prevention
**Vulnerability:** API endpoints accepting user-controlled strings (e.g., `reason`) for CLI execution could allow option injection or argument confusion if values start with hyphens or contain control characters/newlines.
**Learning:** `execFile` avoids shell parsing but arguments starting with `-` can still be parsed as flags by downstream CLI argument parsers (like Python's `argparse`), leading to option confusion or unexpected flag execution.
**Prevention:** Always validate and sanitize option argument strings passed to CLI binaries using `isSafeCliOptionValue` to disallow leading hyphens, control characters, and excess length.
