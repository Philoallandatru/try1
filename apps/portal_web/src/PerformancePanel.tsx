import React, { useState, useEffect } from 'react';
import { performanceMonitor } from './performanceMonitor';
import { BarChart3, X, Download } from 'lucide-react';

export function PerformancePanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [report, setReport] = useState(performanceMonitor.getReport());

  useEffect(() => {
    if (!isOpen) return;

    const interval = setInterval(() => {
      setReport(performanceMonitor.getReport());
    }, 1000);

    return () => clearInterval(interval);
  }, [isOpen]);

  const handleExport = () => {
    const json = performanceMonitor.exportMetrics();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `performance-metrics-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!import.meta.env.DEV) return null;

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-4 right-4 p-3 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 z-50"
        title="Performance Monitor"
      >
        <BarChart3 size={20} />
      </button>

      {isOpen && (
        <div className="fixed bottom-20 right-4 w-96 bg-white border border-gray-300 rounded-lg shadow-xl z-50 max-h-[600px] overflow-auto">
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <h3 className="font-semibold text-gray-900">Performance Monitor</h3>
            <div className="flex gap-2">
              <button
                onClick={handleExport}
                className="p-1 hover:bg-gray-100 rounded"
                title="Export metrics"
              >
                <Download size={16} />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          <div className="p-4 space-y-4">
            {/* Web Vitals */}
            <div>
              <h4 className="font-medium text-sm text-gray-700 mb-2">Web Vitals</h4>
              <div className="space-y-1 text-sm">
                {report.webVitals.LCP && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">LCP:</span>
                    <span className={getVitalColor(report.webVitals.LCP, 2500, 4000)}>
                      {report.webVitals.LCP.toFixed(0)}ms
                    </span>
                  </div>
                )}
                {report.webVitals.FID && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">FID:</span>
                    <span className={getVitalColor(report.webVitals.FID, 100, 300)}>
                      {report.webVitals.FID.toFixed(0)}ms
                    </span>
                  </div>
                )}
                {report.webVitals.CLS && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">CLS:</span>
                    <span className={getVitalColor(report.webVitals.CLS, 0.1, 0.25)}>
                      {report.webVitals.CLS.toFixed(3)}
                    </span>
                  </div>
                )}
                {report.webVitals.FCP && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">FCP:</span>
                    <span className={getVitalColor(report.webVitals.FCP, 1800, 3000)}>
                      {report.webVitals.FCP.toFixed(0)}ms
                    </span>
                  </div>
                )}
                {report.webVitals.TTFB && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">TTFB:</span>
                    <span className={getVitalColor(report.webVitals.TTFB, 800, 1800)}>
                      {report.webVitals.TTFB.toFixed(0)}ms
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* API Performance */}
            <div>
              <h4 className="font-medium text-sm text-gray-700 mb-2">API Performance</h4>
              <div className="space-y-2 text-sm">
                {Object.entries(report.apiMetrics).map(([endpoint, metrics]) => (
                  <div key={endpoint} className="border-l-2 border-blue-500 pl-2">
                    <div className="font-medium text-gray-800 truncate" title={endpoint}>
                      {endpoint.split('/').pop() || endpoint}
                    </div>
                    <div className="text-xs text-gray-600 space-y-0.5">
                      <div>Calls: {metrics.count}</div>
                      <div>Avg: {metrics.avgDuration.toFixed(0)}ms</div>
                      <div>Min: {metrics.minDuration.toFixed(0)}ms</div>
                      <div>Max: {metrics.maxDuration.toFixed(0)}ms</div>
                      {metrics.errorCount > 0 && (
                        <div className="text-red-600">
                          Errors: {metrics.errorCount} ({((metrics.errorCount / metrics.count) * 100).toFixed(1)}%)
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Custom Metrics */}
            {Object.keys(report.customMetrics).length > 0 && (
              <div>
                <h4 className="font-medium text-sm text-gray-700 mb-2">Custom Metrics</h4>
                <div className="space-y-1 text-sm">
                  {Object.entries(report.customMetrics).map(([name, metrics]) => (
                    <div key={name} className="flex justify-between">
                      <span className="text-gray-600 truncate" title={name}>
                        {name}:
                      </span>
                      <span className="text-gray-900">
                        {metrics.avgValue.toFixed(2)} ({metrics.count}x)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function getVitalColor(value: number, goodThreshold: number, needsImprovementThreshold: number): string {
  if (value <= goodThreshold) return 'text-green-600 font-medium';
  if (value <= needsImprovementThreshold) return 'text-yellow-600 font-medium';
  return 'text-red-600 font-medium';
}
