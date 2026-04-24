/**
 * E2E Test: Complete workflow
 * 1. Configure LM Studio model
 * 2. Upload NVMe Spec document
 * 3. Chat with the document
 */

import { test, expect } from '@playwright/test';
import path from 'path';

const BASE_URL = 'http://localhost:5173';
const API_URL = 'http://127.0.0.1:8787';

test.describe('Full E2E Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to home page
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
  });

  test('Step 1: Configure LM Studio model', async ({ page }) => {
    // Navigate to Model Config page
    await page.click('a[href="/model-config"]');
    await expect(page).toHaveURL(`${BASE_URL}/model-config`);

    // Wait for page to load (Chinese text: 模型配置)
    await page.waitForSelector('h1:has-text("模型配置")', { timeout: 10000 });

    // Click on "本地模型" (Local Model) card
    await page.click('text=本地模型');

    // Select LM Studio from provider dropdown
    await page.selectOption('select', 'lm-studio');

    // Fill in model name
    await page.fill('input[placeholder*="输入模型名称"]', 'qwen2.5-4b-instruct');

    // Base URL should be auto-filled, but verify/update if needed
    const baseUrlInput = page.locator('input[placeholder*="http://localhost:1234"]');
    await baseUrlInput.fill('http://localhost:1234/v1');

    // Save configuration (Chinese text: 保存配置)
    await page.click('button:has-text("保存配置")');

    // Wait for success alert (Chinese: 配置已保存)
    page.once('dialog', dialog => {
      expect(dialog.message()).toContain('配置已保存');
      dialog.accept();
    });

    await page.waitForTimeout(1000);
  });

  test('Step 2: Upload document', async ({ page }) => {
    // Navigate to Documents page
    await page.click('a[href="/documents"]');
    await expect(page).toHaveURL(`${BASE_URL}/documents`);

    // Wait for page to load
    await page.waitForSelector('text=Document Management', { timeout: 10000 });

    // Prepare test PDF file path
    const testPdfPath = path.join(process.cwd(), 'tests', 'fixtures', 'test_document.pdf');

    // Upload file via file input
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testPdfPath);

    // Select document type (spec, policy, or other)
    await page.selectOption('select', 'spec');

    // Click upload button
    await page.click('button:has-text("Upload")');

    // Wait for upload to start
    await page.waitForSelector('text=/Uploading|Processing|uploaded/', { timeout: 10000 });

    // Wait for processing to complete (async processing with polling)
    await page.waitForSelector('text=/successfully|indexed/', { timeout: 120000 });

    // Verify document appears in list
    await expect(page.locator('text=test_document').first()).toBeVisible({ timeout: 5000 });
  });

  test('Step 3: Chat with document', async ({ page }) => {
    // Listen to console logs
    page.on('console', msg => console.log('BROWSER:', msg.text()));

    // Navigate to Chat page
    await page.click('a[href="/chat"]');
    await expect(page).toHaveURL(`${BASE_URL}/chat`);

    // Wait for page to load
    await page.waitForSelector('h1:has-text("Chat")', { timeout: 10000 });

    // Wait a bit for React Query to fetch data
    await page.waitForTimeout(2000);

    // Check what options are available
    const options = await page.locator('select option').allTextContents();
    console.log('Available options:', options);

    // Wait for data sources to load
    await page.waitForSelector('select option:not([value=""])', { timeout: 10000 });

    // Select first available data source
    const sourceSelect = page.locator('select');
    await sourceSelect.selectOption({ index: 1 }); // Index 0 is "-- 请选择 --"

    // Type a question
    const questionInput = page.locator('input[type="text"]');
    await questionInput.fill('What is NVMe?');

    // Send message
    await page.click('button:has-text("Send"), button >> svg');

    // Wait for response (may take a while if LM Studio is running)
    await page.waitForSelector('text=/NVMe|思考中/', { timeout: 60000 });

    // Verify at least one message appears (user message)
    const messages = page.locator('.chat-messages > div');
    await expect(messages.first()).toBeVisible();
  });

  test('Complete workflow: Model Config -> Upload -> Chat', async ({ page }) => {
    // Step 1: Configure model
    await page.click('a[href="/model-config"]');
    await page.waitForSelector('h1:has-text("模型配置")');
    await page.click('text=本地模型');
    await page.selectOption('select', 'lm-studio');
    await page.fill('input[placeholder*="输入模型名称"]', 'qwen2.5-4b-instruct');
    await page.locator('input[placeholder*="http://localhost:1234"]').fill('http://localhost:1234/v1');

    // Handle alert dialog
    page.once('dialog', dialog => dialog.accept());
    await page.click('button:has-text("保存配置")');
    await page.waitForTimeout(1000);

    // Step 2: Upload document
    await page.click('a[href="/documents"]');
    await page.waitForSelector('text=Document Management');

    // Check if document already exists
    const existingDoc = page.locator('text=test_document');
    const docExists = await existingDoc.isVisible().catch(() => false);

    if (!docExists) {
      const testPdfPath = path.join(process.cwd(), 'tests', 'fixtures', 'test_document.pdf');
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(testPdfPath);
      await page.selectOption('select', 'spec');
      await page.click('button:has-text("Upload")');
      await page.waitForSelector('text=/successfully|indexed/', { timeout: 120000 });
    }

    // Step 3: Chat
    await page.click('a[href="/chat"]');
    await page.waitForSelector('h1:has-text("Chat")');

    // Select data source
    await page.waitForSelector('select option:not([value=""])', { timeout: 10000 });
    const sourceSelect = page.locator('select');
    await sourceSelect.selectOption({ index: 1 });

    // Ask question
    const questionInput = page.locator('input[type="text"]');
    await questionInput.fill('What is NVMe?');
    await page.click('button:has-text("Send"), button >> svg');

    // Wait for response
    await page.waitForSelector('text=/NVMe|思考中/', { timeout: 60000 });
  });
});

test.describe('API Health Checks', () => {
  test('Backend API is running', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/health`);
    expect(response.ok()).toBeTruthy();
  });

  test('Model config API works', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/model-config`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data).toHaveProperty('config');
  });

  test('Documents API works', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/documents/types`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.types).toHaveProperty('spec');
  });
});
