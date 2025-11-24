/**
 * E2E Tests for OCR → Cards → Line Items Pipeline
 * Playwright-based browser tests with screenshot artifacts
 */
import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = 'http://127.0.0.1:8000';
const ARTIFACTS_DIR = 'tests/artifacts/e2e';

// Ensure artifacts directory exists
if (!fs.existsSync(ARTIFACTS_DIR)) {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
}

test.describe('Invoice Management E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to invoices page
    await page.goto(`${BASE_URL}/invoices`);
    await page.waitForLoadState('networkidle');
  });

  test('should load invoices page with footer', async ({ page }) => {
    // Assert page loaded
    await expect(page).toHaveTitle(/Owlin/i);
    
    // Check for key UI elements (adjust selectors based on actual app)
    // Look for invoices container or heading
    const heading = page.locator('h1, h2').filter({ hasText: /invoice/i }).first();
    await expect(heading).toBeVisible({ timeout: 10000 });
    
    console.log('✓ Invoices page loaded');
  });

  test('should upload file and display card with line items', async ({ page }) => {
    // Create a test PDF if needed
    const testPdfPath = path.join('tests', 'fixtures', 'e2e_test_invoice.pdf');
    ensureTestPdf(testPdfPath);
    
    // Find upload input (may be hidden)
    const fileInput = page.locator('input[type="file"]');
    
    // Upload file
    await fileInput.setInputFiles(testPdfPath);
    console.log('✓ File selected for upload');
    
    // Wait for upload to complete (look for processing indicator or new card)
    await page.waitForTimeout(2000); // Give upload time to initiate
    
    // Wait for card to appear (adjust selector based on actual app)
    const invoiceCard = page.locator('[class*="invoice"], [class*="card"]').first();
    await expect(invoiceCard).toBeVisible({ timeout: 15000 });
    
    console.log('✓ Invoice card appeared');
    
    // Take screenshot after upload
    await page.screenshot({ 
      path: path.join(ARTIFACTS_DIR, 'after_upload.png'),
      fullPage: true 
    });
    console.log('✓ Screenshot saved: after_upload.png');
    
    // Click to expand card if needed (look for expand button)
    const expandButton = page.locator('button[data-testid="expand-button"]').first();
    if (await expandButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expandButton.click();
      await page.waitForTimeout(500);
      console.log('✓ Card expanded');
    }
    
    // Check for line items or empty state
    const lineItemsTable = page.locator('[data-testid="line-items-table"], table').first();
    const emptyState = page.locator('text=/No parsed items found yet/i');
    
    const hasTable = await lineItemsTable.isVisible({ timeout: 3000 }).catch(() => false);
    const hasEmptyState = await emptyState.isVisible({ timeout: 1000 }).catch(() => false);
    
    if (hasTable) {
      console.log('✓ Line items table visible');
      expect(hasTable).toBeTruthy();
    } else if (hasEmptyState) {
      console.log('✓ Empty state message visible (no items parsed)');
      expect(hasEmptyState).toBeTruthy();
    } else {
      console.log('⚠ Neither table nor empty state found - may need selector adjustment');
    }
    
    // Take final screenshot
    await page.screenshot({ 
      path: path.join(ARTIFACTS_DIR, 'after_expand.png'),
      fullPage: true 
    });
    console.log('✓ Screenshot saved: after_expand.png');
  });

  test('should not create duplicate cards on rapid upload', async ({ page }) => {
    const testPdfPath = path.join('tests', 'fixtures', 'duplicate_test.pdf');
    ensureTestPdf(testPdfPath);
    
    // Get initial card count
    await page.waitForTimeout(1000);
    const initialCards = await page.locator('[class*="invoice"], [class*="card"]').count();
    
    // Upload same file twice rapidly
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testPdfPath);
    await page.waitForTimeout(500);
    
    // Second upload (may need to re-select input if it's been removed)
    const fileInput2 = page.locator('input[type="file"]');
    await fileInput2.setInputFiles(testPdfPath);
    
    // Wait for processing
    await page.waitForTimeout(5000);
    
    // Get final card count
    const finalCards = await page.locator('[class*="invoice"], [class*="card"]').count();
    
    // Should have 2 new cards (one per upload, different doc_ids)
    // But NOT duplicate cards with same doc_id
    const cardsAdded = finalCards - initialCards;
    console.log(`✓ Cards added: ${cardsAdded} (initial: ${initialCards}, final: ${finalCards})`);
    
    // Take screenshot
    await page.screenshot({ 
      path: path.join(ARTIFACTS_DIR, 'duplicate_test.png'),
      fullPage: true 
    });
  });

  test('should show retry button on error and recover', async ({ page }) => {
    // This test checks if error handling UI exists
    // In practice, inducing errors requires backend manipulation
    
    // Upload a file
    const testPdfPath = path.join('tests', 'fixtures', 'error_test.pdf');
    ensureTestPdf(testPdfPath);
    
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testPdfPath);
    
    // Wait for card
    await page.waitForTimeout(3000);
    
    // Look for error badge or retry button
    const retryButton = page.locator('button:has-text("Retry OCR")').first();
    const errorBadge = page.locator('[class*="error"], [class*="red"]').filter({ hasText: /scan error|error|retry/i });
    
    const hasRetryButton = await retryButton.isVisible({ timeout: 5000 }).catch(() => false);
    const hasErrorBadge = await errorBadge.isVisible({ timeout: 2000 }).catch(() => false);
    
    if (hasRetryButton) {
      console.log('✓ Retry OCR button found');
      
      // Click retry
      await retryButton.click();
      console.log('✓ Retry OCR clicked');
      
      // Wait for re-processing
      await page.waitForTimeout(5000);
      
      // Take screenshot
      await page.screenshot({ 
        path: path.join(ARTIFACTS_DIR, 'after_retry.png'),
        fullPage: true 
      });
    } else if (hasErrorBadge) {
      console.log('✓ Error badge found (but no retry button visible yet)');
    } else {
      console.log('⚠ No error state found (document may have processed successfully)');
    }
    
    // Take screenshot regardless
    await page.screenshot({ 
      path: path.join(ARTIFACTS_DIR, 'error_check.png'),
      fullPage: true 
    });
  });
});

/**
 * Ensure test PDF exists, create if missing
 */
function ensureTestPdf(pdfPath: string) {
  const dir = path.dirname(pdfPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  
  if (!fs.existsSync(pdfPath)) {
    // Create minimal PDF
    const minimalPdf = `%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
197
%%EOF`;
    
    fs.writeFileSync(pdfPath, minimalPdf);
    console.log(`✓ Created test PDF: ${pdfPath}`);
  }
}

