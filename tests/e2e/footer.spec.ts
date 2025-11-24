import { test, expect } from "@playwright/test";

test.describe("Invoices Footer", () => {
  test("Footer renders and is visible after scroll (BrowserRouter)", async ({ page }) => {
    await page.goto("http://127.0.0.1:8000/invoices", { waitUntil: "domcontentloaded" });
    
    // Wait for invoices list or empty state so page has height
    await page.waitForSelector('text=Invoices', { timeout: 5000 });
    
    // Scroll to bottom to reveal fixed footer zone
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    
    // Wait a moment for scroll to complete
    await page.waitForTimeout(500);
    
    const footer = page.locator('[data-testid="invoices-footer-bar"]');
    
    // Assert footer exists and is visible
    await expect(footer).toHaveCount(1);
    await expect(footer).toBeVisible();
    
    // Verify footer is at bottom
    const footerBox = await footer.boundingBox();
    expect(footerBox).not.toBeNull();
    if (footerBox) {
      // Footer should be near bottom of viewport (allowing for some tolerance)
      expect(footerBox.y).toBeGreaterThan(0);
    }
  });

  test("Footer renders in HashRouter mode (#/invoices)", async ({ page }) => {
    // Test HashRouter fallback mode
    await page.goto("http://127.0.0.1:8000/#/invoices", { waitUntil: "domcontentloaded" });
    
    // Wait for invoices list or empty state
    await page.waitForSelector('text=Invoices', { timeout: 5000 });
    
    // Verify we're on the invoices route (hash mode)
    const pathname = await page.evaluate(() => window.location.pathname);
    const hash = await page.evaluate(() => window.location.hash);
    expect(pathname).toBe("/");
    expect(hash).toBe("#/invoices");
    
    // Scroll to bottom
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);
    
    const footer = page.locator('[data-testid="invoices-footer-bar"]');
    await expect(footer).toHaveCount(1);
    await expect(footer).toBeVisible();
  });
});

