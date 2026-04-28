# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: data-source-setup.integration.spec.ts >> Data Source Setup - From Scratch >> should add Jira source with mock server
- Location: e2e\data-source-setup.integration.spec.ts:61:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('button:has-text("添加数据源")')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('button:has-text("添加数据源")')

```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | /**
  4   |  * E2E Test: Data Source Setup from Scratch
  5   |  *
  6   |  * This test simulates a complete workflow:
  7   |  * 1. Navigate to Data Sources page
  8   |  * 2. Add Jira source with mock server URL and token
  9   |  * 3. Add Confluence source with mock server URL and token
  10  |  * 4. Verify sources are created and synced
  11  |  * 5. Check document counts
  12  |  */
  13  | 
  14  | test.describe('Data Source Setup - From Scratch', () => {
  15  |   const mockJiraUrl = 'http://localhost:8797'; // Mock Jira server
  16  |   const mockConfluenceUrl = 'http://localhost:8798'; // Mock Confluence server
  17  |   const mockToken = 'test-token-123';
  18  |   const mockEmail = 'test@example.com';
  19  |   const workspaceName = 'test-workspace';
  20  | 
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
> 68  |     await expect(addButton).toBeVisible({ timeout: 5000 });
      |                             ^ Error: expect(locator).toBeVisible() failed
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
  121 |     await addButton.click();
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
```