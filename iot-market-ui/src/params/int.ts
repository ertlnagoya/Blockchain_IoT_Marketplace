export function match(value: string): boolean {
  // 纯数字 ID
  return /^[0-9]+$/.test(value);
}