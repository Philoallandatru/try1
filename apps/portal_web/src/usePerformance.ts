import { useEffect, useRef } from 'react';
import { performanceMonitor } from './performanceMonitor';

/**
 * Hook to measure component render performance
 */
export function useRenderPerformance(componentName: string) {
  const renderCount = useRef(0);
  const startTime = useRef(performance.now());

  useEffect(() => {
    const duration = performance.now() - startTime.current;
    renderCount.current += 1;

    performanceMonitor.measureRender(componentName, duration);

    // Reset start time for next render
    startTime.current = performance.now();
  });

  return renderCount.current;
}

/**
 * Hook to measure API call performance
 */
export function useApiPerformance() {
  return {
    measureApiCall: performanceMonitor.measureApiCall.bind(performanceMonitor),
  };
}

/**
 * Hook to track page load metrics
 */
export function usePageLoadMetrics() {
  useEffect(() => {
    // Wait for page to fully load
    const handleLoad = () => {
      setTimeout(() => {
        const metrics = performanceMonitor.getPageLoadMetrics();
        if (metrics) {
          console.log('Page Load Metrics:', metrics);
        }
      }, 0);
    };

    if (document.readyState === 'complete') {
      handleLoad();
    } else {
      window.addEventListener('load', handleLoad);
      return () => window.removeEventListener('load', handleLoad);
    }
  }, []);
}

/**
 * Hook to measure effect execution time
 */
export function useEffectPerformance(effectName: string, effect: () => void | (() => void), deps: unknown[]) {
  useEffect(() => {
    const startTime = performance.now();
    const cleanup = effect();
    const duration = performance.now() - startTime;

    performanceMonitor.recordMetric(`effect.${effectName}`, duration);

    return cleanup;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
