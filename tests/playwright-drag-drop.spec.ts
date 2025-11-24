import { test, expect } from '@playwright/test';

test.describe('OWLIN Drag & Drop Upload Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the upload page
    await page.goto('http://localhost:3000');
    
    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('should handle drag and drop file upload', async ({ page }) => {
    // Wait for backend to be healthy
    const healthBanner = page.locator('[data-testid="backend-health-banner"]');
    await expect(healthBanner).toContainText('Backend is online');
    
    // Create a test file for drag and drop
    const testFile = 'test-drag-drop.pdf';
    const fileContent = Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\ntrailer << /Root 1 0 R >>\n%%EOF');
    
    // Set up file chooser for drag and drop
    const fileChooserPromise = page.waitForEvent('filechooser');
    
    // Find the upload area (drag and drop zone)
    const uploadArea = page.locator('[data-testid="upload-area"]');
    await expect(uploadArea).toBeVisible();
    
    // Simulate drag and drop
    await uploadArea.dispatchEvent('dragover', { dataTransfer: new DataTransfer() });
    await uploadArea.dispatchEvent('drop', { 
      dataTransfer: new DataTransfer(),
      files: [new File([fileContent], testFile, { type: 'application/pdf' })]
    });
    
    // Wait for upload to start
    await page.waitForSelector('[data-testid="upload-status"]', { timeout: 10000 });
    
    // Check upload status shows "Uploading"
    const uploadStatus = page.locator('[data-testid="upload-status"]');
    await expect(uploadStatus).toContainText('Uploading');
    
    // Wait for upload to complete
    await page.waitForSelector('[data-testid="upload-status"]:has-text("Complete")', { timeout: 30000 });
    
    // Check final status
    await expect(uploadStatus).toContainText('Complete');
    
    // Check that file appears in upload list
    const uploadList = page.locator('[data-testid="upload-list"]');
    await expect(uploadList).toContainText(testFile);
  });

  test('should show card state transitions during upload', async ({ page }) => {
    // Wait for backend to be healthy
    const healthBanner = page.locator('[data-testid="backend-health-banner"]');
    await expect(healthBanner).toContainText('Backend is online');
    
    // Create a test file
    const testFile = 'test-state-transitions.pdf';
    const fileContent = Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\ntrailer << /Root 1 0 R >>\n%%EOF');
    
    // Find the upload area
    const uploadArea = page.locator('[data-testid="upload-area"]');
    await expect(uploadArea).toBeVisible();
    
    // Simulate drag and drop
    await uploadArea.dispatchEvent('dragover', { dataTransfer: new DataTransfer() });
    await uploadArea.dispatchEvent('drop', { 
      dataTransfer: new DataTransfer(),
      files: [new File([fileContent], testFile, { type: 'application/pdf' })]
    });
    
    // Assert card state transitions
    // 1. Initial state: idle
    const uploadCard = page.locator('[data-testid="upload-card"]');
    await expect(uploadCard).toBeVisible();
    
    // 2. Uploading state
    await page.waitForSelector('[data-testid="upload-status"]:has-text("Uploading")', { timeout: 5000 });
    const uploadStatus = page.locator('[data-testid="upload-status"]');
    await expect(uploadStatus).toContainText('Uploading');
    
    // 3. Progress indicator
    const progressBar = page.locator('[data-testid="upload-progress"]');
    await expect(progressBar).toBeVisible();
    
    // 4. Final state: processed
    await page.waitForSelector('[data-testid="upload-status"]:has-text("Complete")', { timeout: 30000 });
    await expect(uploadStatus).toContainText('Complete');
    
    // 5. File appears in list
    const uploadList = page.locator('[data-testid="upload-list"]');
    await expect(uploadList).toContainText(testFile);
  });

  test('should disable upload when backend is offline', async ({ page }) => {
    // This test assumes backend is stopped or unreachable
    
    // Wait for backend offline state
    const healthBanner = page.locator('[data-testid="backend-health-banner"]');
    await expect(healthBanner).toContainText('Backend offline');
    
    // Check upload area is disabled
    const uploadArea = page.locator('[data-testid="upload-area"]');
    await expect(uploadArea).toHaveAttribute('data-disabled', 'true');
    
    // Check upload button is disabled
    const uploadButton = page.locator('[data-testid="upload-button"]');
    await expect(uploadButton).toBeDisabled();
    
    // Try to drag and drop (should be ignored)
    const testFile = 'test-offline.pdf';
    const fileContent = Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\ntrailer << /Root 1 0 R >>\n%%EOF');
    
    await uploadArea.dispatchEvent('dragover', { dataTransfer: new DataTransfer() });
    await uploadArea.dispatchEvent('drop', { 
      dataTransfer: new DataTransfer(),
      files: [new File([fileContent], testFile, { type: 'application/pdf' })]
    });
    
    // Should not show upload status (upload ignored)
    const uploadStatus = page.locator('[data-testid="upload-status"]');
    await expect(uploadStatus).not.toBeVisible();
  });

  test('should show specific error on upload failure', async ({ page }) => {
    // Wait for backend to be healthy
    const healthBanner = page.locator('[data-testid="backend-health-banner"]');
    await expect(healthBanner).toContainText('Backend is online');
    
    // Create a large file to trigger error (if backend has size limits)
    const largeFile = 'large-file.pdf';
    const largeContent = Buffer.alloc(10 * 1024 * 1024); // 10MB
    
    // Find the upload area
    const uploadArea = page.locator('[data-testid="upload-area"]');
    await expect(uploadArea).toBeVisible();
    
    // Simulate drag and drop
    await uploadArea.dispatchEvent('dragover', { dataTransfer: new DataTransfer() });
    await uploadArea.dispatchEvent('drop', { 
      dataTransfer: new DataTransfer(),
      files: [new File([largeContent], largeFile, { type: 'application/pdf' })]
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

  test('should handle multiple file drag and drop', async ({ page }) => {
    // Wait for backend to be healthy
    const healthBanner = page.locator('[data-testid="backend-health-banner"]');
    await expect(healthBanner).toContainText('Backend is online');
    
    // Create multiple test files
    const files = [
      { name: 'test1.pdf', content: Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\ntrailer << /Root 1 0 R >>\n%%EOF') },
      { name: 'test2.pdf', content: Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\ntrailer << /Root 1 0 R >>\n%%EOF') }
    ];
    
    // Find the upload area
    const uploadArea = page.locator('[data-testid="upload-area"]');
    await expect(uploadArea).toBeVisible();
    
    // Simulate multiple file drag and drop
    const fileObjects = files.map(f => new File([f.content], f.name, { type: 'application/pdf' }));
    
    await uploadArea.dispatchEvent('dragover', { dataTransfer: new DataTransfer() });
    await uploadArea.dispatchEvent('drop', { 
      dataTransfer: new DataTransfer(),
      files: fileObjects
    });
    
    // Wait for all uploads to complete
    for (const file of files) {
      await page.waitForSelector(`[data-testid="upload-status"]:has-text("Complete")`, { timeout: 30000 });
    }
    
    // Check all files appear in upload list
    const uploadList = page.locator('[data-testid="upload-list"]');
    for (const file of files) {
      await expect(uploadList).toContainText(file.name);
    }
  });

  test('should show upload progress during transfer', async ({ page }) => {
    // Wait for backend to be healthy
    const healthBanner = page.locator('[data-testid="backend-health-banner"]');
    await expect(healthBanner).toContainText('Backend is online');
    
    // Create a test file
    const testFile = 'test-progress.pdf';
    const fileContent = Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\ntrailer << /Root 1 0 R >>\n%%EOF');
    
    // Find the upload area
    const uploadArea = page.locator('[data-testid="upload-area"]');
    await expect(uploadArea).toBeVisible();
    
    // Simulate drag and drop
    await uploadArea.dispatchEvent('dragover', { dataTransfer: new DataTransfer() });
    await uploadArea.dispatchEvent('drop', { 
      dataTransfer: new DataTransfer(),
      files: [new File([fileContent], testFile, { type: 'application/pdf' })]
    });
    
    // Check upload progress is shown
    const progressBar = page.locator('[data-testid="upload-progress"]');
    await expect(progressBar).toBeVisible();
    
    // Check progress text
    const progressText = page.locator('[data-testid="upload-progress-text"]');
    await expect(progressText).toContainText('Uploading');
    
    // Wait for completion
    await page.waitForSelector('[data-testid="upload-status"]:has-text("Complete")', { timeout: 30000 });
    
    // Check final status
    const uploadStatus = page.locator('[data-testid="upload-status"]');
    await expect(uploadStatus).toContainText('Complete');
  });
});
