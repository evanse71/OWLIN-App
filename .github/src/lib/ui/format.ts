// src/lib/ui/format.ts
export function pct(v?: number | null, fallback = 'n/a'): string {
  if (typeof v !== 'number' || Number.isNaN(v)) return fallback;
  return `${Math.round(v * 100)}%`;
}

export function timeStampISO(): string {
  return new Date().toISOString();
}
