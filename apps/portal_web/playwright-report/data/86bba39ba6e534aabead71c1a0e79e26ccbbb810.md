# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: document-management.spec.ts >> Document Management E2E >> should load document types
- Location: e2e\document-management.spec.ts:42:3

# Error details

```
Test timeout of 1860000ms exceeded.
```

```
Error: locator.setInputFiles: Test timeout of 1860000ms exceeded.
Call log:
  - waiting for locator('input[type="file"]')

```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | import path from 'path';
  3   | import { fileURLToPath } from 'url';
  4   | 
  5   | const __filename = fileURLToPath(import.meta.url);
  6   | const __dirname = path.dirname(__filename);
  7   | 
  8   | test.describe('Document Management E2E', () => {
  9   |   const workspaceId = 'demo';
  10  |   const testPdfPath = path.join(__dirname, '../../../documents/PCI_Firmware_v3.3_20210120_NCB.pdf');
  11  | 
  12  |   test.beforeEach(async ({ page }) => {
  13  |     // Navigate to home page first
  14  |     await page.goto('http://localhost:5173');
  15  |     await page.waitForLoadState('networkidle');
  16  | 
  17  |     // Connect to runner if not already connected
  18  |     const tokenInput = page.locator('input[placeholder="change-me"]');
  19  |     if (await tokenInput.isVisible()) {
  20  |       await tokenInput.fill('test-token-123');
  21  |       // Trigger blur event to save token to localStorage
  22  |       await tokenInput.blur();
  23  | 
  24  |       // Wait for workspaces to load
  25  |       await page.waitForTimeout(1500);
  26  | 
  27  |       // Select demo workspace by label (not value)
  28  |       const workspaceSelect = page.locator('select').filter({ hasText: /workspace/i }).first();
  29  |       if (await workspaceSelect.isVisible()) {
  30  |         // Select by label "demo" instead of value
  31  |         await workspaceSelect.selectOption({ label: 'demo' });
  32  |       }
  33  | 
  34  |       await page.waitForTimeout(1000);
  35  |     }
  36  | 
  37  |     // Navigate to data sources page
  38  |     await page.goto('http://localhost:5173/data-sources');
  39  |     await page.waitForLoadState('networkidle');
  40  |   });
  41  | 
  42  |   test('should load document types', async ({ page }) => {
  43  |     // First select a file to make the upload form visible
  44  |     const fileInput = page.locator('input[type="file"]');
> 45  |     await fileInput.setInputFiles(testPdfPath);
      |     ^ Error: locator.setInputFiles: Test timeout of 1860000ms exceeded.
  46  | 
  47  |     // Wait for form to appear
  48  |     await page.waitForTimeout(500);
  49  | 
  50  |     // Check if document type selector exists (using id instead of name)
  51  |     const typeSelector = page.locator('select#document-type');
  52  |     await expect(typeSelector).toBeVisible();
  53  | 
  54  |     // Verify document types are loaded
  55  |     const options = await typeSelector.locator('option').allTextContents();
  56  |     expect(options.length).toBeGreaterThan(0);
  57  |     // Check for "Specification" in the text (may include priority info)
  58  |     const hasSpec = options.some(opt => opt.includes('Specification'));
  59  |     expect(hasSpec).toBeTruthy();
  60  |   });
  61  | 
  62  |   test('should list existing documents', async ({ page }) => {
  63  |     // Wait for documents to load
  64  |     await page.waitForTimeout(1000);
  65  | 
  66  |     // Check if document list exists
  67  |     const documentList = page.locator('.document-list, .documents-table, [data-testid="document-list"]');
  68  | 
  69  |     // Should have at least some documents (from previous uploads)
  70  |     const documentItems = page.locator('.document-card, [data-testid="document-item"]');
  71  |     const count = await documentItems.count();
  72  | 
  73  |     console.log(`Found ${count} documents in the list`);
  74  |     expect(count).toBeGreaterThanOrEqual(0);
  75  |   });
  76  | 
  77  |   test('should filter documents by type', async ({ page }) => {
  78  |     // Find filter dropdown (the one in the documents section, not upload section)
  79  |     const filterDropdown = page.locator('.filter-controls select');
  80  | 
  81  |     if (await filterDropdown.isVisible()) {
  82  |       // Select "spec" type by value
  83  |       await filterDropdown.selectOption('spec');
  84  | 
  85  |       // Wait for filtered results
  86  |       await page.waitForTimeout(500);
  87  | 
  88  |       // Verify filtered results
  89  |       const documentItems = page.locator('.document-card');
  90  |       const count = await documentItems.count();
  91  | 
  92  |       console.log(`Found ${count} spec documents`);
  93  |       expect(count).toBeGreaterThanOrEqual(0);
  94  |     }
  95  |   });
  96  | 
  97  |   test('should upload a new document', async ({ page }) => {
  98  |     // Find file input
  99  |     const fileInput = page.locator('input[type="file"]');
  100 |     await expect(fileInput).toBeAttached();
  101 | 
  102 |     // Upload file
  103 |     await fileInput.setInputFiles(testPdfPath);
  104 | 
  105 |     // Wait for form to appear
  106 |     await page.waitForTimeout(500);
  107 | 
  108 |     // Select document type using the correct id selector
  109 |     const typeSelector = page.locator('select#document-type');
  110 |     await expect(typeSelector).toBeVisible();
  111 |     await typeSelector.selectOption('spec');
  112 | 
  113 |     // Click upload button
  114 |     const uploadButton = page.locator('button').filter({ hasText: /Upload|Submit/ }).first();
  115 |     await uploadButton.click();
  116 | 
  117 |     // Wait for upload to start - look for "Uploading" or "Processing" message
  118 |     const processingMessage = page.locator('.status-message.processing, [role="alert"]').filter({ hasText: /uploading|processing/i });
  119 |     await expect(processingMessage).toBeVisible({ timeout: 10000 });
  120 | 
  121 |     // Note: Full document processing can take 10+ minutes for large PDFs with MinerU
  122 |     // We just verify the upload started successfully, not that it completed
  123 |     console.log('Upload started successfully. Full processing happens in background.');
  124 |   });
  125 | 
  126 |   test('should search uploaded documents', async ({ page }) => {
  127 |     // Navigate to search/analyze page
  128 |     await page.goto('http://localhost:5173');
  129 | 
  130 |     // Find search input
  131 |     const searchInput = page.locator('input[type="text"], input[placeholder*="search"], textarea').first();
  132 | 
  133 |     if (await searchInput.isVisible()) {
  134 |       // Search for PCIe related content
  135 |       await searchInput.fill('PCIe firmware specification');
  136 | 
  137 |       // Click search button
  138 |       const searchButton = page.locator('button').filter({ hasText: /Search|Analyze|Submit/ }).first();
  139 |       await searchButton.click();
  140 | 
  141 |       // Wait for results
  142 |       await page.waitForTimeout(2000);
  143 | 
  144 |       // Check if results contain uploaded documents
  145 |       const resultsArea = page.locator('.search-results, .results, [data-testid="results"]');
```