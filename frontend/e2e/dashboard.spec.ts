import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Mock Helpers – intercept backend API calls so tests can run without a live
// backend.
// ---------------------------------------------------------------------------

async function mockHealthEndpoint(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/health', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'healthy',
        timestamp: Date.now() / 1000,
        services: {
          postgres: { status: 'healthy', details: {} },
          redis: { status: 'healthy', details: {} },
          ollama: { status: 'healthy', details: { latency_ms: 42 } },
        },
      }),
    }),
  );
}

async function mockChatEndpoint(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/agent/chat', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        reply: 'Hello from the AI assistant!',
        reasoning_trace: [
          { node: 'classify', result: 'general_question' },
          { node: 'respond', result: 'generated reply' },
        ],
      }),
    }),
  );
}

// ---------------------------------------------------------------------------
// Test Suite
// ---------------------------------------------------------------------------

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('auth_token', 'mock_token');
  });
});

test.describe('Dashboard – Header & Branding', () => {
  test('displays the logo and title', async ({ page }) => {
    await mockHealthEndpoint(page);
    await page.goto('/');

    // Brand text
    await expect(page.getByText('Persist')).toBeVisible();

    // App header title (defaults to Agent Terminal on page load)
    await expect(
      page.locator('header').getByText('Agent Terminal'),
    ).toBeVisible();
  });
});

test.describe('Dashboard – Integrations Panel', () => {
  test('renders Google, Telegram, and Jira integration cards', async ({ page }) => {
    await mockHealthEndpoint(page);
    await page.goto('/');

    // Navigate to the Integrations panel from the sidebar navigation
    await page.getByRole('button', { name: 'Integrations' }).click();

    // Integration card headings
    await expect(page.getByText('Google OAuth')).toBeVisible();
    await expect(page.getByText('Telegram Bot')).toBeVisible();
    await expect(page.getByText('Atlassian Jira')).toBeVisible();
  });
});

test.describe('Dashboard – Chat Terminal', () => {
  test('accepts a user query and displays an AI response', async ({ page }) => {
    await mockHealthEndpoint(page);
    await mockChatEndpoint(page);
    await page.goto('/');

    // Find the chat input
    const input = page.getByPlaceholder(/ask|query|type|message/i);
    await expect(input).toBeVisible();

    // Type a message and submit
    await input.fill('What is the weather?');
    await input.press('Enter');

    // The AI response text should appear in the chat area
    await expect(page.getByText('Hello from the AI assistant!')).toBeVisible({
      timeout: 10_000,
    });
  });
});

test.describe('Dashboard – Notification Feed', () => {
  test('renders notification feed with tab controls', async ({ page }) => {
    await mockHealthEndpoint(page);

    // Mock the SSE endpoint so EventSource doesn't throw
    await page.route('**/api/v1/notifications/stream', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: 'data: {"type":"email","title":"Test notification","timestamp":"2026-05-26T12:00:00Z"}\n\n',
      }),
    );

    await page.goto('/');

    // The notification feed component should be visible
    await expect(page.getByText(/notification/i)).toBeVisible();
  });
});
