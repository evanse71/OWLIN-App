import { test, expect } from '@playwright/test';

test('health banner goes green (single-port)', async ({ page }) => {
  await page.goto('http://127.0.0.1:8000');
  
  // The banner should not say offline after the first poll
  await expect(page.getByText(/backend is offline/i)).toHaveCount(0, { timeout: 5000 });
  
  // Health endpoint should be reachable same-origin
  const res = await page.request.get('http://127.0.0.1:8000/api/health', { 
    headers: { 'cache-control': 'no-store' } 
  });
  expect(res.ok()).toBeTruthy();
  
  // Verify the health response structure
  const healthData = await res.json();
  expect(healthData).toHaveProperty('status', 'ok');
  expect(healthData).toHaveProperty('version');
});

test('health uses same-origin in single-port', async ({ page }) => {
  const requests: string[] = [];
  page.on('request', r => { 
    if (r.url().endsWith('/api/health')) requests.push(r.url()); 
  });
  
  await page.goto('http://127.0.0.1:8000');
  await expect(page.getByText(/backend is offline/i)).toHaveCount(0, { timeout: 5000 });
  
  // Assert that health requests use same-origin (not cross-origin)
  expect(requests.some(u => u.startsWith('http://127.0.0.1:8000'))).toBeTruthy();
  expect(requests.some(u => u === 'http://127.0.0.1:8000/api/health')).toBeTruthy();
});

test('health banner works in split-port dev mode', async ({ page }) => {
  // This test assumes split-port mode with VITE_API_BASE_URL set
  await page.goto('http://127.0.0.1:8080');
  
  // Wait for the health check to complete
  await page.waitForTimeout(2000);
  
  // The banner should not say offline
  await expect(page.getByText(/backend is offline/i)).toHaveCount(0, { timeout: 5000 });
  
  // Verify API calls work with absolute URL
  const res = await page.request.get('http://127.0.0.1:8000/api/health');
  expect(res.ok()).toBeTruthy();
});
