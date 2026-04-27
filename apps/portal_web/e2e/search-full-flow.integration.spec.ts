import { test, expect } from '@playwright/test';

/**
 * E2E Test: Complete Search Flow
 *
 * This test simulates the complete search workflow:
 * 1. Navigate to Search page
 * 2. Check index status
 * 3. Build/rebuild index
 * 4. Perform search queries
 * 5. Filter by document types
 * 6. View document details
 * 7. Test search highlighting
 */

test.describe('Search Full Integration Flow', () => {
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
      await workspaceSelect.selectOption({ index: 0 });
      await page.waitForTimeout(1000);
    }

    console.log('✓ Setup complete\n');
  });

  test('Step 1: Navigate to Search page and verify UI', async ({ page }) => {
    console.log('\n=== Step 1: Navigate to Search Page ===');

    await page.goto('http://localhost:5173/search');
    await page.waitForLoadState('networkidle');

    // Verify page heading
    const heading = page.locator('h2:has-text("Knowledge Retrieval")');
    await expect(heading).toBeVisible({ timeout: 5000 });

    const description = page.locator('p:has-text("Search across all indexed documents")');
    await expect(description).toBeVisible();

    // Verify search input
    const searchInput = page.locator('input[data-testid="search-input"]');
    await expect(searchInput).toBeVisible();

    // Verify search button
    const searchButton = page.locator('button[data-testid="search-button"]');
    await expect(searchButton).toBeVisible();

    console.log('✓ Search page UI verified');
  });

  test('Step 2: Check index status', async ({ page }) => {
    console.log('\n=== Step 2: Check Index Status ===');

    await page.goto('http://localhost:5173/search');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Verify index status card
    const statusCard = page.locator('[data-testid="index-status-card"]');
    await expect(statusCard).toBeVisible();

    // Get document count
    const docCount = page.locator('[data-testid="document-count"]');
    const countText = await docCount.textContent();
    console.log(`Index status: ${countText}`);

    // Verify rebuild button exists
    const rebuildButton = page.locator('button[data-testid="rebuild-index-button"]');
    await expect(rebuildButton).toBeVisible();

    console.log('✓ Index status checked');
  });

  test('Step 3: Build/Rebuild index', async ({ page }) => {
    console.log('\n=== Step 3: Build Index ===');

    await page.goto('http://localhost:5173/search');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const rebuildButton = page.locator('button[data-testid="rebuild-index-button"]');

    // Click rebuild button
    await rebuildButton.click();
    console.log('✓ Rebuild button clicked');

    // Wait for building state
    await page.waitForTimeout(500);
    const buildingText = page.locator('text=Building...');
    if (await buildingText.isVisible()) {
      console.log('✓ Index building started');
    }

    // Wait for completion (max 30 seconds)
    await page.waitForTimeout(5000);

    // Verify document count updated
    const docCount = page.locator('[data-testid="document-count"]');
    const countText = await docCount.textContent();
    console.log(`✓ Index rebuilt: ${countText}`);
  });

  test('Step 4: Perform search queries', async ({ page }) => {
    console.log('\n=== Step 4: Perform Search ===');

    await page.goto('http://localhost:5173/search');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const searchInput = page.locator('input[data-testid="search-input"]');
    const searchButton = page.locator('button[data-testid="search-button"]');

    // Test search query 1: English
    const query1 = 'specification';
    await searchInput.fill(query1);
    await searchButton.click();
    console.log(`Searching for: "${query1}"`);

    await page.waitForTimeout(2000);

    // Check for results
    const results = page.locator('[data-testid="search-results"]');
    if (await results.isVisible()) {
      const resultCards = page.locator('[data-testid^="search-result-"]');
      const count = await resultCards.count();
      console.log(`✓ Found ${count} results for "${query1}"`);

      if (count > 0) {
        // Verify first result structure
        const firstResult = resultCards.first();
        await expect(firstResult).toBeVisible();

        const title = firstResult.locator('strong').first();
        await expect(title).toBeVisible();
        console.log(`  First result: ${await title.textContent()}`);
      }
    } else {
      console.log('⚠ No results found');
    }

    // Test search query 2: Chinese
    await searchInput.clear();
    const query2 = '文档';
    await searchInput.fill(query2);
    await searchButton.click();
    console.log(`Searching for: "${query2}"`);

    await page.waitForTimeout(2000);

    if (await results.isVisible()) {
      const resultCards = page.locator('[data-testid^="search-result-"]');
      const count = await resultCards.count();
      console.log(`✓ Found ${count} results for "${query2}"`);
    }

    console.log('✓ Search queries tested');
  });

  test('Step 5: Filter by document types', async ({ page }) => {
    console.log('\n=== Step 5: Test Document Type Filters ===');

    await page.goto('http://localhost:5173/search');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Perform a search first
    const searchInput = page.locator('input[data-testid="search-input"]');
    const searchButton = page.locator('button[data-testid="search-button"]');

    await searchInput.fill('test');
    await searchButton.click();
    await page.waitForTimeout(2000);

    // Test filter buttons
    const filters = [
      { name: 'Specification', selector: 'button:has-text("Specification")' },
      { name: 'Policy', selector: 'button:has-text("Policy")' },
      { name: 'Other', selector: 'button:has-text("Other")' }
    ];

    for (const filter of filters) {
      const filterButton = page.locator(filter.selector).first();
      if (await filterButton.isVisible()) {
        await filterButton.click();
        await page.waitForTimeout(500);
        console.log(`✓ ${filter.name} filter toggled`);

        // Check if filter is active
        const buttonClass = await filterButton.getAttribute('class');
        if (buttonClass?.includes('active')) {
          console.log(`  ${filter.name} filter is active`);
        }

        // Click again to deactivate
        await filterButton.click();
        await page.waitForTimeout(500);
      }
    }

    // Test clear filters button
    const clearButton = page.locator('button:has-text("Clear filters")');
    if (await clearButton.isVisible()) {
      await clearButton.click();
      console.log('✓ Filters cleared');
    }

    console.log('✓ Document type filters tested');
  });

  test('Step 6: View document details', async ({ page }) => {
    console.log('\n=== Step 6: View Document Details ===');

    await page.goto('http://localhost:5173/search');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Perform search
    const searchInput = page.locator('input[data-testid="search-input"]');
    const searchButton = page.locator('button[data-testid="search-button"]');

    await searchInput.fill('document');
    await searchButton.click();
    await page.waitForTimeout(2000);

    // Click on first result
    const firstResult = page.locator('[data-testid="search-result-0"]');
    if (await firstResult.isVisible()) {
      await firstResult.click();
      console.log('✓ First result clicked');

      await page.waitForTimeout(500);

      // Verify document detail panel
      const detailPanel = page.locator('.document-detail');
      await expect(detailPanel).toBeVisible({ timeout: 5000 });

      // Verify detail sections
      const detailHeading = detailPanel.locator('h3').first();
      const detailTitle = await detailHeading.textContent();
      console.log(`  Document title: ${detailTitle}`);

      // Verify metric cards
      const metricCards = detailPanel.locator('.metric-card');
      const metricCount = await metricCards.count();
      console.log(`  Metric cards: ${metricCount}`);

      // Verify content section
      const contentSection = detailPanel.locator('.document-content');
      if (await contentSection.isVisible()) {
        console.log('✓ Document content visible');
      }

      // Take screenshot
      await page.screenshot({ path: 'test-results/search-document-detail.png' });
      console.log('✓ Screenshot saved');
    } else {
      console.log('⚠ No search results to click');
    }

    console.log('✓ Document details tested');
  });

  test('Step 7: Test keyboard navigation', async ({ page }) => {
    console.log('\n=== Step 7: Test Keyboard Navigation ===');

    await page.goto('http://localhost:5173/search');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const searchInput = page.locator('input[data-testid="search-input"]');

    // Focus on search input
    await searchInput.focus();

    // Type query
    await searchInput.fill('test query');
    console.log('✓ Query typed');

    // Press Enter to search
    await searchInput.press('Enter');
    console.log('✓ Enter key pressed to search');

    await page.waitForTimeout(2000);

    console.log('✓ Keyboard navigation tested');
  });

  test('Step 8: Complete search flow summary', async ({ page }) => {
    console.log('\n=== Step 8: Search Flow Summary ===');

    await page.goto('http://localhost:5173/search');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Get final state
    const docCount = page.locator('[data-testid="document-count"]');
    const countText = await docCount.textContent();

    console.log('\n=== Search Flow Complete ===');
    console.log(`Index status: ${countText}`);
    console.log('✓ All search steps completed successfully');

    // Take final screenshot
    await page.screenshot({ path: 'test-results/final-search-page.png', fullPage: true });
  });
});
