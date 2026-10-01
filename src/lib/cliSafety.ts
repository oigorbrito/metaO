function isSafeCliString(value: unknown): value is string {
  if (typeof value !== 'string' || value.length === 0 || value.length > 512) {
    return false;
  }
  if (value.startsWith('-')) {
    return false;
  }
  return !/[\0\r\n]/.test(value);
}

export function isSafeCliPositionalId(value: unknown): value is string {
  return isSafeCliString(value);
}

export function isSafeCliOptionValue(value: unknown): value is string {
  return isSafeCliString(value);
}
