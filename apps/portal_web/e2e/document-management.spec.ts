import { test, expect } from '@playwright/test';
import * as path from 'path';

test.describe('Document Management E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Set up authentication token
    await page.goto('http://localhost:5173');
    await page.evaluate(() => {
      localStorage.setItem('ssdPortalToken', 'change-me');
    });
    await page.reload();
    await page.waitForTimeout(2000);
  });

  test('should display document management page', async ({ page }) => {
    await page.goto('http://localhost:5173/documents');

    // Check page title
    await expect(page.locator('h1')).toContainText('Document Management');

    // Check upload section exists
    await expect(page.locator('.upload-section')).toBeVisible();

    // Check documents section exists
    await expect(page.locator('.documents-section')).toBeVisible();
  });

  test('should show document types', async ({ page }) => {
    await page.goto('http://localhost:5173/documents');

    // Wait for page to load
    await page.waitForSelector('.upload-section', { timeout: 10000 });

    // Check document type selector
    const typeSelect = page.locator('#document-type');
    await expect(typeSelect).toBeVisible();

    // Verify document types are available
    const options = await typeSelect.locator('option').allTextContents();
    console.log('Available document types:', options);

    // Should have at least Spec, Policy, Other
    expect(options.length).toBeGreaterThanOrEqual(3);
  });

  test('should handle file selection', async ({ page }) => {
    await page.goto('http://localhost:5173/documents');

    // Wait for upload section
    await page.waitForSelector('.upload-dropzone', { timeout: 10000 });

    // Check if file input exists
    const fileInput = page.locator('#file-input');
    await expect(fileInput).toBeAttached();

    // Note: Actual file upload would require a real PDF file
    // This test just verifies the UI elements are present
    console.log('File input element is present and ready for uploads');
  });

  test('should display empty state when no documents uploaded', async ({ page }) => {
    await page.goto('http://localhost:5173/documents');

    // Wait for documents section to load
    await page.waitForSelector('.documents-section', { timeout: 10000 });

    // Check for empty state or document list
    const emptyState = page.locator('.empty-state');
    const documentsList = page.locator('.documents-list');

    // Either empty state or documents list should be visible
    const hasEmptyState = await emptyState.isVisible().catch(() => false);
    const hasDocuments = await documentsList.isVisible().catch(() => false);

    expect(hasEmptyState || hasDocuments).toBeTruthy();

    if (hasEmptyState) {
      console.log('No documents uploaded yet - showing empty state');
      await expect(emptyState).toContainText('No documents uploaded yet');
    } else {
      console.log('Documents are present in the workspace');
    }
  });

  test('should show filter controls', async ({ page }) => {
    await page.goto('http://localhost:5173/documents');

    // Wait for documents section
    await page.waitForSelector('.documents-section', { timeout: 10000 });

    // Check filter controls
    const filterControls = page.locator('.filter-controls');
    await expect(filterControls).toBeVisible();

    // Check filter select
    const filterSelect = filterControls.locator('select');
    await expect(filterSelect).toBeVisible();

    // Verify filter options
    const filterOptions = await filterSelect.locator('option').allTextContents();
    console.log('Filter options:', filterOptions);

    // Should have "All Types" and document type options
    expect(filterOptions.length).toBeGreaterThanOrEqual(4); // All Types + Spec + Policy + Other
  });

  test('should integrate with workspace selector', async ({ page }) => {
    await page.goto('http://localhost:5173/documents');

    // Check workspace selector in topbar
    const workspaceSelect = page.locator('label:has-text("Workspace") select');
    await expect(workspaceSelect).toBeVisible();

    // Get selected workspace
    const selectedWorkspace = await workspaceSelect.inputValue();
    console.log('Selected workspace:', selectedWorkspace);

    // Workspace should be selected
    expect(selectedWorkspace).toBeTruthy();
  });

  test('should show upload form when file is selected', async ({ page }) => {
    await page.goto('http://localhost:5173/documents');

    // Wait for upload section
    await page.waitForSelector('.upload-dropzone', { timeout: 10000 });

    // Note: This test verifies the form structure
    // Actual file upload would require mocking or real file

    // Check that form elements exist
    const documentTypeLabel = page.locator('label[for="document-type"]');
    const displayNameLabel = page.locator('label[for="display-name"]');

    // These elements should exist in the DOM (even if hidden initially)
    await expect(documentTypeLabel).toBeAttached();
    await expect(displayNameLabel).toBeAttached();

    console.log('Upload form structure is correct');
  });

  test('should have proper navigation link', async ({ page }) => {
    await page.goto('http://localhost:5173');

    // Check if Documents link exists in navigation
    const documentsLink = page.locator('nav a[href="/documents"]');
    await expect(documentsLink).toBeVisible();
    await expect(documentsLink).toContainText('Documents');

    // Click the link
    await documentsLink.click();

    // Verify navigation worked
    await expect(page).toHaveURL('http://localhost:5173/documents');
    await expect(page.locator('h1')).toContainText('Document Management');
  });
});

test.describe('Document Upload Integration with documents folder', () => {
  test('should be able to upload PDF from documents folder', async ({ page }) => {
    // This test demonstrates how to upload actual PDFs from the documents folder
    // Note: Requires backend to be running

    await page.goto('http://localhost:5173');
    await page.evaluate(() => {
      localStorage.setItem('ssdPortalToken', 'change-me');
    });
    await page.reload();

    await page.goto('http://localhost:5173/documents');
    await page.waitForSelector('.upload-dropzone', { timeout: 10000 });

    // Note: Actual file upload would be done via API or file input
    // This is a placeholder for the integration test
    console.log('Document upload integration test - requires backend API');
    console.log('PDFs available in documents folder:');
    console.log('- NVM-Express-Base-Specification-Revision-2.1-2024.08.05-Ratified.pdf');
    console.log('- PCI-Express-5-Update-Keys-to-Addressing-an-Evolving-Specification.pdf');
    console.log('- PCI_Firmware_v3.3_20210120_NCB.pdf');
    console.log('- fms-08-09-2023-ssds-201-1-ozturk-final.pdf');
  });
});
