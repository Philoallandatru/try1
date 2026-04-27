# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: data-source-setup.integration.spec.ts >> Data Source Setup - From Scratch >> should add Confluence source with mock server
- Location: e2e\data-source-setup.integration.spec.ts:114:3

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
  21  |   test.beforeEach(async ({ page }) => {
  22  |     // Navigate to home page
  23  |     await page.goto('http://localhost:5173');
  24  |     await page.waitForLoadState('networkidle');
  25  | 
  26  |     // Connect to runner if needed
  27  |     const tokenInput = page.locator('input[placeholder="change-me"]');
  28  |     if (await tokenInput.isVisible()) {
  29  |       await tokenInput.fill(mockToken);
  30  |       await tokenInput.blur();
  31  |       await page.waitForTimeout(1500);
  32  |     }
  33  | 
  34  |     // Select or create test workspace
  35  |     const workspaceSelect = page.locator('select[data-testid="workspace-selector"]').first();
  36  |     if (await workspaceSelect.isVisible()) {
  37  |       // Try to select test workspace, or use first available
  38  |       const options = await workspaceSelect.locator('option').allTextContents();
  39  |       if (options.includes(workspaceName)) {
  40  |         await workspaceSelect.selectOption({ label: workspaceName });
  41  |       } else {
  42  |         // Use first available workspace
  43  |         await workspaceSelect.selectOption({ index: 0 });
  44  |       }
  45  |       await page.waitForTimeout(1000);
  46  |     }
  47  |   });
  48  | 
  49  |   test('should navigate to Data Sources page', async ({ page }) => {
  50  |     // Navigate to data sources page
  51  |     await page.goto('http://localhost:5173/data-sources');
  52  |     await page.waitForLoadState('networkidle');
  53  | 
  54  |     // Verify page loaded
  55  |     const heading = page.locator('h1:has-text("数据源管理")');
  56  |     await expect(heading).toBeVisible({ timeout: 5000 });
  57  | 
  58  |     console.log('✓ Data Sources page loaded successfully');
  59  |   });
  60  | 
  61  |   test('should add Jira source with mock server', async ({ page }) => {
  62  |     // Navigate to data sources page
  63  |     await page.goto('http://localhost:5173/data-sources');
  64  |     await page.waitForLoadState('networkidle');
  65  | 
  66  |     // Click "Add Source" button
  67  |     const addButton = page.locator('button:has-text("添加数据源")');
  68  |     await expect(addButton).toBeVisible({ timeout: 5000 });
  69  |     await addButton.click();
  70  | 
  71  |     // Wait for modal to appear
  72  |     await page.waitForTimeout(500);
  73  | 
  74  |     // Select Jira type
  75  |     const jiraOption = page.locator('button:has-text("Jira")').first();
  76  |     await expect(jiraOption).toBeVisible({ timeout: 5000 });
  77  |     await jiraOption.click();
  78  | 
  79  |     console.log('✓ Jira option selected');
  80  | 
  81  |     // Fill in Jira configuration
  82  |     const urlInput = page.locator('input[placeholder*="Jira URL"]');
  83  |     await expect(urlInput).toBeVisible({ timeout: 5000 });
  84  |     await urlInput.fill(mockJiraUrl);
  85  | 
  86  |     const emailInput = page.locator('input[placeholder*="邮箱"]');
  87  |     await emailInput.fill(mockEmail);
  88  | 
  89  |     const tokenInput = page.locator('input[placeholder*="API Token"]');
  90  |     await tokenInput.fill(mockToken);
  91  | 
  92  |     // Optional: Add JQL query
  93  |     const jqlInput = page.locator('textarea[placeholder*="JQL"]');
  94  |     if (await jqlInput.isVisible()) {
  95  |       await jqlInput.fill('project = TEST');
  96  |     }
  97  | 
  98  |     console.log('✓ Jira configuration filled');
  99  | 
  100 |     // Click "Add Source" button in modal
  101 |     const submitButton = page.locator('button:has-text("添加数据源")').last();
  102 |     await submitButton.click();
  103 | 
  104 |     // Wait for source to be added
  105 |     await page.waitForTimeout(2000);
  106 | 
  107 |     // Verify Jira source appears in the list
  108 |     const jiraCard = page.locator('.bg-white:has-text("jira")').first();
  109 |     await expect(jiraCard).toBeVisible({ timeout: 10000 });
  110 | 
  111 |     console.log('✓ Jira source added successfully');
  112 |   });
  113 | 
  114 |   test('should add Confluence source with mock server', async ({ page }) => {
  115 |     // Navigate to data sources page
  116 |     await page.goto('http://localhost:5173/data-sources');
  117 |     await page.waitForLoadState('networkidle');
  118 | 
  119 |     // Click "Add Source" button
  120 |     const addButton = page.locator('button:has-text("添加数据源")');
> 121 |     await addButton.click();
      |                     ^ Error: locator.click: Test timeout of 1860000ms exceeded.
  122 |     await page.waitForTimeout(500);
  123 | 
  124 |     // Select Confluence type
  125 |     const confluenceOption = page.locator('button:has-text("Confluence")').first();
  126 |     await expect(confluenceOption).toBeVisible({ timeout: 5000 });
  127 |     await confluenceOption.click();
  128 | 
  129 |     console.log('✓ Confluence option selected');
  130 | 
  131 |     // Fill in Confluence configuration
  132 |     const urlInput = page.locator('input[placeholder*="Confluence URL"]');
  133 |     await expect(urlInput).toBeVisible({ timeout: 5000 });
  134 |     await urlInput.fill(mockConfluenceUrl);
  135 | 
  136 |     const emailInput = page.locator('input[placeholder*="邮箱"]');
  137 |     await emailInput.fill(mockEmail);
  138 | 
  139 |     const tokenInput = page.locator('input[placeholder*="API Token"]');
  140 |     await tokenInput.fill(mockToken);
  141 | 
  142 |     // Optional: Add space key
  143 |     const spaceInput = page.locator('input[placeholder*="空间键"]');
  144 |     if (await spaceInput.isVisible()) {
  145 |       await spaceInput.fill('TEST');
  146 |     }
  147 | 
  148 |     console.log('✓ Confluence configuration filled');
  149 | 
  150 |     // Click "Add Source" button in modal
  151 |     const submitButton = page.locator('button:has-text("添加数据源")').last();
  152 |     await submitButton.click();
  153 | 
  154 |     // Wait for source to be added
  155 |     await page.waitForTimeout(2000);
  156 | 
  157 |     // Verify Confluence source appears in the list
  158 |     const confluenceCard = page.locator('.bg-white:has-text("confluence")').first();
  159 |     await expect(confluenceCard).toBeVisible({ timeout: 10000 });
  160 | 
  161 |     console.log('✓ Confluence source added successfully');
  162 |   });
  163 | 
  164 |   test('should display both Jira and Confluence sources', async ({ page }) => {
  165 |     // Navigate to data sources page
  166 |     await page.goto('http://localhost:5173/data-sources');
  167 |     await page.waitForLoadState('networkidle');
  168 | 
  169 |     // Wait for sources to load
  170 |     await page.waitForTimeout(2000);
  171 | 
  172 |     // Check for Jira tab
  173 |     const jiraTab = page.locator('button:has-text("Jira")').first();
  174 |     if (await jiraTab.isVisible()) {
  175 |       await jiraTab.click();
  176 |       await page.waitForTimeout(500);
  177 | 
  178 |       // Count Jira sources
  179 |       const jiraSources = page.locator('.bg-white:has-text("jira")');
  180 |       const jiraCount = await jiraSources.count();
  181 |       console.log(`Found ${jiraCount} Jira source(s)`);
  182 |     }
  183 | 
  184 |     // Check for Confluence tab
  185 |     const confluenceTab = page.locator('button:has-text("Confluence")').first();
  186 |     if (await confluenceTab.isVisible()) {
  187 |       await confluenceTab.click();
  188 |       await page.waitForTimeout(500);
  189 | 
  190 |       // Count Confluence sources
  191 |       const confluenceSources = page.locator('.bg-white:has-text("confluence")');
  192 |       const confluenceCount = await confluenceSources.count();
  193 |       console.log(`Found ${confluenceCount} Confluence source(s)`);
  194 |     }
  195 | 
  196 |     // Switch to "All Sources" tab
  197 |     const allTab = page.locator('button:has-text("全部")').first();
  198 |     if (await allTab.isVisible()) {
  199 |       await allTab.click();
  200 |       await page.waitForTimeout(500);
  201 |     }
  202 | 
  203 |     console.log('✓ Data sources displayed successfully');
  204 |   });
  205 | 
  206 |   test('should verify source status and document count', async ({ page }) => {
  207 |     // Navigate to data sources page
  208 |     await page.goto('http://localhost:5173/data-sources');
  209 |     await page.waitForLoadState('networkidle');
  210 |     await page.waitForTimeout(2000);
  211 | 
  212 |     // Get all source cards
  213 |     const sourceCards = page.locator('.bg-white.rounded-xl.border');
  214 |     const count = await sourceCards.count();
  215 | 
  216 |     console.log(`\n=== Data Source Status ===`);
  217 |     console.log(`Total sources: ${count}`);
  218 | 
  219 |     // Check each source
  220 |     for (let i = 0; i < count; i++) {
  221 |       const card = sourceCards.nth(i);
```