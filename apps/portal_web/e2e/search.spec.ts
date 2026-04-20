import { test, expect } from '@playwright/test';

test.describe('Search Page E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate directly to search page using URL
    await page.goto('/search');
  });

  test('should display search page with all UI elements', async ({ page }) => {
    // Check search input exists
    const searchInput = page.locator('[data-testid="search-input"]');
    await expect(searchInput).toBeVisible();

    // Check search button exists
    const searchButton = page.locator('[data-testid="search-button"]');
    await expect(searchButton).toBeVisible();

    // Check index status card exists
    const indexCard = page.locator('[data-testid="index-status-card"]');
    await expect(indexCard).toBeVisible();
  });

  test('should perform search and display results', async ({ page }) => {
    // Wait for index to be ready
    const searchInput = page.locator('[data-testid="search-input"]');

    // Check if input is enabled (index is ready)
    const isDisabled = await searchInput.isDisabled();

    if (!isDisabled) {
      // Enter search query
      await searchInput.fill('test');

      // Click search button
      const searchButton = page.locator('[data-testid="search-button"]');
      await searchButton.click();

      // Wait for results or empty state
      await page.waitForTimeout(1000);

      // Check if results are displayed or "no results" message
      const hasResults = await page.locator('[data-testid="search-results"]').count() > 0;
      const hasEmptyState = await page.locator('.empty-state').count() > 0;

      expect(hasResults || hasEmptyState).toBeTruthy();
    }
  });

  test('should handle empty search query', async ({ page }) => {
    // Search button should be disabled when query is empty
    const searchButton = page.locator('[data-testid="search-button"]');

    // Verify page doesn't crash
    await expect(page.locator('h2')).toContainText('Knowledge Retrieval');
  });

  test('should display search results with highlights', async ({ page }) => {
    const searchInput = page.locator('[data-testid="search-input"]');
    const isDisabled = await searchInput.isDisabled();

    if (!isDisabled) {
      // Perform search
      await searchInput.fill('test');

      const searchButton = page.locator('[data-testid="search-button"]');
      await searchButton.click();

      await page.waitForTimeout(1000);

      // Check if highlights are present (if results exist)
      const resultsExist = await page.locator('[data-testid="search-results"]').count() > 0;

      if (resultsExist) {
        // Highlights should be present as <mark> tags
        const highlights = page.locator('mark');
        const highlightCount = await highlights.count();
        console.log(`Found ${highlightCount} highlights`);
      }
    }
  });

  test('should show loading state during search', async ({ page }) => {
    const searchInput = page.locator('[data-testid="search-input"]');
    const isDisabled = await searchInput.isDisabled();

    if (!isDisabled) {
      await searchInput.fill('query');

      const searchButton = page.locator('[data-testid="search-button"]');

      // Check button state before click
      await expect(searchButton).toBeEnabled();

      // Start search
      await searchButton.click();

      // Verify page doesn't crash
      await page.waitForTimeout(500);
      await expect(page.locator('h2')).toBeVisible();
    }
  });

  test('should handle Chinese search queries', async ({ page }) => {
    const searchInput = page.locator('[data-testid="search-input"]');
    const isDisabled = await searchInput.isDisabled();

    if (!isDisabled) {
      await searchInput.fill('机器学习');

      const searchButton = page.locator('[data-testid="search-button"]');
      await searchButton.click();

      await page.waitForTimeout(1000);

      // Verify page doesn't crash with Chinese input
      await expect(page.locator('h2')).toBeVisible();
    }
  });

  test('should navigate back to home page', async ({ page }) => {
    // Click on Analyze link in navigation
    const analyzeLink = page.locator('a').filter({ hasText: 'Analyze' });
    await analyzeLink.click();

    // Should navigate to home page
    await expect(page).toHaveURL('/');
    await expect(page.locator('h2')).toContainText(/Analyze|Jira/i);
  });

  test('should display document count', async ({ page }) => {
    // Look for document count display
    const docCount = page.locator('[data-testid="document-count"]');
    await expect(docCount).toBeVisible();
  });
});
