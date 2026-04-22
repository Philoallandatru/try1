import { test, expect } from '@playwright/test';
import { setupAuthAndWorkspace } from './test-helpers';

test.describe('Chinese Output Test', () => {
  test('should generate Chinese analysis with qwen-9b model', async ({ page }) => {
    await setupAuthAndWorkspace(page, 'change-me', 'demo');

    // Wait for setup to be ready
    await page.waitForSelector('.setup-header', { timeout: 10000 });

    // Enter issue key
    await page.fill('input[placeholder*="SSD"]', 'SSD-SAMPLE-1');

    // Click Run Analysis
    await page.click('button:has-text("Run Analysis")');
    console.log('Submitting analysis request...');

    // Wait for analysis to complete (30 minutes timeout for 9b model)
    await page.waitForSelector('.result-surface, .error', { timeout: 1800000 });
    console.log('Analysis completed');

    // Check if we have results
    const hasResults = await page.locator('.result-surface').count() > 0;
    expect(hasResults).toBeTruthy();

    // Get the RCA section text
    const rcaTab = page.locator('button:has-text("RCA")');
    await rcaTab.click();
    await page.waitForTimeout(1000);

    const rcaContent = await page.locator('.markdown-content').first().textContent();
    console.log('RCA content preview:', rcaContent?.substring(0, 500));

    // Check if content contains Chinese characters
    const hasChinese = /[\u4e00-\u9fff]/.test(rcaContent || '');
    console.log('Contains Chinese:', hasChinese);

    expect(hasChinese).toBeTruthy();

    // Also check other sections
    const sections = ['Spec Impact', 'Decision Brief', 'Summary'];
    for (const section of sections) {
      const tab = page.locator(`button:has-text("${section}")`);
      await tab.click();
      await page.waitForTimeout(500);

      const content = await page.locator('.markdown-content').first().textContent();
      const sectionHasChinese = /[\u4e00-\u9fff]/.test(content || '');
      console.log(`${section} contains Chinese:`, sectionHasChinese);
      expect(sectionHasChinese).toBeTruthy();
    }
  });
});
