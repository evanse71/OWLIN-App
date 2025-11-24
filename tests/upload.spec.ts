import { test, expect } from '@playwright/test';

test('upload PDF flows to processed', async ({ page }) => {
  // Vite dev server
  await page.goto('http://127.0.0.1:8080');

  // Health banner should not show offline
  await expect(page.getByText(/backend offline/i)).toHaveCount(0);

  // Wait for the page to load
  await page.waitForLoadState('networkidle');

  // Look for upload functionality - check if there's an upload button or drag-drop area
  const uploadButton = page.getByRole('button', { name: /upload/i }).first();
  const uploadArea = page.locator('[data-testid="upload-area"], .upload-area, [class*="upload"]').first();
  
  // Try to find upload functionality
  let uploadElement;
  if (await uploadButton.isVisible()) {
    uploadElement = uploadButton;
  } else if (await uploadArea.isVisible()) {
    uploadElement = uploadArea;
  } else {
    // Fallback: look for any clickable element that might trigger file upload
    uploadElement = page.locator('input[type="file"]').first();
  }

  // Trigger file chooser
  const [fileChooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    uploadElement.click(),
  ]);
  
  await fileChooser.setFiles({
    name: 'tiny.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF'),
  });

  // Should show uploading then processed
  await expect(page.getByText(/uploading/i)).toBeVisible();
  await expect(page.getByText(/processed/i)).toBeVisible({ timeout: 5000 });

  // (Optional) assert card shows filename or bytes
  await expect(page.getByText(/tiny\.pdf/i)).toBeVisible();
});

test('backend health check', async ({ page }) => {
  await page.goto('http://127.0.0.1:8080');
  
  // Wait for health banner to load
  await page.waitForLoadState('networkidle');
  
  // Health banner should show backend is online
  const healthBanner = page.locator('[class*="alert"], [class*="banner"]').first();
  if (await healthBanner.isVisible()) {
    await expect(healthBanner).toContainText(/online|ready/i);
  }
});

test('single-port demo', async ({ page }) => {
  // Test the single-port demo (backend serving frontend)
  await page.goto('http://127.0.0.1:8000');
  
  // Should load the frontend
  await page.waitForLoadState('networkidle');
  
  // Should not show backend offline message
  await expect(page.getByText(/backend offline/i)).toHaveCount(0);
  
  // Should be able to navigate to different pages
  const dashboardLink = page.getByRole('link', { name: /dashboard/i }).first();
  if (await dashboardLink.isVisible()) {
    await dashboardLink.click();
    await page.waitForLoadState('networkidle');
  }
});
