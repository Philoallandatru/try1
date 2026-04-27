# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: document-management.spec.ts >> Document Management E2E >> should search uploaded documents
- Location: e2e\document-management.spec.ts:126:3

# Error details

```
Test timeout of 1860000ms exceeded.
```

```
Error: locator.click: Test timeout of 1860000ms exceeded.
Call log:
  - waiting for locator('button').filter({ hasText: /Search|Analyze|Submit/ }).first()

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
        - textbox "Message Knowledge Portal..." [active] [ref=e43]: PCIe firmware specification
        - button "↑" [ref=e44] [cursor=pointer]
```

# Test source

```ts
  39  |     await page.waitForLoadState('networkidle');
  40  |   });
  41  | 
  42  |   test('should load document types', async ({ page }) => {
  43  |     // First select a file to make the upload form visible
  44  |     const fileInput = page.locator('input[type="file"]');
  45  |     await fileInput.setInputFiles(testPdfPath);
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
> 139 |       await searchButton.click();
      |                          ^ Error: locator.click: Test timeout of 1860000ms exceeded.
  140 | 
  141 |       // Wait for results
  142 |       await page.waitForTimeout(2000);
  143 | 
  144 |       // Check if results contain uploaded documents
  145 |       const resultsArea = page.locator('.search-results, .results, [data-testid="results"]');
  146 |       const hasResults = await resultsArea.isVisible();
  147 | 
  148 |       if (hasResults) {
  149 |         const resultText = await resultsArea.textContent();
  150 |         console.log('Search results:', resultText?.substring(0, 200));
  151 |       }
  152 |     }
  153 |   });
  154 | 
  155 |   test('should verify document appears in search with correct metadata', async ({ page }) => {
  156 |     // Make API call to search
  157 |     const response = await page.request.post('http://localhost:8787/api/retrieval/search', {
  158 |       data: {
  159 |         query: 'PCI firmware',
  160 |         top_k: 10,
  161 |         document_types: ['spec']
  162 |       }
  163 |     });
  164 | 
  165 |     expect(response.ok()).toBeTruthy();
  166 |     const data = await response.json();
  167 | 
  168 |     expect(data.status).toBe('success');
  169 |     expect(data.total_results).toBeGreaterThan(0);
  170 | 
  171 |     // Verify results have proper metadata
  172 |     const firstResult = data.results[0];
  173 |     expect(firstResult).toHaveProperty('doc_id');
  174 |     expect(firstResult).toHaveProperty('title');
  175 |     expect(firstResult).toHaveProperty('score');
  176 |     expect(firstResult.metadata).toHaveProperty('document_type');
  177 |     expect(firstResult.metadata.document_type).toBe('spec');
  178 | 
  179 |     console.log('First search result:', {
  180 |       title: firstResult.title,
  181 |       score: firstResult.score,
  182 |       doc_type: firstResult.metadata.document_type
  183 |     });
  184 |   });
  185 | });
  186 | 
```