/**
 * Generate a random opaque idempotency key (8..128 characters ASCII, no spaces)
 */
export function generateIdempotencyKey(prefix: string = 'chk'): string {
  const timestamp = Date.now().toString(36);
  const randomPart = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
  return `${prefix}-${timestamp}-${randomPart}`;
}
