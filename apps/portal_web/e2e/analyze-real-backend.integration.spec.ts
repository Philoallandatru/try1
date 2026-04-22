import { test, expect } from '@playwright/test';

test.describe('Analyze Page - Real Backend Integration', () => {
  test.beforeEach(async ({ page }) => {
    // Set up token
    await page.goto('http://localhost:5173');
    await page.evaluate(() => {
      localStorage.setItem('ssdPortalToken', 'change-me');
    });
    await page.reload();
  });

  test('should load workspace and profiles from backend', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Wait for API calls to complete
    await page.waitForTimeout(2000);

    // Check if workspace selector has loaded
    const workspaceSelect = page.locator('label:has-text("Workspace") select');
    await expect(workspaceSelect).toBeVisible({ timeout: 10000 });

    // Check if it has options (should have at least one workspace)
    const options = await workspaceSelect.locator('option').count();
    console.log(`Found ${options} workspace(s)`);

    if (options === 0) {
      console.log('WARNING: No workspaces found. Backend may not be running or configured.');
    }
  });

  test('should display setup checklist with real backend status', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    await page.waitForSelector('.setup-checklist', { timeout: 10000 });

    // Get setup status
    const setupHeader = page.locator('.setup-header strong');
    const statusText = await setupHeader.textContent();
    console.log('Setup status:', statusText);

    // Check each setup item
    const setupItems = page.locator('.setup-item');
    const count = await setupItems.count();

    for (let i = 0; i < count; i++) {
      const item = setupItems.nth(i);
      const label = await item.locator('strong').textContent();
      const detail = await item.locator('small').textContent();
      const isReady = await item.evaluate(el => el.classList.contains('ready'));

      console.log(`- ${label}: ${isReady ? '✓' : '✗'} (${detail})`);
    }
  });

  test('should attempt real analysis and capture response', async ({ page }) => {
    await page.goto('http://localhost:5173/');

    // Wait for page to load
    await page.waitForSelector('input[placeholder*="SSD-DEMO-A"]', { timeout: 10000 });

    // Check if profiles are available
    const profileSelect = page.locator('label:has-text("Profile") select');
    const profileCount = await profileSelect.locator('option').count();

    console.log(`Found ${profileCount} profile(s)`);

    if (profileCount === 0) {
      console.log('SKIP: No profiles configured. Cannot run analysis.');
      return;
    }

    // Fill in issue key
    const issueInput = page.locator('input[placeholder*="SSD-DEMO-A"]');
    await issueInput.fill('SSD-SAMPLE-1');

    // Check button state
    const runButton = page.locator('button:has-text("Run Analysis")');
    const isDisabled = await runButton.isDisabled();

    console.log(`Run Analysis button disabled: ${isDisabled}`);

    if (isDisabled) {
      console.log('SKIP: Setup not complete. Button is disabled.');

      // Capture why it's disabled
      const setupBadge = page.locator('.setup-badge');
      const badgeText = await setupBadge.textContent();
      console.log('Setup badge:', badgeText);

      return;
    }

    // Set up response listener
    let apiResponse: any = null;
    let apiError: any = null;

    page.on('response', async response => {
      if (response.url().includes('/api/workspace/analyze-jira')) {
        console.log(`API Response: ${response.status()} ${response.statusText()}`);

        try {
          const body = await response.json();
          apiResponse = body;
          console.log('Response body:', JSON.stringify(body, null, 2).substring(0, 500));
        } catch (e) {
          const text = await response.text();
          apiError = text;
          console.log('Response text:', text.substring(0, 500));
        }
      }
    });

    // Click Run Analysis
    await runButton.click();

    // Wait for loading state
    await expect(page.locator('button:has-text("Running...")')).toBeVisible({ timeout: 5000 });
    console.log('Analysis started...');

    // Wait for completion (up to 60 seconds)
    await page.waitForTimeout(60000);

    // Check for results or errors
    const errorDiv = page.locator('.error');
    const errorCount = await errorDiv.count();

    if (errorCount > 0) {
      const errorText = await errorDiv.textContent();
      console.log('ERROR displayed:', errorText);
    }

    // Check for result view
    const resultSurface = page.locator('.result-surface');
    const resultCount = await resultSurface.count();

    if (resultCount > 0) {
      console.log('SUCCESS: Result surface displayed');

      // Capture result details
      const summaryHeading = page.locator('.result-surface h3');
      if (await summaryHeading.count() > 0) {
        const title = await summaryHeading.textContent();
        console.log('Analysis title:', title);
      }
    } else {
      console.log('No result surface found');
    }

    // Check for empty state
    const emptyState = page.locator('.empty-state');
    const emptyCount = await emptyState.count();

    if (emptyCount > 0) {
      const emptyText = await emptyState.textContent();
      console.log('Empty state:', emptyText);
    }
  });

  test('should check backend API endpoints directly', async ({ page, request }) => {
    // Test workspaces endpoint
    try {
      const workspacesResponse = await request.get('http://localhost:8000/api/workspaces', {
        headers: { 'Authorization': 'Bearer change-me' }
      });

      console.log('Workspaces API:', workspacesResponse.status());

      if (workspacesResponse.ok()) {
        const data = await workspacesResponse.json();
        console.log('Workspaces:', JSON.stringify(data, null, 2));
      } else {
        const text = await workspacesResponse.text();
        console.log('Workspaces error:', text);
      }
    } catch (e) {
      console.log('Workspaces API failed:', e);
    }

    // Test profiles endpoint (need workspace_dir)
    try {
      const workspacesResponse = await request.get('http://localhost:8000/api/workspaces', {
        headers: { 'Authorization': 'Bearer change-me' }
      });

      if (workspacesResponse.ok()) {
        const data = await workspacesResponse.json();
        const workspaceDir = data.workspaces?.[0]?.workspace_dir;

        if (workspaceDir) {
          const profilesResponse = await request.get(
            `http://localhost:8000/api/workspace/profiles?workspace_dir=${encodeURIComponent(workspaceDir)}`,
            { headers: { 'Authorization': 'Bearer change-me' } }
          );

          console.log('Profiles API:', profilesResponse.status());

          if (profilesResponse.ok()) {
            const profilesData = await profilesResponse.json();
            console.log('Profiles:', JSON.stringify(profilesData, null, 2));
          } else {
            const text = await profilesResponse.text();
            console.log('Profiles error:', text);
          }
        }
      }
    } catch (e) {
      console.log('Profiles API failed:', e);
    }

    // Test sources endpoint
    try {
      const workspacesResponse = await request.get('http://localhost:8000/api/workspaces', {
        headers: { 'Authorization': 'Bearer change-me' }
      });

      if (workspacesResponse.ok()) {
        const data = await workspacesResponse.json();
        const workspaceDir = data.workspaces?.[0]?.workspace_dir;

        if (workspaceDir) {
          const sourcesResponse = await request.get(
            `http://localhost:8000/api/workspace/sources?workspace_dir=${encodeURIComponent(workspaceDir)}`,
            { headers: { 'Authorization': 'Bearer change-me' } }
          );

          console.log('Sources API:', sourcesResponse.status());

          if (sourcesResponse.ok()) {
            const sourcesData = await sourcesResponse.json();
            console.log('Sources:', JSON.stringify(sourcesData, null, 2));
          } else {
            const text = await sourcesResponse.text();
            console.log('Sources error:', text);
          }
        }
      }
    } catch (e) {
      console.log('Sources API failed:', e);
    }
  });

  test('should test analyze-jira endpoint with mock data', async ({ request }) => {
    // First get workspace
    const workspacesResponse = await request.get('http://localhost:8000/api/workspaces', {
      headers: { 'Authorization': 'Bearer change-me' }
    });

    if (!workspacesResponse.ok()) {
      console.log('Cannot get workspaces. Backend may not be running.');
      return;
    }

    const workspacesData = await workspacesResponse.json();
    const workspaceDir = workspacesData.workspaces?.[0]?.workspace_dir;

    if (!workspaceDir) {
      console.log('No workspace found.');
      return;
    }

    // Get profiles
    const profilesResponse = await request.get(
      `http://localhost:8000/api/workspace/profiles?workspace_dir=${encodeURIComponent(workspaceDir)}`,
      { headers: { 'Authorization': 'Bearer change-me' } }
    );

    if (!profilesResponse.ok()) {
      console.log('Cannot get profiles.');
      return;
    }

    const profilesData = await profilesResponse.json();
    const profile = profilesData.profiles?.[0]?.name;

    if (!profile) {
      console.log('No profile found.');
      return;
    }

    console.log(`Testing analyze-jira with workspace: ${workspaceDir}, profile: ${profile}`);

    // Test analyze endpoint
    try {
      const analyzeResponse = await request.post('http://localhost:8000/api/workspace/analyze-jira', {
        headers: {
          'Authorization': 'Bearer change-me',
          'Content-Type': 'application/json'
        },
        data: {
          workspace_dir: workspaceDir,
          issue_key: 'SSD-SAMPLE-1',
          profile: profile
        },
        timeout: 60000
      });

      console.log('Analyze API:', analyzeResponse.status());

      if (analyzeResponse.ok()) {
        const data = await analyzeResponse.json();
        console.log('Analyze response:', JSON.stringify(data, null, 2).substring(0, 1000));
      } else {
        const text = await analyzeResponse.text();
        console.log('Analyze error:', text.substring(0, 500));
      }
    } catch (e) {
      console.log('Analyze API failed:', e);
    }
  });
});
