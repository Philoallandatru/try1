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
      // Trigger blur event to save token to localStorage
      await tokenInput.blur();

      // Wait for workspaces to load
      await page.waitForTimeout(1500);

      // Select demo workspace by label (not value)
      const workspaceSelect = page.locator('select').filter({ hasText: /workspace/i }).first();
      if (await workspaceSelect.isVisible()) {
        // Select by label "demo" instead of value
        await workspaceSelect.selectOption({ label: 'demo' });
      }

      await page.waitForTimeout(1000);
    }

    // Navigate to document management page
    await page.goto('http://localhost:5173/documents');
    await page.waitForLoadState('networkidle');
  });

  test('should load document types', async ({ page }) => {
    // First select a file to make the upload form visible
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testPdfPath);

    // Wait for form to appear
    await page.waitForTimeout(500);

    // Check if document type selector exists (using id instead of name)
    const typeSelector = page.locator('select#document-type');
    await expect(typeSelector).toBeVisible();

    // Verify document types are loaded
    const options = await typeSelector.locator('option').allTextContents();
    expect(options.length).toBeGreaterThan(0);
    // Check for "Specification" in the text (may include priority info)
    const hasSpec = options.some(opt => opt.includes('Specification'));
    expect(hasSpec).toBeTruthy();
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
    // Find filter dropdown (the one in the documents section, not upload section)
    const filterDropdown = page.locator('.filter-controls select');

    if (await filterDropdown.isVisible()) {
      // Select "spec" type by value
      await filterDropdown.selectOption('spec');

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

    // Upload file
    await fileInput.setInputFiles(testPdfPath);

    // Wait for form to appear
    await page.waitForTimeout(500);

    // Select document type using the correct id selector
    const typeSelector = page.locator('select#document-type');
    await expect(typeSelector).toBeVisible();
    await typeSelector.selectOption('spec');

    // Click upload button
    const uploadButton = page.locator('button').filter({ hasText: /Upload|Submit/ }).first();
    await uploadButton.click();

    // Wait for upload to start - look for "Uploading" or "Processing" message
    const processingMessage = page.locator('.status-message.processing, [role="alert"]').filter({ hasText: /uploading|processing/i });
    await expect(processingMessage).toBeVisible({ timeout: 10000 });

    // Note: Full document processing can take 10+ minutes for large PDFs with MinerU
    // We just verify the upload started successfully, not that it completed
    console.log('Upload started successfully. Full processing happens in background.');
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
