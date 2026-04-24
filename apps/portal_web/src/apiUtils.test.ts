import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { z } from 'zod';
import { fetchWithRetry, ApiError, apiJson } from './apiUtils';

// Mock fetch globally
const mockFetch = vi.fn();
globalThis.fetch = mockFetch as any;

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('apiUtils', () => {
  beforeEach(() => {
    mockFetch.mockClear();
    localStorageMock.clear();
    vi.clearAllTimers();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('ApiError', () => {
    it('creates error with message and status', () => {
      const error = new ApiError('Test error', 404);

      expect(error.message).toBe('Test error');
      expect(error.status).toBe(404);
      expect(error.name).toBe('ApiError');
    });
  });

  describe('fetchWithRetry', () => {
    const testSchema = z.object({ data: z.string() });

    it('returns data on successful request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: 'test' }),
      });

      const result = await fetchWithRetry('/api/test', testSchema);

      expect(result).toEqual({ data: 'test' });
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('throws on non-retryable client error (400)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Invalid input' }),
      });

      await expect(fetchWithRetry('/api/test', testSchema)).rejects.toThrow();
      expect(mockFetch).toHaveBeenCalledTimes(1); // No retry
    });

    it('retries on 500 error', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
          json: async () => ({}),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ data: 'success' }),
        });

      const promise = fetchWithRetry('/api/test', testSchema);

      // Fast-forward through retry delay
      await vi.runAllTimersAsync();

      const result = await promise;

      expect(result).toEqual({ data: 'success' });
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it('retries on 503 error', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 503,
          statusText: 'Service Unavailable',
          json: async () => ({}),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ data: 'success' }),
        });

      const promise = fetchWithRetry('/api/test', testSchema);
      await vi.runAllTimersAsync();
      const result = await promise;

      expect(result).toEqual({ data: 'success' });
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it('respects maxRetries config', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({}),
      });

      const promise = fetchWithRetry('/api/test', testSchema, {}, { maxRetries: 2 });

      // Catch the rejection to prevent unhandled promise rejection
      promise.catch(() => {});

      await vi.runAllTimersAsync();

      await expect(promise).rejects.toThrow();
      expect(mockFetch).toHaveBeenCalledTimes(3); // Initial + 2 retries
    });

    it('uses exponential backoff', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({}),
      });

      const promise = fetchWithRetry(
        '/api/test',
        testSchema,
        {},
        {
          maxRetries: 2,
          initialDelay: 100,
          backoffMultiplier: 2,
        }
      );

      // Catch the rejection to prevent unhandled promise rejection
      promise.catch(() => {});

      // First retry should wait ~100ms
      await vi.advanceTimersByTimeAsync(150);
      expect(mockFetch).toHaveBeenCalledTimes(2);

      // Second retry should wait ~200ms
      await vi.advanceTimersByTimeAsync(250);
      expect(mockFetch).toHaveBeenCalledTimes(3);

      await vi.runAllTimersAsync();
      await expect(promise).rejects.toThrow();
    });

    it('validates response with schema', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ wrong: 'field' }),
      });

      await expect(fetchWithRetry('/api/test', testSchema)).rejects.toThrow();
    });

    it('adds Content-Type header for POST requests', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: 'test' }),
      });

      await fetchWithRetry('/api/test', testSchema, {
        method: 'POST',
        body: JSON.stringify({ test: 'data' }),
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    });
  });

  describe('apiJson', () => {
    const testSchema = z.object({ data: z.string() });

    it('calls fetchWithRetry with correct parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: 'test' }),
      });

      await apiJson('/api/test', testSchema);

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          headers: {},
        })
      );
    });

    it('adds Content-Type header when body is present', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: 'test' }),
      });

      await apiJson('/api/test', testSchema, {
        method: 'POST',
        body: JSON.stringify({ test: 'data' }),
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    it('merges custom headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: 'test' }),
      });

      await apiJson('/api/test', testSchema, {
        headers: { 'X-Custom': 'value' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Custom': 'value',
          }),
        })
      );
    });

    it('passes retry config to fetchWithRetry', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          statusText: 'Error',
          json: async () => ({}),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ data: 'success' }),
        });

      const promise = apiJson('/api/test', testSchema, {}, { maxRetries: 1 });

      await vi.runAllTimersAsync();
      const result = await promise;

      expect(result).toEqual({ data: 'success' });
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });
});
