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

/**
 * Validates that a reason parameter is safe for passing to CLI arguments.
 * Prevents option flag injection (including whitespace-prefixed flags)
 * and disallows ASCII control characters (\x00-\x1f and \x7f) to prevent
 * terminal escape sequence injection, log injection, and obfuscated flags.
 */
export function isSafeCliReason(value: unknown): value is string {
  if (typeof value !== 'string' || value.trim().length === 0 || value.length > 512) {
    return false;
  }
  if (value.trimStart().startsWith('-')) {
    return false;
  }
  return !/[\0-\x1f\x7f]/.test(value);
}
