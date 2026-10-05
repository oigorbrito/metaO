export function isSafeCliPositionalId(value: unknown): value is string {
  if (typeof value !== 'string' || value.length === 0 || value.length > 512) {
    return false;
  }
  if (value.startsWith('-')) {
    return false;
  }
  return !/[\0\r\n]/.test(value);
}

export function isSafeCliReason(value: unknown): value is string {
  if (typeof value !== 'string' || value.trim().length === 0 || value.length > 512) {
    return false;
  }
  if (value.trimStart().startsWith('-')) {
    return false;
  }
  return !/[\0\r\n]/.test(value);
}
