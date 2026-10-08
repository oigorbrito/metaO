/**
 * Validates that a string parameter is safe to pass as a CLI positional ID.
 * Prevents option flag injection (including whitespace-prefixed flags like " --db")
 * and disallows ASCII control characters or whitespace.
 */
export function isSafeCliPositionalId(value: unknown): value is string {
  if (typeof value !== 'string' || value.length === 0 || value.length > 512) {
    return false;
  }
  if (value.trim().startsWith('-')) {
    return false;
  }
  return !/[\s\0-\x1f\x7f]/.test(value);
}

export function isSafeCliReason(value: unknown): value is string {
  if (typeof value !== 'string' || value.trim().length === 0 || value.length > 512) {
    return false;
  }
  if (value.trimStart().startsWith('-')) {
    return false;
  }
  // Disallow ASCII control characters (0-31 and DEL/127) to prevent ANSI escape sequence injection
  // and log/terminal pollution while permitting multi-word reason strings with spaces.
  return !/[\0-\x1f\x7f]/.test(value);
}
