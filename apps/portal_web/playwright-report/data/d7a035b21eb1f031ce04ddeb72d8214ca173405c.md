# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: verify-chinese-output.spec.ts >> Verify Chinese Output and Markdown Rendering >> should display Chinese analysis with proper markdown rendering
- Location: e2e\verify-chinese-output.spec.ts:4:3

# Error details

```
Test timeout of 1860000ms exceeded.
```

```
Error: page.click: Test timeout of 1860000ms exceeded.
Call log:
  - waiting for locator('a[href="/runs"]')

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e4]:
    - generic [ref=e5]:
      - heading "Knowledge Portal" [level=2] [ref=e6]
      - button "+ New Chat" [ref=e7] [cursor=pointer]:
        - generic [ref=e8]: +
        - text: New Chat
    - generic [ref=e9]:
      - generic [ref=e10] [cursor=pointer]: 💬 Chat
      - generic [ref=e11] [cursor=pointer]: 📚 Knowledge Base
      - generic [ref=e12] [cursor=pointer]: 🗄️ Data Sources
      - generic [ref=e13] [cursor=pointer]: 🤖 Models
  - generic [ref=e15]:
    - generic [ref=e17]:
      - generic [ref=e18]: 💡
      - heading "How can I help you today?" [level=1] [ref=e19]
      - paragraph [ref=e20]: Ask me anything about your knowledge base, documents, or get insights from your data sources.
      - generic [ref=e21]:
        - generic [ref=e22] [cursor=pointer]:
          - generic [ref=e23]: Explain a concept
          - generic [ref=e24]: What is LlamaIndex and how does it work?
        - generic [ref=e25] [cursor=pointer]:
          - generic [ref=e26]: Search knowledge base
          - generic [ref=e27]: Find information about data sources configuration
        - generic [ref=e28] [cursor=pointer]:
          - generic [ref=e29]: Technical question
          - generic [ref=e30]: How do I integrate Jira with this system?
        - generic [ref=e31] [cursor=pointer]:
          - generic [ref=e32]: Get started
          - generic [ref=e33]: What can you help me with?
    - generic [ref=e34]:
      - generic [ref=e35]:
        - generic [ref=e36]:
          - generic [ref=e37]: Knowledge Base
          - combobox [ref=e38] [cursor=pointer]:
            - option "Default" [selected]
        - generic [ref=e39]:
          - generic [ref=e40]: Model
          - combobox [ref=e41] [cursor=pointer]:
            - option "Default" [selected]
      - generic [ref=e42]:
        - textbox "Message Knowledge Portal..." [ref=e43]
        - button "↑" [disabled] [ref=e44]
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
> 8  |     await page.click('a[href="/runs"]');
     |                ^ Error: page.click: Test timeout of 1860000ms exceeded.
  9  |     await page.waitForSelector('text=20260421T042441644174Z-bac9f1a0-workspace-deep-analyze', { timeout: 10000 });
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