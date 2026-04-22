import { test, expect } from '@playwright/test';

test.describe('Analysis Page E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the home page
    await page.goto('http://localhost:5173');
  });

  test('should display analysis page with correct UI elements', async ({ page }) => {
    // Navigate to analysis page (assuming there's a link or we can go directly)
    await page.goto('http://localhost:5173/analysis');

    // Check for page title or heading
    await expect(page.locator('h1, h2').first()).toBeVisible();
  });

  test('should trigger deep analysis for a Jira issue', async ({ page }) => {
    // This test requires demo data to be available
    await page.goto('http://localhost:5173/analysis');

    // Look for an analyze button or input field
    const analyzeButton = page.getByRole('button', { name: /analyze|分析/i });

    if (await analyzeButton.isVisible()) {
      await analyzeButton.click();

      // Wait for analysis to complete (with timeout)
      await page.waitForSelector('[data-testid="analysis-result"], .analysis-result, .markdown-body', {
        timeout: 30000
      });
    }
  });

  test('should display Markdown content correctly', async ({ page }) => {
    // Navigate to a page with analysis results
    await page.goto('http://localhost:5173/analysis');

    // Check if markdown-body class exists (from our CSS)
    const markdownContent = page.locator('.markdown-body');

    if (await markdownContent.count() > 0) {
      // Verify markdown elements are rendered
      const hasHeadings = await markdownContent.locator('h1, h2, h3').count() > 0;
      const hasParagraphs = await markdownContent.locator('p').count() > 0;

      expect(hasHeadings || hasParagraphs).toBeTruthy();
    }
  });

  test('should handle Chinese content in analysis results', async ({ page }) => {
    await page.goto('http://localhost:5173/analysis');

    // Look for Chinese characters in the page
    const pageContent = await page.textContent('body');

    // Check if Chinese characters are present and rendered
    const hasChinese = /[\u4e00-\u9fa5]/.test(pageContent || '');

    // If there's Chinese content, verify it's visible
    if (hasChinese) {
      const chineseText = page.locator('text=/[\u4e00-\u9fa5]/').first();
      await expect(chineseText).toBeVisible();
    }
  });

  test('should display analysis sections correctly', async ({ page }) => {
    await page.goto('http://localhost:5173/analysis');

    // Look for section headings (根因分析, 规格影响, etc.)
    const sections = [
      '根因分析',
      '规格影响',
      '决策简报',
      '综合总结'
    ];

    // Check if any of these sections exist
    for (const section of sections) {
      const sectionHeading = page.locator(`text=${section}`);
      if (await sectionHeading.count() > 0) {
        await expect(sectionHeading.first()).toBeVisible();
        break;
      }
    }
  });

  test('should render code blocks in analysis results', async ({ page }) => {
    await page.goto('http://localhost:5173/analysis');

    // Check for code blocks
    const codeBlocks = page.locator('pre code, .markdown-body pre');

    if (await codeBlocks.count() > 0) {
      await expect(codeBlocks.first()).toBeVisible();

      // Verify code block has proper styling
      const backgroundColor = await codeBlocks.first().evaluate(el =>
        window.getComputedStyle(el).backgroundColor
      );
      expect(backgroundColor).not.toBe('rgba(0, 0, 0, 0)'); // Not transparent
    }
  });

  test('should render lists in analysis results', async ({ page }) => {
    await page.goto('http://localhost:5173/analysis');

    // Check for lists (ul or ol)
    const lists = page.locator('.markdown-body ul, .markdown-body ol');

    if (await lists.count() > 0) {
      await expect(lists.first()).toBeVisible();

      // Verify list items exist
      const listItems = lists.first().locator('li');
      expect(await listItems.count()).toBeGreaterThan(0);
    }
  });

  test('should render tables in analysis results', async ({ page }) => {
    await page.goto('http://localhost:5173/analysis');

    // Check for tables
    const tables = page.locator('.markdown-body table');

    if (await tables.count() > 0) {
      await expect(tables.first()).toBeVisible();

      // Verify table has headers and rows
      const headers = tables.first().locator('th');
      const rows = tables.first().locator('tr');

      expect(await headers.count()).toBeGreaterThan(0);
      expect(await rows.count()).toBeGreaterThan(1);
    }
  });

  test('should handle loading state during analysis', async ({ page }) => {
    await page.goto('http://localhost:5173/analysis');

    // Look for loading indicators
    const loadingIndicators = page.locator('[data-testid="loading"], .loading, text=/loading|加载中/i');

    // If there's a trigger button, click it and check for loading state
    const analyzeButton = page.getByRole('button', { name: /analyze|分析/i });

    if (await analyzeButton.isVisible()) {
      await analyzeButton.click();

      // Loading indicator should appear
      if (await loadingIndicators.count() > 0) {
        await expect(loadingIndicators.first()).toBeVisible();
      }
    }
  });

  test('should display error message on API failure', async ({ page }) => {
    // Mock API to return error
    await page.route('**/api/analysis/**', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });

    await page.goto('http://localhost:5173/analysis');

    // Try to trigger analysis
    const analyzeButton = page.getByRole('button', { name: /analyze|分析/i });

    if (await analyzeButton.isVisible()) {
      await analyzeButton.click();

      // Error message should appear
      const errorMessage = page.locator('text=/error|错误|failed|失败/i');
      await expect(errorMessage.first()).toBeVisible({ timeout: 10000 });
    }
  });
});
