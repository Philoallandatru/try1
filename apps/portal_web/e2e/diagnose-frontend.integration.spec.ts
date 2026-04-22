import { test, expect } from '@playwright/test';

test.describe('Frontend Diagnosis', () => {
  test('diagnose why setup checklist shows 0/4', async ({ page }) => {
    // Set up token
    await page.goto('http://localhost:5173');
    await page.evaluate(() => {
      localStorage.setItem('ssdPortalToken', 'change-me');
    });
    await page.reload();

    // Wait for page to load
    await page.waitForTimeout(3000);

    // Check which workspace is selected
    const workspaceSelect = page.locator('label:has-text("Workspace") select');
    const selectedWorkspace = await workspaceSelect.inputValue();
    console.log('Selected workspace:', selectedWorkspace);

    // Get all workspace options
    const options = await workspaceSelect.locator('option').allTextContents();
    console.log('Available workspaces:', options);

    // Check if demo workspace is available
    const hasDemoWorkspace = options.some(opt => opt.includes('demo'));
    console.log('Has demo workspace:', hasDemoWorkspace);

    // If demo is not selected, select it
    if (!selectedWorkspace.includes('demo') && hasDemoWorkspace) {
      console.log('Selecting demo workspace...');
      await workspaceSelect.selectOption({ label: 'demo' });
      await page.waitForTimeout(2000);
    }

    // Check setup checklist after workspace selection
    const setupHeader = page.locator('.setup-header strong');
    const statusText = await setupHeader.textContent();
    console.log('Setup status after selection:', statusText);

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

    // Check if profiles are loaded
    const profileSelect = page.locator('label:has-text("Profile") select');
    const profileOptions = await profileSelect.locator('option').allTextContents();
    console.log('Available profiles:', profileOptions);

    // Intercept API calls to see what's being requested
    const apiCalls: string[] = [];
    page.on('response', response => {
      if (response.url().includes('/api/')) {
        apiCalls.push(`${response.request().method()} ${response.url()} -> ${response.status()}`);
      }
    });

    // Reload to capture API calls
    await page.reload();
    await page.waitForTimeout(3000);

    console.log('\nAPI calls made:');
    apiCalls.forEach(call => console.log('  ' + call));

    // Check React Query state
    const reactQueryState = await page.evaluate(() => {
      // @ts-ignore
      const queryClient = window.__REACT_QUERY_DEVTOOLS_GLOBAL_HOOK__?.queryClient;
      if (!queryClient) return 'React Query not found';

      const cache = queryClient.getQueryCache();
      const queries = cache.getAll();

      return queries.map(q => ({
        queryKey: q.queryKey,
        state: q.state.status,
        dataAvailable: !!q.state.data,
        error: q.state.error?.message
      }));
    });

    console.log('\nReact Query state:', JSON.stringify(reactQueryState, null, 2));
  });

  test('manually check API responses', async ({ page, request }) => {
    // Get workspaces
    const workspacesResp = await request.get('http://localhost:8000/api/workspaces', {
      headers: { 'Authorization': 'Bearer change-me' }
    });
    const workspaces = await workspacesResp.json();
    console.log('Workspaces:', JSON.stringify(workspaces, null, 2));

    const demoWorkspace = workspaces.workspaces.find((w: any) => w.name === 'demo');
    if (!demoWorkspace) {
      console.log('ERROR: Demo workspace not found!');
      return;
    }

    const workspaceDir = demoWorkspace.workspace_dir;
    console.log('\nUsing workspace:', workspaceDir);

    // Get profiles
    const profilesResp = await request.get(
      `http://localhost:8000/api/workspace/profiles?workspace_dir=${encodeURIComponent(workspaceDir)}`,
      { headers: { 'Authorization': 'Bearer change-me' } }
    );
    const profiles = await profilesResp.json();
    console.log('\nProfiles:', JSON.stringify(profiles, null, 2));

    // Get sources
    const sourcesResp = await request.get(
      `http://localhost:8000/api/workspace/sources?workspace_dir=${encodeURIComponent(workspaceDir)}`,
      { headers: { 'Authorization': 'Bearer change-me' } }
    );
    const sources = await sourcesResp.json();
    console.log('\nSources:', JSON.stringify(sources, null, 2).substring(0, 1000));

    // Get spec assets
    const assetsResp = await request.get(
      `http://localhost:8000/api/workspace/spec-assets?workspace_dir=${encodeURIComponent(workspaceDir)}`,
      { headers: { 'Authorization': 'Bearer change-me' } }
    );
    const assets = await assetsResp.json();
    console.log('\nSpec Assets:', JSON.stringify(assets, null, 2));

    // Verify setup requirements
    const jiraSource = sources.sources.find((s: any) => s.kind === 'jira' && s.enabled !== false);
    const confluenceSource = sources.sources.find((s: any) => s.kind === 'confluence' && s.enabled !== false);
    const mineruAsset = assets.assets.find((a: any) => a.asset_id === 'nvme-spec-mineru' && a.parser_used === 'mineru');
    const validProfile = profiles.profiles.find((p: any) => {
      const text = JSON.stringify(p);
      return text.includes('nvme-spec-mineru') && text.includes('llm_backend');
    });

    console.log('\n=== Setup Verification ===');
    console.log('Jira Source:', jiraSource ? '✓ ' + jiraSource.name : '✗ Not found');
    console.log('Confluence Source:', confluenceSource ? '✓ ' + confluenceSource.name : '✗ Not found');
    console.log('MinerU Asset:', mineruAsset ? '✓ ' + mineruAsset.asset_id : '✗ Not found');
    console.log('Valid Profile:', validProfile ? '✓ ' + validProfile.name : '✗ Not found');
  });
});
