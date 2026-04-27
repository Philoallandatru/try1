import { test, expect } from '@playwright/test';

test.describe('Data Sources Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://127.0.0.1:5183/data-sources');
    await page.waitForLoadState('networkidle');
  });

  test('should display page title and description', async ({ page }) => {
    await expect(page.locator('h2')).toContainText('数据源管理');
    await expect(page.getByText('管理 Jira、Confluence 和文件数据源')).toBeVisible();
  });

  test('should show add data source buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: '添加 Jira' }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: '添加 Confluence' }).first()).toBeVisible();
  });

  test('should open Jira modal when clicking add Jira button', async ({ page }) => {
    await page.getByRole('button', { name: '添加 Jira', exact: true }).click();

    // Modal should open with Jira-specific fields
    await expect(page.getByRole('heading', { name: '添加 Jira 数据源' })).toBeVisible();
    await expect(page.getByText('数据源名称')).toBeVisible();
    await expect(page.getByText('Base URL')).toBeVisible();
    await expect(page.getByText('Project Key')).toBeVisible();
  });

  test('should open Confluence modal when clicking add Confluence button', async ({ page }) => {
    await page.getByRole('button', { name: '添加 Confluence', exact: true }).click();

    // Modal should open with Confluence-specific fields
    await expect(page.getByRole('heading', { name: '添加 Confluence 数据源' })).toBeVisible();
    await expect(page.getByText('数据源名称')).toBeVisible();
    await expect(page.getByText('Base URL')).toBeVisible();
    await expect(page.getByText('Space Key')).toBeVisible();
  });

  test('should validate required fields in Jira form', async ({ page }) => {
    await page.getByRole('button', { name: '添加 Jira', exact: true }).first().click();

    // Clear all fields
    await page.locator('input[placeholder="my_jira"]').clear();
    await page.locator('input[placeholder="http://localhost:8888"]').clear();
    await page.locator('input[placeholder="mock-token"]').clear();

    // Try to submit without filling required fields
    await page.getByRole('button', { name: '创建数据源' }).click();

    // Form should show validation errors
    await expect(page.getByText('名称不能为空')).toBeVisible();
  });

  test('should add a Jira data source successfully', async ({ page }) => {
    await page.getByRole('button', { name: '添加 Jira', exact: true }).first().click();

    // Fill in the form
    const uniqueName = 'test_jira_' + Date.now();
    await page.locator('input[placeholder="my_jira"]').fill(uniqueName);
    await page.locator('input[placeholder="http://localhost:8888"]').fill('http://localhost:8888');
    await page.locator('input[placeholder="mock-token"]').fill('mock-token');

    // Submit form
    await page.getByRole('button', { name: '创建数据源' }).click();

    // Wait for success and modal to close
    await page.waitForTimeout(2000);

    // Modal should close
    await expect(page.getByRole('heading', { name: '添加 Jira 数据源' })).not.toBeVisible();

    // New data source should appear in the list
    await expect(page.getByText(uniqueName)).toBeVisible();
  });

  test('should add a Confluence data source successfully', async ({ page }) => {
    await page.getByRole('button', { name: '添加 Confluence', exact: true }).click();

    // Fill in the form
    const uniqueName = 'test_confluence_' + Date.now();
    await page.locator('input[placeholder="my_confluence"]').fill(uniqueName);
    await page.locator('input[placeholder="http://localhost:8888"]').fill('http://localhost:8888');
    await page.locator('input[placeholder="mock-token"]').fill('mock-token');

    // Submit form
    await page.getByRole('button', { name: '创建数据源' }).click();

    // Wait for success
    await page.waitForTimeout(2000);

    // Modal should close
    await expect(page.getByRole('heading', { name: '添加 Confluence 数据源' })).not.toBeVisible();

    // New data source should appear in the list
    await expect(page.getByText(uniqueName)).toBeVisible();
  });

  test('should close modal when clicking cancel', async ({ page }) => {
    await page.getByRole('button', { name: '添加 Jira', exact: true }).click();
    await expect(page.getByRole('heading', { name: '添加 Jira 数据源' })).toBeVisible();

    // Click cancel
    await page.getByRole('button', { name: '取消' }).click();

    // Modal should close
    await expect(page.getByRole('heading', { name: '添加 Jira 数据源' })).not.toBeVisible();
  });

  test('should display data sources when they exist', async ({ page }) => {
    // Check that data source sections are visible
    const jiraSection = page.getByRole('heading', { name: /Jira 数据源/ });
    const confluenceSection = page.getByRole('heading', { name: /Confluence 数据源/ });

    // At least one section should be visible (since previous tests created data sources)
    const jiraVisible = await jiraSection.isVisible();
    const confluenceVisible = await confluenceSection.isVisible();

    expect(jiraVisible || confluenceVisible).toBeTruthy();
  });

  test('should show delete button for existing data sources', async ({ page }) => {
    // First add a data source
    await page.getByRole('button', { name: '添加 Jira', exact: true }).click();
    const uniqueName = 'test_delete_' + Date.now();
    await page.locator('input[placeholder="my_jira"]').fill(uniqueName);
    await page.locator('input[placeholder="http://localhost:8888"]').fill('http://localhost:8888');
    await page.locator('input[placeholder="mock-token"]').fill('mock-token');
    await page.getByRole('button', { name: '创建数据源' }).click();
    await page.waitForTimeout(2000);

    // Find the data source card and check for delete button
    const card = page.locator('.config-item').filter({ hasText: uniqueName });
    await expect(card.getByRole('button', { name: '删除' })).toBeVisible();
  });

  test('should group data sources by type', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Jira 数据源/ })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Confluence 数据源/ })).toBeVisible();
  });

  test('should show help text for Mock Server', async ({ page }) => {
    await expect(page.getByText('Mock Server: http://localhost:8888')).toBeVisible();
  });

  test('should display data source details', async ({ page }) => {
    // Add a data source first
    await page.getByRole('button', { name: '添加 Jira', exact: true }).click();
    const uniqueName = 'test_details_' + Date.now();
    await page.locator('input[placeholder="my_jira"]').fill(uniqueName);
    await page.locator('input[placeholder="http://localhost:8888"]').fill('http://localhost:8888');
    await page.locator('input[placeholder="mock-token"]').fill('mock-token');
    await page.getByRole('button', { name: '创建数据源' }).click();
    await page.waitForTimeout(2000);

    // Check if details are displayed
    const card = page.locator('.config-item').filter({ hasText: uniqueName });
    await expect(card).toBeVisible();
    await expect(card.locator('.badge').getByText('jira', { exact: true })).toBeVisible();
  });
});
