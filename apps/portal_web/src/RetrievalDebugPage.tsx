import React, { useState } from 'react';

interface DebugResult {
  query: string;
  results: Array<{
    doc_id: string;
    content: string;
    score: float;
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
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>检索调试工具</h1>

      <div style={{ marginBottom: '20px', padding: '20px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            查询内容
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入要调试的查询..."
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

        <div style={{ display: 'flex', gap: '20px', marginBottom: '15px' }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              检索策略
            </label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                fontSize: '14px',
                border: '1px solid #ccc',
                borderRadius: '4px',
              }}
            >
              <option value="hybrid">混合检索</option>
              <option value="semantic">语义检索</option>
              <option value="keyword">关键词检索</option>
              <option value="splade">SPLADE</option>
            </select>
          </div>

          <div style={{ flex: 1 }}>
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
                width: '100%',
                padding: '8px',
                fontSize: '14px',
                border: '1px solid #ccc',
                borderRadius: '4px',
              }}
            />
          </div>
        </div>

        <button
          onClick={handleDebug}
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
          {loading ? '调试中...' : '开始调试'}
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
            <h3 style={{ marginTop: 0 }}>调试信息</h3>
            <p><strong>策略:</strong> {result.debug_info.strategy}</p>
            <p><strong>检索时间:</strong> {result.debug_info.retrieval_time_ms.toFixed(2)} ms</p>
            <p><strong>文档总数:</strong> {result.debug_info.total_docs}</p>
            <p><strong>返回结果:</strong> {result.results.length}</p>
          </div>

          <h2>检索结果</h2>
          {result.results.length === 0 ? (
            <p style={{ color: '#666' }}>未找到相关结果</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              {result.results.map((doc, index) => (
                <div
                  key={doc.doc_id}
                  style={{
                    padding: '15px',
                    border: '1px solid #ddd',
                    borderRadius: '8px',
                    backgroundColor: '#f9f9f9',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <h3 style={{ margin: 0, fontSize: '16px' }}>
                      #{index + 1} - {doc.doc_id}
                    </h3>
                    <span style={{
                      padding: '4px 8px',
                      backgroundColor: doc.score > 0.8 ? '#28a745' : doc.score > 0.5 ? '#ffc107' : '#dc3545',
                      color: 'white',
                      borderRadius: '4px',
                      fontSize: '14px',
                      fontWeight: 'bold',
                    }}>
                      {doc.score.toFixed(4)}
                    </span>
                  </div>

                  <p style={{
                    margin: '10px 0',
                    padding: '10px',
                    backgroundColor: 'white',
                    border: '1px solid #e0e0e0',
                    borderRadius: '4px',
                    fontSize: '14px',
                    lineHeight: '1.6',
                  }}>
                    {doc.content}
                  </p>

                  {Object.keys(doc.metadata).length > 0 && (
                    <details style={{ marginTop: '10px' }}>
                      <summary style={{ cursor: 'pointer', fontWeight: 'bold', fontSize: '14px' }}>
                        元数据
                      </summary>
                      <pre style={{
                        marginTop: '10px',
                        padding: '10px',
                        backgroundColor: '#f5f5f5',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        fontSize: '12px',
                        overflow: 'auto',
                      }}>
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
