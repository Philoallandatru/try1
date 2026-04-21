import { test, expect } from '@playwright/test';

test.describe('Verify Chinese Output and Markdown Rendering', () => {
  test('should display Chinese analysis with proper markdown rendering', async ({ page }) => {
    await page.goto('http://localhost:5173');

    // Navigate to the latest run
    await page.click('a[href="/runs"]');
    await page.waitForSelector('text=20260421T042441644174Z-bac9f1a0-workspace-deep-analyze', { timeout: 10000 });
    await page.click('text=20260421T042441644174Z-bac9f1a0-workspace-deep-analyze');

    // Wait for content to load
    await page.waitForSelector('.markdown-content', { timeout: 10000 });

    // Verify Chinese characters are present
    const content = await page.textContent('body');
    expect(content).toContain('根因分析');
    expect(content).toContain('深度分析报告');
    expect(content).toContain('固件版本');

    // Verify markdown is rendered (not raw)
    const rawMarkdown = await page.locator('text=/^###/').count();
    expect(rawMarkdown).toBe(0); // Should not have raw ### symbols

    // Verify headings are rendered as HTML
    const h1Count = await page.locator('h1').count();
    const h2Count = await page.locator('h2').count();
    const h3Count = await page.locator('h3').count();

    console.log(`Found ${h1Count} h1, ${h2Count} h2, ${h3Count} h3 headings`);
    expect(h1Count).toBeGreaterThan(0);
    expect(h2Count).toBeGreaterThan(0);

    // Verify lists are rendered
    const listItems = await page.locator('li').count();
    console.log(`Found ${listItems} list items`);
    expect(listItems).toBeGreaterThan(0);

    // Take screenshot for visual verification
    await page.screenshot({ path: 'test-results/chinese-output-verification.png', fullPage: true });

    console.log('✅ Chinese output and markdown rendering verified successfully!');
  });
});
