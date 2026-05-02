import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiJson } from "./apiUtils";
import "./retrieval-evaluation.css";
import {
  Upload,
  Play,
  Trash2,
  BarChart3,
  FileText,
  CheckCircle2,
  XCircle,
  Loader2,
  Database,
  TrendingUp,
  AlertCircle,
} from "lucide-react";

// Schemas
const datasetSchema = z.object({
  dataset_id: z.string(),
  name: z.string(),
  description: z.string(),
  version: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
  total_queries: z.number(),
  total_documents: z.number(),
  categories: z.record(z.string(), z.number()),
});

const datasetsResponseSchema = z.object({
  status: z.string(),
  datasets: z.array(datasetSchema),
});

const evaluationResultSchema = z.object({
  run_id: z.string(),
  dataset_id: z.string(),
  dataset_name: z.string(),
  timestamp: z.string(),
  top_k: z.number(),
  total_queries: z.number(),
  aggregate_metrics: z.object({
    mean_average_precision: z.number(),
    mean_reciprocal_rank: z.number(),
    mean_ndcg_at_5: z.number(),
    mean_ndcg_at_10: z.number(),
    mean_precision_at_5: z.number(),
    mean_recall_at_5: z.number(),
  }),
});

const evaluationResultsResponseSchema = z.object({
  status: z.string(),
  results: z.array(evaluationResultSchema),
});

const evaluateResponseSchema = z.object({
  status: z.string(),
  run_id: z.string().optional(),
  aggregate_metrics: z.object({
    total_queries: z.number(),
    mean_average_precision: z.number(),
    mean_reciprocal_rank: z.number(),
    mean_ndcg_at_5: z.number(),
    mean_ndcg_at_10: z.number(),
    mean_precision_at_1: z.number(),
    mean_precision_at_3: z.number(),
    mean_precision_at_5: z.number(),
    mean_precision_at_10: z.number(),
    mean_recall_at_1: z.number(),
    mean_recall_at_3: z.number(),
    mean_recall_at_5: z.number(),
    mean_recall_at_10: z.number(),
  }),
  per_query_results: z.array(z.object({
    query_id: z.string(),
    query_text: z.string(),
    average_precision: z.number(),
    reciprocal_rank: z.number(),
    ndcg_at_5: z.number(),
    precision_at_5: z.number(),
    recall_at_5: z.number(),
  })),
});

type Dataset = z.infer<typeof datasetSchema>;
type EvaluationResult = z.infer<typeof evaluationResultSchema>;
type EvaluateResponse = z.infer<typeof evaluateResponseSchema>;

export function RetrievalEvaluationPage({ workspaceDir }: { workspaceDir: string }) {
  const [activeTab, setActiveTab] = useState<"datasets" | "evaluate" | "results">("datasets");
  const [selectedDataset, setSelectedDataset] = useState<string>("");
  const [selectedResult, setSelectedResult] = useState<string>("");
  const [uploadContent, setUploadContent] = useState("");
  const [evaluationResult, setEvaluationResult] = useState<EvaluateResponse | null>(null);

  const queryClient = useQueryClient();

  // Fetch datasets
  const datasets = useQuery({
    queryKey: ["retrieval-datasets"],
    queryFn: () => apiJson("/api/retrieval/datasets", datasetsResponseSchema),
  });

  // Fetch evaluation results
  const evaluationResults = useQuery({
    queryKey: ["retrieval-results"],
    queryFn: () => apiJson("/api/retrieval/results", evaluationResultsResponseSchema),
  });

  // Upload dataset mutation
  const uploadDataset = useMutation({
    mutationFn: (content: string) =>
      apiJson(
        "/api/retrieval/datasets",
        z.object({ status: z.string(), dataset: datasetSchema }),
        {
          method: "POST",
          body: JSON.stringify({ content }),
        }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["retrieval-datasets"] });
      setUploadContent("");
    },
  });

  // Delete dataset mutation
  const deleteDataset = useMutation({
    mutationFn: (datasetId: string) =>
      apiJson(
        `/api/retrieval/datasets/${datasetId}`,
        z.object({ status: z.string(), message: z.string() }),
        { method: "DELETE" }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["retrieval-datasets"] });
    },
  });

  // Run evaluation mutation
  const runEvaluation = useMutation({
    mutationFn: ({ datasetPath, topK }: { datasetPath: string; topK: number }) =>
      apiJson(
        "/api/retrieval/evaluate",
        evaluateResponseSchema,
        {
          method: "POST",
          body: JSON.stringify({
            golden_dataset_path: datasetPath,
            top_k: topK,
            save_result: true,
          }),
        }
      ),
    onSuccess: (data) => {
      setEvaluationResult(data);
      queryClient.invalidateQueries({ queryKey: ["retrieval-results"] });
      setActiveTab("results");
    },
  });

  // Delete evaluation result mutation
  const deleteResult = useMutation({
    mutationFn: (runId: string) =>
      apiJson(
        `/api/retrieval/results/${runId}`,
        z.object({ status: z.string(), message: z.string() }),
        { method: "DELETE" }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["retrieval-results"] });
    },
  });

  return (
    <section className="page-grid">
      <div className="primary-surface">
        <div className="section-heading">
          <p className="eyebrow">Retrieval Evaluation</p>
          <h2>检索质量评估</h2>
          <p>管理 Golden Datasets，执行评估，查看检索质量指标</p>
        </div>

        {/* Tabs */}
        <div className="run-tabs" role="tablist">
          <button
            className={activeTab === "datasets" ? "active" : ""}
            onClick={() => setActiveTab("datasets")}
            type="button"
          >
            <Database size={16} /> Datasets
          </button>
          <button
            className={activeTab === "evaluate" ? "active" : ""}
            onClick={() => setActiveTab("evaluate")}
            type="button"
          >
            <Play size={16} /> Run Evaluation
          </button>
          <button
            className={activeTab === "results" ? "active" : ""}
            onClick={() => setActiveTab("results")}
            type="button"
          >
            <BarChart3 size={16} /> Results
          </button>
        </div>

        {/* Dataset Management Tab */}
        {activeTab === "datasets" && (
          <div className="tab-panel">
            <div className="section-heading">
              <h3>Golden Datasets</h3>
              <p>上传和管理评估数据集</p>
            </div>

            {/* Upload Dataset */}
            <div className="stack-form">
              <label>
                Upload Dataset (YAML)
                <textarea
                  value={uploadContent}
                  onChange={(e) => setUploadContent(e.target.value)}
                  placeholder="Paste YAML content here..."
                  rows={10}
                  className="retrieval-eval-textarea"
                />
              </label>
              <button
                disabled={!uploadContent.trim() || uploadDataset.isPending}
                onClick={() => uploadDataset.mutate(uploadContent)}
                type="button"
              >
                {uploadDataset.isPending ? (
                  <><Loader2 size={16} className="spin" /> Uploading...</>
                ) : (
                  <><Upload size={16} /> Upload Dataset</>
                )}
              </button>
              {uploadDataset.error && (
                <div className="error">
                  <XCircle size={16} /> {String(uploadDataset.error.message)}
                </div>
              )}
            </div>

            {/* Dataset List */}
            <div className="list-stack">
              <p className="eyebrow">Available Datasets ({datasets.data?.datasets.length || 0})</p>
              {datasets.isLoading && <p>Loading datasets...</p>}
              {datasets.data?.datasets.map((dataset) => (
                <div className="list-row" key={dataset.dataset_id}>
                  <div>
                    <strong>{dataset.name}</strong>
                    <p className="dataset-description">
                      {dataset.description}
                    </p>
                    <div className="dataset-metadata">
                      <span>{dataset.total_queries} queries</span>
                      <span>{dataset.total_documents} documents</span>
                      <span>v{dataset.version}</span>
                    </div>
                    <div className="dataset-categories">
                      {Object.entries(dataset.categories).map(([cat, count]) => (
                        <span key={cat} className="pill category-pill">
                          {cat}: {count}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="row-actions">
                    <button
                      onClick={() => {
                        setSelectedDataset(dataset.dataset_id);
                        setActiveTab("evaluate");
                      }}
                      type="button"
                    >
                      <Play size={14} /> Evaluate
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Delete dataset "${dataset.name}"?`)) {
                          deleteDataset.mutate(dataset.dataset_id);
                        }
                      }}
                      type="button"
                    >
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
                </div>
              ))}
              {datasets.data?.datasets.length === 0 && (
                <div className="empty-state">
                  <FileText size={48} />
                  <p>No datasets uploaded yet</p>
                  <p className="empty-state-hint">Upload a YAML dataset above to get started</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Evaluation Tab */}
        {activeTab === "evaluate" && (
          <div className="tab-panel">
            <div className="section-heading">
              <h3>Run Evaluation</h3>
              <p>执行检索评估并查看指标</p>
            </div>

            <form
              className="stack-form"
              onSubmit={(e) => {
                e.preventDefault();
                const formData = new FormData(e.currentTarget);
                const datasetPath = formData.get("datasetPath") as string;
                const topK = parseInt(formData.get("topK") as string);
                runEvaluation.mutate({ datasetPath, topK });
              }}
            >
              <label>
                Dataset Path
                <input
                  name="datasetPath"
                  defaultValue="data/golden_dataset.yaml"
                  placeholder="data/golden_dataset.yaml"
                  required
                />
              </label>
              <label>
                Top K
                <input
                  name="topK"
                  type="number"
                  defaultValue={10}
                  min={1}
                  max={100}
                  required
                />
              </label>
              <button disabled={runEvaluation.isPending} type="submit">
                {runEvaluation.isPending ? (
                  <><Loader2 size={16} className="spin" /> Running...</>
                ) : (
                  <><Play size={16} /> Run Evaluation</>
                )}
              </button>
            </form>

            {runEvaluation.error && (
              <div className="error">
                <XCircle size={16} /> {String(runEvaluation.error.message)}
              </div>
            )}

            {evaluationResult && (
              <div className="evaluation-results">
                <div className="section-heading">
                  <h3>Evaluation Results</h3>
                  {evaluationResult.run_id && (
                    <p className="run-id-text">
                      Run ID: {evaluationResult.run_id}
                    </p>
                  )}
                </div>

                {/* Aggregate Metrics */}
                <div className="coverage-grid metrics-grid">
                  <MetricCard
                    label="MAP"
                    value={evaluationResult.aggregate_metrics.mean_average_precision.toFixed(3)}
                    icon={<TrendingUp size={16} />}
                  />
                  <MetricCard
                    label="MRR"
                    value={evaluationResult.aggregate_metrics.mean_reciprocal_rank.toFixed(3)}
                    icon={<TrendingUp size={16} />}
                  />
                  <MetricCard
                    label="NDCG@5"
                    value={evaluationResult.aggregate_metrics.mean_ndcg_at_5.toFixed(3)}
                    icon={<BarChart3 size={16} />}
                  />
                  <MetricCard
                    label="NDCG@10"
                    value={evaluationResult.aggregate_metrics.mean_ndcg_at_10.toFixed(3)}
                    icon={<BarChart3 size={16} />}
                  />
                  <MetricCard
                    label="P@5"
                    value={evaluationResult.aggregate_metrics.mean_precision_at_5.toFixed(3)}
                    icon={<CheckCircle2 size={16} />}
                  />
                  <MetricCard
                    label="R@5"
                    value={evaluationResult.aggregate_metrics.mean_recall_at_5.toFixed(3)}
                    icon={<CheckCircle2 size={16} />}
                  />
                </div>

                {/* Per-Query Results */}
                <div className="section-heading per-query-section">
                  <p className="eyebrow">Per-Query Results</p>
                  <p>{evaluationResult.per_query_results.length} queries evaluated</p>
                </div>

                <div className="list-stack">
                  {evaluationResult.per_query_results.slice(0, 10).map((query, index) => (
                    <div className="list-row" key={query.query_id}>
                      <div>
                        <strong>#{index + 1} {query.query_text}</strong>
                        <div className="query-metrics">
                          <span>AP: {query.average_precision.toFixed(3)}</span>
                          <span>RR: {query.reciprocal_rank.toFixed(3)}</span>
                          <span>NDCG@5: {query.ndcg_at_5.toFixed(3)}</span>
                          <span>P@5: {query.precision_at_5.toFixed(3)}</span>
                          <span>R@5: {query.recall_at_5.toFixed(3)}</span>
                        </div>
                      </div>
                      <div>
                        {query.average_precision >= 0.8 ? (
                          <CheckCircle2 size={16} className="status-icon-success" />
                        ) : query.average_precision >= 0.5 ? (
                          <AlertCircle size={16} className="status-icon-warning" />
                        ) : (
                          <XCircle size={16} className="status-icon-error" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Results Tab */}
        {activeTab === "results" && (
          <div className="tab-panel">
            <div className="section-heading">
              <h3>Evaluation History</h3>
              <p>查看历史评估结果</p>
            </div>

            <div className="list-stack">
              <p className="eyebrow">Recent Evaluations ({evaluationResults.data?.results.length || 0})</p>
              {evaluationResults.isLoading && <p>Loading results...</p>}
              {evaluationResults.data?.results.map((result) => (
                <div className="list-row" key={result.run_id}>
                  <div>
                    <strong>{result.dataset_name}</strong>
                    <p className="result-timestamp">
                      {new Date(result.timestamp).toLocaleString()}
                    </p>
                    <div className="result-metadata">
                      <span>{result.total_queries} queries</span>
                      <span>Top-{result.top_k}</span>
                    </div>
                    <div className="result-metrics">
                      <span>MAP: {result.aggregate_metrics.mean_average_precision.toFixed(3)}</span>
                      <span>MRR: {result.aggregate_metrics.mean_reciprocal_rank.toFixed(3)}</span>
                      <span>NDCG@5: {result.aggregate_metrics.mean_ndcg_at_5.toFixed(3)}</span>
                      <span>P@5: {result.aggregate_metrics.mean_precision_at_5.toFixed(3)}</span>
                    </div>
                  </div>
                  <div className="row-actions">
                    <button
                      onClick={() => {
                        if (confirm(`Delete result "${result.run_id}"?`)) {
                          deleteResult.mutate(result.run_id);
                        }
                      }}
                      type="button"
                    >
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
                </div>
              ))}
              {evaluationResults.data?.results.length === 0 && (
                <div className="empty-state">
                  <BarChart3 size={48} />
                  <p>No evaluation results yet</p>
                  <p className="empty-state-hint">Run an evaluation to see results here</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function MetricCard({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="metric-card">
      <div className="metric-icon-container">
        {icon}
        <span className="metric-label">{label}</span>
      </div>
      <strong className="metric-value">{value}</strong>
    </div>
  );
}
