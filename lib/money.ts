export const toCents = (v: number | string) => Math.round(Number(String(v).replace(/[,£\s]/g, '')) * 100);
export const fromCents = (c: number) => c / 100;
export const sumCents = (xs: Array<number | string | null | undefined>): number =>
  xs.reduce((acc: number, v) => acc + (isFinite(Number(v)) ? toCents(String(v ?? 0)) : 0), 0);
export const formatGBP = (c: number) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 2 }).format(fromCents(c)); 