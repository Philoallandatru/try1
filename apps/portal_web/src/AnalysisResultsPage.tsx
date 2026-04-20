import { useState, useEffect } from "react";
import { FileText, Clock, TrendingUp, Search } from "lucide-react";

interface AnalysisResult {
  issue_id: string;
  title: string;
  analyzed_at: string;
  citation_count: number;
}

interface AnalysisResultsPageProps {
  workspaceDir: string;
}

export function AnalysisResultsPage({ workspaceDir }: AnalysisResultsPageProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIssue, setSelectedIssue] = useState<string | null>(null);
  const [analysisContent, setAnalysisContent] = useState<string>("");

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    try {
      const response = await fetch(
        `/api/analysis/knowledge/search?workspace_dir=${encodeURIComponent(workspaceDir)}&query=${encodeURIComponent(searchQuery)}&limit=20`
      );
      const data = await response.json();
      setResults(data.results || []);
    } catch (error) {
      console.error("Search failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadAnalysis = async (issueId: string) => {
    setSelectedIssue(issueId);
    setLoading(true);
    try {
      const response = await fetch(
        `/api/analysis/deep/${issueId}?workspace_dir=${encodeURIComponent(workspaceDir)}`
      );
      const data = await response.json();
      setAnalysisContent(data.content || "No content available");
    } catch (error) {
      console.error("Failed to load analysis:", error);
      setAnalysisContent("Failed to load analysis");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="analysis-results-page">
      <div className="page-header">
        <h1><FileText size={24} /> Analysis Results</h1>
        <p>Search and view deep analysis results from the knowledge base</p>
      </div>

      <div className="search-section">
        <div className="search-bar">
          <Search size={20} />
          <input
            type="text"
            placeholder="Search knowledge base (e.g., 'NVMe flush', 'S4 resume')"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <button onClick={handleSearch} disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </div>

      <div className="results-container">
        <div className="results-list">
          <h2>Search Results ({results.length})</h2>
          {results.length === 0 ? (
            <div className="empty-state">
              <p>No results yet. Try searching for an issue or topic.</p>
            </div>
          ) : (
            <ul>
              {results.map((result) => (
                <li
                  key={result.issue_id}
                  className={selectedIssue === result.issue_id ? "selected" : ""}
                  onClick={() => loadAnalysis(result.issue_id)}
                >
                  <div className="result-header">
                    <strong>{result.issue_id}</strong>
                    <span className="citation-count">
                      <TrendingUp size={14} /> {result.citation_count} citations
                    </span>
                  </div>
                  <div className="result-title">{result.title}</div>
                  <div className="result-meta">
                    <Clock size={12} />
                    {new Date(result.analyzed_at).toLocaleString()}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="analysis-viewer">
          <h2>Analysis Content</h2>
          {selectedIssue ? (
            loading ? (
              <div className="loading">Loading analysis...</div>
            ) : (
              <div className="analysis-content">
                <pre>{analysisContent}</pre>
              </div>
            )
          ) : (
            <div className="empty-state">
              <p>Select a result to view its analysis</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
