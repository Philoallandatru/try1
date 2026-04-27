# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: jira-confluence-full-flow.integration.spec.ts >> Jira/Confluence Full Integration Flow >> Step 3: Add Confluence source with complete configuration
- Location: e2e\jira-confluence-full-flow.integration.spec.ts:169:3

# Error details

```
Test timeout of 1860000ms exceeded.
```

```
Error: locator.click: Test timeout of 1860000ms exceeded.
Call log:
  - waiting for locator('button:has-text("添加数据源")')

```

# Test source

```ts
  77  |     await expect(addButton).toBeVisible();
  78  | 
  79  |     console.log('✓ Data Sources page UI verified');
  80  |   });
  81  | 
  82  |   test('Step 2: Add Jira source with complete configuration', async ({ page }) => {
  83  |     console.log('\n=== Step 2: Add Jira Source ===');
  84  | 
  85  |     await page.goto('http://localhost:5173/data-sources');
  86  |     await page.waitForLoadState('networkidle');
  87  | 
  88  |     // Open add source modal
  89  |     const addButton = page.locator('button:has-text("添加数据源")');
  90  |     await addButton.click();
  91  |     await page.waitForTimeout(500);
  92  | 
  93  |     // Verify modal opened
  94  |     const modalTitle = page.locator('h2:has-text("添加数据源")');
  95  |     await expect(modalTitle).toBeVisible({ timeout: 5000 });
  96  |     console.log('✓ Add source modal opened');
  97  | 
  98  |     // Select Jira type
  99  |     const jiraButton = page.locator('button:has-text("Jira")').first();
  100 |     await expect(jiraButton).toBeVisible();
  101 |     await jiraButton.click();
  102 |     await page.waitForTimeout(300);
  103 | 
  104 |     // Verify Jira button is selected (should have blue background)
  105 |     const jiraButtonClass = await jiraButton.getAttribute('class');
  106 |     expect(jiraButtonClass).toContain('border-blue-500');
  107 |     console.log('✓ Jira type selected');
  108 | 
  109 |     // Fill in Jira configuration
  110 |     console.log('Filling Jira configuration...');
  111 | 
  112 |     const urlInput = page.locator('input[placeholder*="Jira URL"]');
  113 |     await expect(urlInput).toBeVisible({ timeout: 5000 });
  114 |     await urlInput.fill(mockJiraUrl);
  115 |     console.log(`  URL: ${mockJiraUrl}`);
  116 | 
  117 |     const emailInput = page.locator('input[placeholder*="邮箱"]');
  118 |     await emailInput.fill(testEmail);
  119 |     console.log(`  Email: ${testEmail}`);
  120 | 
  121 |     const tokenInput = page.locator('input[placeholder*="API Token"]');
  122 |     await tokenInput.fill(testToken);
  123 |     console.log(`  Token: ${testToken.substring(0, 10)}...`);
  124 | 
  125 |     // Add JQL query
  126 |     const jqlInput = page.locator('textarea[placeholder*="JQL"]');
  127 |     if (await jqlInput.isVisible()) {
  128 |       const jqlQuery = 'project = SSD AND status != Done';
  129 |       await jqlInput.fill(jqlQuery);
  130 |       console.log(`  JQL: ${jqlQuery}`);
  131 |     }
  132 | 
  133 |     // Take screenshot before submission
  134 |     await page.screenshot({ path: 'test-results/jira-config-filled.png' });
  135 | 
  136 |     // Submit the form
  137 |     const submitButton = page.locator('button:has-text("添加数据源")').last();
  138 |     await submitButton.click();
  139 |     console.log('✓ Form submitted');
  140 | 
  141 |     // Wait for modal to close and source to be added
  142 |     await page.waitForTimeout(2000);
  143 | 
  144 |     // Verify modal closed
  145 |     const modalStillVisible = await modalTitle.isVisible().catch(() => false);
  146 |     expect(modalStillVisible).toBe(false);
  147 |     console.log('✓ Modal closed');
  148 | 
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
> 177 |     await addButton.click();
      |                     ^ Error: locator.click: Test timeout of 1860000ms exceeded.
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
  249 |     await allTab.click();
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
```