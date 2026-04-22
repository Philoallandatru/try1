/**
 * Performance monitoring and metrics collection
 */

export interface PerformanceMetric {
  name: string;
  value: number;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export interface PageLoadMetrics {
  dns: number;
  tcp: number;
  request: number;
  response: number;
  domParsing: number;
  domContentLoaded: number;
  loadComplete: number;
  firstPaint?: number;
  firstContentfulPaint?: number;
  largestContentfulPaint?: number;
  firstInputDelay?: number;
  cumulativeLayoutShift?: number;
}

class PerformanceMonitor {
  private metrics: PerformanceMetric[] = [];
  private observers: PerformanceObserver[] = [];
  private enabled: boolean = true;

  constructor() {
    if (typeof window !== 'undefined') {
      this.initializeObservers();
    }
  }

  /**
   * Initialize performance observers
   */
  private initializeObservers(): void {
    // Observe Largest Contentful Paint (LCP)
    if ('PerformanceObserver' in window) {
      try {
        const lcpObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const lastEntry = entries[entries.length - 1] as PerformanceEntry & {
            renderTime?: number;
            loadTime?: number;
          };

          this.recordMetric('LCP', lastEntry.renderTime || lastEntry.loadTime || 0);
        });
        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
        this.observers.push(lcpObserver);
      } catch (e) {
        console.warn('LCP observer not supported:', e);
      }

      // Observe First Input Delay (FID)
      try {
        const fidObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            const fidEntry = entry as PerformanceEntry & { processingStart?: number };
            const fid = fidEntry.processingStart ? fidEntry.processingStart - entry.startTime : 0;
            this.recordMetric('FID', fid);
          });
        });
        fidObserver.observe({ entryTypes: ['first-input'] });
        this.observers.push(fidObserver);
      } catch (e) {
        console.warn('FID observer not supported:', e);
      }

      // Observe Cumulative Layout Shift (CLS)
      try {
        let clsValue = 0;
        const clsObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            const clsEntry = entry as PerformanceEntry & { hadRecentInput?: boolean; value?: number };
            if (!clsEntry.hadRecentInput) {
              clsValue += clsEntry.value || 0;
              this.recordMetric('CLS', clsValue);
            }
          });
        });
        clsObserver.observe({ entryTypes: ['layout-shift'] });
        this.observers.push(clsObserver);
      } catch (e) {
        console.warn('CLS observer not supported:', e);
      }
    }
  }

  /**
   * Record a performance metric
   */
  recordMetric(name: string, value: number, metadata?: Record<string, unknown>): void {
    if (!this.enabled) return;

    const metric: PerformanceMetric = {
      name,
      value,
      timestamp: Date.now(),
      metadata,
    };

    this.metrics.push(metric);

    // Keep only last 100 metrics to prevent memory leak
    if (this.metrics.length > 100) {
      this.metrics.shift();
    }
  }

  /**
   * Get page load metrics
   */
  getPageLoadMetrics(): PageLoadMetrics | null {
    if (typeof window === 'undefined' || !window.performance) {
      return null;
    }

    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    if (!navigation) {
      return null;
    }

    const paint = performance.getEntriesByType('paint');
    const fp = paint.find((entry) => entry.name === 'first-paint');
    const fcp = paint.find((entry) => entry.name === 'first-contentful-paint');

    const lcpMetric = this.metrics.find((m) => m.name === 'LCP');
    const fidMetric = this.metrics.find((m) => m.name === 'FID');
    const clsMetric = this.metrics.find((m) => m.name === 'CLS');

    return {
      dns: navigation.domainLookupEnd - navigation.domainLookupStart,
      tcp: navigation.connectEnd - navigation.connectStart,
      request: navigation.responseStart - navigation.requestStart,
      response: navigation.responseEnd - navigation.responseStart,
      domParsing: navigation.domInteractive - navigation.responseEnd,
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
      loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
      firstPaint: fp?.startTime,
      firstContentfulPaint: fcp?.startTime,
      largestContentfulPaint: lcpMetric?.value,
      firstInputDelay: fidMetric?.value,
      cumulativeLayoutShift: clsMetric?.value,
    };
  }

  /**
   * Measure API call duration
   */
  async measureApiCall<T>(
    name: string,
    apiCall: () => Promise<T>,
    metadata?: Record<string, unknown>
  ): Promise<T> {
    const startTime = performance.now();

    try {
      const result = await apiCall();
      const duration = performance.now() - startTime;

      this.recordMetric(`api.${name}`, duration, {
        ...metadata,
        status: 'success',
      });

      return result;
    } catch (error) {
      const duration = performance.now() - startTime;

      this.recordMetric(`api.${name}`, duration, {
        ...metadata,
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      throw error;
    }
  }

  /**
   * Measure component render time
   */
  measureRender(componentName: string, duration: number): void {
    this.recordMetric(`render.${componentName}`, duration);
  }

  /**
   * Get all recorded metrics
   */
  getMetrics(): PerformanceMetric[] {
    return [...this.metrics];
  }

  /**
   * Get metrics by name
   */
  getMetricsByName(name: string): PerformanceMetric[] {
    return this.metrics.filter((m) => m.name === name);
  }

  /**
   * Get average metric value
   */
  getAverageMetric(name: string): number | null {
    const metrics = this.getMetricsByName(name);
    if (metrics.length === 0) return null;

    const sum = metrics.reduce((acc, m) => acc + m.value, 0);
    return sum / metrics.length;
  }

  /**
   * Clear all metrics
   */
  clearMetrics(): void {
    this.metrics = [];
  }

  /**
   * Enable/disable monitoring
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }

  /**
   * Get performance summary
   */
  getSummary(): Record<string, { avg: number; min: number; max: number; count: number }> {
    const summary: Record<string, { avg: number; min: number; max: number; count: number }> = {};

    const metricNames = [...new Set(this.metrics.map((m) => m.name))];

    metricNames.forEach((name) => {
      const metrics = this.getMetricsByName(name);
      const values = metrics.map((m) => m.value);

      summary[name] = {
        avg: values.reduce((a, b) => a + b, 0) / values.length,
        min: Math.min(...values),
        max: Math.max(...values),
        count: values.length,
      };
    });

    return summary;
  }

  /**
   * Export metrics as JSON
   */
  exportMetrics(): string {
    return JSON.stringify({
      metrics: this.metrics,
      summary: this.getSummary(),
      pageLoad: this.getPageLoadMetrics(),
      timestamp: Date.now(),
    }, null, 2);
  }

  /**
   * Log performance summary to console
   */
  logSummary(): void {
    console.group('Performance Summary');

    const pageLoad = this.getPageLoadMetrics();
    if (pageLoad) {
      console.group('Page Load Metrics');
      console.table({
        'DNS Lookup': `${pageLoad.dns.toFixed(2)}ms`,
        'TCP Connection': `${pageLoad.tcp.toFixed(2)}ms`,
        'Request': `${pageLoad.request.toFixed(2)}ms`,
        'Response': `${pageLoad.response.toFixed(2)}ms`,
        'DOM Parsing': `${pageLoad.domParsing.toFixed(2)}ms`,
        'DOM Content Loaded': `${pageLoad.domContentLoaded.toFixed(2)}ms`,
        'Load Complete': `${pageLoad.loadComplete.toFixed(2)}ms`,
        'First Paint': pageLoad.firstPaint ? `${pageLoad.firstPaint.toFixed(2)}ms` : 'N/A',
        'First Contentful Paint': pageLoad.firstContentfulPaint ? `${pageLoad.firstContentfulPaint.toFixed(2)}ms` : 'N/A',
        'Largest Contentful Paint': pageLoad.largestContentfulPaint ? `${pageLoad.largestContentfulPaint.toFixed(2)}ms` : 'N/A',
        'First Input Delay': pageLoad.firstInputDelay ? `${pageLoad.firstInputDelay.toFixed(2)}ms` : 'N/A',
        'Cumulative Layout Shift': pageLoad.cumulativeLayoutShift ? pageLoad.cumulativeLayoutShift.toFixed(3) : 'N/A',
      });
      console.groupEnd();
    }

    const summary = this.getSummary();
    if (Object.keys(summary).length > 0) {
      console.group('Custom Metrics');
      console.table(
        Object.entries(summary).map(([name, stats]) => ({
          Metric: name,
          Average: `${stats.avg.toFixed(2)}ms`,
          Min: `${stats.min.toFixed(2)}ms`,
          Max: `${stats.max.toFixed(2)}ms`,
          Count: stats.count,
        }))
      );
      console.groupEnd();
    }

    console.groupEnd();
  }

  /**
   * Initialize performance monitoring
   */
  init(): void {
    if (typeof window !== 'undefined' && this.observers.length === 0) {
      this.initializeObservers();
    }
  }

  /**
   * Get performance report
   */
  getReport(): {
    webVitals: {
      LCP?: number;
      FID?: number;
      CLS?: number;
      FCP?: number;
      TTFB?: number;
    };
    apiMetrics: Record<string, {
      count: number;
      avgDuration: number;
      minDuration: number;
      maxDuration: number;
      errorCount: number;
    }>;
    customMetrics: Record<string, {
      count: number;
      avgValue: number;
      minValue: number;
      maxValue: number;
    }>;
  } {
    const pageLoad = this.getPageLoadMetrics();

    // Group API metrics
    const apiMetrics: Record<string, {
      count: number;
      avgDuration: number;
      minDuration: number;
      maxDuration: number;
      errorCount: number;
    }> = {};

    this.metrics
      .filter(m => m.name.startsWith('api.'))
      .forEach(metric => {
        const endpoint = metric.name.replace('api.', '');
        if (!apiMetrics[endpoint]) {
          apiMetrics[endpoint] = {
            count: 0,
            avgDuration: 0,
            minDuration: Infinity,
            maxDuration: 0,
            errorCount: 0,
          };
        }

        apiMetrics[endpoint].count++;
        apiMetrics[endpoint].avgDuration += metric.value;
        apiMetrics[endpoint].minDuration = Math.min(apiMetrics[endpoint].minDuration, metric.value);
        apiMetrics[endpoint].maxDuration = Math.max(apiMetrics[endpoint].maxDuration, metric.value);

        if (metric.metadata?.error) {
          apiMetrics[endpoint].errorCount++;
        }
      });

    // Calculate averages
    Object.keys(apiMetrics).forEach(endpoint => {
      apiMetrics[endpoint].avgDuration /= apiMetrics[endpoint].count;
    });

    // Group custom metrics
    const customMetrics: Record<string, {
      count: number;
      avgValue: number;
      minValue: number;
      maxValue: number;
    }> = {};

    this.metrics
      .filter(m => !m.name.startsWith('api.') && !['LCP', 'FID', 'CLS'].includes(m.name))
      .forEach(metric => {
        if (!customMetrics[metric.name]) {
          customMetrics[metric.name] = {
            count: 0,
            avgValue: 0,
            minValue: Infinity,
            maxValue: 0,
          };
        }

        customMetrics[metric.name].count++;
        customMetrics[metric.name].avgValue += metric.value;
        customMetrics[metric.name].minValue = Math.min(customMetrics[metric.name].minValue, metric.value);
        customMetrics[metric.name].maxValue = Math.max(customMetrics[metric.name].maxValue, metric.value);
      });

    // Calculate averages
    Object.keys(customMetrics).forEach(name => {
      customMetrics[name].avgValue /= customMetrics[name].count;
    });

    return {
      webVitals: {
        LCP: this.metrics.find(m => m.name === 'LCP')?.value,
        FID: this.metrics.find(m => m.name === 'FID')?.value,
        CLS: this.metrics.find(m => m.name === 'CLS')?.value,
        FCP: pageLoad?.firstContentfulPaint,
        TTFB: pageLoad ? pageLoad.request + pageLoad.response : undefined,
      },
      apiMetrics,
      customMetrics,
    };
  }

  /**
   * Cleanup observers
   */
  destroy(): void {
    this.observers.forEach((observer) => observer.disconnect());
    this.observers = [];
    this.metrics = [];
  }
}

// Singleton instance
export const performanceMonitor = new PerformanceMonitor();

// Expose to window for debugging
if (typeof window !== 'undefined') {
  (window as unknown as { performanceMonitor: PerformanceMonitor }).performanceMonitor = performanceMonitor;
}
