# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: jira-confluence-full-flow.integration.spec.ts >> Jira/Confluence Full Integration Flow >> Step 1: Navigate to Data Sources page and verify UI
- Location: e2e\jira-confluence-full-flow.integration.spec.ts:54:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('h1:has-text("数据源管理")')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('h1:has-text("数据源管理")')

```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | /**
  4   |  * E2E Test: Complete Jira/Confluence Integration Flow
  5   |  *
  6   |  * This test simulates the complete workflow from scratch:
  7   |  * 1. Setup mock Jira/Confluence servers (using fixtures or real mock servers)
  8   |  * 2. Navigate to Data Sources page
  9   |  * 3. Add Jira source with URL and credentials
  10  |  * 4. Add Confluence source with URL and credentials
  11  |  * 5. Trigger sync/parsing
  12  |  * 6. Verify documents are parsed and indexed
  13  |  * 7. Test search functionality with parsed documents
  14  |  */
  15  | 
  16  | test.describe('Jira/Confluence Full Integration Flow', () => {
  17  |   // Mock server configuration
  18  |   const mockJiraUrl = 'http://localhost:8797';
  19  |   const mockConfluenceUrl = 'http://localhost:8798';
  20  |   const testEmail = 'test@example.com';
  21  |   const testToken = 'mock-api-token-12345';
  22  |   const runnerToken = 'test-token-123';
  23  | 
  24  |   test.beforeEach(async ({ page }) => {
  25  |     console.log('\n=== Test Setup ===');
  26  | 
  27  |     // Navigate to home page
  28  |     await page.goto('http://localhost:5173');
  29  |     await page.waitForLoadState('networkidle');
  30  | 
  31  |     // Setup runner connection
  32  |     const tokenInput = page.locator('input[placeholder="change-me"]');
  33  |     if (await tokenInput.isVisible()) {
  34  |       console.log('Setting up runner connection...');
  35  |       await tokenInput.fill(runnerToken);
  36  |       await tokenInput.blur();
  37  |       await page.waitForTimeout(1500);
  38  |     }
  39  | 
  40  |     // Select workspace
  41  |     const workspaceSelect = page.locator('select[data-testid="workspace-selector"]').first();
  42  |     if (await workspaceSelect.isVisible()) {
  43  |       const options = await workspaceSelect.locator('option').allTextContents();
  44  |       console.log('Available workspaces:', options);
  45  | 
  46  |       // Select first workspace or create new one
  47  |       await workspaceSelect.selectOption({ index: 0 });
  48  |       await page.waitForTimeout(1000);
  49  |     }
  50  | 
  51  |     console.log('✓ Setup complete\n');
  52  |   });
  53  | 
  54  |   test('Step 1: Navigate to Data Sources page and verify UI', async ({ page }) => {
  55  |     console.log('\n=== Step 1: Navigate to Data Sources ===');
  56  | 
  57  |     await page.goto('http://localhost:5173/data-sources');
  58  |     await page.waitForLoadState('networkidle');
  59  | 
  60  |     // Verify page elements
  61  |     const heading = page.locator('h1:has-text("数据源管理")');
> 62  |     await expect(heading).toBeVisible({ timeout: 5000 });
      |                           ^ Error: expect(locator).toBeVisible() failed
  63  | 
  64  |     const description = page.locator('p:has-text("统一管理")');
  65  |     await expect(description).toBeVisible();
  66  | 
  67  |     // Verify tabs
  68  |     const tabs = ['全部', '文件', 'Jira', 'Confluence'];
  69  |     for (const tabName of tabs) {
  70  |       const tab = page.locator(`button:has-text("${tabName}")`).first();
  71  |       await expect(tab).toBeVisible();
  72  |       console.log(`✓ Tab "${tabName}" found`);
  73  |     }
  74  | 
  75  |     // Verify "Add Source" button
  76  |     const addButton = page.locator('button:has-text("添加数据源")');
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
```