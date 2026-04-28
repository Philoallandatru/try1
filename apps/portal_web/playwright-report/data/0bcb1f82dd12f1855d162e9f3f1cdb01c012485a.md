# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: analyze-page.spec.ts >> Analyze Page E2E Tests >> should validate form inputs
- Location: e2e\analyze-page.spec.ts:225:3

# Error details

```
Test timeout of 1860000ms exceeded.
```

```
Error: locator.fill: Test timeout of 1860000ms exceeded.
Call log:
  - waiting for locator('input[placeholder*="SSD-DEMO-A"]')

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
  133 |       await expect(errorMessage).toContainText(/error|failed|Internal Server Error/i);
  134 |     }
  135 |   });
  136 | 
  137 |   test('should show recent issues in datalist', async ({ page }) => {
  138 |     // Set up recent issues in localStorage
  139 |     await page.goto('http://localhost:5173/');
  140 |     await page.evaluate(() => {
  141 |       localStorage.setItem('ssdPortalRecent:issues', JSON.stringify(['SSD-DEMO-A', 'SSD-DEMO-B', 'SSD-SAMPLE-1']));
  142 |     });
  143 |     await page.reload();
  144 | 
  145 |     // Check if datalist exists
  146 |     const datalist = page.locator('#recent-issues');
  147 |     if (await datalist.count() > 0) {
  148 |       const options = await datalist.locator('option').count();
  149 |       expect(options).toBeGreaterThan(0);
  150 |     }
  151 |   });
  152 | 
  153 |   test('should display result view after successful analysis', async ({ page }) => {
  154 |     await page.goto('http://localhost:5173/');
  155 | 
  156 |     // Wait for page load
  157 |     await page.waitForSelector('.analyze-grid', { timeout: 10000 });
  158 | 
  159 |     // Check if result surface exists (might be empty initially)
  160 |     const resultSurface = page.locator('.result-surface');
  161 |     await expect(resultSurface).toBeVisible();
  162 |   });
  163 | 
  164 |   test('should handle workspace selection', async ({ page }) => {
  165 |     await page.goto('http://localhost:5173/');
  166 | 
  167 |     // Check for workspace selector
  168 |     const workspaceSelect = page.locator('label:has-text("Workspace") select');
  169 | 
  170 |     if (await workspaceSelect.count() > 0) {
  171 |       await expect(workspaceSelect).toBeVisible();
  172 | 
  173 |       // Check if it has options
  174 |       const options = await workspaceSelect.locator('option').count();
  175 |       expect(options).toBeGreaterThan(0);
  176 |     }
  177 |   });
  178 | 
  179 |   test('should show advanced options when clicked', async ({ page }) => {
  180 |     await page.goto('http://localhost:5173/');
  181 | 
  182 |     // Find and click Advanced button
  183 |     const advancedButton = page.locator('button:has-text("Advanced")');
  184 | 
  185 |     if (await advancedButton.count() > 0) {
  186 |       await advancedButton.click();
  187 | 
  188 |       // Check if advanced grid appears
  189 |       const advancedGrid = page.locator('.advanced-grid');
  190 |       await expect(advancedGrid).toBeVisible();
  191 | 
  192 |       // Click again to hide
  193 |       await page.locator('button:has-text("Hide Advanced")').click();
  194 |       await expect(advancedGrid).not.toBeVisible();
  195 |     }
  196 |   });
  197 | 
  198 |   test('should navigate to other pages from sidebar', async ({ page }) => {
  199 |     await page.goto('http://localhost:5173/');
  200 | 
  201 |     // Check sidebar navigation
  202 |     const searchLink = page.locator('nav a:has-text("Search")');
  203 |     await expect(searchLink).toBeVisible();
  204 | 
  205 |     await searchLink.click();
  206 |     await expect(page).toHaveURL('http://localhost:5173/search');
  207 | 
  208 |     // Navigate back
  209 |     const analyzeLink = page.locator('nav a:has-text("Analyze")');
  210 |     await analyzeLink.click();
  211 |     await expect(page).toHaveURL('http://localhost:5173/');
  212 |   });
  213 | 
  214 |   test('should check backend connectivity', async ({ page }) => {
  215 |     await page.goto('http://localhost:5173/');
  216 | 
  217 |     // Wait for initial API calls
  218 |     await page.waitForTimeout(2000);
  219 | 
  220 |     // Check for connection status
  221 |     const statusIndicator = page.locator('text=/Runner connected|Runner waiting/');
  222 |     await expect(statusIndicator).toBeVisible();
  223 |   });
  224 | 
  225 |   test('should validate form inputs', async ({ page }) => {
  226 |     await page.goto('http://localhost:5173/');
  227 | 
  228 |     // Try to submit empty form
  229 |     const runButton = page.locator('button:has-text("Run Analysis")');
  230 | 
  231 |     // Button should be disabled if setup is not complete or form is invalid
  232 |     const issueInput = page.locator('input[placeholder*="SSD-DEMO-A"]');
> 233 |     await issueInput.fill('');
      |                      ^ Error: locator.fill: Test timeout of 1860000ms exceeded.
  234 | 
  235 |     // Check button state after clearing input
  236 |     await page.waitForTimeout(500);
  237 |   });
  238 | 
  239 |   test('should display setup checklist items correctly', async ({ page }) => {
  240 |     await page.goto('http://localhost:5173/');
  241 | 
  242 |     await page.waitForSelector('.setup-checklist', { timeout: 10000 });
  243 | 
  244 |     // Check for specific setup items
  245 |     const expectedItems = ['Jira Source', 'Confluence Source', 'File Asset', 'Analysis Profile'];
  246 | 
  247 |     for (const item of expectedItems) {
  248 |       const setupItem = page.locator(`.setup-item:has-text("${item}")`);
  249 |       if (await setupItem.count() > 0) {
  250 |         await expect(setupItem).toBeVisible();
  251 |       }
  252 |     }
  253 |   });
  254 | 
  255 |   test('should handle setup item navigation', async ({ page }) => {
  256 |     await page.goto('http://localhost:5173/');
  257 | 
  258 |     await page.waitForSelector('.setup-checklist', { timeout: 10000 });
  259 | 
  260 |     // Click on a setup item (e.g., Sources)
  261 |     const sourcesItem = page.locator('.setup-item:has-text("Jira Source")');
  262 | 
  263 |     if (await sourcesItem.count() > 0) {
  264 |       await sourcesItem.click();
  265 | 
  266 |       // Should navigate to sources page
  267 |       await expect(page).toHaveURL(/\/sources/);
  268 |     }
  269 |   });
  270 | });
  271 | 
```