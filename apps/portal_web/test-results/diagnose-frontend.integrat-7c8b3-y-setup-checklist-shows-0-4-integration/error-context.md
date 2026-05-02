# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: diagnose-frontend.integration.spec.ts >> Frontend Diagnosis >> diagnose why setup checklist shows 0/4
- Location: e2e\diagnose-frontend.integration.spec.ts:4:3

# Error details

```
Test timeout of 1860000ms exceeded.
```

```
Error: locator.inputValue: Test timeout of 1860000ms exceeded.
Call log:
  - waiting for locator('label:has-text("Workspace") select')

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
  3   | test.describe('Frontend Diagnosis', () => {
  4   |   test('diagnose why setup checklist shows 0/4', async ({ page }) => {
  5   |     // Set up token
  6   |     await page.goto('http://localhost:5173');
  7   |     await page.evaluate(() => {
  8   |       localStorage.setItem('ssdPortalToken', 'change-me');
  9   |     });
  10  |     await page.reload();
  11  | 
  12  |     // Wait for page to load
  13  |     await page.waitForTimeout(3000);
  14  | 
  15  |     // Check which workspace is selected
  16  |     const workspaceSelect = page.locator('label:has-text("Workspace") select');
> 17  |     const selectedWorkspace = await workspaceSelect.inputValue();
      |                                                     ^ Error: locator.inputValue: Test timeout of 1860000ms exceeded.
  18  |     console.log('Selected workspace:', selectedWorkspace);
  19  | 
  20  |     // Get all workspace options
  21  |     const options = await workspaceSelect.locator('option').allTextContents();
  22  |     console.log('Available workspaces:', options);
  23  | 
  24  |     // Check if demo workspace is available
  25  |     const hasDemoWorkspace = options.some(opt => opt.includes('demo'));
  26  |     console.log('Has demo workspace:', hasDemoWorkspace);
  27  | 
  28  |     // If demo is not selected, select it
  29  |     if (!selectedWorkspace.includes('demo') && hasDemoWorkspace) {
  30  |       console.log('Selecting demo workspace...');
  31  |       await workspaceSelect.selectOption({ label: 'demo' });
  32  |       await page.waitForTimeout(2000);
  33  |     }
  34  | 
  35  |     // Check setup checklist after workspace selection
  36  |     const setupHeader = page.locator('.setup-header strong');
  37  |     const statusText = await setupHeader.textContent();
  38  |     console.log('Setup status after selection:', statusText);
  39  | 
  40  |     // Check each setup item
  41  |     const setupItems = page.locator('.setup-item');
  42  |     const count = await setupItems.count();
  43  | 
  44  |     for (let i = 0; i < count; i++) {
  45  |       const item = setupItems.nth(i);
  46  |       const label = await item.locator('strong').textContent();
  47  |       const detail = await item.locator('small').textContent();
  48  |       const isReady = await item.evaluate(el => el.classList.contains('ready'));
  49  | 
  50  |       console.log(`- ${label}: ${isReady ? '✓' : '✗'} (${detail})`);
  51  |     }
  52  | 
  53  |     // Check if profiles are loaded
  54  |     const profileSelect = page.locator('label:has-text("Profile") select');
  55  |     const profileOptions = await profileSelect.locator('option').allTextContents();
  56  |     console.log('Available profiles:', profileOptions);
  57  | 
  58  |     // Intercept API calls to see what's being requested
  59  |     const apiCalls: string[] = [];
  60  |     page.on('response', response => {
  61  |       if (response.url().includes('/api/')) {
  62  |         apiCalls.push(`${response.request().method()} ${response.url()} -> ${response.status()}`);
  63  |       }
  64  |     });
  65  | 
  66  |     // Reload to capture API calls
  67  |     await page.reload();
  68  |     await page.waitForTimeout(3000);
  69  | 
  70  |     console.log('\nAPI calls made:');
  71  |     apiCalls.forEach(call => console.log('  ' + call));
  72  | 
  73  |     // Check React Query state
  74  |     const reactQueryState = await page.evaluate(() => {
  75  |       // @ts-ignore
  76  |       const queryClient = window.__REACT_QUERY_DEVTOOLS_GLOBAL_HOOK__?.queryClient;
  77  |       if (!queryClient) return 'React Query not found';
  78  | 
  79  |       const cache = queryClient.getQueryCache();
  80  |       const queries = cache.getAll();
  81  | 
  82  |       return queries.map(q => ({
  83  |         queryKey: q.queryKey,
  84  |         state: q.state.status,
  85  |         dataAvailable: !!q.state.data,
  86  |         error: q.state.error?.message
  87  |       }));
  88  |     });
  89  | 
  90  |     console.log('\nReact Query state:', JSON.stringify(reactQueryState, null, 2));
  91  |   });
  92  | 
  93  |   test('manually check API responses', async ({ page, request }) => {
  94  |     // Get workspaces
  95  |     const workspacesResp = await request.get('http://localhost:8000/api/workspaces', {
  96  |       headers: { 'Authorization': 'Bearer change-me' }
  97  |     });
  98  |     const workspaces = await workspacesResp.json();
  99  |     console.log('Workspaces:', JSON.stringify(workspaces, null, 2));
  100 | 
  101 |     const demoWorkspace = workspaces.workspaces.find((w: any) => w.name === 'demo');
  102 |     if (!demoWorkspace) {
  103 |       console.log('ERROR: Demo workspace not found!');
  104 |       return;
  105 |     }
  106 | 
  107 |     const workspaceDir = demoWorkspace.workspace_dir;
  108 |     console.log('\nUsing workspace:', workspaceDir);
  109 | 
  110 |     // Get profiles
  111 |     const profilesResp = await request.get(
  112 |       `http://localhost:8000/api/workspace/profiles?workspace_dir=${encodeURIComponent(workspaceDir)}`,
  113 |       { headers: { 'Authorization': 'Bearer change-me' } }
  114 |     );
  115 |     const profiles = await profilesResp.json();
  116 |     console.log('\nProfiles:', JSON.stringify(profiles, null, 2));
  117 | 
```