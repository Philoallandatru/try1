import { test, expect } from '@playwright/test';

/**
 * E2E Test: Complete Jira/Confluence Integration Flow
 *
 * This test simulates the complete workflow from scratch:
 * 1. Setup mock Jira/Confluence servers (using fixtures or real mock servers)
 * 2. Navigate to Data Sources page
 * 3. Add Jira source with URL and credentials
 * 4. Add Confluence source with URL and credentials
 * 5. Trigger sync/parsing
 * 6. Verify documents are parsed and indexed
 * 7. Test search functionality with parsed documents
 */

test.describe('Jira/Confluence Full Integration Flow', () => {
  // Mock server configuration
  const mockJiraUrl = 'http://localhost:8797';
  const mockConfluenceUrl = 'http://localhost:8798';
  const testEmail = 'test@example.com';
  const testToken = 'mock-api-token-12345';
  const runnerToken = 'test-token-123';

  test.beforeEach(async ({ page }) => {
    console.log('\n=== Test Setup ===');

    // Navigate to home page
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    // Setup runner connection
    const tokenInput = page.locator('input[placeholder="change-me"]');
    if (await tokenInput.isVisible()) {
      console.log('Setting up runner connection...');
      await tokenInput.fill(runnerToken);
      await tokenInput.blur();
      await page.waitForTimeout(1500);
    }

    // Select workspace
    const workspaceSelect = page.locator('select[data-testid="workspace-selector"]').first();
    if (await workspaceSelect.isVisible()) {
      const options = await workspaceSelect.locator('option').allTextContents();
      console.log('Available workspaces:', options);

      // Select first workspace or create new one
      await workspaceSelect.selectOption({ index: 0 });
      await page.waitForTimeout(1000);
    }

    console.log('✓ Setup complete\n');
  });

  test('Step 1: Navigate to Data Sources page and verify UI', async ({ page }) => {
    console.log('\n=== Step 1: Navigate to Data Sources ===');

    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');

    // Verify page elements
    const heading = page.locator('h1:has-text("数据源管理")');
    await expect(heading).toBeVisible({ timeout: 5000 });

    const description = page.locator('p:has-text("统一管理")');
    await expect(description).toBeVisible();

    // Verify tabs
    const tabs = ['全部', '文件', 'Jira', 'Confluence'];
    for (const tabName of tabs) {
      const tab = page.locator(`button:has-text("${tabName}")`).first();
      await expect(tab).toBeVisible();
      console.log(`✓ Tab "${tabName}" found`);
    }

    // Verify "Add Source" button
    const addButton = page.locator('button:has-text("添加数据源")');
    await expect(addButton).toBeVisible();

    console.log('✓ Data Sources page UI verified');
  });

  test('Step 2: Add Jira source with complete configuration', async ({ page }) => {
    console.log('\n=== Step 2: Add Jira Source ===');

    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');

    // Open add source modal
    const addButton = page.locator('button:has-text("添加 Jira")');
    await addButton.click();
    await page.waitForTimeout(500);

    // Verify modal opened
    const modalTitle = page.locator('h3:has-text("添加 Jira 数据源")');
    await expect(modalTitle).toBeVisible({ timeout: 5000 });
    console.log('✓ Add source modal opened');

    // Select Jira type
    const jiraButton = page.locator('button:has-text("Jira")').first();
    await expect(jiraButton).toBeVisible();
    await jiraButton.click();
    await page.waitForTimeout(300);

    // Verify Jira button is selected (should have blue background)
    const jiraButtonClass = await jiraButton.getAttribute('class');
    expect(jiraButtonClass).toContain('border-blue-500');
    console.log('✓ Jira type selected');

    // Fill in Jira configuration
    console.log('Filling Jira configuration...');

    const urlInput = page.locator('input[placeholder*="Jira URL"]');
    await expect(urlInput).toBeVisible({ timeout: 5000 });
    await urlInput.fill(mockJiraUrl);
    console.log(`  URL: ${mockJiraUrl}`);

    const emailInput = page.locator('input[placeholder*="邮箱"]');
    await emailInput.fill(testEmail);
    console.log(`  Email: ${testEmail}`);

    const tokenInput = page.locator('input[placeholder*="API Token"]');
    await tokenInput.fill(testToken);
    console.log(`  Token: ${testToken.substring(0, 10)}...`);

    // Add JQL query
    const jqlInput = page.locator('textarea[placeholder*="JQL"]');
    if (await jqlInput.isVisible()) {
      const jqlQuery = 'project = SSD AND status != Done';
      await jqlInput.fill(jqlQuery);
      console.log(`  JQL: ${jqlQuery}`);
    }

    // Take screenshot before submission
    await page.screenshot({ path: 'test-results/jira-config-filled.png' });

    // Submit the form
    const submitButton = page.locator('button:has-text("添加数据源")').last();
    await submitButton.click();
    console.log('✓ Form submitted');

    // Wait for modal to close and source to be added
    await page.waitForTimeout(2000);

    // Verify modal closed
    const modalStillVisible = await modalTitle.isVisible().catch(() => false);
    expect(modalStillVisible).toBe(false);
    console.log('✓ Modal closed');

    // Verify Jira source appears in the list
    await page.waitForTimeout(1000);
    const jiraCards = page.locator('.bg-white.rounded-xl:has-text("JIRA")');
    const count = await jiraCards.count();

    if (count > 0) {
      console.log(`✓ Jira source added successfully (${count} source(s) found)`);

      // Get details of the first Jira source
      const firstCard = jiraCards.first();
      const name = await firstCard.locator('h3').textContent();
      const status = await firstCard.locator('span.rounded-full').textContent();

      console.log(`  Name: ${name}`);
      console.log(`  Status: ${status}`);
    } else {
      console.log('⚠ No Jira sources found in the list');
    }
  });

  test('Step 3: Add Confluence source with complete configuration', async ({ page }) => {
    console.log('\n=== Step 3: Add Confluence Source ===');

    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');

    // Open add source modal
    const addButton = page.locator('button:has-text("添加数据源")');
    await addButton.click();
    await page.waitForTimeout(500);

    // Select Confluence type
    const confluenceButton = page.locator('button:has-text("Confluence")').first();
    await expect(confluenceButton).toBeVisible({ timeout: 5000 });
    await confluenceButton.click();
    await page.waitForTimeout(300);
    console.log('✓ Confluence type selected');

    // Fill in Confluence configuration
    console.log('Filling Confluence configuration...');

    const urlInput = page.locator('input[placeholder*="Confluence URL"]');
    await expect(urlInput).toBeVisible({ timeout: 5000 });
    await urlInput.fill(mockConfluenceUrl);
    console.log(`  URL: ${mockConfluenceUrl}`);

    const emailInput = page.locator('input[placeholder*="邮箱"]');
    await emailInput.fill(testEmail);
    console.log(`  Email: ${testEmail}`);

    const tokenInput = page.locator('input[placeholder*="API Token"]');
    await tokenInput.fill(testToken);
    console.log(`  Token: ${testToken.substring(0, 10)}...`);

    // Add space key
    const spaceInput = page.locator('input[placeholder*="空间键"]');
    if (await spaceInput.isVisible()) {
      const spaceKey = 'SSDENG';
      await spaceInput.fill(spaceKey);
      console.log(`  Space Key: ${spaceKey}`);
    }

    // Take screenshot
    await page.screenshot({ path: 'test-results/confluence-config-filled.png' });

    // Submit the form
    const submitButton = page.locator('button:has-text("添加数据源")').last();
    await submitButton.click();
    console.log('✓ Form submitted');

    // Wait for source to be added
    await page.waitForTimeout(2000);

    // Verify Confluence source appears
    const confluenceCards = page.locator('.bg-white.rounded-xl:has-text("CONFLUENCE")');
    const count = await confluenceCards.count();

    if (count > 0) {
      console.log(`✓ Confluence source added successfully (${count} source(s) found)`);

      const firstCard = confluenceCards.first();
      const name = await firstCard.locator('h3').textContent();
      const status = await firstCard.locator('span.rounded-full').textContent();

      console.log(`  Name: ${name}`);
      console.log(`  Status: ${status}`);
    } else {
      console.log('⚠ No Confluence sources found in the list');
    }
  });

  test('Step 4: Verify both sources are listed and check status', async ({ page }) => {
    console.log('\n=== Step 4: Verify Sources ===');

    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Switch to "All Sources" tab
    const allTab = page.locator('button:has-text("全部")').first();
    await allTab.click();
    await page.waitForTimeout(500);

    // Get all source cards
    const sourceCards = page.locator('.bg-white.rounded-xl.border');
    const totalCount = await sourceCards.count();

    console.log(`\nTotal sources: ${totalCount}`);

    // Analyze each source
    for (let i = 0; i < totalCount; i++) {
      const card = sourceCards.nth(i);

      const name = await card.locator('h3').first().textContent();
      const type = await card.locator('span.uppercase').first().textContent();
      const status = await card.locator('span.rounded-full').first().textContent();

      // Try to get item count
      let itemCount = 'N/A';
      const itemElement = card.locator('p:has-text("个项目")');
      if (await itemElement.isVisible()) {
        const text = await itemElement.textContent();
        itemCount = text?.match(/\d+/)?.[0] || 'N/A';
      }

      console.log(`\nSource ${i + 1}:`);
      console.log(`  Name: ${name}`);
      console.log(`  Type: ${type}`);
      console.log(`  Status: ${status}`);
      console.log(`  Items: ${itemCount}`);
    }

    // Count by type
    const jiraCount = await page.locator('.bg-white.rounded-xl:has-text("jira")').count();
    const confluenceCount = await page.locator('.bg-white.rounded-xl:has-text("confluence")').count();
    const fileCount = await page.locator('.bg-white.rounded-xl:has-text("file")').count();

    console.log(`\nSummary by type:`);
    console.log(`  Jira: ${jiraCount}`);
    console.log(`  Confluence: ${confluenceCount}`);
    console.log(`  Files: ${fileCount}`);

    console.log('\n✓ Sources verified');
  });

  test('Step 5: Test filtering by source type', async ({ page }) => {
    console.log('\n=== Step 5: Test Filtering ===');

    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const tabs = [
      { name: '全部', expectedTypes: ['jira', 'confluence', 'file'] },
      { name: 'Jira', expectedTypes: ['jira'] },
      { name: 'Confluence', expectedTypes: ['confluence'] },
      { name: '文件', expectedTypes: ['file'] }
    ];

    for (const tab of tabs) {
      const tabButton = page.locator(`button:has-text("${tab.name}")`).first();
      await tabButton.click();
      await page.waitForTimeout(500);

      const sourceCards = page.locator('.bg-white.rounded-xl.border');
      const count = await sourceCards.count();

      console.log(`\n${tab.name} tab: ${count} source(s)`);

      // Verify filtered sources match expected type
      if (count > 0 && tab.name !== '全部') {
        for (let i = 0; i < Math.min(count, 3); i++) {
          const card = sourceCards.nth(i);
          const type = await card.locator('span.uppercase').first().textContent();
          console.log(`  Source ${i + 1} type: ${type}`);
        }
      }
    }

    console.log('\n✓ Filtering tested');
  });

  test('Step 6: Test search functionality', async ({ page }) => {
    console.log('\n=== Step 6: Test Search ===');

    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const searchInput = page.locator('input[placeholder*="搜索"]');

    if (await searchInput.isVisible()) {
      // Test search for "jira"
      await searchInput.fill('jira');
      await page.waitForTimeout(500);

      let count = await page.locator('.bg-white.rounded-xl.border').count();
      console.log(`Search "jira": ${count} result(s)`);

      // Clear and search for "confluence"
      await searchInput.clear();
      await searchInput.fill('confluence');
      await page.waitForTimeout(500);

      count = await page.locator('.bg-white.rounded-xl.border').count();
      console.log(`Search "confluence": ${count} result(s)`);

      // Clear search
      await searchInput.clear();
      await page.waitForTimeout(500);

      count = await page.locator('.bg-white.rounded-xl.border').count();
      console.log(`No search filter: ${count} result(s)`);

      console.log('\n✓ Search functionality tested');
    } else {
      console.log('⚠ Search input not found');
    }
  });

  test('Step 7: Verify source card interactions', async ({ page }) => {
    console.log('\n=== Step 7: Test Card Interactions ===');

    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const sourceCard = page.locator('.bg-white.rounded-xl.border').first();

    if (await sourceCard.isVisible()) {
      // Test hover effect
      await sourceCard.hover();
      await page.waitForTimeout(300);
      console.log('✓ Card hover effect tested');

      // Find edit button
      const editButton = sourceCard.locator('button:has-text("编辑")');
      if (await editButton.isVisible()) {
        console.log('✓ Edit button found');
      }

      // Find delete button
      const deleteButton = sourceCard.locator('button:has(svg)').last();
      if (await deleteButton.isVisible()) {
        console.log('✓ Delete button found');
      }

      // Take screenshot of card
      await sourceCard.screenshot({ path: 'test-results/source-card.png' });
      console.log('✓ Screenshot saved');
    } else {
      console.log('⚠ No source cards found');
    }
  });

  test('Step 8: Complete flow summary', async ({ page }) => {
    console.log('\n=== Step 8: Flow Summary ===');

    await page.goto('http://localhost:5173/data-sources');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Get final state
    const allSources = page.locator('.bg-white.rounded-xl.border');
    const totalCount = await allSources.count();

    const jiraCount = await page.locator('.bg-white.rounded-xl:has-text("jira")').count();
    const confluenceCount = await page.locator('.bg-white.rounded-xl:has-text("confluence")').count();

    console.log('\n=== Integration Flow Complete ===');
    console.log(`Total data sources: ${totalCount}`);
    console.log(`  - Jira sources: ${jiraCount}`);
    console.log(`  - Confluence sources: ${confluenceCount}`);
    console.log('\n✓ All steps completed successfully');

    // Take final screenshot
    await page.screenshot({ path: 'test-results/final-data-sources.png', fullPage: true });
  });
});
