import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Data Source Management
 *
 * Test Coverage:
 * 1. File data source selection and parsing
 * 2. Jira data source configuration
 * 3. Confluence data source configuration
 * 4. Profile configuration and management
 * 5. Jira deep analysis workflow
 */

const BASE_URL = 'http://localhost:5173';
const API_URL = 'http://localhost:8787';

test.describe('Data Source Management', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to home page
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test.describe('File Data Source', () => {
    test('should upload and parse PDF document', async ({ page }) => {
      // Navigate to data source page
      await page.click('text=数据源');
      await expect(page).toHaveURL(/.*data-source/);

      // Wait for page to load
      await page.waitForSelector('h1:has-text("数据源配置")');

      // Click on file upload option
      await page.click('text=文件上传');

      // Upload a test PDF file
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles('tests/fixtures/test_document.pdf');

      // Select document type
      await page.selectOption('select[name="document_type"]', 'spec');

      // Optional: Set display name
      await page.fill('input[name="display_name"]', '测试规格文档');

      // Submit upload
      await page.click('button:has-text("上传")');

      // Wait for upload success message
      await expect(page.locator('text=上传成功')).toBeVisible({ timeout: 10000 });

      // Wait for background processing
      await page.waitForTimeout(2000);

      // Verify document appears in list
      await page.click('text=文档列表');
      await expect(page.locator('text=测试规格文档')).toBeVisible();
    });

    test('should display parsing results', async ({ page }) => {
      // Navigate to documents page
      await page.goto(`${BASE_URL}/documents`);

      // Wait for documents to load
      await page.waitForSelector('.document-list');

      // Click on a document to view details
      await page.click('.document-item:first-child');

      // Verify parsing results are displayed
      await expect(page.locator('.document-content')).toBeVisible();
      await expect(page.locator('.content-blocks')).toBeVisible();

      // Check for different content block types
      const hasText = await page.locator('.block-type-text').count() > 0;
      const hasTable = await page.locator('.block-type-table').count() > 0;
      const hasImage = await page.locator('.block-type-image').count() > 0;

      expect(hasText || hasTable || hasImage).toBeTruthy();
    });

    test('should filter documents by type', async ({ page }) => {
      await page.goto(`${BASE_URL}/documents`);

      // Select document type filter
      await page.selectOption('select[name="document_type"]', 'spec');

      // Wait for filtered results
      await page.waitForTimeout(1000);

      // Verify only spec documents are shown
      const documents = page.locator('.document-item');
      const count = await documents.count();

      for (let i = 0; i < count; i++) {
        const docType = await documents.nth(i).getAttribute('data-type');
        expect(docType).toBe('spec');
      }
    });
  });

  test.describe('Jira Data Source Configuration', () => {
    test('should configure Jira data source', async ({ page }) => {
      // Navigate to data source configuration
      await page.goto(`${BASE_URL}/data-source`);
      await page.waitForSelector('h1:has-text("数据源配置")');

      // Click on Jira configuration
      await page.click('text=Jira');

      // Fill in Jira configuration
      await page.fill('input[name="jira_url"]', 'https://your-domain.atlassian.net');
      await page.fill('input[name="jira_email"]', 'test@example.com');
      await page.fill('input[name="jira_api_token"]', 'test-api-token');

      // Test connection
      await page.click('button:has-text("测试连接")');

      // Wait for connection test result
      await expect(page.locator('text=连接成功')).toBeVisible({ timeout: 10000 });

      // Save configuration
      await page.click('button:has-text("保存配置")');

      // Verify success message
      await expect(page.locator('text=配置已保存')).toBeVisible();
    });

    test('should configure JQL query', async ({ page }) => {
      await page.goto(`${BASE_URL}/data-source`);
      await page.click('text=Jira');

      // Navigate to JQL configuration
      await page.click('text=JQL 查询');

      // Enter JQL query
      const jqlQuery = 'project = TEST AND status = "In Progress"';
      await page.fill('textarea[name="jql_query"]', jqlQuery);

      // Validate JQL
      await page.click('button:has-text("验证 JQL")');

      // Wait for validation result
      await expect(page.locator('text=JQL 有效')).toBeVisible({ timeout: 5000 });

      // Preview results
      await page.click('button:has-text("预览结果")');

      // Verify preview shows issues
      await expect(page.locator('.jira-issue-preview')).toBeVisible();
      const issueCount = await page.locator('.jira-issue-item').count();
      expect(issueCount).toBeGreaterThan(0);

      // Save JQL query
      await page.click('button:has-text("保存查询")');
      await expect(page.locator('text=查询已保存')).toBeVisible();
    });

    test('should configure Jira field mapping', async ({ page }) => {
      await page.goto(`${BASE_URL}/data-source/jira/field-mapping`);

      // Map custom fields
      await page.selectOption('select[name="priority_field"]', 'customfield_10001');
      await page.selectOption('select[name="severity_field"]', 'customfield_10002');
      await page.selectOption('select[name="component_field"]', 'components');

      // Save field mapping
      await page.click('button:has-text("保存映射")');
      await expect(page.locator('text=字段映射已保存')).toBeVisible();
    });
  });

  test.describe('Confluence Data Source Configuration', () => {
    test('should configure Confluence data source', async ({ page }) => {
      await page.goto(`${BASE_URL}/data-source`);
      await page.waitForSelector('h1:has-text("数据源配置")');

      // Click on Confluence configuration
      await page.click('text=Confluence');

      // Fill in Confluence configuration
      await page.fill('input[name="confluence_url"]', 'https://your-domain.atlassian.net/wiki');
      await page.fill('input[name="confluence_email"]', 'test@example.com');
      await page.fill('input[name="confluence_api_token"]', 'test-api-token');

      // Test connection
      await page.click('button:has-text("测试连接")');
      await expect(page.locator('text=连接成功')).toBeVisible({ timeout: 10000 });

      // Save configuration
      await page.click('button:has-text("保存配置")');
      await expect(page.locator('text=配置已保存')).toBeVisible();
    });

    test('should configure Confluence space selection', async ({ page }) => {
      await page.goto(`${BASE_URL}/data-source/confluence`);

      // Select space
      await page.click('button:has-text("选择空间")');

      // Wait for space list to load
      await page.waitForSelector('.space-list');

      // Select a space
      await page.click('.space-item:has-text("TEST")');

      // Configure page selection
      await page.click('text=页面选择');

      // Option 1: Select specific pages
      await page.click('input[type="radio"][value="specific"]');
      await page.fill('input[name="page_ids"]', '123456,789012');

      // Option 2: Select by label
      // await page.click('input[type="radio"][value="label"]');
      // await page.fill('input[name="label"]', 'documentation');

      // Option 3: Select entire space
      // await page.click('input[type="radio"][value="space"]');

      // Save selection
      await page.click('button:has-text("保存选择")');
      await expect(page.locator('text=选择已保存')).toBeVisible();
    });

    test('should configure CQL query', async ({ page }) => {
      await page.goto(`${BASE_URL}/data-source/confluence`);

      // Navigate to CQL configuration
      await page.click('text=CQL 查询');

      // Enter CQL query
      const cqlQuery = 'space = TEST AND label = "api-docs"';
      await page.fill('textarea[name="cql_query"]', cqlQuery);

      // Validate CQL
      await page.click('button:has-text("验证 CQL")');
      await expect(page.locator('text=CQL 有效')).toBeVisible({ timeout: 5000 });

      // Preview results
      await page.click('button:has-text("预览结果")');
      await expect(page.locator('.confluence-page-preview')).toBeVisible();

      // Save CQL query
      await page.click('button:has-text("保存查询")');
      await expect(page.locator('text=查询已保存')).toBeVisible();
    });
  });

  test.describe('Profile Configuration', () => {
    test('should create a new profile', async ({ page }) => {
      // Navigate to profile management
      await page.goto(`${BASE_URL}/profiles`);
      await page.waitForSelector('h1:has-text("配置文件")');

      // Click create new profile
      await page.click('button:has-text("新建配置")');

      // Fill in profile details
      await page.fill('input[name="profile_name"]', 'test-profile');
      await page.fill('input[name="description"]', '测试配置文件');

      // Configure LLM settings
      await page.selectOption('select[name="llm_provider"]', 'openai');
      await page.fill('input[name="api_key"]', 'sk-test-key');
      await page.fill('input[name="model"]', 'gpt-4');
      await page.fill('input[name="temperature"]', '0.7');
      await page.fill('input[name="max_tokens"]', '2000');

      // Save profile
      await page.click('button:has-text("保存")');

      // Verify success
      await expect(page.locator('text=配置已创建')).toBeVisible();
      await expect(page.locator('text=test-profile')).toBeVisible();
    });

    test('should edit existing profile', async ({ page }) => {
      await page.goto(`${BASE_URL}/profiles`);

      // Select a profile to edit
      await page.click('.profile-item:first-child .edit-button');

      // Update profile settings
      await page.fill('input[name="temperature"]', '0.5');
      await page.fill('input[name="max_tokens"]', '3000');

      // Add system prompt
      await page.fill('textarea[name="system_prompt"]', '你是一个专业的技术分析助手。');

      // Save changes
      await page.click('button:has-text("保存更改")');

      // Verify update
      await expect(page.locator('text=配置已更新')).toBeVisible();
    });

    test('should configure retrieval settings in profile', async ({ page }) => {
      await page.goto(`${BASE_URL}/profiles`);
      await page.click('.profile-item:first-child .edit-button');

      // Navigate to retrieval settings tab
      await page.click('text=检索设置');

      // Configure retrieval strategy
      await page.selectOption('select[name="retrieval_strategy"]', 'hybrid');
      await page.fill('input[name="top_k"]', '10');
      await page.fill('input[name="similarity_threshold"]', '0.7');

      // Configure reranking
      await page.check('input[name="enable_reranking"]');
      await page.selectOption('select[name="reranker_model"]', 'cross-encoder');

      // Configure chunking
      await page.fill('input[name="chunk_size"]', '512');
      await page.fill('input[name="chunk_overlap"]', '50');

      // Save retrieval settings
      await page.click('button:has-text("保存设置")');
      await expect(page.locator('text=检索设置已保存')).toBeVisible();
    });

    test('should configure prompt templates in profile', async ({ page }) => {
      await page.goto(`${BASE_URL}/profiles`);
      await page.click('.profile-item:first-child .edit-button');

      // Navigate to prompt templates tab
      await page.click('text=提示词模板');

      // Configure analysis prompt
      await page.fill('textarea[name="analysis_prompt"]', `
分析以下 Jira 问题：
问题: {issue_key}
描述: {description}
请提供详细的分析和建议。
      `.trim());

      // Configure summary prompt
      await page.fill('textarea[name="summary_prompt"]', `
总结以下内容：
{content}
请用简洁的语言概括要点。
      `.trim());

      // Configure recommendation prompt
      await page.fill('textarea[name="recommendation_prompt"]', `
基于以下信息提供建议：
{context}
请给出可行的解决方案。
      `.trim());

      // Save templates
      await page.click('button:has-text("保存模板")');
      await expect(page.locator('text=模板已保存')).toBeVisible();
    });

    test('should set default profile', async ({ page }) => {
      await page.goto(`${BASE_URL}/profiles`);

      // Find a profile and set as default
      await page.click('.profile-item:has-text("test-profile") .set-default-button');

      // Verify default status
      await expect(page.locator('.profile-item:has-text("test-profile") .default-badge')).toBeVisible();
      await expect(page.locator('text=默认配置已设置')).toBeVisible();
    });

    test('should duplicate profile', async ({ page }) => {
      await page.goto(`${BASE_URL}/profiles`);

      // Duplicate a profile
      await page.click('.profile-item:first-child .duplicate-button');

      // Enter new profile name
      await page.fill('input[name="new_profile_name"]', 'test-profile-copy');

      // Confirm duplication
      await page.click('button:has-text("确认复制")');

      // Verify new profile exists
      await expect(page.locator('text=配置已复制')).toBeVisible();
      await expect(page.locator('text=test-profile-copy')).toBeVisible();
    });

    test('should validate profile configuration', async ({ page }) => {
      await page.goto(`${BASE_URL}/profiles`);
      await page.click('.profile-item:first-child .edit-button');

      // Click validate button
      await page.click('button:has-text("验证配置")');

      // Wait for validation
      await expect(page.locator('.validation-progress')).toBeVisible();

      // Check validation results
      await expect(page.locator('.validation-results')).toBeVisible({ timeout: 10000 });

      // Verify different validation checks
      await expect(page.locator('.validation-item:has-text("API 连接")')).toBeVisible();
      await expect(page.locator('.validation-item:has-text("模型可用性")')).toBeVisible();
      await expect(page.locator('.validation-item:has-text("提示词格式")')).toBeVisible();
    });

    test('should delete profile', async ({ page }) => {
      await page.goto(`${BASE_URL}/profiles`);

      // Get initial profile count
      const initialCount = await page.locator('.profile-item').count();

      // Delete a profile (not the default one)
      await page.click('.profile-item:not(:has(.default-badge)) .delete-button');

      // Confirm deletion
      await page.click('button:has-text("确认删除")');

      // Verify deletion
      await expect(page.locator('text=配置已删除')).toBeVisible();

      // Verify count decreased
      const newCount = await page.locator('.profile-item').count();
      expect(newCount).toBe(initialCount - 1);
    });

    test('should export and import profile', async ({ page }) => {
      await page.goto(`${BASE_URL}/profiles`);

      // Export profile
      await page.click('.profile-item:first-child .export-button');
      const downloadPromise = page.waitForEvent('download');
      await page.click('button:has-text("导出配置")');
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/profile.*\.json/);

      // Import profile
      await page.click('button:has-text("导入配置")');
      const fileInput = page.locator('input[type="file"][accept=".json"]');
      await fileInput.setInputFiles(await download.path());

      // Confirm import
      await page.click('button:has-text("确认导入")');
      await expect(page.locator('text=配置已导入')).toBeVisible();
    });
  });

  test.describe('Jira Deep Analysis', () => {
    test('should perform basic Jira analysis', async ({ page }) => {
      // Navigate to analysis page
      await page.goto(`${BASE_URL}/analyze`);
      await page.waitForSelector('h1:has-text("分析")');

      // Select Jira as data source
      await page.selectOption('select[name="data_source"]', 'jira');

      // Enter Jira issue key
      await page.fill('input[name="issue_key"]', 'TEST-123');

      // Start analysis
      await page.click('button:has-text("开始分析")');

      // Wait for analysis to complete
      await expect(page.locator('text=分析完成')).toBeVisible({ timeout: 60000 });

      // Verify analysis results are displayed
      await expect(page.locator('.analysis-results')).toBeVisible();
      await expect(page.locator('.issue-summary')).toBeVisible();
      await expect(page.locator('.issue-details')).toBeVisible();
    });

    test('should perform deep analysis with related issues', async ({ page }) => {
      await page.goto(`${BASE_URL}/analyze`);

      // Select Jira data source
      await page.selectOption('select[name="data_source"]', 'jira');
      await page.fill('input[name="issue_key"]', 'TEST-123');

      // Enable deep analysis options
      await page.check('input[name="include_related"]');
      await page.check('input[name="include_subtasks"]');
      await page.check('input[name="include_links"]');

      // Set analysis depth
      await page.selectOption('select[name="depth"]', '2');

      // Start deep analysis
      await page.click('button:has-text("深度分析")');

      // Wait for analysis with progress indicator
      await expect(page.locator('.analysis-progress')).toBeVisible();
      await expect(page.locator('text=正在分析')).toBeVisible();

      // Wait for completion
      await expect(page.locator('text=分析完成')).toBeVisible({ timeout: 120000 });

      // Verify deep analysis results
      await expect(page.locator('.related-issues')).toBeVisible();
      await expect(page.locator('.issue-graph')).toBeVisible();
      await expect(page.locator('.dependency-tree')).toBeVisible();

      // Check for related issues
      const relatedCount = await page.locator('.related-issue-item').count();
      expect(relatedCount).toBeGreaterThan(0);
    });

    test('should analyze Jira issue with AI insights', async ({ page }) => {
      await page.goto(`${BASE_URL}/analyze`);

      // Configure analysis
      await page.selectOption('select[name="data_source"]', 'jira');
      await page.fill('input[name="issue_key"]', 'TEST-123');

      // Enable AI analysis
      await page.check('input[name="enable_ai"]');

      // Select AI analysis options
      await page.check('input[name="ai_summary"]');
      await page.check('input[name="ai_recommendations"]');
      await page.check('input[name="ai_risk_assessment"]');

      // Start analysis
      await page.click('button:has-text("AI 分析")');

      // Wait for AI analysis
      await expect(page.locator('text=AI 分析中')).toBeVisible();
      await expect(page.locator('text=分析完成')).toBeVisible({ timeout: 120000 });

      // Verify AI insights
      await expect(page.locator('.ai-summary')).toBeVisible();
      await expect(page.locator('.ai-recommendations')).toBeVisible();
      await expect(page.locator('.risk-assessment')).toBeVisible();

      // Check for specific AI-generated content
      const summaryText = await page.locator('.ai-summary').textContent();
      expect(summaryText).toBeTruthy();
      expect(summaryText!.length).toBeGreaterThan(50);
    });

    test('should export analysis results', async ({ page }) => {
      await page.goto(`${BASE_URL}/analyze`);

      // Perform analysis first
      await page.selectOption('select[name="data_source"]', 'jira');
      await page.fill('input[name="issue_key"]', 'TEST-123');
      await page.click('button:has-text("开始分析")');
      await expect(page.locator('text=分析完成')).toBeVisible({ timeout: 60000 });

      // Export results
      await page.click('button:has-text("导出")');

      // Select export format
      await page.click('text=PDF');

      // Wait for download
      const downloadPromise = page.waitForEvent('download');
      await page.click('button:has-text("确认导出")');
      const download = await downloadPromise;

      // Verify download
      expect(download.suggestedFilename()).toMatch(/analysis.*\.pdf/);
    });

    test('should handle analysis errors gracefully', async ({ page }) => {
      await page.goto(`${BASE_URL}/analyze`);

      // Try to analyze with invalid issue key
      await page.selectOption('select[name="data_source"]', 'jira');
      await page.fill('input[name="issue_key"]', 'INVALID-999999');
      await page.click('button:has-text("开始分析")');

      // Verify error message is displayed
      await expect(page.locator('text=问题不存在')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('.error-message')).toBeVisible();

      // Verify user can retry
      await expect(page.locator('button:has-text("重试")')).toBeVisible();
    });
  });

  test.describe('Complete Workflow: Data Source to Analysis', () => {
    test('should complete full workflow from configuration to analysis', async ({ page }) => {
      // Step 1: Configure Jira data source
      await page.goto(`${BASE_URL}/data-source`);
      await page.click('text=Jira');
      await page.fill('input[name="jira_url"]', 'https://your-domain.atlassian.net');
      await page.fill('input[name="jira_email"]', 'test@example.com');
      await page.fill('input[name="jira_api_token"]', 'test-api-token');
      await page.click('button:has-text("保存配置")');
      await expect(page.locator('text=配置已保存')).toBeVisible();

      // Step 2: Upload a document
      await page.goto(`${BASE_URL}/documents`);
      await page.click('button:has-text("上传文档")');
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles('tests/fixtures/test_document.pdf');
      await page.selectOption('select[name="document_type"]', 'spec');
      await page.click('button:has-text("上传")');
      await expect(page.locator('text=上传成功')).toBeVisible({ timeout: 10000 });

      // Step 3: Perform Jira analysis
      await page.goto(`${BASE_URL}/analyze`);
      await page.selectOption('select[name="data_source"]', 'jira');
      await page.fill('input[name="issue_key"]', 'TEST-123');
      await page.check('input[name="include_related"]');
      await page.check('input[name="enable_ai"]');
      await page.click('button:has-text("深度分析")');

      // Wait for analysis
      await expect(page.locator('text=分析完成')).toBeVisible({ timeout: 120000 });

      // Step 4: Verify comprehensive results
      await expect(page.locator('.issue-summary')).toBeVisible();
      await expect(page.locator('.related-issues')).toBeVisible();
      await expect(page.locator('.ai-summary')).toBeVisible();
      await expect(page.locator('.document-references')).toBeVisible();

      // Step 5: Export results
      await page.click('button:has-text("导出")');
      await page.click('text=PDF');
      const downloadPromise = page.waitForEvent('download');
      await page.click('button:has-text("确认导出")');
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/analysis.*\.pdf/);
    });
  });
});

test.describe('API Health Checks for Data Sources', () => {
  test('should verify data source API endpoints', async ({ request }) => {
    // Check documents API
    const documentsResponse = await request.get(`${API_URL}/api/documents/list?workspace=demo`);
    expect(documentsResponse.ok()).toBeTruthy();

    // Check document types API
    const typesResponse = await request.get(`${API_URL}/api/documents/types`);
    expect(typesResponse.ok()).toBeTruthy();
    const types = await typesResponse.json();
    expect(types.types).toBeDefined();

    // Check workspace sources API
    const sourcesResponse = await request.get(`${API_URL}/api/workspace/sources?workspace_dir=demo`);
    expect(sourcesResponse.ok()).toBeTruthy();
  });

  test('should verify Jira analysis API', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/workspace/analyze-jira`, {
      data: {
        workspace_dir: 'demo',
        issue_key: 'TEST-123',
        include_related: true,
        depth: 2,
      },
    });

    // May fail if Jira not configured, but should return proper error
    if (!response.ok()) {
      const error = await response.json();
      expect(error.detail).toBeDefined();
    }
  });
});
