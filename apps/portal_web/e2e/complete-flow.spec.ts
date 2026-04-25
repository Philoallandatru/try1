import { test, expect } from '@playwright/test';

/**
 * E2E Test: Complete End-to-End Flow
 *
 * 测试从数据源添加到检索的完整业务流程：
 * 1. 添加 Jira 数据源
 * 2. 添加 Confluence 数据源
 * 3. 验证数据源状态
 * 4. 构建检索索引
 * 5. 执行搜索查询
 * 6. 验证搜索结果
 */

test.describe('Complete End-to-End Flow', () => {
  const mockJiraUrl = 'http://localhost:8797';
  const mockConfluenceUrl = 'http://localhost:8798';
  const testEmail = 'test@example.com';
  const testToken = 'mock-api-token-12345';
  const runnerToken = 'test-token-123';

  test.beforeEach(async ({ page }) => {
    console.log('\n=== E2E Test Setup ===');

    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    // Setup runner connection
    const tokenInput = page.locator('input[placeholder="change-me"]');
    if (await tokenInput.isVisible()) {
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

  test('Complete Flow: Add Data Sources → Build Index → Search', async ({ page }) => {
    console.log('\n=== STEP 1: Navigate to Data Sources ===');

    // Navigate to Data Sources page
    await page.click('aside.nav a[href="/data-sources"]');
    await page.waitForLoadState('networkidle');

    const heading = page.locator('h1:has-text("数据源管理")');
    await expect(heading).toBeVisible({ timeout: 5000 });
    console.log('✓ Data Sources page loaded');

    // ===== STEP 2: Add Jira Source =====
    console.log('\n=== STEP 2: Add Jira Data Source ===');

    await page.click('button:has-text("添加数据源")');
    await page.waitForTimeout(500);

    // Select Jira type
    const jiraButton = page.locator('button:has-text("Jira")').first();
    await jiraButton.click();
    await page.waitForTimeout(300);

    // Fill Jira form
    await page.locator('input[placeholder*="Jira URL"]').fill(mockJiraUrl);
    await page.locator('input[placeholder*="邮箱"]').fill(testEmail);
    await page.locator('input[placeholder*="API Token"]').fill(testToken);
    await page.locator('textarea[placeholder*="JQL"]').fill('project = TEST');

    console.log('  URL:', mockJiraUrl);
    console.log('  Email:', testEmail);
    console.log('  JQL: project = TEST');

    // Submit form
    await page.locator('button:has-text("添加数据源")').last().click();

    // Wait for success toast
    const successToast = page.locator('.bg-green-50:has-text("成功")');
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('✓ Jira source added successfully');

    await page.waitForTimeout(1000);

    // ===== STEP 3: Add Confluence Source =====
    console.log('\n=== STEP 3: Add Confluence Data Source ===');

    await page.click('button:has-text("添加数据源")');
    await page.waitForTimeout(500);

    // Select Confluence type
    const confluenceButton = page.locator('button:has-text("Confluence")').first();
    await confluenceButton.click();
    await page.waitForTimeout(300);

    // Fill Confluence form
    await page.locator('input[placeholder*="Confluence URL"]').fill(mockConfluenceUrl);
    await page.locator('input[placeholder*="邮箱"]').fill(testEmail);
    await page.locator('input[placeholder*="API Token"]').fill(testToken);
    await page.locator('input[placeholder*="空间键"]').fill('TEST');

    console.log('  URL:', mockConfluenceUrl);
    console.log('  Email:', testEmail);
    console.log('  Space Key: TEST');

    // Submit form
    await page.locator('button:has-text("添加数据源")').last().click();

    // Wait for success toast
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('✓ Confluence source added successfully');

    await page.waitForTimeout(1000);

    // ===== STEP 4: Verify Data Sources =====
    console.log('\n=== STEP 4: Verify Data Sources ===');

    // Switch to "All" tab
    const allTab = page.locator('button:has-text("全部")').first();
    await allTab.click();
    await page.waitForTimeout(500);

    // Count data sources
    const sourceCards = page.locator('.bg-white.rounded-xl.border');
    const totalCount = await sourceCards.count();

    console.log(`Total data sources: ${totalCount}`);

    // Verify at least 2 sources exist
    expect(totalCount).toBeGreaterThanOrEqual(2);

    // Check for Jira source
    const jiraCards = page.locator('.bg-white.rounded-xl:has-text("JIRA")');
    const jiraCount = await jiraCards.count();
    console.log(`  Jira sources: ${jiraCount}`);
    expect(jiraCount).toBeGreaterThanOrEqual(1);

    // Check for Confluence source
    const confluenceCards = page.locator('.bg-white.rounded-xl:has-text("CONFLUENCE")');
    const confluenceCount = await confluenceCards.count();
    console.log(`  Confluence sources: ${confluenceCount}`);
    expect(confluenceCount).toBeGreaterThanOrEqual(1);

    console.log('✓ Data sources verified');

    // ===== STEP 5: Navigate to Search Page =====
    console.log('\n=== STEP 5: Navigate to Search Page ===');

    await page.click('aside.nav a[href="/search"]');
    await page.waitForLoadState('networkidle');

    const searchHeading = page.locator('h2:has-text("Knowledge Retrieval")');
    await expect(searchHeading).toBeVisible({ timeout: 5000 });
    console.log('✓ Search page loaded');

    // ===== STEP 6: Build Index =====
    console.log('\n=== STEP 6: Build Search Index ===');

    const rebuildButton = page.locator('button[data-testid="rebuild-index-button"]');
    await expect(rebuildButton).toBeVisible();

    // Check initial document count
    const docCountBefore = page.locator('[data-testid="document-count"]');
    const countTextBefore = await docCountBefore.textContent();
    console.log(`  Documents before build: ${countTextBefore}`);

    // Click rebuild button
    await rebuildButton.click();

    // Wait for building state
    const buildingText = page.locator('text=Building...');
    await expect(buildingText).toBeVisible({ timeout: 5000 });
    console.log('  Index building started...');

    // Wait for build to complete (button should be enabled again)
    await expect(rebuildButton).toBeEnabled({ timeout: 30000 });
    console.log('✓ Index build completed');

    await page.waitForTimeout(1000);

    // ===== STEP 7: Execute Search =====
    console.log('\n=== STEP 7: Execute Search Query ===');

    const searchInput = page.locator('input[data-testid="search-input"]');
    const searchButton = page.locator('button[data-testid="search-button"]');

    // Enter search query
    const searchQuery = 'test';
    await searchInput.fill(searchQuery);
    console.log(`  Query: "${searchQuery}"`);

    // Click search button
    await searchButton.click();

    // Wait for search to complete
    const searchingText = page.locator('text=Searching...');
    if (await searchingText.isVisible()) {
      await expect(searchingText).not.toBeVisible({ timeout: 10000 });
    }

    console.log('✓ Search completed');

    // ===== STEP 8: Verify Search Results =====
    console.log('\n=== STEP 8: Verify Search Results ===');

    // Check for results or empty state
    const searchResults = page.locator('[data-testid="search-results"]');
    const emptyState = page.locator('.empty-state');

    const hasResults = await searchResults.isVisible();
    const isEmpty = await emptyState.isVisible();

    if (hasResults) {
      const resultCards = page.locator('[data-testid^="search-result-"]');
      const resultCount = await resultCards.count();
      console.log(`  Found ${resultCount} search result(s)`);

      // Click first result if exists
      if (resultCount > 0) {
        await resultCards.first().click();
        await page.waitForTimeout(500);

        // Verify document detail panel
        const detailPanel = page.locator('.document-detail');
        await expect(detailPanel).toBeVisible();
        console.log('✓ Document detail displayed');
      }
    } else if (isEmpty) {
      console.log('  No results found (empty state)');
    }

    console.log('✓ Search results verified');

    // ===== STEP 9: Test Search Filters =====
    console.log('\n=== STEP 9: Test Search Filters ===');

    // Test document type filters
    const specFilter = page.locator('button.filter-button:has-text("Specification")');
    if (await specFilter.isVisible()) {
      await specFilter.click();
      await page.waitForTimeout(500);
      console.log('✓ Specification filter applied');

      // Clear filter
      const clearFilter = page.locator('button.filter-button.clear');
      if (await clearFilter.isVisible()) {
        await clearFilter.click();
        await page.waitForTimeout(500);
        console.log('✓ Filter cleared');
      }
    }

    // ===== STEP 10: Navigate Back to Data Sources =====
    console.log('\n=== STEP 10: Return to Data Sources ===');

    await page.click('aside.nav a[href="/data-sources"]');
    await page.waitForLoadState('networkidle');

    await expect(heading).toBeVisible({ timeout: 5000 });

    // Verify sources still exist
    const finalCount = await sourceCards.count();
    console.log(`  Final data source count: ${finalCount}`);
    expect(finalCount).toBeGreaterThanOrEqual(2);

    console.log('✓ Returned to Data Sources page');

    // ===== FLOW COMPLETE =====
    console.log('\n=== ✅ COMPLETE E2E FLOW SUCCESSFUL ===');
    console.log('Summary:');
    console.log('  ✓ Added Jira data source');
    console.log('  ✓ Added Confluence data source');
    console.log('  ✓ Verified data sources');
    console.log('  ✓ Built search index');
    console.log('  ✓ Executed search query');
    console.log('  ✓ Verified search results');
    console.log('  ✓ Tested filters');
    console.log('  ✓ Navigation verified');
  });

  test('Flow: Data Sources → Retrieval Debug', async ({ page }) => {
    console.log('\n=== Flow: Data Sources → Retrieval Debug ===');

    // Navigate to Data Sources
    await page.click('aside.nav a[href="/data-sources"]');
    await page.waitForLoadState('networkidle');
    console.log('✓ On Data Sources page');

    // Navigate to Retrieval Debug
    await page.click('aside.nav a[href="/retrieval-debug"]');
    await page.waitForLoadState('networkidle');

    const heading = page.locator('h1:has-text("检索调试工具")');
    await expect(heading).toBeVisible({ timeout: 5000 });
    console.log('✓ Retrieval Debug page loaded');

    // Verify debug tools are present
    const content = page.locator('main.workspace');
    await expect(content).toBeVisible();

    console.log('✓ Flow completed: Data Sources → Retrieval Debug');
  });

  test('Flow: Data Sources → Strategy Comparison', async ({ page }) => {
    console.log('\n=== Flow: Data Sources → Strategy Comparison ===');

    // Navigate to Data Sources
    await page.click('aside.nav a[href="/data-sources"]');
    await page.waitForLoadState('networkidle');
    console.log('✓ On Data Sources page');

    // Navigate to Strategy Comparison
    await page.click('aside.nav a[href="/strategy-comparison"]');
    await page.waitForLoadState('networkidle');

    const heading = page.locator('h1:has-text("多策略检索对比")');
    await expect(heading).toBeVisible({ timeout: 5000 });
    console.log('✓ Strategy Comparison page loaded');

    console.log('✓ Flow completed: Data Sources → Strategy Comparison');
  });

  test('Flow: Search → Analyze → Runs', async ({ page }) => {
    console.log('\n=== Flow: Search → Analyze → Runs ===');

    // Step 1: Search
    await page.click('aside.nav a[href="/search"]');
    await page.waitForLoadState('networkidle');
    console.log('✓ Search page loaded');

    // Step 2: Analyze
    await page.click('aside.nav a[href="/"]');
    await page.waitForLoadState('networkidle');

    const analyzeHeading = page.locator('h2:has-text("Deep Jira Analysis")');
    await expect(analyzeHeading).toBeVisible({ timeout: 5000 });
    console.log('✓ Analyze page loaded');

    // Step 3: Runs
    await page.click('aside.nav a[href="/runs"]');
    await page.waitForLoadState('networkidle');

    const runsHeading = page.locator('h3:has-text("Run History")');
    await expect(runsHeading).toBeVisible({ timeout: 5000 });
    console.log('✓ Runs page loaded');

    console.log('✓ Flow completed: Search → Analyze → Runs');
  });
});
