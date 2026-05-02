import React, { useState } from 'react';
import './retrieval-debug.css';

interface DebugResult {
  query: string;
  results: Array<{
    doc_id: string;
    content: string;
    score: number;
    metadata: Record<string, any>;
  }>;
  debug_info: {
    query_embedding?: number[];
    retrieval_time_ms: number;
    total_docs: number;
    strategy: string;
  };
}

export default function RetrievalDebugPage() {
  const [query, setQuery] = useState('');
  const [strategy, setStrategy] = useState('hybrid');
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DebugResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDebug = async () => {
    if (!query.trim()) {
      setError('请输入查询内容');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/retrieval/debug', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          strategy,
          top_k: topK,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '调试失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container retrieval-debug-container">
      <header className="page-header retrieval-debug-header">
        <h1 className="retrieval-debug-title">检索调试工具</h1>
        <p className="page-description retrieval-debug-description">深入分析检索过程和结果质量</p>
      </header>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <div className="mb-6">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            查询内容
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入要调试的查询..."
            className="w-full min-h-[80px] px-4 py-3 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              检索策略
            </label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full px-4 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="hybrid">混合检索</option>
              <option value="semantic">语义检索</option>
              <option value="keyword">关键词检索</option>
              <option value="splade">SPLADE</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              返回结果数
            </label>
            <input
              type="number"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
              min="1"
              max="20"
              className="w-full px-4 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <button
          onClick={handleDebug}
          disabled={loading}
          className={`px-6 py-3 text-base font-semibold rounded-lg transition-all ${
            loading
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow-md'
          }`}
        >
          {loading ? '调试中...' : '开始调试'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg mb-6">
          <span className="font-semibold">错误:</span> {error}
        </div>
      )}

      {result && (
        <div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">调试信息</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-gray-600 mb-1">策略</p>
                <p className="font-semibold text-gray-900">{result.debug_info.strategy}</p>
              </div>
              <div>
                <p className="text-gray-600 mb-1">检索时间</p>
                <p className="font-semibold text-gray-900">{result.debug_info.retrieval_time_ms.toFixed(2)} ms</p>
              </div>
              <div>
                <p className="text-gray-600 mb-1">文档总数</p>
                <p className="font-semibold text-gray-900">{result.debug_info.total_docs}</p>
              </div>
              <div>
                <p className="text-gray-600 mb-1">返回结果</p>
                <p className="font-semibold text-gray-900">{result.results.length}</p>
              </div>
            </div>
          </div>

          <h2 className="text-xl font-bold text-gray-900 mb-4">检索结果</h2>
          {result.results.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
              <p className="text-gray-500">未找到相关结果</p>
            </div>
          ) : (
            <div className="space-y-4">
              {result.results.map((doc, index) => (
                <div
                  key={doc.doc_id}
                  className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow"
                >
                  <div className="flex justify-between items-start mb-3">
                    <h3 className="text-base font-semibold text-gray-900">
                      #{index + 1} - {doc.doc_id}
                    </h3>
                    <span className={`px-3 py-1 rounded-lg text-sm font-bold text-white ${
                      doc.score > 0.8 ? 'bg-green-500' : doc.score > 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}>
                      {doc.score.toFixed(4)}
                    </span>
                  </div>

                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-3">
                    <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                      {doc.content}
                    </p>
                  </div>

                  {Object.keys(doc.metadata).length > 0 && (
                    <details className="mt-3">
                      <summary className="cursor-pointer font-semibold text-sm text-gray-700 hover:text-gray-900">
                        元数据
                      </summary>
                      <pre className="mt-2 p-3 bg-gray-100 border border-gray-200 rounded-lg text-xs overflow-auto">
                        {JSON.stringify(doc.metadata, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
