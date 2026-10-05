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
