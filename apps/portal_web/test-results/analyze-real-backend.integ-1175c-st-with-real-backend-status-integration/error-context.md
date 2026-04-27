# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: analyze-real-backend.integration.spec.ts >> Analyze Page - Real Backend Integration >> should display setup checklist with real backend status
- Location: e2e\analyze-real-backend.integration.spec.ts:32:3

# Error details

```
TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator('.setup-checklist') to be visible

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
  3   | test.describe('Analyze Page - Real Backend Integration', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     // Set up token
  6   |     await page.goto('http://localhost:5173');
  7   |     await page.evaluate(() => {
  8   |       localStorage.setItem('ssdPortalToken', 'change-me');
  9   |     });
  10  |     await page.reload();
  11  |   });
  12  | 
  13  |   test('should load workspace and profiles from backend', async ({ page }) => {
  14  |     await page.goto('http://localhost:5173/');
  15  | 
  16  |     // Wait for API calls to complete
  17  |     await page.waitForTimeout(2000);
  18  | 
  19  |     // Check if workspace selector has loaded
  20  |     const workspaceSelect = page.locator('label:has-text("Workspace") select');
  21  |     await expect(workspaceSelect).toBeVisible({ timeout: 10000 });
  22  | 
  23  |     // Check if it has options (should have at least one workspace)
  24  |     const options = await workspaceSelect.locator('option').count();
  25  |     console.log(`Found ${options} workspace(s)`);
  26  | 
  27  |     if (options === 0) {
  28  |       console.log('WARNING: No workspaces found. Backend may not be running or configured.');
  29  |     }
  30  |   });
  31  | 
  32  |   test('should display setup checklist with real backend status', async ({ page }) => {
  33  |     await page.goto('http://localhost:5173/');
  34  | 
> 35  |     await page.waitForSelector('.setup-checklist', { timeout: 10000 });
      |                ^ TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
  36  | 
  37  |     // Get setup status
  38  |     const setupHeader = page.locator('.setup-header strong');
  39  |     const statusText = await setupHeader.textContent();
  40  |     console.log('Setup status:', statusText);
  41  | 
  42  |     // Check each setup item
  43  |     const setupItems = page.locator('.setup-item');
  44  |     const count = await setupItems.count();
  45  | 
  46  |     for (let i = 0; i < count; i++) {
  47  |       const item = setupItems.nth(i);
  48  |       const label = await item.locator('strong').textContent();
  49  |       const detail = await item.locator('small').textContent();
  50  |       const isReady = await item.evaluate(el => el.classList.contains('ready'));
  51  | 
  52  |       console.log(`- ${label}: ${isReady ? '✓' : '✗'} (${detail})`);
  53  |     }
  54  |   });
  55  | 
  56  |   test('should attempt real analysis and capture response', async ({ page }) => {
  57  |     await page.goto('http://localhost:5173/');
  58  | 
  59  |     // Wait for page to load
  60  |     await page.waitForSelector('input[placeholder*="SSD-DEMO-A"]', { timeout: 10000 });
  61  | 
  62  |     // Check if profiles are available
  63  |     const profileSelect = page.locator('label:has-text("Profile") select');
  64  |     const profileCount = await profileSelect.locator('option').count();
  65  | 
  66  |     console.log(`Found ${profileCount} profile(s)`);
  67  | 
  68  |     if (profileCount === 0) {
  69  |       console.log('SKIP: No profiles configured. Cannot run analysis.');
  70  |       return;
  71  |     }
  72  | 
  73  |     // Fill in issue key
  74  |     const issueInput = page.locator('input[placeholder*="SSD-DEMO-A"]');
  75  |     await issueInput.fill('SSD-SAMPLE-1');
  76  | 
  77  |     // Check button state
  78  |     const runButton = page.locator('button:has-text("Run Analysis")');
  79  |     const isDisabled = await runButton.isDisabled();
  80  | 
  81  |     console.log(`Run Analysis button disabled: ${isDisabled}`);
  82  | 
  83  |     if (isDisabled) {
  84  |       console.log('SKIP: Setup not complete. Button is disabled.');
  85  | 
  86  |       // Capture why it's disabled
  87  |       const setupBadge = page.locator('.setup-badge');
  88  |       const badgeText = await setupBadge.textContent();
  89  |       console.log('Setup badge:', badgeText);
  90  | 
  91  |       return;
  92  |     }
  93  | 
  94  |     // Set up response listener
  95  |     let apiResponse: any = null;
  96  |     let apiError: any = null;
  97  | 
  98  |     page.on('response', async response => {
  99  |       if (response.url().includes('/api/workspace/analyze-jira')) {
  100 |         console.log(`API Response: ${response.status()} ${response.statusText()}`);
  101 | 
  102 |         try {
  103 |           const body = await response.json();
  104 |           apiResponse = body;
  105 |           console.log('Response body:', JSON.stringify(body, null, 2).substring(0, 500));
  106 |         } catch (e) {
  107 |           const text = await response.text();
  108 |           apiError = text;
  109 |           console.log('Response text:', text.substring(0, 500));
  110 |         }
  111 |       }
  112 |     });
  113 | 
  114 |     // Click Run Analysis
  115 |     await runButton.click();
  116 | 
  117 |     // Wait for loading state
  118 |     await expect(page.locator('button:has-text("Running...")')).toBeVisible({ timeout: 5000 });
  119 |     console.log('Analysis started...');
  120 | 
  121 |     // Wait for completion (up to 60 seconds)
  122 |     await page.waitForTimeout(60000);
  123 | 
  124 |     // Check for results or errors
  125 |     const errorDiv = page.locator('.error');
  126 |     const errorCount = await errorDiv.count();
  127 | 
  128 |     if (errorCount > 0) {
  129 |       const errorText = await errorDiv.textContent();
  130 |       console.log('ERROR displayed:', errorText);
  131 |     }
  132 | 
  133 |     // Check for result view
  134 |     const resultSurface = page.locator('.result-surface');
  135 |     const resultCount = await resultSurface.count();
```