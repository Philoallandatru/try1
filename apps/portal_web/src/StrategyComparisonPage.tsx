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
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      <h1>多策略检索对比</h1>

      <div style={{ marginBottom: '20px', padding: '20px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            查询内容
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入要对比的查询..."
            style={{
              width: '100%',
              minHeight: '80px',
              padding: '10px',
              fontSize: '14px',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            选择策略 (至少选择2个)
          </label>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {availableStrategies.map(strategy => (
              <label
                key={strategy.value}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '8px 12px',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  backgroundColor: selectedStrategies.includes(strategy.value) ? '#007bff' : 'white',
                  color: selectedStrategies.includes(strategy.value) ? 'white' : 'black',
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedStrategies.includes(strategy.value)}
                  onChange={() => handleStrategyToggle(strategy.value)}
                  style={{ marginRight: '8px' }}
                />
                {strategy.label}
              </label>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            返回结果数
          </label>
          <input
            type="number"
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
            min="1"
            max="20"
            style={{
              width: '200px',
              padding: '8px',
              fontSize: '14px',
              border: '1px solid #ccc',
              borderRadius: '4px',
            }}
          />
        </div>

        <button
          onClick={handleCompare}
          disabled={loading}
          style={{
            padding: '10px 20px',
            fontSize: '16px',
            backgroundColor: loading ? '#ccc' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? '对比中...' : '开始对比'}
        </button>
      </div>

      {error && (
        <div style={{
          padding: '15px',
          marginBottom: '20px',
          backgroundColor: '#f8d7da',
          color: '#721c24',
          border: '1px solid #f5c6cb',
          borderRadius: '4px',
        }}>
          错误: {error}
        </div>
      )}

      {result && (
        <div>
          <div style={{
            padding: '15px',
            marginBottom: '20px',
            backgroundColor: '#d4edda',
            border: '1px solid #c3e6cb',
            borderRadius: '4px',
          }}>
            <h3 style={{ marginTop: 0 }}>对比指标</h3>
            <p><strong>结果重叠率:</strong> {(result.comparison_metrics.overlap_rate * 100).toFixed(1)}%</p>
            <p><strong>平均分数差异:</strong> {result.comparison_metrics.avg_score_diff.toFixed(4)}</p>
          </div>

          <h2>策略对比结果</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', gap: '20px' }}>
            {result.strategies.map((strategyResult) => (
              <div
                key={strategyResult.strategy}
                style={{
                  padding: '15px',
                  border: '2px solid #007bff',
                  borderRadius: '8px',
                  backgroundColor: '#f8f9fa',
                }}
              >
                <h3 style={{ marginTop: 0, color: '#007bff' }}>
                  {availableStrategies.find(s => s.value === strategyResult.strategy)?.label || strategyResult.strategy}
                </h3>

                <div style={{ marginBottom: '15px', fontSize: '14px', color: '#666' }}>
                  <p><strong>检索时间:</strong> {strategyResult.metrics.retrieval_time_ms.toFixed(2)} ms</p>
                  <p><strong>结果数量:</strong> {strategyResult.metrics.total_results}</p>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {strategyResult.results.map((doc, index) => (
                    <div
                      key={doc.doc_id}
                      style={{
                        padding: '10px',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        backgroundColor: 'white',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ fontSize: '14px', fontWeight: 'bold' }}>
                          #{index + 1} - {doc.doc_id}
                        </span>
                        <span style={{
                          padding: '2px 6px',
                          backgroundColor: doc.score > 0.8 ? '#28a745' : doc.score > 0.5 ? '#ffc107' : '#dc3545',
                          color: 'white',
                          borderRadius: '3px',
                          fontSize: '12px',
                        }}>
                          {doc.score.toFixed(3)}
                        </span>
                      </div>
                      <p style={{
                        margin: 0,
                        fontSize: '13px',
                        lineHeight: '1.5',
                        color: '#333',
                      }}>
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
