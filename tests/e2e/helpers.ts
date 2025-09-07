import { expect, request } from "@playwright/test";

export async function fetchInvoicesSample(limit = 5) {
  const api = await request.newContext();
  const res = await api.get(`http://localhost:8000/api/invoices?limit=${limit}`);
  expect(res.ok(), `/api/invoices should be 200`).toBeTruthy();
  return await res.json();
}

export function validateTotals(invoice: any) {
  const sum = (invoice.lines || []).reduce((a:number, l:any) => a + Number(l.net || 0) + Number(l.tax || 0), 0);
  const total = Number(invoice.total_gross ?? invoice.total ?? 0);
  const ok = Math.abs(sum - total) <= 0.02 * Math.max(total, 1);
  return { ok, sum, total };
}

export async function expectVisible(page: any, sel: string, name: string) {
  const el = page.locator(sel);
  await expect(el, `${name} should be visible`).toBeVisible();
}

export async function expectNotVisible(page: any, sel: string, name: string) {
  const el = page.locator(sel);
  await expect(el, `${name} should not be visible`).not.toBeVisible();
}

export async function clickSafely(page: any, sel: string, name: string) {
  const el = page.locator(sel);
  if (await el.count() > 0) {
    await el.click();
    return true;
  }
  return false;
}

export async function fillSafely(page: any, sel: string, value: string, name: string) {
  const el = page.locator(sel);
  if (await el.count() > 0) {
    await el.fill(value);
    return true;
  }
  return false;
} 