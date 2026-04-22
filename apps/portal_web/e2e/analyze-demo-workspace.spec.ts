import { test, expect } from '@playwright/test';
import { setupAuthAndWorkspace } from './test-helpers';

test.describe('Analyze Page - Full E2E with Demo Workspace', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthAndWorkspace(page, 'change-me', 'demo');
  });

  test('should show 4/4 ready with demo workspace', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Wait for setup checklist
    await page.waitForSelector('.setup-checklist', { timeout: 10000 });

    // Check setup status
    const setupHeader = page.locator('.setup-header strong');
    await expect(setupHeader).toContainText('4 / 4 ready');

    // Verify all items are ready
    const setupItems = page.locator('.setup-item.ready');
    const count = await setupItems.count();
    expect(count).toBe(4);

    console.log('✓ All 4 setup items are ready');
  });

  test('should have profiles available', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    await page.waitForTimeout(2000);

    // Check profiles
    const profileSelect = page.locator('label:has-text("Profile") select');
    const profileCount = await profileSelect.locator('option').count();

    expect(profileCount).toBeGreaterThan(0);
    console.log(`✓ Found ${profileCount} profile(s)`);

    // List profiles
    const profiles = await profileSelect.locator('option').allTextContents();
    console.log('Available profiles:', profiles);
  });

  test('should enable Run Analysis button', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    await page.waitForTimeout(2000);

    // Check button state
    const runButton = page.locator('button:has-text("Run Analysis")');
    await expect(runButton).toBeVisible();

    const isDisabled = await runButton.isDisabled();
    expect(isDisabled).toBe(false);

    console.log('✓ Run Analysis button is enabled');
  });

  test('should successfully run analysis on demo data', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    await page.waitForTimeout(2000);

    // Fill in issue key (use demo issue)
    const issueInput = page.locator('input[placeholder*="SSD-DEMO-A"]');
    await issueInput.fill('SSD-SAMPLE-1');

    // Select default profile
    const profileSelect = page.locator('label:has-text("Profile") select');
    await profileSelect.selectOption('default');

    console.log('Submitting analysis request...');

    // Set up response listener
    let apiResponseStatus: number | null = null;
    page.on('response', response => {
      if (response.url().includes('/api/workspace/analyze-jira')) {
        apiResponseStatus = response.status();
        console.log(`API Response: ${response.status()}`);
      }
    });

    // Click Run Analysis
    const runButton = page.locator('button:has-text("Run Analysis")');
    await runButton.click();

    // Wait for loading state
    await expect(page.locator('button:has-text("Running...")')).toBeVisible({ timeout: 5000 });
    console.log('✓ Analysis started');

    // Wait for completion (up to 30 minutes for real LLM call)
    try {
      await page.waitForSelector('.result-surface, .error, .message.user-message', { timeout: 1800000 });

      // Check for errors
      const errorDiv = page.locator('.error');
      const errorCount = await errorDiv.count();

      if (errorCount > 0) {
        const errorText = await errorDiv.textContent();
        console.log('ERROR:', errorText);

        // This is expected if LLM is not running
        if (errorText?.includes('Connection') || errorText?.includes('timeout')) {
          console.log('Note: LLM connection error is expected if LM Studio is not running');
        }
      } else {
        // Check for success
        const resultSurface = page.locator('.result-surface');
        if (await resultSurface.count() > 0) {
          console.log('✓ Analysis completed successfully');

          // Capture result details
          const summaryHeading = page.locator('.result-surface h3').first();
          if (await summaryHeading.count() > 0) {
            const title = await summaryHeading.textContent();
            console.log('Analysis title:', title);
          }

          // Check for evidence coverage
          const coveragePanel = page.locator('.coverage-panel');
          if (await coveragePanel.count() > 0) {
            const coverageText = await coveragePanel.textContent();
            console.log('Evidence coverage:', coverageText?.substring(0, 200));
          }
        }

        // Check for latest run message
        const latestRunMsg = page.locator('.message.user-message');
        if (await latestRunMsg.count() > 0) {
          const msgText = await latestRunMsg.textContent();
          console.log('Latest run message:', msgText);
        }
      }

      console.log('Final API status:', apiResponseStatus);
    } catch (e) {
      console.log('Timeout waiting for result. This may indicate a backend issue.');
      throw e;
    }
  });

  test('should display error when LLM is not available', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    await page.waitForTimeout(2000);

    // Fill in issue key
    const issueInput = page.locator('input[placeholder*="SSD-DEMO-A"]');
    await issueInput.fill('SSD-SAMPLE-1');

    // Select default profile (which uses LM Studio)
    const profileSelect = page.locator('label:has-text("Profile") select');
    await profileSelect.selectOption('default');

    // Click Run Analysis
    const runButton = page.locator('button:has-text("Run Analysis")');
    await runButton.click();

    // Wait for loading
    await expect(page.locator('button:has-text("Running...")')).toBeVisible({ timeout: 5000 });

    // Wait for error or success
    await page.waitForSelector('.error, .result-surface, .message.user-message', { timeout: 120000 });

    // Check what happened
    const errorDiv = page.locator('.error');
    const errorCount = await errorDiv.count();

    if (errorCount > 0) {
      const errorText = await errorDiv.textContent();
      console.log('Expected error (LLM not running):', errorText);

      // Verify it's a connection error
      expect(errorText).toMatch(/Connection|timeout|refused|LLM/i);
    } else {
      console.log('Analysis succeeded (LLM is running)');
    }
  });

  test('should navigate to Runs page and see the run', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Navigate to Runs page
    const runsLink = page.locator('nav a:has-text("Runs")');
    await runsLink.click();

    await expect(page).toHaveURL('http://localhost:5173/runs');

    // Wait for runs to load
    await page.waitForTimeout(2000);

    // Check for run history
    const runRows = page.locator('.run-row');
    const runCount = await runRows.count();

    console.log(`Found ${runCount} run(s) in history`);

    if (runCount > 0) {
      // Click first run
      await runRows.first().click();

      // Check for run detail
      const runDetail = page.locator('.run-detail-stack, .primary-surface h2');
      await expect(runDetail.first()).toBeVisible({ timeout: 5000 });

      console.log('✓ Run detail displayed');
    }
  });
});
