# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test-markdown-rendering.spec.ts >> Markdown Rendering Test >> should render markdown in Runs page
- Location: e2e\test-markdown-rendering.spec.ts:9:3

# Error details

```
TimeoutError: locator.waitFor: Timeout 10000ms exceeded.
Call log:
  - waiting for locator('[data-testid="workspace-selector"]') to be visible

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
  1  | import { Page } from '@playwright/test';
  2  | 
  3  | /**
  4  |  * Set up authentication token and wait for page to reload
  5  |  */
  6  | export async function setupAuth(page: Page, token: string = 'change-me') {
  7  |   await page.goto('http://localhost:5173');
  8  |   await page.evaluate((t) => {
  9  |     localStorage.setItem('ssdPortalToken', t);
  10 |   }, token);
  11 |   await page.reload();
  12 | }
  13 | 
  14 | /**
  15 |  * Wait for workspace selector to be ready and select a workspace
  16 |  * @param page - Playwright page object
  17 |  * @param preferredWorkspace - Preferred workspace name (e.g., 'demo')
  18 |  * @returns The selected workspace name
  19 |  */
  20 | export async function selectWorkspace(
  21 |   page: Page,
  22 |   preferredWorkspace: string = 'demo'
  23 | ): Promise<string | null> {
  24 |   // Wait for workspace selector to be visible
  25 |   const workspaceSelect = page.locator('[data-testid="workspace-selector"]');
> 26 |   await workspaceSelect.waitFor({ state: 'visible', timeout: 10000 });
     |                         ^ TimeoutError: locator.waitFor: Timeout 10000ms exceeded.
  27 | 
  28 |   // Wait for options to load
  29 |   await page.waitForFunction(
  30 |     () => {
  31 |       const select = document.querySelector('[data-testid="workspace-selector"]') as HTMLSelectElement;
  32 |       return select && select.options.length > 0;
  33 |     },
  34 |     { timeout: 10000 }
  35 |   );
  36 | 
  37 |   // Get available workspace options
  38 |   const options = await workspaceSelect.locator('option').allTextContents();
  39 |   console.log('Available workspaces:', options);
  40 | 
  41 |   // Try to select preferred workspace if it exists
  42 |   const hasPreferredWorkspace = options.some(opt =>
  43 |     opt.toLowerCase().includes(preferredWorkspace.toLowerCase())
  44 |   );
  45 | 
  46 |   if (hasPreferredWorkspace) {
  47 |     console.log(`Selecting ${preferredWorkspace} workspace...`);
  48 |     await workspaceSelect.selectOption({ label: preferredWorkspace });
  49 |     await page.waitForTimeout(1000);
  50 |     return preferredWorkspace;
  51 |   }
  52 | 
  53 |   // Select first available workspace if any
  54 |   if (options.length > 0 && !options[0].includes('No workspace')) {
  55 |     console.log(`${preferredWorkspace} workspace not found. Selecting first available:`, options[0]);
  56 |     await workspaceSelect.selectOption({ index: 0 });
  57 |     await page.waitForTimeout(1000);
  58 |     return options[0];
  59 |   }
  60 | 
  61 |   console.log('WARNING: No workspaces available');
  62 |   return null;
  63 | }
  64 | 
  65 | /**
  66 |  * Setup auth and select workspace in one call
  67 |  */
  68 | export async function setupAuthAndWorkspace(
  69 |   page: Page,
  70 |   token: string = 'change-me',
  71 |   preferredWorkspace: string = 'demo'
  72 | ): Promise<string | null> {
  73 |   await setupAuth(page, token);
  74 |   return await selectWorkspace(page, preferredWorkspace);
  75 | }
  76 | 
  77 | /**
  78 |  * Wait for API response and return status
  79 |  */
  80 | export async function waitForApiResponse(
  81 |   page: Page,
  82 |   urlPattern: string,
  83 |   timeout: number = 30000
  84 | ): Promise<number | null> {
  85 |   return new Promise((resolve) => {
  86 |     const timer = setTimeout(() => resolve(null), timeout);
  87 | 
  88 |     page.on('response', (response) => {
  89 |       if (response.url().includes(urlPattern)) {
  90 |         clearTimeout(timer);
  91 |         resolve(response.status());
  92 |       }
  93 |     });
  94 |   });
  95 | }
  96 | 
```