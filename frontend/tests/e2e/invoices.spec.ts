import { test, expect } from '@playwright/test';

test.describe('Invoices Page E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to invoices page
    await page.goto('/invoices');
    
    // Wait for page to load
    await page.waitForSelector('[data-testid="invoices-page"]', { timeout: 10000 });
  });

  test('loads invoices page with default layout', async ({ page }) => {
    // Check that all main components are present
    await expect(page.locator('h1')).toContainText('Invoices');
    await expect(page.locator('[data-testid="filter-panel"]')).toBeVisible();
    await expect(page.locator('[data-testid="upload-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="invoice-cards-panel"]')).toBeVisible();
    await expect(page.locator('[data-testid="invoice-detail-box"]')).toBeVisible();
  });

  test('filter panel functionality', async ({ page }) => {
    // Test search functionality
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('test supplier');
    await page.waitForTimeout(350); // Wait for debounce
    
    // Test venue dropdown
    const venueSelect = page.locator('[data-testid="venue-select"]');
    await venueSelect.selectOption('venue-1');
    
    // Test supplier dropdown
    const supplierSelect = page.locator('[data-testid="supplier-select"]');
    await supplierSelect.selectOption('Test Supplier');
    
    // Test date range
    const dateFrom = page.locator('[data-testid="date-from"]');
    const dateTo = page.locator('[data-testid="date-to"]');
    await dateFrom.fill('2024-01-01');
    await dateTo.fill('2024-12-31');
    
    // Test filter toggles
    const flaggedToggle = page.locator('[data-testid="only-flagged-toggle"]');
    await flaggedToggle.click();
    
    const unmatchedToggle = page.locator('[data-testid="only-unmatched-toggle"]');
    await unmatchedToggle.click();
    
    // Test sort dropdown
    const sortSelect = page.locator('[data-testid="sort-select"]');
    await sortSelect.selectOption('value_desc');
    
    // Verify filters are applied
    await expect(page.locator('[data-testid="filtered-indicator"]')).toBeVisible();
    
    // Test reset filters
    const resetButton = page.locator('[data-testid="reset-filters"]');
    await resetButton.click();
    
    // Verify filters are reset
    await expect(searchInput).toHaveValue('');
    await expect(venueSelect).toHaveValue('all');
    await expect(flaggedToggle).not.toBeChecked();
  });

  test('upload functionality', async ({ page }) => {
    // Test file upload via drag and drop
    const uploadArea = page.locator('[data-testid="upload-area"]');
    
    // Create a mock PDF file
    const filePath = 'test-files/sample-invoice.pdf';
    
    // Simulate drag and drop
    await uploadArea.dispatchEvent('dragover');
    await page.setInputFiles('[data-testid="file-input"]', filePath);
    
    // Wait for upload to complete
    await expect(page.locator('[data-testid="upload-progress"]')).toBeVisible();
    await expect(page.locator('[data-testid="upload-success"]')).toBeVisible({ timeout: 30000 });
  });

  test('invoice card interactions', async ({ page }) => {
    // Wait for invoice cards to load
    await page.waitForSelector('[data-testid="invoice-card"]', { timeout: 10000 });
    
    // Test card expansion
    const firstCard = page.locator('[data-testid="invoice-card"]').first();
    await firstCard.click();
    
    // Verify card is expanded
    await expect(firstCard).toHaveAttribute('data-expanded', 'true');
    
    // Verify detail box shows invoice details
    await expect(page.locator('[data-testid="invoice-detail-box"]')).toContainText('Invoice Details');
    
    // Test keyboard navigation
    await firstCard.press('Escape');
    await expect(firstCard).toHaveAttribute('data-expanded', 'false');
  });

  test('role-aware filter defaults', async ({ page }) => {
    // Test finance role defaults
    await page.goto('/invoices?role=finance');
    await page.waitForSelector('[data-testid="filter-panel"]');
    
    const flaggedToggle = page.locator('[data-testid="only-flagged-toggle"]');
    await expect(flaggedToggle).toBeChecked();
    
    // Test GM role defaults
    await page.goto('/invoices?role=GM');
    await page.waitForSelector('[data-testid="filter-panel"]');
    
    const sortSelect = page.locator('[data-testid="sort-select"]');
    await expect(sortSelect).toHaveValue('supplier_asc');
    
    // Test shift lead role defaults
    await page.goto('/invoices?role=shift_lead');
    await page.waitForSelector('[data-testid="filter-panel"]');
    
    const unmatchedToggle = page.locator('[data-testid="only-unmatched-toggle"]');
    await expect(unmatchedToggle).toBeChecked();
  });

  test('offline queue functionality', async ({ page }) => {
    // Simulate offline mode
    await page.route('**/api/**', route => route.abort());
    
    // Try to upload a file
    const uploadArea = page.locator('[data-testid="upload-area"]');
    const filePath = 'test-files/sample-invoice.pdf';
    
    await page.setInputFiles('[data-testid="file-input"]', filePath);
    
    // Verify file is queued
    await expect(page.locator('[data-testid="offline-queue"]')).toBeVisible();
    await expect(page.locator('[data-testid="queued-file"]')).toContainText('sample-invoice.pdf');
    
    // Simulate coming back online
    await page.unroute('**/api/**');
    
    // Verify queue is processed
    await expect(page.locator('[data-testid="queue-processing"]')).toBeVisible();
    await expect(page.locator('[data-testid="queue-empty"]')).toBeVisible({ timeout: 30000 });
  });

  test('accessibility features', async ({ page }) => {
    // Test keyboard navigation
    await page.keyboard.press('Tab');
    await expect(page.locator('[data-testid="search-input"]')).toBeFocused();
    
    await page.keyboard.press('Tab');
    await expect(page.locator('[data-testid="venue-select"]')).toBeFocused();
    
    // Test ARIA labels
    await expect(page.locator('[data-testid="filter-panel"]')).toHaveAttribute('role', 'complementary');
    await expect(page.locator('[data-testid="upload-area"]')).toHaveAttribute('role', 'button');
    
    // Test screen reader support
    await expect(page.locator('[data-testid="search-input"]')).toHaveAttribute('aria-describedby');
    await expect(page.locator('[data-testid="only-flagged-toggle"]')).toHaveAttribute('role', 'switch');
  });

  test('error handling', async ({ page }) => {
    // Simulate API error
    await page.route('**/api/invoices**', route => 
      route.fulfill({ status: 500, body: 'Internal Server Error' })
    );
    
    // Reload page
    await page.reload();
    
    // Verify error message is displayed
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText('Error Loading Invoices');
  });

  test('performance with large datasets', async ({ page }) => {
    // Mock large dataset
    await page.route('**/api/invoices**', route => 
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          invoices: Array.from({ length: 1000 }, (_, i) => ({
            id: i,
            supplier_name: `Supplier ${i}`,
            invoice_number: `INV-${i}`,
            total_amount: 100 + i,
            status: 'parsed',
            confidence: 85 + (i % 15)
          })),
          count: 1000
        })
      })
    );
    
    // Reload page
    await page.reload();
    
    // Verify page loads within performance budget
    const loadTime = await page.evaluate(() => performance.now());
    expect(loadTime).toBeLessThan(3000); // 3 seconds max
    
    // Verify virtualization is working
    await expect(page.locator('[data-testid="invoice-card"]')).toHaveCount(20); // Only visible cards
  });

  test('URL state persistence', async ({ page }) => {
    // Apply filters
    await page.locator('[data-testid="search-input"]').fill('test');
    await page.locator('[data-testid="venue-select"]').selectOption('venue-1');
    await page.locator('[data-testid="only-flagged-toggle"]').click();
    
    // Verify URL contains filter state
    await expect(page).toHaveURL(/search_text=test/);
    await expect(page).toHaveURL(/venue_id=venue-1/);
    await expect(page).toHaveURL(/only_flagged=true/);
    
    // Reload page
    await page.reload();
    
    // Verify filters are restored
    await expect(page.locator('[data-testid="search-input"]')).toHaveValue('test');
    await expect(page.locator('[data-testid="venue-select"]')).toHaveValue('venue-1');
    await expect(page.locator('[data-testid="only-flagged-toggle"]')).toBeChecked();
  });
}); 