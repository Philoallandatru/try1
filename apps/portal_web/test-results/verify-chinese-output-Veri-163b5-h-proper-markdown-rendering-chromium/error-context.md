# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: verify-chinese-output.spec.ts >> Verify Chinese Output and Markdown Rendering >> should display Chinese analysis with proper markdown rendering
- Location: e2e\verify-chinese-output.spec.ts:4:3

# Error details

```
TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator('text=20260421T042441644174Z-bac9f1a0-workspace-deep-analyze') to be visible

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - generic [ref=e5]:
      - generic [ref=e6]: S
      - generic [ref=e7]:
        - paragraph [ref=e8]: SSD Platform
        - heading "Codex Ops" [level=1] [ref=e9]
    - generic [ref=e10]: Workspace
    - navigation [ref=e11]:
      - link "Analyze" [ref=e12] [cursor=pointer]:
        - /url: /
        - img [ref=e13]
        - text: Analyze
      - link "Search" [ref=e16] [cursor=pointer]:
        - /url: /search
        - img [ref=e17]
        - text: Search
      - link "Runs" [active] [ref=e20] [cursor=pointer]:
        - /url: /runs
        - img [ref=e21]
        - text: Runs
      - link "Analysis" [ref=e24] [cursor=pointer]:
        - /url: /analysis
        - img [ref=e25]
        - text: Analysis
      - link "Daily Report" [ref=e27] [cursor=pointer]:
        - /url: /daily-report
        - img [ref=e28]
        - text: Daily Report
      - link "Batch Analysis" [ref=e30] [cursor=pointer]:
        - /url: /batch-analysis
        - img [ref=e31]
        - text: Batch Analysis
      - link "Sources" [ref=e35] [cursor=pointer]:
        - /url: /sources
        - img [ref=e36]
        - text: Sources
      - link "Profiles" [ref=e40] [cursor=pointer]:
        - /url: /profiles
        - img [ref=e41]
        - text: Profiles
      - link "Wiki" [ref=e44] [cursor=pointer]:
        - /url: /wiki
        - img [ref=e45]
        - text: Wiki
      - link "Reports" [ref=e48] [cursor=pointer]:
        - /url: /reports
        - img [ref=e49]
        - text: Reports
      - link "Spec Lab" [ref=e51] [cursor=pointer]:
        - /url: /spec
        - img [ref=e52]
        - text: Spec Lab
      - link "Admin" [ref=e55] [cursor=pointer]:
        - /url: /admin/
        - img [ref=e56]
        - text: Admin
    - generic [ref=e62]: Runner waiting
  - main [ref=e63]:
    - generic [ref=e64]:
      - generic [ref=e67]:
        - paragraph [ref=e68]: Local Runner
        - strong [ref=e69]: Connect Runner
      - generic "Runner controls" [ref=e70]:
        - generic [ref=e71]:
          - text: Token
          - textbox "Token" [ref=e72]:
            - /placeholder: change-me
        - generic [ref=e73]:
          - text: Workspace
          - combobox "Workspace" [ref=e74]:
            - option "No workspace" [selected]
        - generic [ref=e75]:
          - text: New
          - generic [ref=e76]:
            - textbox "New Create" [ref=e77]: real-workspace
            - button "Create" [ref=e78] [cursor=pointer]
    - generic [ref=e79]:
      - heading "Connect the runner" [level=3] [ref=e80]
      - paragraph [ref=e81]: Enter the local runner token to load workspaces, sources, profiles, and runs.
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('Verify Chinese Output and Markdown Rendering', () => {
  4  |   test('should display Chinese analysis with proper markdown rendering', async ({ page }) => {
  5  |     await page.goto('http://localhost:5173');
  6  | 
  7  |     // Navigate to the latest run
  8  |     await page.click('a[href="/runs"]');
> 9  |     await page.waitForSelector('text=20260421T042441644174Z-bac9f1a0-workspace-deep-analyze', { timeout: 10000 });
     |                ^ TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
  10 |     await page.click('text=20260421T042441644174Z-bac9f1a0-workspace-deep-analyze');
  11 | 
  12 |     // Wait for content to load
  13 |     await page.waitForSelector('.markdown-content', { timeout: 10000 });
  14 | 
  15 |     // Verify Chinese characters are present
  16 |     const content = await page.textContent('body');
  17 |     expect(content).toContain('根因分析');
  18 |     expect(content).toContain('深度分析报告');
  19 |     expect(content).toContain('固件版本');
  20 | 
  21 |     // Verify markdown is rendered (not raw)
  22 |     const rawMarkdown = await page.locator('text=/^###/').count();
  23 |     expect(rawMarkdown).toBe(0); // Should not have raw ### symbols
  24 | 
  25 |     // Verify headings are rendered as HTML
  26 |     const h1Count = await page.locator('h1').count();
  27 |     const h2Count = await page.locator('h2').count();
  28 |     const h3Count = await page.locator('h3').count();
  29 | 
  30 |     console.log(`Found ${h1Count} h1, ${h2Count} h2, ${h3Count} h3 headings`);
  31 |     expect(h1Count).toBeGreaterThan(0);
  32 |     expect(h2Count).toBeGreaterThan(0);
  33 | 
  34 |     // Verify lists are rendered
  35 |     const listItems = await page.locator('li').count();
  36 |     console.log(`Found ${listItems} list items`);
  37 |     expect(listItems).toBeGreaterThan(0);
  38 | 
  39 |     // Take screenshot for visual verification
  40 |     await page.screenshot({ path: 'test-results/chinese-output-verification.png', fullPage: true });
  41 | 
  42 |     console.log('✅ Chinese output and markdown rendering verified successfully!');
  43 |   });
  44 | });
  45 | 
```