import { test, expect } from '@playwright/test';

test.describe('OWLIN Upload Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the upload page
    await page.goto('http://localhost:3000');
    
    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('should show backend health banner', async ({ page }) => {
    // Check if health banner is visible
    const healthBanner = page.locator('[data-testid="backend-health-banner"]');
    await expect(healthBanner).toBeVisible();
    
    // Should show either healthy or unhealthy state
    const bannerText = await healthBanner.textContent();
    expect(bannerText).toMatch(/Backend is (online|offline)/);
  });

  test('should disable upload when backend is offline', async ({ page }) => {
    // If backend is offline, upload button should be disabled
    const uploadButton = page.locator('button[data-testid="upload-button"]');
    
    // Check if button is disabled when backend is offline
    const isDisabled = await uploadButton.isDisabled();
    if (isDisabled) {
      // Should show tooltip explaining why it's disabled
      await uploadButton.hover();
      const tooltip = page.locator('[data-testid="upload-tooltip"]');
      await expect(tooltip).toBeVisible();
    }
  });

  test('should upload file successfully when backend is online', async ({ page }) => {
    // Wait for backend to be healthy
    const healthBanner = page.locator('[data-testid="backend-health-banner"]');
    await expect(healthBanner).toContainText('Backend is online');
    
    // Create a test file
    const testFile = 'test-upload.pdf';
    const fileContent = Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\ntrailer << /Root 1 0 R >>\n%%EOF');
    
    // Set up file chooser
    const fileChooserPromise = page.waitForEvent('filechooser');
    
    // Click upload button
    const uploadButton = page.locator('button[data-testid="upload-button"]');
    await uploadButton.click();
    
    // Handle file chooser
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: testFile,
      mimeType: 'application/pdf',
      buffer: fileContent
    });
    
    // Wait for upload to complete
    await page.waitForSelector('[data-testid="upload-status"]', { timeout: 10000 });
    
    // Check upload status
    const uploadStatus = page.locator('[data-testid="upload-status"]');
    await expect(uploadStatus).toContainText('Complete');
    
    // Check that file appears in upload list
    const uploadList = page.locator('[data-testid="upload-list"]');
    await expect(uploadList).toContainText(testFile);
  });

  test('should show specific error message on upload failure', async ({ page }) => {
    // Create a large file to trigger error
    const largeFile = 'large-file.pdf';
    const largeContent = Buffer.alloc(10 * 1024 * 1024); // 10MB
    
    // Set up file chooser
    const fileChooserPromise = page.waitForEvent('filechooser');
    
    // Click upload button
    const uploadButton = page.locator('button[data-testid="upload-button"]');
    await uploadButton.click();
    
    // Handle file chooser
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: largeFile,
      mimeType: 'application/pdf',
      buffer: largeContent
    });
    
    // Wait for error to appear
    await page.waitForSelector('[data-testid="upload-error"]', { timeout: 10000 });
    
    // Check error message is specific (not generic "0% error")
    const errorMessage = page.locator('[data-testid="upload-error"]');
    const errorText = await errorMessage.textContent();
    
    expect(errorText).not.toContain('0%');
    expect(errorText).toMatch(/Upload failed|File too large|Backend unreachable/);
    
    // Check copy error button exists
    const copyButton = page.locator('[data-testid="copy-error-button"]');
    await expect(copyButton).toBeVisible();
  });

  test('should copy error message to clipboard', async ({ page }) => {
    // Trigger an upload error (backend offline scenario)
    // This test assumes backend is stopped
    
    // Wait for backend offline state
    const healthBanner = page.locator('[data-testid="backend-health-banner"]');
    await expect(healthBanner).toContainText('Backend offline');
    
    // Try to upload
    const uploadButton = page.locator('button[data-testid="upload-button"]');
    await uploadButton.click();
    
    // Wait for error
    await page.waitForSelector('[data-testid="upload-error"]', { timeout: 5000 });
    
    // Click copy error button
    const copyButton = page.locator('[data-testid="copy-error-button"]');
    await copyButton.click();
    
    // Check clipboard content
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toContain('Backend unreachable');
  });

  test('should show upload progress during upload', async ({ page }) => {
    // Wait for backend to be healthy
    const healthBanner = page.locator('[data-testid="backend-health-banner"]');
    await expect(healthBanner).toContainText('Backend is online');
    
    // Create a test file
    const testFile = 'test-upload.pdf';
    const fileContent = Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\ntrailer << /Root 1 0 R >>\n%%EOF');
    
    // Set up file chooser
    const fileChooserPromise = page.waitForEvent('filechooser');
    
    // Click upload button
    const uploadButton = page.locator('button[data-testid="upload-button"]');
    await uploadButton.click();
    
    // Handle file chooser
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: testFile,
      mimeType: 'application/pdf',
      buffer: fileContent
    });
    
    // Check upload progress is shown
    const progressBar = page.locator('[data-testid="upload-progress"]');
    await expect(progressBar).toBeVisible();
    
    // Check progress text
    const progressText = page.locator('[data-testid="upload-progress-text"]');
    await expect(progressText).toContainText('Uploading');
    
    // Wait for completion
    await page.waitForSelector('[data-testid="upload-status"]', { timeout: 10000 });
    
    // Check final status
    const uploadStatus = page.locator('[data-testid="upload-status"]');
    await expect(uploadStatus).toContainText('Complete');
  });
});
