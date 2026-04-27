# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: search.spec.ts >> Search Page E2E Tests >> should navigate back to home page
- Location: e2e\search.spec.ts:120:3

# Error details

```
Test timeout of 1860000ms exceeded.
```

```
Error: locator.click: Test timeout of 1860000ms exceeded.
Call log:
  - waiting for locator('a').filter({ hasText: 'Analyze' })

```

# Test source

```ts
  23  |   test('should perform search and display results', async ({ page }) => {
  24  |     // Wait for index to be ready
  25  |     const searchInput = page.locator('[data-testid="search-input"]');
  26  | 
  27  |     // Check if input is enabled (index is ready)
  28  |     const isDisabled = await searchInput.isDisabled();
  29  | 
  30  |     if (!isDisabled) {
  31  |       // Enter search query
  32  |       await searchInput.fill('test');
  33  | 
  34  |       // Click search button
  35  |       const searchButton = page.locator('[data-testid="search-button"]');
  36  |       await searchButton.click();
  37  | 
  38  |       // Wait for results or empty state
  39  |       await page.waitForTimeout(1000);
  40  | 
  41  |       // Check if results are displayed or "no results" message
  42  |       const hasResults = await page.locator('[data-testid="search-results"]').count() > 0;
  43  |       const hasEmptyState = await page.locator('.empty-state').count() > 0;
  44  | 
  45  |       expect(hasResults || hasEmptyState).toBeTruthy();
  46  |     }
  47  |   });
  48  | 
  49  |   test('should handle empty search query', async ({ page }) => {
  50  |     // Search button should be disabled when query is empty
  51  |     const searchButton = page.locator('[data-testid="search-button"]');
  52  | 
  53  |     // Verify page doesn't crash
  54  |     await expect(page.locator('h2')).toContainText('Knowledge Retrieval');
  55  |   });
  56  | 
  57  |   test('should display search results with highlights', async ({ page }) => {
  58  |     const searchInput = page.locator('[data-testid="search-input"]');
  59  |     const isDisabled = await searchInput.isDisabled();
  60  | 
  61  |     if (!isDisabled) {
  62  |       // Perform search
  63  |       await searchInput.fill('test');
  64  | 
  65  |       const searchButton = page.locator('[data-testid="search-button"]');
  66  |       await searchButton.click();
  67  | 
  68  |       await page.waitForTimeout(1000);
  69  | 
  70  |       // Check if highlights are present (if results exist)
  71  |       const resultsExist = await page.locator('[data-testid="search-results"]').count() > 0;
  72  | 
  73  |       if (resultsExist) {
  74  |         // Highlights should be present as <mark> tags
  75  |         const highlights = page.locator('mark');
  76  |         const highlightCount = await highlights.count();
  77  |         console.log(`Found ${highlightCount} highlights`);
  78  |       }
  79  |     }
  80  |   });
  81  | 
  82  |   test('should show loading state during search', async ({ page }) => {
  83  |     const searchInput = page.locator('[data-testid="search-input"]');
  84  |     const isDisabled = await searchInput.isDisabled();
  85  | 
  86  |     if (!isDisabled) {
  87  |       await searchInput.fill('query');
  88  | 
  89  |       const searchButton = page.locator('[data-testid="search-button"]');
  90  | 
  91  |       // Check button state before click
  92  |       await expect(searchButton).toBeEnabled();
  93  | 
  94  |       // Start search
  95  |       await searchButton.click();
  96  | 
  97  |       // Verify page doesn't crash
  98  |       await page.waitForTimeout(500);
  99  |       await expect(page.locator('h2')).toBeVisible();
  100 |     }
  101 |   });
  102 | 
  103 |   test('should handle Chinese search queries', async ({ page }) => {
  104 |     const searchInput = page.locator('[data-testid="search-input"]');
  105 |     const isDisabled = await searchInput.isDisabled();
  106 | 
  107 |     if (!isDisabled) {
  108 |       await searchInput.fill('机器学习');
  109 | 
  110 |       const searchButton = page.locator('[data-testid="search-button"]');
  111 |       await searchButton.click();
  112 | 
  113 |       await page.waitForTimeout(1000);
  114 | 
  115 |       // Verify page doesn't crash with Chinese input
  116 |       await expect(page.locator('h2')).toBeVisible();
  117 |     }
  118 |   });
  119 | 
  120 |   test('should navigate back to home page', async ({ page }) => {
  121 |     // Click on Analyze link in navigation
  122 |     const analyzeLink = page.locator('a').filter({ hasText: 'Analyze' });
> 123 |     await analyzeLink.click();
      |                       ^ Error: locator.click: Test timeout of 1860000ms exceeded.
  124 | 
  125 |     // Should navigate to home page
  126 |     await expect(page).toHaveURL('/');
  127 |     await expect(page.locator('h2')).toContainText(/Analyze|Jira/i);
  128 |   });
  129 | 
  130 |   test('should display document count', async ({ page }) => {
  131 |     // Look for document count display
  132 |     const docCount = page.locator('[data-testid="document-count"]');
  133 |     await expect(docCount).toBeVisible();
  134 |   });
  135 | });
  136 | 
```