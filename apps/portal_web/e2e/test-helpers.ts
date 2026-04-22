import { Page } from '@playwright/test';

/**
 * Set up authentication token and wait for page to reload
 */
export async function setupAuth(page: Page, token: string = 'change-me') {
  await page.goto('http://localhost:5173');
  await page.evaluate((t) => {
    localStorage.setItem('ssdPortalToken', t);
  }, token);
  await page.reload();
}

/**
 * Wait for workspace selector to be ready and select a workspace
 * @param page - Playwright page object
 * @param preferredWorkspace - Preferred workspace name (e.g., 'demo')
 * @returns The selected workspace name
 */
export async function selectWorkspace(
  page: Page,
  preferredWorkspace: string = 'demo'
): Promise<string | null> {
  // Wait for workspace selector to be visible
  const workspaceSelect = page.locator('[data-testid="workspace-selector"]');
  await workspaceSelect.waitFor({ state: 'visible', timeout: 10000 });

  // Wait for options to load
  await page.waitForFunction(
    () => {
      const select = document.querySelector('[data-testid="workspace-selector"]') as HTMLSelectElement;
      return select && select.options.length > 0;
    },
    { timeout: 10000 }
  );

  // Get available workspace options
  const options = await workspaceSelect.locator('option').allTextContents();
  console.log('Available workspaces:', options);

  // Try to select preferred workspace if it exists
  const hasPreferredWorkspace = options.some(opt =>
    opt.toLowerCase().includes(preferredWorkspace.toLowerCase())
  );

  if (hasPreferredWorkspace) {
    console.log(`Selecting ${preferredWorkspace} workspace...`);
    await workspaceSelect.selectOption({ label: preferredWorkspace });
    await page.waitForTimeout(1000);
    return preferredWorkspace;
  }

  // Select first available workspace if any
  if (options.length > 0 && !options[0].includes('No workspace')) {
    console.log(`${preferredWorkspace} workspace not found. Selecting first available:`, options[0]);
    await workspaceSelect.selectOption({ index: 0 });
    await page.waitForTimeout(1000);
    return options[0];
  }

  console.log('WARNING: No workspaces available');
  return null;
}

/**
 * Setup auth and select workspace in one call
 */
export async function setupAuthAndWorkspace(
  page: Page,
  token: string = 'change-me',
  preferredWorkspace: string = 'demo'
): Promise<string | null> {
  await setupAuth(page, token);
  return await selectWorkspace(page, preferredWorkspace);
}

/**
 * Wait for API response and return status
 */
export async function waitForApiResponse(
  page: Page,
  urlPattern: string,
  timeout: number = 30000
): Promise<number | null> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(null), timeout);

    page.on('response', (response) => {
      if (response.url().includes(urlPattern)) {
        clearTimeout(timer);
        resolve(response.status());
      }
    });
  });
}
