import { test, expect } from '@playwright/test';

/**
 * E2E Test: Sidebar Navigation
 *
 * 测试所有侧边栏入口的导航功能
 * 验证每个页面是否正确加载
 */

test.describe('Sidebar Navigation Tests', () => {
  const runnerToken = 'test-token-123';

  test.beforeEach(async ({ page }) => {
    console.log('\n=== Setup ===');

    // Navigate to home page
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    // Setup runner connection if needed
    const tokenInput = page.locator('input[placeholder="change-me"]');
    if (await tokenInput.isVisible()) {
      console.log('Setting up runner connection...');
      await tokenInput.fill(runnerToken);
      await tokenInput.blur();
      await page.waitForTimeout(1000);
    }

    // Select workspace
    const workspaceSelect = page.locator('select[data-testid="workspace-selector"]').first();
    if (await workspaceSelect.isVisible()) {
      await workspaceSelect.selectOption({ index: 0 });
      await page.waitForTimeout(500);
    }

    console.log('✓ Setup complete\n');
  });

  // 定义所有侧边栏路由
  const routes = [
    { path: '/', label: 'Analyze', icon: 'Search', expectedHeading: 'Deep Jira Analysis' },
    { path: '/search', label: 'Search', icon: 'FileText', expectedHeading: 'Knowledge Retrieval' },
    { path: '/chat', label: 'Chat', icon: 'MessageSquare', expectedHeading: 'Chat' },
    { path: '/runs', label: 'Runs', icon: 'Clock', expectedHeading: 'Run History' },
    { path: '/analysis', label: 'Analysis', icon: 'BarChart3', expectedHeading: 'Analysis Results' },
    { path: '/daily-report', label: 'Daily Report', icon: 'Calendar', expectedHeading: 'Daily Report' },
    { path: '/batch-analysis', label: 'Batch Analysis', icon: 'Layers', expectedHeading: 'Batch Analysis' },
    { path: '/data-sources', label: 'Data Sources', icon: 'Database', expectedHeading: '数据源管理' },
    { path: '/retrieval-eval', label: 'Retrieval Eval', icon: 'BarChart3', expectedHeading: 'Retrieval Evaluation' },
    { path: '/retrieval-debug', label: 'Retrieval Debug', icon: 'Settings', expectedHeading: '检索调试工具' },
    { path: '/strategy-comparison', label: 'Strategy Compare', icon: 'BarChart3', expectedHeading: '检索策略对比' },
    { path: '/profiles', label: 'Profiles', icon: 'Settings', expectedHeading: 'Analysis Settings' },
    { path: '/model-config', label: 'Model Config', icon: 'Sliders', expectedHeading: 'Model Configuration' },
    { path: '/wiki', label: 'Wiki', icon: 'FileText', expectedHeading: 'Wiki' },
    { path: '/reports', label: 'Reports', icon: 'BarChart3', expectedHeading: 'Reports' },
  ];

  test('should display all sidebar navigation links', async ({ page }) => {
    console.log('\n=== Testing Sidebar Links ===');

    for (const route of routes) {
      const link = page.locator(`aside.nav a[href="${route.path}"]`);
      await expect(link).toBeVisible({ timeout: 5000 });
      console.log(`✓ Link found: ${route.label}`);
    }

    console.log('\n✓ All sidebar links are visible');
  });

  test('should navigate to Analyze page', async ({ page }) => {
    console.log('\n=== Testing Analyze Page ===');

    await page.click('aside.nav a[href="/"]');
    await page.waitForLoadState('networkidle');

    const heading = page.locator('h2:has-text("Deep Jira Analysis")');
    await expect(heading).toBeVisible({ timeout: 5000 });

    // Verify setup checklist
    const setupChecklist = page.locator('.setup-checklist');
    await expect(setupChecklist).toBeVisible();

    console.log('✓ Analyze page loaded successfully');
  });

  test('should navigate to Search page', async ({ page }) => {
    console.log('\n=== Testing Search Page ===');

    await page.click('aside.nav a[href="/search"]');
    await page.waitForLoadState('networkidle');

    const heading = page.locator('h2:has-text("Knowledge Retrieval")');
    await expect(heading).toBeVisible({ timeout: 5000 });

    // Verify search input exists
    const searchInput = page.locator('input[data-testid="search-input"]');
    await expect(searchInput).toBeVisible();

    // Verify index status card
    const indexStatus = page.locator('[data-testid="index-status-card"]');
    await expect(indexStatus).toBeVisible();

    console.log('✓ Search page loaded successfully');
  });

  test('should navigate to Chat page', async ({ page }) => {
    console.log('\n=== Testing Chat Page ===');

    await page.click('aside.nav a[href="/chat"]');
    await page.waitForLoadState('networkidle');

    // Chat page should load (check for any content)
    const content = page.locator('main.workspace');
    await expect(content).toBeVisible({ timeout: 5000 });

    console.log('✓ Chat page loaded successfully');
  });

  test('should navigate to Data Sources page', async ({ page }) => {
    console.log('\n=== Testing Data Sources Page ===');

    await page.click('aside.nav a[href="/data-sources"]');
    await page.waitForLoadState('networkidle');

    const heading = page.locator('h1:has-text("数据源管理")');
    await expect(heading).toBeVisible({ timeout: 5000 });

    // Verify add button (use .first() to handle multiple buttons)
    const addButton = page.locator('button:has-text("添加数据源")').first();
    await expect(addButton).toBeVisible();

    // Verify tabs
    const tabs = ['全部', '文件', 'Jira', 'Confluence'];
    for (const tab of tabs) {
      const tabButton = page.locator(`button:has-text("${tab}")`).first();
      await expect(tabButton).toBeVisible();
    }

    console.log('✓ Data Sources page loaded successfully');
  });

  test('should navigate to Retrieval Debug page', async ({ page }) => {
    console.log('\n=== Testing Retrieval Debug Page ===');

    await page.click('aside.nav a[href="/retrieval-debug"]');
    await page.waitForLoadState('networkidle');

    const heading = page.locator('h1:has-text("检索调试工具")');
    await expect(heading).toBeVisible({ timeout: 5000 });

    console.log('✓ Retrieval Debug page loaded successfully');
  });

  test('should navigate to Strategy Comparison page', async ({ page }) => {
    console.log('\n=== Testing Strategy Comparison Page ===');

    await page.click('aside.nav a[href="/strategy-comparison"]');
    await page.waitForLoadState('networkidle');

    // Check for the actual heading text
    const heading = page.locator('h1:has-text("多策略检索对比")');
    await expect(heading).toBeVisible({ timeout: 5000 });

    console.log('✓ Strategy Comparison page loaded successfully');
  });

  test('should navigate to Profiles page', async ({ page }) => {
    console.log('\n=== Testing Profiles Page ===');

    await page.click('aside.nav a[href="/profiles"]');
    await page.waitForLoadState('networkidle');

    const heading = page.locator('h2:has-text("Analysis Settings")');
    await expect(heading).toBeVisible({ timeout: 5000 });

    console.log('✓ Profiles page loaded successfully');
  });

  test('should navigate to Runs page', async ({ page }) => {
    console.log('\n=== Testing Runs Page ===');

    await page.click('aside.nav a[href="/runs"]');
    await page.waitForLoadState('networkidle');

    // Runs page should show run history panel
    const runHistory = page.locator('h3:has-text("Run History")');
    await expect(runHistory).toBeVisible({ timeout: 5000 });

    console.log('✓ Runs page loaded successfully');
  });

  test('should highlight active navigation link', async ({ page }) => {
    console.log('\n=== Testing Active Link Highlighting ===');

    // Navigate to Data Sources
    await page.click('aside.nav a[href="/data-sources"]');
    await page.waitForLoadState('networkidle');

    // Check if the link has active class
    const activeLink = page.locator('aside.nav a[href="/data-sources"].active');
    await expect(activeLink).toBeVisible();

    console.log('✓ Active link is highlighted');

    // Navigate to Search
    await page.click('aside.nav a[href="/search"]');
    await page.waitForLoadState('networkidle');

    // Data Sources should no longer be active
    const inactiveLink = page.locator('aside.nav a[href="/data-sources"]:not(.active)');
    await expect(inactiveLink).toBeVisible();

    // Search should be active
    const searchActive = page.locator('aside.nav a[href="/search"].active');
    await expect(searchActive).toBeVisible();

    console.log('✓ Active link updates correctly');
  });

  test('should navigate through multiple pages sequentially', async ({ page }) => {
    console.log('\n=== Testing Sequential Navigation ===');

    const testRoutes = [
      { path: '/data-sources', heading: '数据源管理' },
      { path: '/search', heading: 'Knowledge Retrieval' },
      { path: '/retrieval-debug', heading: '检索调试工具' },
      { path: '/', heading: 'Deep Jira Analysis' },
    ];

    for (const route of testRoutes) {
      console.log(`Navigating to ${route.path}...`);

      await page.click(`aside.nav a[href="${route.path}"]`);
      await page.waitForLoadState('networkidle');

      const heading = page.locator(`h1:has-text("${route.heading}"), h2:has-text("${route.heading}")`);
      await expect(heading).toBeVisible({ timeout: 5000 });

      console.log(`✓ ${route.path} loaded`);
    }

    console.log('\n✓ Sequential navigation completed');
  });

  test('should maintain workspace selection across navigation', async ({ page }) => {
    console.log('\n=== Testing Workspace Persistence ===');

    // Get initial workspace
    const workspaceSelect = page.locator('select[data-testid="workspace-selector"]');
    const initialWorkspace = await workspaceSelect.inputValue();

    console.log(`Initial workspace: ${initialWorkspace}`);

    // Navigate to different pages
    await page.click('aside.nav a[href="/data-sources"]');
    await page.waitForLoadState('networkidle');

    let currentWorkspace = await workspaceSelect.inputValue();
    expect(currentWorkspace).toBe(initialWorkspace);
    console.log('✓ Workspace maintained on Data Sources page');

    await page.click('aside.nav a[href="/search"]');
    await page.waitForLoadState('networkidle');

    currentWorkspace = await workspaceSelect.inputValue();
    expect(currentWorkspace).toBe(initialWorkspace);
    console.log('✓ Workspace maintained on Search page');

    console.log('\n✓ Workspace selection persists across navigation');
  });
});
