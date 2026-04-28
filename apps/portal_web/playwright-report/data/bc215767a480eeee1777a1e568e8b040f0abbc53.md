# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: index-management.spec.ts >> Index Management E2E Tests >> should handle index rebuild if available
- Location: e2e\index-management.spec.ts:43:3

# Error details

```
Test timeout of 1860000ms exceeded.
```

```
Error: locator.isEnabled: Test timeout of 1860000ms exceeded.
Call log:
  - waiting for locator('[data-testid="rebuild-index-button"]')

```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('Index Management E2E Tests', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/');
  6   |   });
  7   | 
  8   |   test('should display home page with correct branding', async ({ page }) => {
  9   |     // Check page title matches actual branding
  10  |     await expect(page.locator('h1')).toContainText('SSD Quality Wiki');
  11  |   });
  12  | 
  13  |   test('should show index build button in search page', async ({ page }) => {
  14  |     // Navigate to search page using URL
  15  |     await page.goto('/search');
  16  | 
  17  |     // Look for rebuild index button
  18  |     const rebuildButton = page.locator('[data-testid="rebuild-index-button"]');
  19  |     await expect(rebuildButton).toBeVisible();
  20  |   });
  21  | 
  22  |   test('should navigate to search page', async ({ page }) => {
  23  |     // Find search link
  24  |     const searchLink = page.locator('a').filter({ hasText: 'Search' });
  25  | 
  26  |     await expect(searchLink).toBeVisible();
  27  |     await searchLink.click();
  28  | 
  29  |     // Verify navigation by checking URL and content
  30  |     await expect(page).toHaveURL('/search');
  31  |     await expect(page.locator('h2')).toContainText('Knowledge Retrieval');
  32  |   });
  33  | 
  34  |   test('should display document count in search page', async ({ page }) => {
  35  |     // Navigate to search page
  36  |     await page.goto('/search');
  37  | 
  38  |     // Look for document count display
  39  |     const docCount = page.locator('[data-testid="document-count"]');
  40  |     await expect(docCount).toBeVisible();
  41  |   });
  42  | 
  43  |   test('should handle index rebuild if available', async ({ page }) => {
  44  |     // Navigate to search page
  45  |     await page.goto('/search');
  46  | 
  47  |     // Look for rebuild button
  48  |     const rebuildButton = page.locator('[data-testid="rebuild-index-button"]');
  49  | 
> 50  |     if (await rebuildButton.isEnabled()) {
      |                             ^ Error: locator.isEnabled: Test timeout of 1860000ms exceeded.
  51  |       await rebuildButton.click();
  52  | 
  53  |       // Wait for rebuild to complete or show progress
  54  |       await page.waitForTimeout(2000);
  55  | 
  56  |       // Button should still be visible
  57  |       await expect(rebuildButton).toBeVisible();
  58  |     }
  59  |   });
  60  | 
  61  |   test('should show index statistics in search page', async ({ page }) => {
  62  |     // Navigate to search page
  63  |     await page.goto('/search');
  64  |     await page.waitForTimeout(1000);
  65  | 
  66  |     // Look for index status card
  67  |     const indexCard = page.locator('[data-testid="index-status-card"]');
  68  |     await expect(indexCard).toBeVisible();
  69  | 
  70  |     // Should show document count
  71  |     const docCount = page.locator('[data-testid="document-count"]');
  72  |     await expect(docCount).toBeVisible();
  73  |   });
  74  | 
  75  |   test('should handle API errors gracefully', async ({ page }) => {
  76  |     // Navigate to search page
  77  |     await page.goto('/search');
  78  | 
  79  |     // Perform action that triggers API call
  80  |     const searchInput = page.locator('[data-testid="search-input"]');
  81  |     const isDisabled = await searchInput.isDisabled();
  82  | 
  83  |     if (!isDisabled) {
  84  |       await searchInput.fill('test query');
  85  | 
  86  |       const searchButton = page.locator('[data-testid="search-button"]');
  87  |       await searchButton.click();
  88  | 
  89  |       await page.waitForTimeout(1000);
  90  |     }
  91  | 
  92  |     // Page should not crash - main heading should still be visible
  93  |     await expect(page.locator('h2')).toBeVisible();
  94  |   });
  95  | 
  96  |   test('should maintain responsive layout', async ({ page }) => {
  97  |     // Test at different viewport sizes
  98  |     await page.setViewportSize({ width: 375, height: 667 }); // Mobile
  99  |     await expect(page.locator('h1')).toBeVisible();
  100 | 
  101 |     await page.setViewportSize({ width: 768, height: 1024 }); // Tablet
  102 |     await expect(page.locator('h1')).toBeVisible();
  103 | 
  104 |     await page.setViewportSize({ width: 1920, height: 1080 }); // Desktop
  105 |     await expect(page.locator('h1')).toBeVisible();
  106 |   });
  107 | });
  108 | 
```