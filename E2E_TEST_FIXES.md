# E2E Test Fixes

## Summary
Fixed Playwright E2E tests to match the actual frontend implementation. The tests were failing because they used incorrect selectors and expected English text, while the actual pages use Chinese text and different UI structures.

## Changes Made

### 1. Model Configuration Test (Step 1)
**Issues:**
- Expected "Model Configuration" but page shows "模型配置" (Chinese)
- Expected button clicks for "Local Model" and "LM Studio" but actual UI uses cards and dropdowns
- Incorrect input selectors

**Fixes:**
- Changed selector to `h1:has-text("模型配置")`
- Click on "本地模型" card instead of button
- Use `selectOption` for provider dropdown
- Updated input placeholder selectors to match Chinese text
- Handle alert dialog for "配置已保存" (Configuration saved)

### 2. Document Upload Test (Step 2)
**Issues:**
- Incorrect order of operations (select type before file)
- Expected immediate success message but upload is async with polling

**Fixes:**
- Upload file first, then select document type
- Wait for async processing with longer timeout (120s)
- Updated success message regex to match actual responses

### 3. Chat Test (Step 3)
**Issues:**
- Expected multiple select elements (model + source) but only one exists
- Incorrect message container selectors
- Expected specific message count

**Fixes:**
- Wait for data sources to load first
- Select from single dropdown (index 1, skipping "-- 请选择 --")
- Use correct input selector `input[type="text"]`
- Updated button selector to handle SVG icon
- Wait for Chinese text "思考中..." (Thinking...)
- Check for message visibility instead of exact count

### 4. Complete Workflow Test
**Issues:**
- Combined all issues from individual tests

**Fixes:**
- Applied all fixes from Steps 1-3
- Added proper dialog handling
- Added document existence check to avoid duplicate uploads
- Proper timeout handling for async operations

### 5. API Health Check
**Issues:**
- Used `/health` instead of `/api/health`

**Fixes:**
- Already fixed in previous iteration to use `/api/health`

## Test Structure

```typescript
test.describe('Full E2E Workflow', () => {
  test('Step 1: Configure LM Studio model', async ({ page }) => { ... });
  test('Step 2: Upload document', async ({ page }) => { ... });
  test('Step 3: Chat with document', async ({ page }) => { ... });
  test('Complete workflow: Model Config -> Upload -> Chat', async ({ page }) => { ... });
});

test.describe('API Health Checks', () => {
  test('Backend API is running', async ({ request }) => { ... });
  test('Model config API works', async ({ request }) => { ... });
  test('Documents API works', async ({ request }) => { ... });
});
```

## Key Learnings

1. **Internationalization**: Frontend uses Chinese text, tests must match
2. **Async Operations**: Document processing is async with polling, need longer timeouts
3. **UI Structure**: Actual implementation differs from initial assumptions
4. **Alert Dialogs**: Model config uses browser alerts, need dialog handlers
5. **Selector Strategy**: Use text content and semantic selectors over CSS classes

## Running Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run with UI mode
npm run test:e2e:ui

# Run in headed mode (see browser)
npm run test:e2e:headed

# Debug mode
npm run test:e2e:debug
```

## Prerequisites

1. Backend server running on port 8787
2. Frontend dev server running on port 5173
3. Test PDF fixture at `tests/fixtures/test_document.pdf`
4. (Optional) LM Studio running on port 1234 for full chat functionality

## Expected Results

- 7 total tests
- API health checks should pass immediately
- UI tests may timeout if servers not running
- Chat test may fail if LM Studio not running (expected)
