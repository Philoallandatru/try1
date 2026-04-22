import { test, expect } from '@playwright/test';

test.describe('Markdown Rendering Test', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173');
    await page.evaluate(() => {
      localStorage.setItem('ssdPortalToken', 'change-me');
    });
    await page.reload();
    await page.waitForTimeout(2000);

    // Select demo workspace
    const workspaceSelect = page.locator('select').first();
    await workspaceSelect.selectOption({ label: 'demo' });
    await page.waitForTimeout(2000);
  });

  test('should render markdown in Runs page', async ({ page }) => {
    // Navigate to Runs page
    await page.goto('http://localhost:5173/runs');
    await page.waitForTimeout(3000);

    // Check if there are any runs
    const runRows = page.locator('.run-row');
    const runCount = await runRows.count();
    console.log(`Found ${runCount} runs`);

    if (runCount > 0) {
      // Click the first run
      await runRows.first().click();
      await page.waitForTimeout(2000);

      // Wait for run detail to load
      await page.waitForSelector('.run-detail-stack', { timeout: 10000 });

      // Click on RCA tab
      const rcaTab = page.locator('button[role="tab"]:has-text("RCA")');
      await rcaTab.click();
      await page.waitForTimeout(1000);

      // Check if markdown content is rendered
      const tabPanel = page.locator('.tab-panel');
      const content = await tabPanel.textContent();
      console.log('RCA Tab Content (first 500 chars):', content?.substring(0, 500));

      // Check for markdown elements (should be rendered as HTML, not raw markdown)
      const hasRawMarkdown = content?.includes('###') || content?.includes('##');
      console.log('Has raw markdown (###, ##):', hasRawMarkdown);

      // Check for rendered HTML elements
      const markdownDiv = page.locator('.markdown-content');
      const hasMarkdownDiv = await markdownDiv.count() > 0;
      console.log('Has .markdown-content div:', hasMarkdownDiv);

      if (hasMarkdownDiv) {
        // Check for rendered heading elements
        const headings = markdownDiv.locator('h1, h2, h3, h4');
        const headingCount = await headings.count();
        console.log('Number of rendered headings:', headingCount);

        if (headingCount > 0) {
          const firstHeading = await headings.first().textContent();
          console.log('First heading text:', firstHeading);
        }
      }

      // Take a screenshot
      await page.screenshot({ path: 'test-results/markdown-rendering.png', fullPage: true });
      console.log('Screenshot saved to test-results/markdown-rendering.png');
    } else {
      console.log('No runs found. Please run an analysis first.');
    }
  });

  test('should check all section tabs for markdown rendering', async ({ page }) => {
    await page.goto('http://localhost:5173/runs');
    await page.waitForTimeout(3000);

    const runRows = page.locator('.run-row');
    const runCount = await runRows.count();

    if (runCount > 0) {
      await runRows.first().click();
      await page.waitForTimeout(2000);

      await page.waitForSelector('.run-detail-stack', { timeout: 10000 });

      // Test each section tab
      const tabs = ['RCA', 'Spec Impact', 'Decision Brief'];

      for (const tabName of tabs) {
        console.log(`\n--- Testing ${tabName} tab ---`);
        const tab = page.locator(`button[role="tab"]:has-text("${tabName}")`);
        await tab.click();
        await page.waitForTimeout(1000);

        const tabPanel = page.locator('.tab-panel');
        const content = await tabPanel.textContent();

        const hasRawMarkdown = content?.includes('###') || content?.includes('##');
        console.log(`${tabName} - Has raw markdown:`, hasRawMarkdown);

        const markdownDiv = page.locator('.markdown-content');
        const hasMarkdownDiv = await markdownDiv.count() > 0;
        console.log(`${tabName} - Has .markdown-content div:`, hasMarkdownDiv);

        if (hasMarkdownDiv) {
          const headings = markdownDiv.locator('h1, h2, h3, h4');
          const headingCount = await headings.count();
          console.log(`${tabName} - Number of rendered headings:`, headingCount);
        }
      }
    }
  });
});
