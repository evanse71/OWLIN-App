import { test, expect } from '@playwright/test';

// Test data for multi-invoice scenarios
const multiInvoiceTestData = {
  singleInvoice: {
    filename: 'single_invoice.pdf',
    expectedCards: 1,
    expectedPageRanges: ['1-2']
  },
  multiInvoice: {
    filename: 'multi_invoice.pdf',
    expectedCards: 3,
    expectedPageRanges: ['1-2', '3-4', '5-6']
  },
  ambiguousInvoice: {
    filename: 'ambiguous_invoice.pdf',
    expectedCards: 1,
    expectedManualReview: true
  }
};

test.describe('Multi-Invoice PDF Splitting', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to invoices page
    await page.goto('/invoices');
    await page.waitForLoadState('networkidle');
  });

  test('should display single invoice correctly', async ({ page }) => {
    // Mock API response for single invoice
    await page.route('/api/invoices', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: '1',
            supplier_name: 'Test Supplier',
            invoice_number: 'INV-001',
            invoice_date: '2024-01-01',
            total_amount: 100.00,
            page_range: '1-2',
            requires_manual_review: false,
            parent_pdf_filename: 'single_invoice.pdf',
            status: 'processed'
          }
        ])
      });
    });

    // Reload page to get mocked data
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Check that single invoice card is displayed
    const invoiceCards = await page.locator('[data-invoice-id]').count();
    expect(invoiceCards).toBe(1);

    // Check page range badge
    const pageRangeBadge = await page.locator('text=pp. 1-2').count();
    expect(pageRangeBadge).toBe(1);

    // Check no manual review badge
    const manualReviewBadge = await page.locator('text=Split Required').count();
    expect(manualReviewBadge).toBe(0);
  });

  test('should display multiple invoices from single PDF', async ({ page }) => {
    // Mock API response for multi-invoice PDF
    await page.route('/api/invoices', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: '1',
            supplier_name: 'Test Supplier',
            invoice_number: 'INV-001',
            invoice_date: '2024-01-01',
            total_amount: 100.00,
            page_range: '1-2',
            requires_manual_review: false,
            parent_pdf_filename: 'multi_invoice.pdf',
            status: 'processed'
          },
          {
            id: '2',
            supplier_name: 'Test Supplier',
            invoice_number: 'INV-002',
            invoice_date: '2024-01-01',
            total_amount: 200.00,
            page_range: '3-4',
            requires_manual_review: false,
            parent_pdf_filename: 'multi_invoice.pdf',
            status: 'processed'
          },
          {
            id: '3',
            supplier_name: 'Test Supplier',
            invoice_number: 'INV-003',
            invoice_date: '2024-01-01',
            total_amount: 300.00,
            page_range: '5-6',
            requires_manual_review: false,
            parent_pdf_filename: 'multi_invoice.pdf',
            status: 'processed'
          }
        ])
      });
    });

    // Reload page to get mocked data
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Check that multiple invoice cards are displayed
    const invoiceCards = await page.locator('[data-invoice-id]').count();
    expect(invoiceCards).toBe(3);

    // Check page range badges
    const pageRangeBadges = await page.locator('text=pp. 1-2, pp. 3-4, pp. 5-6').count();
    expect(pageRangeBadges).toBeGreaterThan(0);

    // Check parent PDF grouping header
    const groupHeader = await page.locator('text=multi_invoice.pdf').count();
    expect(groupHeader).toBeGreaterThan(0);
  });

  test('should display manual review badge for low confidence invoices', async ({ page }) => {
    // Mock API response for ambiguous invoice
    await page.route('/api/invoices', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: '1',
            supplier_name: 'Test Supplier',
            invoice_number: 'INV-001',
            invoice_date: '2024-01-01',
            total_amount: 100.00,
            page_range: '1-3',
            requires_manual_review: true,
            parent_pdf_filename: 'ambiguous_invoice.pdf',
            boundary_confidence: 0.4,
            status: 'processed'
          }
        ])
      });
    });

    // Reload page to get mocked data
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Check manual review badge
    const manualReviewBadge = await page.locator('text=Split Required').count();
    expect(manualReviewBadge).toBe(1);

    // Check debug panel is available
    const debugPanelButton = await page.locator('text=Debug Panel').count();
    expect(debugPanelButton).toBe(1);
  });

  test('should show debug panel when expanded', async ({ page }) => {
    // Mock API response for manual review invoice
    await page.route('/api/invoices', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: '1',
            supplier_name: 'Test Supplier',
            invoice_number: 'INV-001',
            invoice_date: '2024-01-01',
            total_amount: 100.00,
            page_range: '1-3',
            requires_manual_review: true,
            parent_pdf_filename: 'ambiguous_invoice.pdf',
            boundary_confidence: 0.4,
            status: 'processed'
          }
        ])
      });
    });

    // Reload page to get mocked data
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Click debug panel button
    await page.click('text=Debug Panel');

    // Check debug panel content
    await expect(page.locator('text=Boundary Detection Confidence')).toBeVisible();
    await expect(page.locator('text=40%')).toBeVisible();
    await expect(page.locator('text=Retry OCR')).toBeVisible();
    await expect(page.locator('text=Mark as Correct')).toBeVisible();
  });

  test('should handle OCR retry functionality', async ({ page }) => {
    // Mock API responses
    await page.route('/api/invoices', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: '1',
            supplier_name: 'Test Supplier',
            invoice_number: 'INV-001',
            invoice_date: '2024-01-01',
            total_amount: 100.00,
            page_range: '1-3',
            requires_manual_review: true,
            parent_pdf_filename: 'ambiguous_invoice.pdf',
            boundary_confidence: 0.4,
            status: 'processed'
          }
        ])
      });
    });

    // Mock retry OCR endpoint
    await page.route('/api/invoices/1/retry_ocr', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          invoice_id: '1',
          new_confidence: 0.8,
          confidence_improvement: 0.4,
          retry_count: 1,
          message: 'OCR retry completed successfully'
        })
      });
    });

    // Reload page to get mocked data
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Open debug panel
    await page.click('text=Debug Panel');

    // Click retry OCR button
    await page.click('text=Retry OCR');

    // Check that retry was successful (confidence should update)
    await expect(page.locator('text=80%')).toBeVisible();
  });

  test('should group invoices by parent PDF filename', async ({ page }) => {
    // Mock API response with invoices from different PDFs
    await page.route('/api/invoices', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: '1',
            supplier_name: 'Supplier A',
            invoice_number: 'INV-001',
            invoice_date: '2024-01-01',
            total_amount: 100.00,
            page_range: '1-2',
            requires_manual_review: false,
            parent_pdf_filename: 'batch_1.pdf',
            status: 'processed'
          },
          {
            id: '2',
            supplier_name: 'Supplier A',
            invoice_number: 'INV-002',
            invoice_date: '2024-01-01',
            total_amount: 200.00,
            page_range: '3-4',
            requires_manual_review: false,
            parent_pdf_filename: 'batch_1.pdf',
            status: 'processed'
          },
          {
            id: '3',
            supplier_name: 'Supplier B',
            invoice_number: 'INV-003',
            invoice_date: '2024-01-01',
            total_amount: 300.00,
            page_range: '1-2',
            requires_manual_review: false,
            parent_pdf_filename: 'batch_2.pdf',
            status: 'processed'
          }
        ])
      });
    });

    // Reload page to get mocked data
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Check that invoices are grouped by parent PDF
    await expect(page.locator('text=batch_1.pdf')).toBeVisible();
    await expect(page.locator('text=batch_2.pdf')).toBeVisible();

    // Check group headers show correct invoice counts
    await expect(page.locator('text=2 invoices')).toBeVisible();
    await expect(page.locator('text=1 invoice')).toBeVisible();
  });

  test('should handle confidence badge tooltips', async ({ page }) => {
    // Mock API response with different confidence levels
    await page.route('/api/invoices', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: '1',
            supplier_name: 'Test Supplier',
            invoice_number: 'INV-001',
            invoice_date: '2024-01-01',
            total_amount: 100.00,
            page_range: '1-2',
            requires_manual_review: false,
            parent_pdf_filename: 'test.pdf',
            boundary_confidence: 0.9,
            status: 'processed'
          }
        ])
      });
    });

    // Reload page to get mocked data
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Hover over confidence badge
    const confidenceBadge = page.locator('[data-invoice-id="1"] .confidence-badge');
    await confidenceBadge.hover();

    // Check tooltip appears
    await expect(page.locator('text=OCR results are reliable. Minimal review needed.')).toBeVisible();
  });

  test('should handle upload of multi-invoice PDF', async ({ page }) => {
    // Mock file upload endpoint
    await page.route('/api/upload', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Multi-invoice PDF processed successfully',
          original_filename: 'multi_invoice.pdf',
          invoices_found: 3,
          invoices_saved: 3,
          saved_invoices: [
            {
              invoice_id: '1',
              supplier_name: 'Test Supplier',
              invoice_number: 'INV-001',
              total_amount: 100.00,
              confidence: 0.9,
              pages: [1, 2],
              line_items_count: 2
            },
            {
              invoice_id: '2',
              supplier_name: 'Test Supplier',
              invoice_number: 'INV-002',
              total_amount: 200.00,
              confidence: 0.8,
              pages: [3, 4],
              line_items_count: 3
            },
            {
              invoice_id: '3',
              supplier_name: 'Test Supplier',
              invoice_number: 'INV-003',
              total_amount: 300.00,
              confidence: 0.7,
              pages: [5, 6],
              line_items_count: 4
            }
          ]
        })
      });
    });

    // Navigate to upload page
    await page.goto('/upload');

    // Upload file (simulate file selection)
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'multi_invoice.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('fake pdf content')
    });

    // Wait for upload to complete
    await expect(page.locator('text=Multi-invoice PDF processed successfully')).toBeVisible();

    // Check that multiple invoices were created
    await expect(page.locator('text=3 invoices found')).toBeVisible();
  });
}); 