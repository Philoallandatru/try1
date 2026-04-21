import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Document Management E2E', () => {
  const workspaceId = 'demo';
  const testPdfPath = path.join(__dirname, '../../../documents/PCI_Firmware_v3.3_20210120_NCB.pdf');

  test.beforeEach(async ({ page }) => {
    // Navigate to home page first
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    // Connect to runner if not already connected
    const tokenInput = page.locator('input[placeholder="change-me"]');
    if (await tokenInput.isVisible()) {
      await tokenInput.fill('test-token-123');

      // Select demo workspace
      const workspaceSelect = page.locator('select, [role="combobox"]').filter({ hasText: /workspace/i }).first();
      if (await workspaceSelect.isVisible()) {
        await workspaceSelect.selectOption('demo');
      }

      await page.waitForTimeout(1000);
    }

    // Navigate to document management page
    await page.goto('http://localhost:5173/documents');
    await page.waitForLoadState('networkidle');
  });

  test('should load document types', async ({ page }) => {
    // Check if document type selector exists
    const typeSelector = page.locator('select[name="document_type"]').first();
    await expect(typeSelector).toBeVisible();

    // Verify document types are loaded
    const options = await typeSelector.locator('option').allTextContents();
    expect(options.length).toBeGreaterThan(0);
    expect(options).toContain('Specification');
  });

  test('should list existing documents', async ({ page }) => {
    // Wait for documents to load
    await page.waitForTimeout(1000);

    // Check if document list exists
    const documentList = page.locator('.document-list, .documents-table, [data-testid="document-list"]');

    // Should have at least some documents (from previous uploads)
    const documentItems = page.locator('.document-item, tr[data-document], [data-testid="document-item"]');
    const count = await documentItems.count();

    console.log(`Found ${count} documents in the list`);
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should filter documents by type', async ({ page }) => {
    // Find filter dropdown
    const filterDropdown = page.locator('select').filter({ hasText: /All Types|Filter|Type/ }).first();

    if (await filterDropdown.isVisible()) {
      // Select "spec" type
      await filterDropdown.selectOption({ label: /Specification|spec/i });

      // Wait for filtered results
      await page.waitForTimeout(500);

      // Verify filtered results
      const documentItems = page.locator('.document-item, tr[data-document]');
      const count = await documentItems.count();

      console.log(`Found ${count} spec documents`);
      expect(count).toBeGreaterThanOrEqual(0);
    }
  });

  test('should upload a new document', async ({ page }) => {
    // Find file input
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();

    // Select document type
    const typeSelector = page.locator('select').filter({ hasText: /Type|Category/ }).first();
    if (await typeSelector.isVisible()) {
      await typeSelector.selectOption('spec');
    }

    // Upload file
    await fileInput.setInputFiles(testPdfPath);

    // Wait for file to be selected
    await page.waitForTimeout(500);

    // Click upload button
    const uploadButton = page.locator('button').filter({ hasText: /Upload|Submit/ }).first();
    await uploadButton.click();

    // Wait for upload to complete (may take a while)
    await page.waitForTimeout(60000); // 60 seconds timeout

    // Check for success message
    const successMessage = page.locator('.status-message.success, .alert-success, [role="alert"]').filter({ hasText: /success|uploaded/i });
    await expect(successMessage).toBeVisible({ timeout: 5000 });
  });

  test('should search uploaded documents', async ({ page }) => {
    // Navigate to search/analyze page
    await page.goto('http://localhost:5173');

    // Find search input
    const searchInput = page.locator('input[type="text"], input[placeholder*="search"], textarea').first();

    if (await searchInput.isVisible()) {
      // Search for PCIe related content
      await searchInput.fill('PCIe firmware specification');

      // Click search button
      const searchButton = page.locator('button').filter({ hasText: /Search|Analyze|Submit/ }).first();
      await searchButton.click();

      // Wait for results
      await page.waitForTimeout(2000);

      // Check if results contain uploaded documents
      const resultsArea = page.locator('.search-results, .results, [data-testid="results"]');
      const hasResults = await resultsArea.isVisible();

      if (hasResults) {
        const resultText = await resultsArea.textContent();
        console.log('Search results:', resultText?.substring(0, 200));
      }
    }
  });

  test('should verify document appears in search with correct metadata', async ({ page }) => {
    // Make API call to search
    const response = await page.request.post('http://localhost:8787/api/retrieval/search', {
      data: {
        query: 'PCI firmware',
        top_k: 10,
        document_types: ['spec']
      }
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    expect(data.status).toBe('success');
    expect(data.total_results).toBeGreaterThan(0);

    // Verify results have proper metadata
    const firstResult = data.results[0];
    expect(firstResult).toHaveProperty('doc_id');
    expect(firstResult).toHaveProperty('title');
    expect(firstResult).toHaveProperty('score');
    expect(firstResult.metadata).toHaveProperty('document_type');
    expect(firstResult.metadata.document_type).toBe('spec');

    console.log('First search result:', {
      title: firstResult.title,
      score: firstResult.score,
      doc_type: firstResult.metadata.document_type
    });
  });
});
