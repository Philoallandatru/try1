# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: jira-confluence-full-flow.integration.spec.ts >> Jira/Confluence Full Integration Flow >> Step 4: Verify both sources are listed and check status
- Location: e2e\jira-confluence-full-flow.integration.spec.ts:240:3

# Error details

```
Test timeout of 1860000ms exceeded.
```

```
Error: locator.click: Test timeout of 1860000ms exceeded.
Call log:
  - waiting for locator('button:has-text("全部")').first()

```

# Test source

```ts
  149 |     // Verify Jira source appears in the list
  150 |     await page.waitForTimeout(1000);
  151 |     const jiraCards = page.locator('.bg-white.rounded-xl:has-text("JIRA")');
  152 |     const count = await jiraCards.count();
  153 | 
  154 |     if (count > 0) {
  155 |       console.log(`✓ Jira source added successfully (${count} source(s) found)`);
  156 | 
  157 |       // Get details of the first Jira source
  158 |       const firstCard = jiraCards.first();
  159 |       const name = await firstCard.locator('h3').textContent();
  160 |       const status = await firstCard.locator('span.rounded-full').textContent();
  161 | 
  162 |       console.log(`  Name: ${name}`);
  163 |       console.log(`  Status: ${status}`);
  164 |     } else {
  165 |       console.log('⚠ No Jira sources found in the list');
  166 |     }
  167 |   });
  168 | 
  169 |   test('Step 3: Add Confluence source with complete configuration', async ({ page }) => {
  170 |     console.log('\n=== Step 3: Add Confluence Source ===');
  171 | 
  172 |     await page.goto('http://localhost:5173/data-sources');
  173 |     await page.waitForLoadState('networkidle');
  174 | 
  175 |     // Open add source modal
  176 |     const addButton = page.locator('button:has-text("添加数据源")');
  177 |     await addButton.click();
  178 |     await page.waitForTimeout(500);
  179 | 
  180 |     // Select Confluence type
  181 |     const confluenceButton = page.locator('button:has-text("Confluence")').first();
  182 |     await expect(confluenceButton).toBeVisible({ timeout: 5000 });
  183 |     await confluenceButton.click();
  184 |     await page.waitForTimeout(300);
  185 |     console.log('✓ Confluence type selected');
  186 | 
  187 |     // Fill in Confluence configuration
  188 |     console.log('Filling Confluence configuration...');
  189 | 
  190 |     const urlInput = page.locator('input[placeholder*="Confluence URL"]');
  191 |     await expect(urlInput).toBeVisible({ timeout: 5000 });
  192 |     await urlInput.fill(mockConfluenceUrl);
  193 |     console.log(`  URL: ${mockConfluenceUrl}`);
  194 | 
  195 |     const emailInput = page.locator('input[placeholder*="邮箱"]');
  196 |     await emailInput.fill(testEmail);
  197 |     console.log(`  Email: ${testEmail}`);
  198 | 
  199 |     const tokenInput = page.locator('input[placeholder*="API Token"]');
  200 |     await tokenInput.fill(testToken);
  201 |     console.log(`  Token: ${testToken.substring(0, 10)}...`);
  202 | 
  203 |     // Add space key
  204 |     const spaceInput = page.locator('input[placeholder*="空间键"]');
  205 |     if (await spaceInput.isVisible()) {
  206 |       const spaceKey = 'SSDENG';
  207 |       await spaceInput.fill(spaceKey);
  208 |       console.log(`  Space Key: ${spaceKey}`);
  209 |     }
  210 | 
  211 |     // Take screenshot
  212 |     await page.screenshot({ path: 'test-results/confluence-config-filled.png' });
  213 | 
  214 |     // Submit the form
  215 |     const submitButton = page.locator('button:has-text("添加数据源")').last();
  216 |     await submitButton.click();
  217 |     console.log('✓ Form submitted');
  218 | 
  219 |     // Wait for source to be added
  220 |     await page.waitForTimeout(2000);
  221 | 
  222 |     // Verify Confluence source appears
  223 |     const confluenceCards = page.locator('.bg-white.rounded-xl:has-text("CONFLUENCE")');
  224 |     const count = await confluenceCards.count();
  225 | 
  226 |     if (count > 0) {
  227 |       console.log(`✓ Confluence source added successfully (${count} source(s) found)`);
  228 | 
  229 |       const firstCard = confluenceCards.first();
  230 |       const name = await firstCard.locator('h3').textContent();
  231 |       const status = await firstCard.locator('span.rounded-full').textContent();
  232 | 
  233 |       console.log(`  Name: ${name}`);
  234 |       console.log(`  Status: ${status}`);
  235 |     } else {
  236 |       console.log('⚠ No Confluence sources found in the list');
  237 |     }
  238 |   });
  239 | 
  240 |   test('Step 4: Verify both sources are listed and check status', async ({ page }) => {
  241 |     console.log('\n=== Step 4: Verify Sources ===');
  242 | 
  243 |     await page.goto('http://localhost:5173/data-sources');
  244 |     await page.waitForLoadState('networkidle');
  245 |     await page.waitForTimeout(2000);
  246 | 
  247 |     // Switch to "All Sources" tab
  248 |     const allTab = page.locator('button:has-text("全部")').first();
> 249 |     await allTab.click();
      |                  ^ Error: locator.click: Test timeout of 1860000ms exceeded.
  250 |     await page.waitForTimeout(500);
  251 | 
  252 |     // Get all source cards
  253 |     const sourceCards = page.locator('.bg-white.rounded-xl.border');
  254 |     const totalCount = await sourceCards.count();
  255 | 
  256 |     console.log(`\nTotal sources: ${totalCount}`);
  257 | 
  258 |     // Analyze each source
  259 |     for (let i = 0; i < totalCount; i++) {
  260 |       const card = sourceCards.nth(i);
  261 | 
  262 |       const name = await card.locator('h3').first().textContent();
  263 |       const type = await card.locator('span.uppercase').first().textContent();
  264 |       const status = await card.locator('span.rounded-full').first().textContent();
  265 | 
  266 |       // Try to get item count
  267 |       let itemCount = 'N/A';
  268 |       const itemElement = card.locator('p:has-text("个项目")');
  269 |       if (await itemElement.isVisible()) {
  270 |         const text = await itemElement.textContent();
  271 |         itemCount = text?.match(/\d+/)?.[0] || 'N/A';
  272 |       }
  273 | 
  274 |       console.log(`\nSource ${i + 1}:`);
  275 |       console.log(`  Name: ${name}`);
  276 |       console.log(`  Type: ${type}`);
  277 |       console.log(`  Status: ${status}`);
  278 |       console.log(`  Items: ${itemCount}`);
  279 |     }
  280 | 
  281 |     // Count by type
  282 |     const jiraCount = await page.locator('.bg-white.rounded-xl:has-text("jira")').count();
  283 |     const confluenceCount = await page.locator('.bg-white.rounded-xl:has-text("confluence")').count();
  284 |     const fileCount = await page.locator('.bg-white.rounded-xl:has-text("file")').count();
  285 | 
  286 |     console.log(`\nSummary by type:`);
  287 |     console.log(`  Jira: ${jiraCount}`);
  288 |     console.log(`  Confluence: ${confluenceCount}`);
  289 |     console.log(`  Files: ${fileCount}`);
  290 | 
  291 |     console.log('\n✓ Sources verified');
  292 |   });
  293 | 
  294 |   test('Step 5: Test filtering by source type', async ({ page }) => {
  295 |     console.log('\n=== Step 5: Test Filtering ===');
  296 | 
  297 |     await page.goto('http://localhost:5173/data-sources');
  298 |     await page.waitForLoadState('networkidle');
  299 |     await page.waitForTimeout(1000);
  300 | 
  301 |     const tabs = [
  302 |       { name: '全部', expectedTypes: ['jira', 'confluence', 'file'] },
  303 |       { name: 'Jira', expectedTypes: ['jira'] },
  304 |       { name: 'Confluence', expectedTypes: ['confluence'] },
  305 |       { name: '文件', expectedTypes: ['file'] }
  306 |     ];
  307 | 
  308 |     for (const tab of tabs) {
  309 |       const tabButton = page.locator(`button:has-text("${tab.name}")`).first();
  310 |       await tabButton.click();
  311 |       await page.waitForTimeout(500);
  312 | 
  313 |       const sourceCards = page.locator('.bg-white.rounded-xl.border');
  314 |       const count = await sourceCards.count();
  315 | 
  316 |       console.log(`\n${tab.name} tab: ${count} source(s)`);
  317 | 
  318 |       // Verify filtered sources match expected type
  319 |       if (count > 0 && tab.name !== '全部') {
  320 |         for (let i = 0; i < Math.min(count, 3); i++) {
  321 |           const card = sourceCards.nth(i);
  322 |           const type = await card.locator('span.uppercase').first().textContent();
  323 |           console.log(`  Source ${i + 1} type: ${type}`);
  324 |         }
  325 |       }
  326 |     }
  327 | 
  328 |     console.log('\n✓ Filtering tested');
  329 |   });
  330 | 
  331 |   test('Step 6: Test search functionality', async ({ page }) => {
  332 |     console.log('\n=== Step 6: Test Search ===');
  333 | 
  334 |     await page.goto('http://localhost:5173/data-sources');
  335 |     await page.waitForLoadState('networkidle');
  336 |     await page.waitForTimeout(1000);
  337 | 
  338 |     const searchInput = page.locator('input[placeholder*="搜索"]');
  339 | 
  340 |     if (await searchInput.isVisible()) {
  341 |       // Test search for "jira"
  342 |       await searchInput.fill('jira');
  343 |       await page.waitForTimeout(500);
  344 | 
  345 |       let count = await page.locator('.bg-white.rounded-xl.border').count();
  346 |       console.log(`Search "jira": ${count} result(s)`);
  347 | 
  348 |       // Clear and search for "confluence"
  349 |       await searchInput.clear();
```