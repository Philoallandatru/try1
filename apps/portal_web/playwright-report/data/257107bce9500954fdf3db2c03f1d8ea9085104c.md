# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: complete-flow.spec.ts >> Complete End-to-End Flow >> Flow: Search → Analyze → Runs
- Location: e2e\complete-flow.spec.ts:326:3

# Error details

```
Test timeout of 1860000ms exceeded.
```

```
Error: page.click: Test timeout of 1860000ms exceeded.
Call log:
  - waiting for locator('aside.nav a[href="/search"]')

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
  230 |       }
  231 |     } else if (isEmpty) {
  232 |       console.log('  No results found (empty state)');
  233 |     }
  234 | 
  235 |     console.log('✓ Search results verified');
  236 | 
  237 |     // ===== STEP 9: Test Search Filters =====
  238 |     console.log('\n=== STEP 9: Test Search Filters ===');
  239 | 
  240 |     // Test document type filters
  241 |     const specFilter = page.locator('button.filter-button:has-text("Specification")');
  242 |     if (await specFilter.isVisible()) {
  243 |       await specFilter.click();
  244 |       await page.waitForTimeout(500);
  245 |       console.log('✓ Specification filter applied');
  246 | 
  247 |       // Clear filter
  248 |       const clearFilter = page.locator('button.filter-button.clear');
  249 |       if (await clearFilter.isVisible()) {
  250 |         await clearFilter.click();
  251 |         await page.waitForTimeout(500);
  252 |         console.log('✓ Filter cleared');
  253 |       }
  254 |     }
  255 | 
  256 |     // ===== STEP 10: Navigate Back to Data Sources =====
  257 |     console.log('\n=== STEP 10: Return to Data Sources ===');
  258 | 
  259 |     await page.click('aside.nav a[href="/data-sources"]');
  260 |     await page.waitForLoadState('networkidle');
  261 | 
  262 |     await expect(heading).toBeVisible({ timeout: 5000 });
  263 | 
  264 |     // Verify sources still exist
  265 |     const finalCount = await sourceCards.count();
  266 |     console.log(`  Final data source count: ${finalCount}`);
  267 |     expect(finalCount).toBeGreaterThanOrEqual(2);
  268 | 
  269 |     console.log('✓ Returned to Data Sources page');
  270 | 
  271 |     // ===== FLOW COMPLETE =====
  272 |     console.log('\n=== ✅ COMPLETE E2E FLOW SUCCESSFUL ===');
  273 |     console.log('Summary:');
  274 |     console.log('  ✓ Added Jira data source');
  275 |     console.log('  ✓ Added Confluence data source');
  276 |     console.log('  ✓ Verified data sources');
  277 |     console.log('  ✓ Built search index');
  278 |     console.log('  ✓ Executed search query');
  279 |     console.log('  ✓ Verified search results');
  280 |     console.log('  ✓ Tested filters');
  281 |     console.log('  ✓ Navigation verified');
  282 |   });
  283 | 
  284 |   test('Flow: Data Sources → Retrieval Debug', async ({ page }) => {
  285 |     console.log('\n=== Flow: Data Sources → Retrieval Debug ===');
  286 | 
  287 |     // Navigate to Data Sources
  288 |     await page.click('aside.nav a[href="/data-sources"]');
  289 |     await page.waitForLoadState('networkidle');
  290 |     console.log('✓ On Data Sources page');
  291 | 
  292 |     // Navigate to Retrieval Debug
  293 |     await page.click('aside.nav a[href="/retrieval-debug"]');
  294 |     await page.waitForLoadState('networkidle');
  295 | 
  296 |     const heading = page.locator('h1:has-text("检索调试工具")');
  297 |     await expect(heading).toBeVisible({ timeout: 5000 });
  298 |     console.log('✓ Retrieval Debug page loaded');
  299 | 
  300 |     // Verify debug tools are present
  301 |     const content = page.locator('main.workspace');
  302 |     await expect(content).toBeVisible();
  303 | 
  304 |     console.log('✓ Flow completed: Data Sources → Retrieval Debug');
  305 |   });
  306 | 
  307 |   test('Flow: Data Sources → Strategy Comparison', async ({ page }) => {
  308 |     console.log('\n=== Flow: Data Sources → Strategy Comparison ===');
  309 | 
  310 |     // Navigate to Data Sources
  311 |     await page.click('aside.nav a[href="/data-sources"]');
  312 |     await page.waitForLoadState('networkidle');
  313 |     console.log('✓ On Data Sources page');
  314 | 
  315 |     // Navigate to Strategy Comparison
  316 |     await page.click('aside.nav a[href="/strategy-comparison"]');
  317 |     await page.waitForLoadState('networkidle');
  318 | 
  319 |     const heading = page.locator('h1:has-text("多策略检索对比")');
  320 |     await expect(heading).toBeVisible({ timeout: 5000 });
  321 |     console.log('✓ Strategy Comparison page loaded');
  322 | 
  323 |     console.log('✓ Flow completed: Data Sources → Strategy Comparison');
  324 |   });
  325 | 
  326 |   test('Flow: Search → Analyze → Runs', async ({ page }) => {
  327 |     console.log('\n=== Flow: Search → Analyze → Runs ===');
  328 | 
  329 |     // Step 1: Search
> 330 |     await page.click('aside.nav a[href="/search"]');
      |                ^ Error: page.click: Test timeout of 1860000ms exceeded.
  331 |     await page.waitForLoadState('networkidle');
  332 |     console.log('✓ Search page loaded');
  333 | 
  334 |     // Step 2: Analyze
  335 |     await page.click('aside.nav a[href="/"]');
  336 |     await page.waitForLoadState('networkidle');
  337 | 
  338 |     const analyzeHeading = page.locator('h2:has-text("Deep Jira Analysis")');
  339 |     await expect(analyzeHeading).toBeVisible({ timeout: 5000 });
  340 |     console.log('✓ Analyze page loaded');
  341 | 
  342 |     // Step 3: Runs
  343 |     await page.click('aside.nav a[href="/runs"]');
  344 |     await page.waitForLoadState('networkidle');
  345 | 
  346 |     const runsHeading = page.locator('h3:has-text("Run History")');
  347 |     await expect(runsHeading).toBeVisible({ timeout: 5000 });
  348 |     console.log('✓ Runs page loaded');
  349 | 
  350 |     console.log('✓ Flow completed: Search → Analyze → Runs');
  351 |   });
  352 | });
  353 | 
```