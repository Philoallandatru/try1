# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: complete-flow.spec.ts >> Complete End-to-End Flow >> Complete Flow: Add Data Sources → Build Index → Search
- Location: e2e\complete-flow.spec.ts:46:3

# Error details

```
Test timeout of 1860000ms exceeded.
```

```
Error: page.click: Test timeout of 1860000ms exceeded.
Call log:
  - waiting for locator('aside.nav a[href="/data-sources"]')

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
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | /**
  4   |  * E2E Test: Complete End-to-End Flow
  5   |  *
  6   |  * 测试从数据源添加到检索的完整业务流程：
  7   |  * 1. 添加 Jira 数据源
  8   |  * 2. 添加 Confluence 数据源
  9   |  * 3. 验证数据源状态
  10  |  * 4. 构建检索索引
  11  |  * 5. 执行搜索查询
  12  |  * 6. 验证搜索结果
  13  |  */
  14  | 
  15  | test.describe('Complete End-to-End Flow', () => {
  16  |   const mockJiraUrl = 'http://localhost:8797';
  17  |   const mockConfluenceUrl = 'http://localhost:8798';
  18  |   const testEmail = 'test@example.com';
  19  |   const testToken = 'mock-api-token-12345';
  20  |   const runnerToken = 'test-token-123';
  21  | 
  22  |   test.beforeEach(async ({ page }) => {
  23  |     console.log('\n=== E2E Test Setup ===');
  24  | 
  25  |     await page.goto('http://localhost:5173');
  26  |     await page.waitForLoadState('networkidle');
  27  | 
  28  |     // Setup runner connection
  29  |     const tokenInput = page.locator('input[placeholder="change-me"]');
  30  |     if (await tokenInput.isVisible()) {
  31  |       await tokenInput.fill(runnerToken);
  32  |       await tokenInput.blur();
  33  |       await page.waitForTimeout(1000);
  34  |     }
  35  | 
  36  |     // Select workspace
  37  |     const workspaceSelect = page.locator('select[data-testid="workspace-selector"]').first();
  38  |     if (await workspaceSelect.isVisible()) {
  39  |       await workspaceSelect.selectOption({ index: 0 });
  40  |       await page.waitForTimeout(500);
  41  |     }
  42  | 
  43  |     console.log('✓ Setup complete\n');
  44  |   });
  45  | 
  46  |   test('Complete Flow: Add Data Sources → Build Index → Search', async ({ page }) => {
  47  |     console.log('\n=== STEP 1: Navigate to Data Sources ===');
  48  | 
  49  |     // Navigate to Data Sources page
> 50  |     await page.click('aside.nav a[href="/data-sources"]');
      |                ^ Error: page.click: Test timeout of 1860000ms exceeded.
  51  |     await page.waitForLoadState('networkidle');
  52  | 
  53  |     const heading = page.locator('h1:has-text("数据源管理")');
  54  |     await expect(heading).toBeVisible({ timeout: 5000 });
  55  |     console.log('✓ Data Sources page loaded');
  56  | 
  57  |     // ===== STEP 2: Add Jira Source =====
  58  |     console.log('\n=== STEP 2: Add Jira Data Source ===');
  59  | 
  60  |     await page.click('button:has-text("添加数据源")');
  61  |     await page.waitForTimeout(500);
  62  | 
  63  |     // Select Jira type
  64  |     const jiraButton = page.locator('button:has-text("Jira")').first();
  65  |     await jiraButton.click();
  66  |     await page.waitForTimeout(300);
  67  | 
  68  |     // Fill Jira form
  69  |     await page.locator('input[placeholder*="Jira URL"]').fill(mockJiraUrl);
  70  |     await page.locator('input[placeholder*="邮箱"]').fill(testEmail);
  71  |     await page.locator('input[placeholder*="API Token"]').fill(testToken);
  72  |     await page.locator('textarea[placeholder*="JQL"]').fill('project = TEST');
  73  | 
  74  |     console.log('  URL:', mockJiraUrl);
  75  |     console.log('  Email:', testEmail);
  76  |     console.log('  JQL: project = TEST');
  77  | 
  78  |     // Submit form
  79  |     await page.locator('button:has-text("添加数据源")').last().click();
  80  | 
  81  |     // Wait for success toast
  82  |     const successToast = page.locator('.bg-green-50:has-text("成功")');
  83  |     await expect(successToast).toBeVisible({ timeout: 10000 });
  84  |     console.log('✓ Jira source added successfully');
  85  | 
  86  |     await page.waitForTimeout(1000);
  87  | 
  88  |     // ===== STEP 3: Add Confluence Source =====
  89  |     console.log('\n=== STEP 3: Add Confluence Data Source ===');
  90  | 
  91  |     await page.click('button:has-text("添加数据源")');
  92  |     await page.waitForTimeout(500);
  93  | 
  94  |     // Select Confluence type
  95  |     const confluenceButton = page.locator('button:has-text("Confluence")').first();
  96  |     await confluenceButton.click();
  97  |     await page.waitForTimeout(300);
  98  | 
  99  |     // Fill Confluence form
  100 |     await page.locator('input[placeholder*="Confluence URL"]').fill(mockConfluenceUrl);
  101 |     await page.locator('input[placeholder*="邮箱"]').fill(testEmail);
  102 |     await page.locator('input[placeholder*="API Token"]').fill(testToken);
  103 |     await page.locator('input[placeholder*="空间键"]').fill('TEST');
  104 | 
  105 |     console.log('  URL:', mockConfluenceUrl);
  106 |     console.log('  Email:', testEmail);
  107 |     console.log('  Space Key: TEST');
  108 | 
  109 |     // Submit form
  110 |     await page.locator('button:has-text("添加数据源")').last().click();
  111 | 
  112 |     // Wait for success toast
  113 |     await expect(successToast).toBeVisible({ timeout: 10000 });
  114 |     console.log('✓ Confluence source added successfully');
  115 | 
  116 |     await page.waitForTimeout(1000);
  117 | 
  118 |     // ===== STEP 4: Verify Data Sources =====
  119 |     console.log('\n=== STEP 4: Verify Data Sources ===');
  120 | 
  121 |     // Switch to "All" tab
  122 |     const allTab = page.locator('button:has-text("全部")').first();
  123 |     await allTab.click();
  124 |     await page.waitForTimeout(500);
  125 | 
  126 |     // Count data sources
  127 |     const sourceCards = page.locator('.bg-white.rounded-xl.border');
  128 |     const totalCount = await sourceCards.count();
  129 | 
  130 |     console.log(`Total data sources: ${totalCount}`);
  131 | 
  132 |     // Verify at least 2 sources exist
  133 |     expect(totalCount).toBeGreaterThanOrEqual(2);
  134 | 
  135 |     // Check for Jira source
  136 |     const jiraCards = page.locator('.bg-white.rounded-xl:has-text("JIRA")');
  137 |     const jiraCount = await jiraCards.count();
  138 |     console.log(`  Jira sources: ${jiraCount}`);
  139 |     expect(jiraCount).toBeGreaterThanOrEqual(1);
  140 | 
  141 |     // Check for Confluence source
  142 |     const confluenceCards = page.locator('.bg-white.rounded-xl:has-text("CONFLUENCE")');
  143 |     const confluenceCount = await confluenceCards.count();
  144 |     console.log(`  Confluence sources: ${confluenceCount}`);
  145 |     expect(confluenceCount).toBeGreaterThanOrEqual(1);
  146 | 
  147 |     console.log('✓ Data sources verified');
  148 | 
  149 |     // ===== STEP 5: Navigate to Search Page =====
  150 |     console.log('\n=== STEP 5: Navigate to Search Page ===');
```