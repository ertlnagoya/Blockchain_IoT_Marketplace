export function match(value: string): boolean {
  // 以太坊地址 0x + 40 个十六进制
  return /^0x[0-9a-fA-F]{40}$/.test(value);
}