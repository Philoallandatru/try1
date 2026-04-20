import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';

interface BatchAnalysisResult {
  batch_id: string;
  started_at: string;
  completed_at?: string;
  total: number;
  completed: number;
  failed: number;
  results: Array<{
    issue_id: string;
    success: boolean;
    result?: any;
    error?: string;
  }>;
}

export function BatchAnalysisPage() {
  const [selectedIssues, setSelectedIssues] = useState<string[]>([]);
  const [issueInput, setIssueInput] = useState('');
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null);

  // Fetch batch list
  const { data: batches } = useQuery({
    queryKey: ['batches'],
    queryFn: async () => {
      const workspaceDir = localStorage.getItem('workspace_dir') || '/workspace';
      const response = await fetch(`/api/analysis/batches?workspace_dir=${encodeURIComponent(workspaceDir)}`);
      if (!response.ok) throw new Error('Failed to fetch batches');
      return response.json();
    },
    refetchInterval: 5000,
  });

  // Fetch current batch result
  const { data: batchResult } = useQuery({
    queryKey: ['batch', currentBatchId],
    queryFn: async () => {
      if (!currentBatchId) return null;
      const workspaceDir = localStorage.getItem('workspace_dir') || '/workspace';
      const response = await fetch(`/api/analysis/batch/${currentBatchId}?workspace_dir=${encodeURIComponent(workspaceDir)}`);
      if (!response.ok) throw new Error('Failed to fetch batch result');
      return response.json();
    },
    enabled: !!currentBatchId,
    refetchInterval: (query) => {
      // Stop polling if batch is complete
      if (query.state.data && query.state.data.completed_at) return false;
      return 2000;
    },
  });

  // Start batch analysis mutation
  const startBatchMutation = useMutation({
    mutationFn: async (issueIds: string[]) => {
      const workspaceDir = localStorage.getItem('workspace_dir') || '/workspace';
      const response = await fetch('/api/analysis/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_dir: workspaceDir,
          issue_ids: issueIds,
          llm_backend: 'none',
          max_concurrent: 5,
        }),
      });
      if (!response.ok) throw new Error('Failed to start batch analysis');
      return response.json();
    },
    onSuccess: (data) => {
      setCurrentBatchId(data.batch_id);
      setSelectedIssues([]);
    },
  });

  const handleAddIssue = () => {
    const trimmed = issueInput.trim();
    if (trimmed && !selectedIssues.includes(trimmed)) {
      setSelectedIssues([...selectedIssues, trimmed]);
      setIssueInput('');
    }
  };

  const handleRemoveIssue = (issueId: string) => {
    setSelectedIssues(selectedIssues.filter(id => id !== issueId));
  };

  const handleStartBatch = () => {
    if (selectedIssues.length > 0) {
      startBatchMutation.mutate(selectedIssues);
    }
  };

  const handleExport = async (batchId: string, format: 'markdown' | 'html') => {
    const workspaceDir = localStorage.getItem('workspace_dir') || '/workspace';
    const url = `/api/export/batch/${batchId}/${format}?workspace_dir=${encodeURIComponent(workspaceDir)}`;
    window.open(url, '_blank');
  };

  return (
    <div className="batch-analysis-page">
      <h1>Batch Analysis</h1>

      {/* Issue Selection */}
      <div className="batch-section">
        <h2>Select Issues</h2>
        <div className="issue-input-group">
          <input
            type="text"
            value={issueInput}
            onChange={(e) => setIssueInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddIssue()}
            placeholder="Enter issue ID (e.g., SSD-100)"
            className="issue-input"
          />
          <button onClick={handleAddIssue} className="btn-add">Add</button>
        </div>

        {selectedIssues.length > 0 && (
          <div className="selected-issues">
            <h3>Selected Issues ({selectedIssues.length})</h3>
            <div className="issue-chips">
              {selectedIssues.map(issueId => (
                <div key={issueId} className="issue-chip">
                  <span>{issueId}</span>
                  <button onClick={() => handleRemoveIssue(issueId)} className="btn-remove">×</button>
                </div>
              ))}
            </div>
            <button
              onClick={handleStartBatch}
              disabled={startBatchMutation.isPending}
              className="btn-primary"
            >
              {startBatchMutation.isPending ? 'Starting...' : 'Start Batch Analysis'}
            </button>
          </div>
        )}
      </div>

      {/* Current Batch Progress */}
      {batchResult && (
        <div className="batch-section">
          <h2>Current Batch: {currentBatchId}</h2>
          <div className="batch-progress">
            <div className="progress-stats">
              <div className="stat">
                <span className="stat-label">Total:</span>
                <span className="stat-value">{batchResult.total}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Completed:</span>
                <span className="stat-value success">{batchResult.completed}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Failed:</span>
                <span className="stat-value error">{batchResult.failed}</span>
              </div>
            </div>

            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${(batchResult.completed / batchResult.total) * 100}%` }}
              />
            </div>

            {batchResult.completed_at && (
              <div className="batch-actions">
                <button onClick={() => handleExport(currentBatchId!, 'markdown')} className="btn-secondary">
                  Export as Markdown
                </button>
                <button onClick={() => handleExport(currentBatchId!, 'html')} className="btn-secondary">
                  Export as HTML
                </button>
              </div>
            )}
          </div>

          {/* Results List */}
          <div className="batch-results">
            <h3>Results</h3>
            {batchResult.results.map((result: any) => (
              <div key={result.issue_id} className={`result-item ${result.success ? 'success' : 'error'}`}>
                <span className="result-icon">{result.success ? '✓' : '✗'}</span>
                <span className="result-issue">{result.issue_id}</span>
                {result.error && <span className="result-error">{result.error}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Batch History */}
      {batches && batches.length > 0 && (
        <div className="batch-section">
          <h2>Batch History</h2>
          <div className="batch-list">
            {batches.map((batch: any) => (
              <div key={batch.batch_id} className="batch-item">
                <div className="batch-info">
                  <span className="batch-id">{batch.batch_id}</span>
                  <span className="batch-date">{new Date(batch.started_at).toLocaleString()}</span>
                  <span className="batch-stats">
                    {batch.completed}/{batch.total} completed
                  </span>
                </div>
                <div className="batch-item-actions">
                  <button onClick={() => setCurrentBatchId(batch.batch_id)} className="btn-link">
                    View
                  </button>
                  {batch.completed_at && (
                    <>
                      <button onClick={() => handleExport(batch.batch_id, 'markdown')} className="btn-link">
                        Markdown
                      </button>
                      <button onClick={() => handleExport(batch.batch_id, 'html')} className="btn-link">
                        HTML
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
