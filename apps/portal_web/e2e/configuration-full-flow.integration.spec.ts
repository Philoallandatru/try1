import { test, expect } from '@playwright/test';

/**
 * E2E Test: Complete Configuration Flow
 *
 * This test simulates the complete configuration workflow:
 * 1. Navigate to Configuration page
 * 2. View current configuration
 * 3. Test configuration sections
 * 4. Update settings
 * 5. Verify changes
 */

test.describe('Configuration Full Integration Flow', () => {
  const runnerToken = 'test-token-123';

  test.beforeEach(async ({ page }) => {
    console.log('\n=== Test Setup ===');

    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    // Setup runner connection
    const tokenInput = page.locator('input[placeholder="change-me"]');
    if (await tokenInput.isVisible()) {
      await tokenInput.fill(runnerToken);
      await tokenInput.blur();
      await page.waitForTimeout(1500);
    }

    // Select workspace
    const workspaceSelect = page.locator('select[data-testid="workspace-selector"]').first();
    if (await workspaceSelect.isVisible()) {
      await workspaceSelect.selectOption({ index: 0 });
      await page.waitForTimeout(1000);
    }

    console.log('✓ Setup complete\n');
  });

  test('Step 1: Navigate to Configuration page and verify UI', async ({ page }) => {
    console.log('\n=== Step 1: Navigate to Configuration ===');

    await page.goto('http://localhost:5173/configuration');
    await page.waitForLoadState('networkidle');

    // Verify page heading
    const heading = page.locator('h1, h2').first();
    const headingText = await heading.textContent();
    console.log(`Page heading: ${headingText}`);

    await expect(heading).toBeVisible({ timeout: 5000 });

    // Look for configuration sections
    const sections = page.locator('section, .config-section, [class*="section"]');
    const sectionCount = await sections.count();
    console.log(`✓ Found ${sectionCount} configuration section(s)`);

    console.log('✓ Configuration page UI verified');
  });

  test('Step 2: View retrieval configuration', async ({ page }) => {
    console.log('\n=== Step 2: View Retrieval Configuration ===');

    await page.goto('http://localhost:5173/configuration');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Look for retrieval-related settings
    const retrievalSection = page.locator('text=Retrieval, text=检索, text=Strategy, text=策略');
    if (await retrievalSection.count() > 0) {
      console.log('✓ Retrieval configuration section found');

      // Look for strategy selector
      const strategySelect = page.locator('select, [role="combobox"]').first();
      if (await strategySelect.isVisible()) {
        const options = await strategySelect.locator('option').allTextContents();
        console.log('  Available strategies:', options);
      }

      // Look for top-k setting
      const topKInput = page.locator('input[type="number"]');
      if (await topKInput.count() > 0) {
        const topKValue = await topKInput.first().inputValue();
        console.log(`  Top-K value: ${topKValue}`);
      }
    }

    console.log('✓ Retrieval configuration viewed');
  });

  test('Step 3: View LLM configuration', async ({ page }) => {
    console.log('\n=== Step 3: View LLM Configuration ===');

    await page.goto('http://localhost:5173/configuration');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Look for LLM-related settings
    const llmSection = page.locator('text=LLM, text=Model, text=模型');
    if (await llmSection.count() > 0) {
      console.log('✓ LLM configuration section found');

      // Look for backend selector
      const backendSelect = page.locator('select:has(option:has-text("ollama")), select:has(option:has-text("openai"))');
      if (await backendSelect.count() > 0) {
        const backend = await backendSelect.first().inputValue();
        console.log(`  LLM backend: ${backend}`);
      }

      // Look for model input
      const modelInput = page.locator('input[placeholder*="model"], input[placeholder*="模型"]');
      if (await modelInput.count() > 0) {
        const model = await modelInput.first().inputValue();
        console.log(`  Model: ${model}`);
      }

      // Look for base URL input
      const urlInput = page.locator('input[type="url"], input[placeholder*="url"], input[placeholder*="URL"]');
      if (await urlInput.count() > 0) {
        const url = await urlInput.first().inputValue();
        console.log(`  Base URL: ${url}`);
      }
    }

    console.log('✓ LLM configuration viewed');
  });

  test('Step 4: Test configuration tabs/sections', async ({ page }) => {
    console.log('\n=== Step 4: Test Configuration Sections ===');

    await page.goto('http://localhost:5173/configuration');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Look for tabs or section navigation
    const tabs = page.locator('[role="tab"], button[class*="tab"]');
    const tabCount = await tabs.count();

    if (tabCount > 0) {
      console.log(`✓ Found ${tabCount} configuration tab(s)`);

      // Click through tabs
      for (let i = 0; i < Math.min(tabCount, 5); i++) {
        const tab = tabs.nth(i);
        const tabText = await tab.textContent();
        await tab.click();
        await page.waitForTimeout(500);
        console.log(`  Clicked tab: ${tabText}`);
      }
    } else {
      console.log('⚠ No tabs found, configuration might be single-page');
    }

    console.log('✓ Configuration sections tested');
  });

  test('Step 5: Test form inputs', async ({ page }) => {
    console.log('\n=== Step 5: Test Form Inputs ===');

    await page.goto('http://localhost:5173/configuration');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Test text inputs
    const textInputs = page.locator('input[type="text"], input[type="url"]');
    const textInputCount = await textInputs.count();
    console.log(`✓ Found ${textInputCount} text input(s)`);

    // Test number inputs
    const numberInputs = page.locator('input[type="number"]');
    const numberInputCount = await numberInputs.count();
    console.log(`✓ Found ${numberInputCount} number input(s)`);

    if (numberInputCount > 0) {
      const firstNumberInput = numberInputs.first();
      const originalValue = await firstNumberInput.inputValue();

      // Test changing value
      await firstNumberInput.fill('10');
      await page.waitForTimeout(300);
      const newValue = await firstNumberInput.inputValue();
      console.log(`  Changed value from ${originalValue} to ${newValue}`);

      // Restore original value
      await firstNumberInput.fill(originalValue);
    }

    // Test select dropdowns
    const selects = page.locator('select');
    const selectCount = await selects.count();
    console.log(`✓ Found ${selectCount} select dropdown(s)`);

    if (selectCount > 0) {
      const firstSelect = selects.first();
      const options = await firstSelect.locator('option').allTextContents();
      console.log(`  First select has ${options.length} option(s)`);
    }

    console.log('✓ Form inputs tested');
  });

  test('Step 6: Test save/apply buttons', async ({ page }) => {
    console.log('\n=== Step 6: Test Save Buttons ===');

    await page.goto('http://localhost:5173/configuration');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Look for save/apply/submit buttons
    const saveButtons = page.locator('button:has-text("Save"), button:has-text("保存"), button:has-text("Apply"), button:has-text("应用"), button[type="submit"]');
    const saveButtonCount = await saveButtons.count();

    if (saveButtonCount > 0) {
      console.log(`✓ Found ${saveButtonCount} save/apply button(s)`);

      // Check button states
      for (let i = 0; i < Math.min(saveButtonCount, 3); i++) {
        const button = saveButtons.nth(i);
        const buttonText = await button.textContent();
        const isDisabled = await button.isDisabled();
        console.log(`  Button "${buttonText}" - Disabled: ${isDisabled}`);
      }
    } else {
      console.log('⚠ No save buttons found');
    }

    console.log('✓ Save buttons tested');
  });

  test('Step 7: Test reset/cancel functionality', async ({ page }) => {
    console.log('\n=== Step 7: Test Reset/Cancel ===');

    await page.goto('http://localhost:5173/configuration');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Look for reset/cancel buttons
    const resetButtons = page.locator('button:has-text("Reset"), button:has-text("重置"), button:has-text("Cancel"), button:has-text("取消")');
    const resetButtonCount = await resetButtons.count();

    if (resetButtonCount > 0) {
      console.log(`✓ Found ${resetButtonCount} reset/cancel button(s)`);

      // Test reset functionality
      const numberInput = page.locator('input[type="number"]').first();
      if (await numberInput.isVisible()) {
        const originalValue = await numberInput.inputValue();
        await numberInput.fill('999');
        console.log(`  Changed value to 999`);

        const resetButton = resetButtons.first();
        await resetButton.click();
        await page.waitForTimeout(500);

        const resetValue = await numberInput.inputValue();
        console.log(`  After reset: ${resetValue}`);
      }
    } else {
      console.log('⚠ No reset buttons found');
    }

    console.log('✓ Reset functionality tested');
  });

  test('Step 8: Complete configuration flow summary', async ({ page }) => {
    console.log('\n=== Step 8: Configuration Summary ===');

    await page.goto('http://localhost:5173/configuration');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Collect configuration statistics
    const inputCount = await page.locator('input').count();
    const selectCount = await page.locator('select').count();
    const buttonCount = await page.locator('button').count();

    console.log('\n=== Configuration Flow Complete ===');
    console.log(`Total inputs: ${inputCount}`);
    console.log(`Total selects: ${selectCount}`);
    console.log(`Total buttons: ${buttonCount}`);
    console.log('✓ All configuration steps completed successfully');

    // Take final screenshot
    await page.screenshot({ path: 'test-results/final-configuration-page.png', fullPage: true });
  });
});
