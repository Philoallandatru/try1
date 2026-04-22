import { z } from "zod";
import { formatErrorForDisplay } from "./errorMessages";

export interface RetryConfig {
  maxRetries?: number;
  initialDelay?: number;
  maxDelay?: number;
  backoffMultiplier?: number;
  retryableStatuses?: number[];
}

const DEFAULT_RETRY_CONFIG: Required<RetryConfig> = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 10000,
  backoffMultiplier: 2,
  retryableStatuses: [408, 429, 500, 502, 503, 504],
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public response?: Response,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function isRetryableError(error: unknown, retryableStatuses: number[]): boolean {
  if (error instanceof ApiError && error.status) {
    return retryableStatuses.includes(error.status);
  }
  if (error instanceof TypeError && error.message.includes("fetch")) {
    return true; // Network errors
  }
  return false;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function calculateDelay(
  attempt: number,
  initialDelay: number,
  maxDelay: number,
  backoffMultiplier: number,
): number {
  const exponentialDelay = initialDelay * Math.pow(backoffMultiplier, attempt);
  const jitter = Math.random() * 0.1 * exponentialDelay; // 10% jitter
  return Math.min(exponentialDelay + jitter, maxDelay);
}

export async function fetchWithRetry<T>(
  path: string,
  schema: z.ZodType<T>,
  init: RequestInit = {},
  retryConfig: RetryConfig = {},
): Promise<T> {
  const config = { ...DEFAULT_RETRY_CONFIG, ...retryConfig };
  const headers = init.headers || {};

  let lastError: unknown;

  for (let attempt = 0; attempt <= config.maxRetries; attempt++) {
    try {
      const response = await fetch(path, {
        ...init,
        headers: {
          ...headers,
          ...(init.body ? { "Content-Type": "application/json" } : {}),
        },
      });

      if (!response.ok) {
        let message = response.statusText;
        try {
          const payload = await response.json();
          message = payload.detail || payload.message || message;
        } catch {
          // Keep HTTP status text
        }

        const error = new ApiError(message, response.status, response);

        // Don't retry client errors (4xx except specific ones)
        if (response.status >= 400 && response.status < 500) {
          if (!config.retryableStatuses.includes(response.status)) {
            throw error;
          }
        }

        throw error;
      }

      const data = await response.json();
      return schema.parse(data);
    } catch (error) {
      lastError = error;

      // Don't retry if it's not a retryable error
      if (!isRetryableError(error, config.retryableStatuses)) {
        // Convert to user-friendly error before throwing
        const friendlyMessage = formatErrorForDisplay(error);
        throw new Error(friendlyMessage);
      }

      // Don't retry if we've exhausted attempts
      if (attempt >= config.maxRetries) {
        // Convert to user-friendly error before throwing
        const friendlyMessage = formatErrorForDisplay(error);
        throw new Error(friendlyMessage);
      }

      // Calculate delay and wait before retry
      const delayMs = calculateDelay(
        attempt,
        config.initialDelay,
        config.maxDelay,
        config.backoffMultiplier,
      );

      console.warn(
        `API request failed (attempt ${attempt + 1}/${config.maxRetries + 1}), retrying in ${Math.round(delayMs)}ms...`,
        error,
      );

      await delay(delayMs);
    }
  }

  // Convert final error to user-friendly message
  const friendlyMessage = formatErrorForDisplay(lastError);
  throw new Error(friendlyMessage);
}

export function tokenHeaders(): HeadersInit {
  const token = localStorage.getItem("ssdPortalToken") || "";
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiJson<T>(
  path: string,
  schema: z.ZodType<T>,
  init: RequestInit = {},
  retryConfig?: RetryConfig,
): Promise<T> {
  return fetchWithRetry(
    path,
    schema,
    {
      ...init,
      headers: {
        ...tokenHeaders(),
        ...(init.headers || {}),
      },
    },
    retryConfig,
  );
}
