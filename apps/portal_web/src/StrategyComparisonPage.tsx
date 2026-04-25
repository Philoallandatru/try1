import React, { useState } from 'react';

interface StrategyResult {
  strategy: string;
  results: Array<{
    doc_id: string;
    content: string;
    score: number;
  }>;
  metrics: {
    retrieval_time_ms: number;
    total_results: number;
  };
}

interface ComparisonResult {
  query: string;
  strategies: StrategyResult[];
  comparison_metrics: {
    overlap_rate: number;
    avg_score_diff: number;
  };
}

export default function StrategyComparisonPage() {
  const [query, setQuery] = useState('');
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>(['hybrid', 'semantic']);
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const availableStrategies = [
    { value: 'hybrid', label: '混合检索' },
    { value: 'semantic', label: '语义检索' },
    { value: 'keyword', label: '关键词检索' },
    { value: 'splade', label: 'SPLADE' },
  ];

  const handleStrategyToggle = (strategy: string) => {
    setSelectedStrategies(prev =>
      prev.includes(strategy)
        ? prev.filter(s => s !== strategy)
        : [...prev, strategy]
    );
  };

  const handleCompare = async () => {
    if (!query.trim()) {
      setError('请输入查询内容');
      return;
    }

    if (selectedStrategies.length < 2) {
      setError('请至少选择两个策略进行对比');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/retrieval/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          strategies: selectedStrategies,
          top_k: topK,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '对比失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container" style={{ maxWidth: '1400px', margin: '0 auto' }}>
      <header className="page-header" style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: '700', marginBottom: '0.5rem' }}>多策略检索对比</h1>
        <p className="page-description" style={{ fontSize: '1rem', color: '#6b7280' }}>对比不同检索策略的性能和结果</p>
      </header>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <div className="mb-6">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            查询内容
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入要对比的查询..."
            className="w-full min-h-[80px] px-4 py-3 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>

        <div className="mb-6">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            选择策略 (至少选择2个)
          </label>
          <div className="flex gap-3 flex-wrap">
            {availableStrategies.map(strategy => (
              <label
                key={strategy.value}
                className={`flex items-center px-4 py-2 border-2 rounded-lg cursor-pointer transition-all ${
                  selectedStrategies.includes(strategy.value)
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedStrategies.includes(strategy.value)}
                  onChange={() => handleStrategyToggle(strategy.value)}
                  className="mr-2 w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <span className="font-medium">{strategy.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            返回结果数
          </label>
          <input
            type="number"
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
            min="1"
            max="20"
            className="w-48 px-4 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <button
          onClick={handleCompare}
          disabled={loading}
          className={`px-6 py-3 text-base font-semibold rounded-lg transition-all ${
            loading
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow-md'
          }`}
        >
          {loading ? '对比中...' : '开始对比'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg mb-6">
          <span className="font-semibold">错误:</span> {error}
        </div>
      )}

      {result && (
        <div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">对比指标</h3>
            <div className="space-y-2 text-sm">
              <p className="text-gray-700">
                <span className="font-semibold">结果重叠率:</span> {(result.comparison_metrics.overlap_rate * 100).toFixed(1)}%
              </p>
              <p className="text-gray-700">
                <span className="font-semibold">平均分数差异:</span> {result.comparison_metrics.avg_score_diff.toFixed(4)}
              </p>
            </div>
          </div>

          <h2 className="text-xl font-bold text-gray-900 mb-4">策略对比结果</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {result.strategies.map((strategyResult) => (
              <div
                key={strategyResult.strategy}
                className="bg-white border-2 border-blue-500 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow"
              >
                <h3 className="text-lg font-bold text-blue-600 mb-4">
                  {availableStrategies.find(s => s.value === strategyResult.strategy)?.label || strategyResult.strategy}
                </h3>

                <div className="mb-4 space-y-1 text-sm text-gray-600">
                  <p>
                    <span className="font-semibold">检索时间:</span> {strategyResult.metrics.retrieval_time_ms.toFixed(2)} ms
                  </p>
                  <p>
                    <span className="font-semibold">结果数量:</span> {strategyResult.metrics.total_results}
                  </p>
                </div>

                <div className="space-y-3">
                  {strategyResult.results.map((doc, index) => (
                    <div
                      key={doc.doc_id}
                      className="bg-gray-50 border border-gray-200 rounded-lg p-3 hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-sm font-semibold text-gray-900">
                          #{index + 1} - {doc.doc_id}
                        </span>
                        <span className={`px-2 py-1 rounded text-xs font-bold text-white ${
                          doc.score > 0.8 ? 'bg-green-500' : doc.score > 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}>
                          {doc.score.toFixed(3)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 leading-relaxed">
                        {doc.content.length > 150 ? doc.content.substring(0, 150) + '...' : doc.content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
