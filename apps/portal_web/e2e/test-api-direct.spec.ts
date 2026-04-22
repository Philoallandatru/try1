import { test, expect } from '@playwright/test';

test.describe('Direct API Test', () => {
  test('should fetch workspaces via API', async ({ page }) => {
    // Navigate to the app first to set up localStorage
    await page.goto('http://localhost:5173');

    // Set token in localStorage
    await page.evaluate(() => {
      localStorage.setItem('ssdPortalToken', 'change-me');
    });

    // Make direct API call
    const response = await page.request.get('http://localhost:8000/api/workspaces', {
      headers: {
        'Authorization': 'Bearer change-me'
      }
    });

    console.log('API Response Status:', response.status());
    const body = await response.text();
    console.log('API Response Body:', body);

    expect(response.ok()).toBeTruthy();

    const data = JSON.parse(body);
    console.log('Parsed workspaces:', JSON.stringify(data, null, 2));

    // Check if demo workspace exists
    const demoWorkspace = data.workspaces?.find((w: any) => w.name === 'demo');
    console.log('Demo workspace:', demoWorkspace);
    expect(demoWorkspace).toBeDefined();
  });

  test('should load page and check workspace dropdown', async ({ page }) => {
    await page.goto('http://localhost:5173');

    await page.evaluate(() => {
      localStorage.setItem('ssdPortalToken', 'change-me');
    });

    // Reload to apply token
    await page.reload();

    // Wait for workspaces to load
    await page.waitForTimeout(3000);

    // Check if workspace select exists
    const workspaceSelect = page.locator('select').first();
    await expect(workspaceSelect).toBeVisible();

    // Get all options
    const options = await workspaceSelect.locator('option').allTextContents();
    console.log('Available workspace options:', options);

    // Try to find demo
    const hasDemoOption = options.some(opt => opt.includes('demo'));
    console.log('Has demo option:', hasDemoOption);
  });
});
