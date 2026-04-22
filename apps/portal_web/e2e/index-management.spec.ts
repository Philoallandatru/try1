import { test, expect } from '@playwright/test';

test.describe('Index Management E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display home page with correct branding', async ({ page }) => {
    // Check page title matches actual branding
    await expect(page.locator('h1')).toContainText('SSD Quality Wiki');
  });

  test('should show index build button in search page', async ({ page }) => {
    // Navigate to search page using URL
    await page.goto('/search');

    // Look for rebuild index button
    const rebuildButton = page.locator('[data-testid="rebuild-index-button"]');
    await expect(rebuildButton).toBeVisible();
  });

  test('should navigate to search page', async ({ page }) => {
    // Find search link
    const searchLink = page.locator('a').filter({ hasText: 'Search' });

    await expect(searchLink).toBeVisible();
    await searchLink.click();

    // Verify navigation by checking URL and content
    await expect(page).toHaveURL('/search');
    await expect(page.locator('h2')).toContainText('Knowledge Retrieval');
  });

  test('should display document count in search page', async ({ page }) => {
    // Navigate to search page
    await page.goto('/search');

    // Look for document count display
    const docCount = page.locator('[data-testid="document-count"]');
    await expect(docCount).toBeVisible();
  });

  test('should handle index rebuild if available', async ({ page }) => {
    // Navigate to search page
    await page.goto('/search');

    // Look for rebuild button
    const rebuildButton = page.locator('[data-testid="rebuild-index-button"]');

    if (await rebuildButton.isEnabled()) {
      await rebuildButton.click();

      // Wait for rebuild to complete or show progress
      await page.waitForTimeout(2000);

      // Button should still be visible
      await expect(rebuildButton).toBeVisible();
    }
  });

  test('should show index statistics in search page', async ({ page }) => {
    // Navigate to search page
    await page.goto('/search');
    await page.waitForTimeout(1000);

    // Look for index status card
    const indexCard = page.locator('[data-testid="index-status-card"]');
    await expect(indexCard).toBeVisible();

    // Should show document count
    const docCount = page.locator('[data-testid="document-count"]');
    await expect(docCount).toBeVisible();
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Navigate to search page
    await page.goto('/search');

    // Perform action that triggers API call
    const searchInput = page.locator('[data-testid="search-input"]');
    const isDisabled = await searchInput.isDisabled();

    if (!isDisabled) {
      await searchInput.fill('test query');

      const searchButton = page.locator('[data-testid="search-button"]');
      await searchButton.click();

      await page.waitForTimeout(1000);
    }

    // Page should not crash - main heading should still be visible
    await expect(page.locator('h2')).toBeVisible();
  });

  test('should maintain responsive layout', async ({ page }) => {
    // Test at different viewport sizes
    await page.setViewportSize({ width: 375, height: 667 }); // Mobile
    await expect(page.locator('h1')).toBeVisible();

    await page.setViewportSize({ width: 768, height: 1024 }); // Tablet
    await expect(page.locator('h1')).toBeVisible();

    await page.setViewportSize({ width: 1920, height: 1080 }); // Desktop
    await expect(page.locator('h1')).toBeVisible();
  });
});
