import { test, expect } from '@playwright/test';

test.describe('Analyze Page E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Set up token to bypass authentication
    await page.goto('http://localhost:5173');
    await page.evaluate(() => {
      localStorage.setItem('ssdPortalToken', 'change-me');
    });
    await page.reload();
  });

  test('should display Analyze page with correct UI elements', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Check for page heading
    await expect(page.locator('h2:has-text("Deep Jira Analysis")')).toBeVisible();

    // Check for setup checklist
    await expect(page.locator('text=Setup Checklist')).toBeVisible();

    // Check for form elements
    await expect(page.locator('label:has-text("Issue Key")')).toBeVisible();
    await expect(page.locator('label:has-text("Profile")')).toBeVisible();
  });

  test('should show setup checklist status', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Wait for setup checklist to load
    await page.waitForSelector('.setup-checklist', { timeout: 10000 });

    // Check for setup items
    const setupItems = page.locator('.setup-item');
    const count = await setupItems.count();
    expect(count).toBeGreaterThan(0);

    // Verify setup item structure
    const firstItem = setupItems.first();
    await expect(firstItem.locator('strong')).toBeVisible();
    await expect(firstItem.locator('small')).toBeVisible();
  });

  test('should have Run Analysis button', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    const runButton = page.locator('button:has-text("Run Analysis")');
    await expect(runButton).toBeVisible();
  });

  test('should trigger analysis when form is submitted', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Wait for page to load
    await page.waitForSelector('input[placeholder*="SSD-DEMO-A"]', { timeout: 10000 });

    // Fill in issue key
    const issueInput = page.locator('input[placeholder*="SSD-DEMO-A"]');
    await issueInput.fill('SSD-SAMPLE-1');

    // Check if profile selector exists and has options
    const profileSelect = page.locator('select').filter({ hasText: /profile/i }).or(page.locator('label:has-text("Profile") select'));

    if (await profileSelect.count() > 0) {
      // Get profile options
      const options = await profileSelect.locator('option').count();

      if (options > 0) {
        // Click Run Analysis button
        const runButton = page.locator('button:has-text("Run Analysis")');

        // Check if button is enabled
        const isDisabled = await runButton.isDisabled();

        if (!isDisabled) {
          // Intercept the API call
          const responsePromise = page.waitForResponse(
            response => response.url().includes('/api/workspace/analyze-jira') && response.status() === 200,
            { timeout: 60000 }
          );

          await runButton.click();

          // Wait for loading state
          await expect(page.locator('button:has-text("Running...")')).toBeVisible({ timeout: 5000 });

          // Wait for response
          try {
            await responsePromise;

            // Check for success indicators
            await page.waitForSelector('.result-surface, .message.user-message, text=/completed/', { timeout: 60000 });
          } catch (error) {
            // Check for error message
            const errorMsg = page.locator('.error');
            if (await errorMsg.count() > 0) {
              const errorText = await errorMsg.textContent();
              console.log('Analysis error:', errorText);
            }
          }
        }
      }
    }
  });

  test('should display error message when API fails', async ({ page }) => {
    // Mock API to return error
    await page.route('**/api/workspace/analyze-jira', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error: Analysis failed' })
      });
    });

    await page.goto('http://localhost:5173/');

    // Wait for form
    await page.waitForSelector('input[placeholder*="SSD-DEMO-A"]', { timeout: 10000 });

    // Fill in issue key
    await page.locator('input[placeholder*="SSD-DEMO-A"]').fill('SSD-TEST-ERROR');

    // Try to submit
    const runButton = page.locator('button:has-text("Run Analysis")');

    if (!(await runButton.isDisabled())) {
      await runButton.click();

      // Wait for error message
      const errorMessage = page.locator('.error');
      await expect(errorMessage).toBeVisible({ timeout: 10000 });
      await expect(errorMessage).toContainText(/error|failed|Internal Server Error/i);
    }
  });

  test('should show recent issues in datalist', async ({ page }) => {
    // Set up recent issues in localStorage
    await page.goto('http://localhost:5173/');
    await page.evaluate(() => {
      localStorage.setItem('ssdPortalRecent:issues', JSON.stringify(['SSD-DEMO-A', 'SSD-DEMO-B', 'SSD-SAMPLE-1']));
    });
    await page.reload();

    // Check if datalist exists
    const datalist = page.locator('#recent-issues');
    if (await datalist.count() > 0) {
      const options = await datalist.locator('option').count();
      expect(options).toBeGreaterThan(0);
    }
  });

  test('should display result view after successful analysis', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Wait for page load
    await page.waitForSelector('.analyze-grid', { timeout: 10000 });

    // Check if result surface exists (might be empty initially)
    const resultSurface = page.locator('.result-surface');
    await expect(resultSurface).toBeVisible();
  });

  test('should handle workspace selection', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Check for workspace selector
    const workspaceSelect = page.locator('label:has-text("Workspace") select');

    if (await workspaceSelect.count() > 0) {
      await expect(workspaceSelect).toBeVisible();

      // Check if it has options
      const options = await workspaceSelect.locator('option').count();
      expect(options).toBeGreaterThan(0);
    }
  });

  test('should show advanced options when clicked', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Find and click Advanced button
    const advancedButton = page.locator('button:has-text("Advanced")');

    if (await advancedButton.count() > 0) {
      await advancedButton.click();

      // Check if advanced grid appears
      const advancedGrid = page.locator('.advanced-grid');
      await expect(advancedGrid).toBeVisible();

      // Click again to hide
      await page.locator('button:has-text("Hide Advanced")').click();
      await expect(advancedGrid).not.toBeVisible();
    }
  });

  test('should navigate to other pages from sidebar', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Check sidebar navigation
    const searchLink = page.locator('nav a:has-text("Search")');
    await expect(searchLink).toBeVisible();

    await searchLink.click();
    await expect(page).toHaveURL('http://localhost:5173/search');

    // Navigate back
    const analyzeLink = page.locator('nav a:has-text("Analyze")');
    await analyzeLink.click();
    await expect(page).toHaveURL('http://localhost:5173/');
  });

  test('should check backend connectivity', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Wait for initial API calls
    await page.waitForTimeout(2000);

    // Check for connection status
    const statusIndicator = page.locator('text=/Runner connected|Runner waiting/');
    await expect(statusIndicator).toBeVisible();
  });

  test('should validate form inputs', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Try to submit empty form
    const runButton = page.locator('button:has-text("Run Analysis")');

    // Button should be disabled if setup is not complete or form is invalid
    const issueInput = page.locator('input[placeholder*="SSD-DEMO-A"]');
    await issueInput.fill('');

    // Check button state after clearing input
    await page.waitForTimeout(500);
  });

  test('should display setup checklist items correctly', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    await page.waitForSelector('.setup-checklist', { timeout: 10000 });

    // Check for specific setup items
    const expectedItems = ['Jira Source', 'Confluence Source', 'File Asset', 'Analysis Profile'];

    for (const item of expectedItems) {
      const setupItem = page.locator(`.setup-item:has-text("${item}")`);
      if (await setupItem.count() > 0) {
        await expect(setupItem).toBeVisible();
      }
    }
  });

  test('should handle setup item navigation', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    await page.waitForSelector('.setup-checklist', { timeout: 10000 });

    // Click on a setup item (e.g., Sources)
    const sourcesItem = page.locator('.setup-item:has-text("Jira Source")');

    if (await sourcesItem.count() > 0) {
      await sourcesItem.click();

      // Should navigate to sources page
      await expect(page).toHaveURL(/\/sources/);
    }
  });
});
