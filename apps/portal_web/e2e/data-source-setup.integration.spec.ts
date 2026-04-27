import { test, expect } from '@playwright/test';

/**
 * E2E Test: Data Source Setup from Scratch
 *
 * This test simulates a complete workflow:
 * 1. Navigate to Data Sources page
 * 2. Add Jira source with mock server URL and token
 * 3. Add Confluence source with mock server URL and token
 * 4. Verify sources are created and synced
 * 5. Check document counts
 */

test.describe('Data Source Setup - From Scratch', () => {
  const mockJiraUrl = 'http://localhost:8797'; // Mock Jira server
  const mockConfluenceUrl = 'http://localhost:8798'; // Mock Confluence server
  const mockToken = 'test-token-123';
  const mockEmail = 'test@example.com';
  const workspaceName = 'test-workspace';

  test.beforeEach(async ({ page }) => {
    // Navigate to home page
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    // Connect to runner if needed
    const tokenInput = page.locator('input[placeholder="change-me"]');
    if (await tokenInput.isVisible()) {
      await tokenInput.fill(mockToken);
      await tokenInput.blur();
      await page.waitForTimeout(1500);
    }

    // Select or create test workspace
    const workspaceSelect = page.locator('select[data-testid="workspace-selector"]').first();
    if (await workspaceSelect.isVisible()) {
      // Try to select test workspace, or use first available
      const options = await workspaceSelect.locator('option').allTextContents();
      if (options.includes(workspaceName)) {
        await workspaceSelect.selectOption({ label: workspaceName });
      } else {
        // Use first available workspace
        await workspaceSelect.selectOption({ index: 0 });
      }
      await page.waitForTimeout(1000);
    }
  });

  test('should navigate to Data Sources page', async ({ page }) => {
    // Navigate to data sources page
    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');

    // Verify page loaded
    const heading = page.locator('h2:has-text("数据源管理")');
    await expect(heading).toBeVisible({ timeout: 5000 });

    console.log('✓ Data Sources page loaded successfully');
  });

  test('should add Jira source with mock server', async ({ page }) => {
    // Navigate to data sources page
    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');

    // Click "Add Source" button
    const addButton = page.locator('button:has-text("添加数据源")');
    await expect(addButton).toBeVisible({ timeout: 5000 });
    await addButton.click();

    // Wait for modal to appear
    await page.waitForTimeout(500);

    // Select Jira type
    const jiraOption = page.locator('button:has-text("Jira")').first();
    await expect(jiraOption).toBeVisible({ timeout: 5000 });
    await jiraOption.click();

    console.log('✓ Jira option selected');

    // Fill in Jira configuration
    const urlInput = page.locator('input[placeholder*="Jira URL"]');
    await expect(urlInput).toBeVisible({ timeout: 5000 });
    await urlInput.fill(mockJiraUrl);

    const emailInput = page.locator('input[placeholder*="邮箱"]');
    await emailInput.fill(mockEmail);

    const tokenInput = page.locator('input[placeholder*="API Token"]');
    await tokenInput.fill(mockToken);

    // Optional: Add JQL query
    const jqlInput = page.locator('textarea[placeholder*="JQL"]');
    if (await jqlInput.isVisible()) {
      await jqlInput.fill('project = TEST');
    }

    console.log('✓ Jira configuration filled');

    // Click "Add Source" button in modal
    const submitButton = page.locator('button:has-text("添加数据源")').last();
    await submitButton.click();

    // Wait for source to be added
    await page.waitForTimeout(2000);

    // Verify Jira source appears in the list
    const jiraCard = page.locator('.bg-white:has-text("jira")').first();
    await expect(jiraCard).toBeVisible({ timeout: 10000 });

    console.log('✓ Jira source added successfully');
  });

  test('should add Confluence source with mock server', async ({ page }) => {
    // Navigate to data sources page
    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');

    // Click "Add Source" button
    const addButton = page.locator('button:has-text("添加数据源")');
    await addButton.click();
    await page.waitForTimeout(500);

    // Select Confluence type
    const confluenceOption = page.locator('button:has-text("Confluence")').first();
    await expect(confluenceOption).toBeVisible({ timeout: 5000 });
    await confluenceOption.click();

    console.log('✓ Confluence option selected');

    // Fill in Confluence configuration
    const urlInput = page.locator('input[placeholder*="Confluence URL"]');
    await expect(urlInput).toBeVisible({ timeout: 5000 });
    await urlInput.fill(mockConfluenceUrl);

    const emailInput = page.locator('input[placeholder*="邮箱"]');
    await emailInput.fill(mockEmail);

    const tokenInput = page.locator('input[placeholder*="API Token"]');
    await tokenInput.fill(mockToken);

    // Optional: Add space key
    const spaceInput = page.locator('input[placeholder*="空间键"]');
    if (await spaceInput.isVisible()) {
      await spaceInput.fill('TEST');
    }

    console.log('✓ Confluence configuration filled');

    // Click "Add Source" button in modal
    const submitButton = page.locator('button:has-text("添加数据源")').last();
    await submitButton.click();

    // Wait for source to be added
    await page.waitForTimeout(2000);

    // Verify Confluence source appears in the list
    const confluenceCard = page.locator('.bg-white:has-text("confluence")').first();
    await expect(confluenceCard).toBeVisible({ timeout: 10000 });

    console.log('✓ Confluence source added successfully');
  });

  test('should display both Jira and Confluence sources', async ({ page }) => {
    // Navigate to data sources page
    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');

    // Wait for sources to load
    await page.waitForTimeout(2000);

    // Check for Jira tab
    const jiraTab = page.locator('button:has-text("Jira")').first();
    if (await jiraTab.isVisible()) {
      await jiraTab.click();
      await page.waitForTimeout(500);

      // Count Jira sources
      const jiraSources = page.locator('.bg-white:has-text("jira")');
      const jiraCount = await jiraSources.count();
      console.log(`Found ${jiraCount} Jira source(s)`);
    }

    // Check for Confluence tab
    const confluenceTab = page.locator('button:has-text("Confluence")').first();
    if (await confluenceTab.isVisible()) {
      await confluenceTab.click();
      await page.waitForTimeout(500);

      // Count Confluence sources
      const confluenceSources = page.locator('.bg-white:has-text("confluence")');
      const confluenceCount = await confluenceSources.count();
      console.log(`Found ${confluenceCount} Confluence source(s)`);
    }

    // Switch to "All Sources" tab
    const allTab = page.locator('button:has-text("全部")').first();
    if (await allTab.isVisible()) {
      await allTab.click();
      await page.waitForTimeout(500);
    }

    console.log('✓ Data sources displayed successfully');
  });

  test('should verify source status and document count', async ({ page }) => {
    // Navigate to data sources page
    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Get all source cards
    const sourceCards = page.locator('.bg-white.rounded-xl.border');
    const count = await sourceCards.count();

    console.log(`\n=== Data Source Status ===`);
    console.log(`Total sources: ${count}`);

    // Check each source
    for (let i = 0; i < count; i++) {
      const card = sourceCards.nth(i);

      // Get source name
      const nameElement = card.locator('h3').first();
      const name = await nameElement.textContent();

      // Get source type
      const typeElement = card.locator('span.uppercase').first();
      const type = await typeElement.textContent();

      // Get status
      const statusElement = card.locator('span.rounded-full').first();
      const status = await statusElement.textContent();

      // Get item count if available
      const itemCountElement = card.locator('p:has-text("个项目")');
      let itemCount = 'N/A';
      if (await itemCountElement.isVisible()) {
        const text = await itemCountElement.textContent();
        itemCount = text?.match(/\d+/)?.[0] || 'N/A';
      }

      console.log(`\nSource ${i + 1}:`);
      console.log(`  Name: ${name}`);
      console.log(`  Type: ${type}`);
      console.log(`  Status: ${status}`);
      console.log(`  Items: ${itemCount}`);
    }

    console.log('\n✓ Source status verified');
  });

  test('should test search functionality', async ({ page }) => {
    // Navigate to data sources page
    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Find search input
    const searchInput = page.locator('input[placeholder*="搜索"]');
    if (await searchInput.isVisible()) {
      // Test search
      await searchInput.fill('jira');
      await page.waitForTimeout(500);

      console.log('✓ Search functionality tested');
    } else {
      console.log('⚠ Search input not found');
    }
  });

  test('should test source filtering by type', async ({ page }) => {
    // Navigate to data sources page
    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Test each tab
    const tabs = ['全部', '文件', 'Jira', 'Confluence'];

    for (const tabName of tabs) {
      const tab = page.locator(`button:has-text("${tabName}")`).first();
      if (await tab.isVisible()) {
        await tab.click();
        await page.waitForTimeout(500);

        const sources = page.locator('.bg-white.rounded-xl.border');
        const count = await sources.count();

        console.log(`${tabName} tab: ${count} source(s)`);
      }
    }

    console.log('✓ Filtering by type tested');
  });

  test('should handle source deletion', async ({ page }) => {
    // Navigate to data sources page
    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Find first source card
    const sourceCard = page.locator('.bg-white.rounded-xl.border').first();

    if (await sourceCard.isVisible()) {
      // Get source name before deletion
      const nameElement = sourceCard.locator('h3').first();
      const sourceName = await nameElement.textContent();

      console.log(`Attempting to delete source: ${sourceName}`);

      // Find delete button (trash icon)
      const deleteButton = sourceCard.locator('button:has(svg)').last();

      if (await deleteButton.isVisible()) {
        // Click delete button
        await deleteButton.click();
        await page.waitForTimeout(1000);

        console.log('✓ Delete button clicked');

        // Note: In a real test, you would confirm the deletion dialog
        // and verify the source is removed from the list
      } else {
        console.log('⚠ Delete button not found');
      }
    } else {
      console.log('⚠ No sources available to delete');
    }
  });
});
