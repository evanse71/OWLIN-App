export const toCents = (v: number | string) => Math.round(Number(String(v).replace(/[,£\s]/g, '')) * 100);
export const fromCents = (c: number) => c / 100;
export const sumCents = (xs: Array<number | string | null | undefined>): number =>
  xs.reduce((acc: number, v) => {
    const value = v ?? 0;
    const numValue = Number(value);
    return acc + (isFinite(numValue) ? toCents(String(value)) : 0);
  }, 0);
export const formatGBP = (c: number) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 2 }).format(fromCents(c));

// Add the missing functions
export const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-GB', { 
    style: 'currency', 
    currency: 'GBP', 
    minimumFractionDigits: 2 
  }).format(amount / 100);
};

export const formatDateShort = (date: string | Date) => {
  if (!date) return '';
  const d = new Date(date);
  return d.toLocaleDateString('en-GB', { 
    day: '2-digit', 
    month: 'short', 
    year: 'numeric' 
  });
};

// VAT display formatter
export const pounds = (p?: number | null) =>
  typeof p === 'number' ? `£${(p/100).toLocaleString('en-GB', {minimumFractionDigits:2, maximumFractionDigits:2})}` : '—'; 