export function fitsPasswordBytes(password: string): boolean {
  return new TextEncoder().encode(password).length <= 72;
}
