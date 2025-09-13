import { test, expect } from "@playwright/test";

test("Manual overlay creates invoice and blocks duplicates", async ({ page }) => {
  await page.goto("http://localhost:3000/invoices");
  await page.getByRole("button", { name: "+ Manual Invoice" }).click();

  // focus on first input
  await expect(page.locator('input').first()).toBeFocused();

  // fill header
  await page.getByLabel("Supplier ID").fill("sup1");
  await page.getByLabel("Supplier Name").fill("Acme");
  await page.getByLabel("Date").fill("2025-09-13");
  await page.getByLabel("Invoice Ref").fill("INV-PLAY-001");

  // line items (using visible labels/columns)
  await page.getByPlaceholder("e.g. Birra Moretti 330ml").fill("Beer 275ml");
  await page.getByLabel("Outer", { exact: false }).first().fill("2");
  await page.getByLabel("Items/Outer", { exact: false }).first().fill("24");
  await page.getByLabel("Unit £", { exact: false }).first().fill("1.05");
  await page.getByRole("button", { name: "Create Invoice" }).click();

  // toast appears then overlay closes
  await expect(page.getByText(/Invoice saved/i)).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // try duplicate
  await page.getByRole("button", { name: "+ Manual Invoice" }).click();
  await page.getByLabel("Supplier ID").fill("sup1");
  await page.getByLabel("Supplier Name").fill("Acme");
  await page.getByLabel("Date").fill("2025-09-13");
  await page.getByLabel("Invoice Ref").fill("INV-PLAY-001");
  await page.getByPlaceholder("e.g. Birra Moretti 330ml").fill("Beer 275ml");
  await page.getByLabel("Outer", { exact: false }).first().fill("1");
  await page.getByLabel("Items/Outer", { exact: false }).first().fill("24");
  await page.getByLabel("Unit £", { exact: false }).first().fill("1.05");
  await page.getByRole("button", { name: "Create Invoice" }).click();

  // inline error on Invoice Ref
  await expect(page.getByText(/Already used/i)).toBeVisible();
});
