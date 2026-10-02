## 2026-03-30 - Leading Whitespace Flag Injection Bypass in CLI Input Validation
**Vulnerability:** `isSafeCliPositionalId` checked `value.startsWith('-')` without trimming leading whitespace, allowing flag injection strings such as `" --db"` or `"\t-h"` to pass input validation.
**Learning:** Checking for option flags with `startsWith('-')` on untrimmed strings allows whitespace prefixing bypasses.
**Prevention:** Always check trimmed strings (`value.trim().startsWith('-')`) and enforce strict character sets disallowing untrimmed whitespace (`/\s/`) in positional identifier validation functions.
