# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: sidebar-navigation.spec.ts >> Sidebar Navigation Tests >> should navigate to Data Sources page
- Location: e2e\sidebar-navigation.spec.ts:119:3

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
  22  |     if (await tokenInput.isVisible()) {
  23  |       console.log('Setting up runner connection...');
  24  |       await tokenInput.fill(runnerToken);
  25  |       await tokenInput.blur();
  26  |       await page.waitForTimeout(1000);
  27  |     }
  28  | 
  29  |     // Select workspace
  30  |     const workspaceSelect = page.locator('select[data-testid="workspace-selector"]').first();
  31  |     if (await workspaceSelect.isVisible()) {
  32  |       await workspaceSelect.selectOption({ index: 0 });
  33  |       await page.waitForTimeout(500);
  34  |     }
  35  | 
  36  |     console.log('✓ Setup complete\n');
  37  |   });
  38  | 
  39  |   // 定义所有侧边栏路由
  40  |   const routes = [
  41  |     { path: '/', label: 'Analyze', icon: 'Search', expectedHeading: 'Deep Jira Analysis' },
  42  |     { path: '/search', label: 'Search', icon: 'FileText', expectedHeading: 'Knowledge Retrieval' },
  43  |     { path: '/chat', label: 'Chat', icon: 'MessageSquare', expectedHeading: 'Chat' },
  44  |     { path: '/runs', label: 'Runs', icon: 'Clock', expectedHeading: 'Run History' },
  45  |     { path: '/analysis', label: 'Analysis', icon: 'BarChart3', expectedHeading: 'Analysis Results' },
  46  |     { path: '/daily-report', label: 'Daily Report', icon: 'Calendar', expectedHeading: 'Daily Report' },
  47  |     { path: '/batch-analysis', label: 'Batch Analysis', icon: 'Layers', expectedHeading: 'Batch Analysis' },
  48  |     { path: '/data-sources', label: 'Data Sources', icon: 'Database', expectedHeading: '数据源管理' },
  49  |     { path: '/retrieval-eval', label: 'Retrieval Eval', icon: 'BarChart3', expectedHeading: 'Retrieval Evaluation' },
  50  |     { path: '/retrieval-debug', label: 'Retrieval Debug', icon: 'Settings', expectedHeading: '检索调试工具' },
  51  |     { path: '/strategy-comparison', label: 'Strategy Compare', icon: 'BarChart3', expectedHeading: '检索策略对比' },
  52  |     { path: '/profiles', label: 'Profiles', icon: 'Settings', expectedHeading: 'Analysis Settings' },
  53  |     { path: '/model-config', label: 'Model Config', icon: 'Sliders', expectedHeading: 'Model Configuration' },
  54  |     { path: '/wiki', label: 'Wiki', icon: 'FileText', expectedHeading: 'Wiki' },
  55  |     { path: '/reports', label: 'Reports', icon: 'BarChart3', expectedHeading: 'Reports' },
  56  |   ];
  57  | 
  58  |   test('should display all sidebar navigation links', async ({ page }) => {
  59  |     console.log('\n=== Testing Sidebar Links ===');
  60  | 
  61  |     for (const route of routes) {
  62  |       const link = page.locator(`aside.nav a[href="${route.path}"]`);
  63  |       await expect(link).toBeVisible({ timeout: 5000 });
  64  |       console.log(`✓ Link found: ${route.label}`);
  65  |     }
  66  | 
  67  |     console.log('\n✓ All sidebar links are visible');
  68  |   });
  69  | 
  70  |   test('should navigate to Analyze page', async ({ page }) => {
  71  |     console.log('\n=== Testing Analyze Page ===');
  72  | 
  73  |     await page.click('aside.nav a[href="/"]');
  74  |     await page.waitForLoadState('networkidle');
  75  | 
  76  |     const heading = page.locator('h2:has-text("Deep Jira Analysis")');
  77  |     await expect(heading).toBeVisible({ timeout: 5000 });
  78  | 
  79  |     // Verify setup checklist
  80  |     const setupChecklist = page.locator('.setup-checklist');
  81  |     await expect(setupChecklist).toBeVisible();
  82  | 
  83  |     console.log('✓ Analyze page loaded successfully');
  84  |   });
  85  | 
  86  |   test('should navigate to Search page', async ({ page }) => {
  87  |     console.log('\n=== Testing Search Page ===');
  88  | 
  89  |     await page.click('aside.nav a[href="/search"]');
  90  |     await page.waitForLoadState('networkidle');
  91  | 
  92  |     const heading = page.locator('h2:has-text("Knowledge Retrieval")');
  93  |     await expect(heading).toBeVisible({ timeout: 5000 });
  94  | 
  95  |     // Verify search input exists
  96  |     const searchInput = page.locator('input[data-testid="search-input"]');
  97  |     await expect(searchInput).toBeVisible();
  98  | 
  99  |     // Verify index status card
  100 |     const indexStatus = page.locator('[data-testid="index-status-card"]');
  101 |     await expect(indexStatus).toBeVisible();
  102 | 
  103 |     console.log('✓ Search page loaded successfully');
  104 |   });
  105 | 
  106 |   test('should navigate to Chat page', async ({ page }) => {
  107 |     console.log('\n=== Testing Chat Page ===');
  108 | 
  109 |     await page.click('aside.nav a[href="/chat"]');
  110 |     await page.waitForLoadState('networkidle');
  111 | 
  112 |     // Chat page should load (check for any content)
  113 |     const content = page.locator('main.workspace');
  114 |     await expect(content).toBeVisible({ timeout: 5000 });
  115 | 
  116 |     console.log('✓ Chat page loaded successfully');
  117 |   });
  118 | 
  119 |   test('should navigate to Data Sources page', async ({ page }) => {
  120 |     console.log('\n=== Testing Data Sources Page ===');
  121 | 
> 122 |     await page.click('aside.nav a[href="/data-sources"]');
      |                ^ Error: page.click: Test timeout of 1860000ms exceeded.
  123 |     await page.waitForLoadState('networkidle');
  124 | 
  125 |     const heading = page.locator('h1:has-text("数据源管理")');
  126 |     await expect(heading).toBeVisible({ timeout: 5000 });
  127 | 
  128 |     // Verify add button (use .first() to handle multiple buttons)
  129 |     const addButton = page.locator('button:has-text("添加数据源")').first();
  130 |     await expect(addButton).toBeVisible();
  131 | 
  132 |     // Verify tabs
  133 |     const tabs = ['全部', '文件', 'Jira', 'Confluence'];
  134 |     for (const tab of tabs) {
  135 |       const tabButton = page.locator(`button:has-text("${tab}")`).first();
  136 |       await expect(tabButton).toBeVisible();
  137 |     }
  138 | 
  139 |     console.log('✓ Data Sources page loaded successfully');
  140 |   });
  141 | 
  142 |   test('should navigate to Retrieval Debug page', async ({ page }) => {
  143 |     console.log('\n=== Testing Retrieval Debug Page ===');
  144 | 
  145 |     await page.click('aside.nav a[href="/retrieval-debug"]');
  146 |     await page.waitForLoadState('networkidle');
  147 | 
  148 |     const heading = page.locator('h1:has-text("检索调试工具")');
  149 |     await expect(heading).toBeVisible({ timeout: 5000 });
  150 | 
  151 |     console.log('✓ Retrieval Debug page loaded successfully');
  152 |   });
  153 | 
  154 |   test('should navigate to Strategy Comparison page', async ({ page }) => {
  155 |     console.log('\n=== Testing Strategy Comparison Page ===');
  156 | 
  157 |     await page.click('aside.nav a[href="/strategy-comparison"]');
  158 |     await page.waitForLoadState('networkidle');
  159 | 
  160 |     // Check for the actual heading text
  161 |     const heading = page.locator('h1:has-text("多策略检索对比")');
  162 |     await expect(heading).toBeVisible({ timeout: 5000 });
  163 | 
  164 |     console.log('✓ Strategy Comparison page loaded successfully');
  165 |   });
  166 | 
  167 |   test('should navigate to Profiles page', async ({ page }) => {
  168 |     console.log('\n=== Testing Profiles Page ===');
  169 | 
  170 |     await page.click('aside.nav a[href="/profiles"]');
  171 |     await page.waitForLoadState('networkidle');
  172 | 
  173 |     const heading = page.locator('h2:has-text("Analysis Settings")');
  174 |     await expect(heading).toBeVisible({ timeout: 5000 });
  175 | 
  176 |     console.log('✓ Profiles page loaded successfully');
  177 |   });
  178 | 
  179 |   test('should navigate to Runs page', async ({ page }) => {
  180 |     console.log('\n=== Testing Runs Page ===');
  181 | 
  182 |     await page.click('aside.nav a[href="/runs"]');
  183 |     await page.waitForLoadState('networkidle');
  184 | 
  185 |     // Runs page should show run history panel
  186 |     const runHistory = page.locator('h3:has-text("Run History")');
  187 |     await expect(runHistory).toBeVisible({ timeout: 5000 });
  188 | 
  189 |     console.log('✓ Runs page loaded successfully');
  190 |   });
  191 | 
  192 |   test('should highlight active navigation link', async ({ page }) => {
  193 |     console.log('\n=== Testing Active Link Highlighting ===');
  194 | 
  195 |     // Navigate to Data Sources
  196 |     await page.click('aside.nav a[href="/data-sources"]');
  197 |     await page.waitForLoadState('networkidle');
  198 | 
  199 |     // Check if the link has active class
  200 |     const activeLink = page.locator('aside.nav a[href="/data-sources"].active');
  201 |     await expect(activeLink).toBeVisible();
  202 | 
  203 |     console.log('✓ Active link is highlighted');
  204 | 
  205 |     // Navigate to Search
  206 |     await page.click('aside.nav a[href="/search"]');
  207 |     await page.waitForLoadState('networkidle');
  208 | 
  209 |     // Data Sources should no longer be active
  210 |     const inactiveLink = page.locator('aside.nav a[href="/data-sources"]:not(.active)');
  211 |     await expect(inactiveLink).toBeVisible();
  212 | 
  213 |     // Search should be active
  214 |     const searchActive = page.locator('aside.nav a[href="/search"].active');
  215 |     await expect(searchActive).toBeVisible();
  216 | 
  217 |     console.log('✓ Active link updates correctly');
  218 |   });
  219 | 
  220 |   test('should navigate through multiple pages sequentially', async ({ page }) => {
  221 |     console.log('\n=== Testing Sequential Navigation ===');
  222 | 
```