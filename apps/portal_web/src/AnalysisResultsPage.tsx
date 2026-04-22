import { useState, useEffect } from "react";
import { FileText, Clock, TrendingUp, Search, Wifi, WifiOff } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useWebSocket } from "./useWebSocket";
import { SkeletonList, SkeletonText } from "./SkeletonLoader";

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
  const [progress, setProgress] = useState<number>(0);

  // WebSocket for real-time updates
  const wsUrl = selectedIssue
    ? `ws://localhost:8000/api/analysis/deep/${selectedIssue}/stream?workspace_dir=${encodeURIComponent(workspaceDir)}`
    : null;

  const { isConnected, lastMessage } = useWebSocket(wsUrl, {
    onMessage: (message) => {
      if (message.type === "progress" && message.progress !== undefined) {
        setProgress(message.progress);
      } else if (message.type === "section" && message.data) {
        setAnalysisContent((prev) => prev + "\n\n" + String(message.data));
      } else if (message.type === "complete" && message.data) {
        setAnalysisContent(String(message.data));
        setProgress(100);
        setLoading(false);
      } else if (message.type === "error") {
        console.error("WebSocket error:", message.error);
        setLoading(false);
      }
    },
    onOpen: () => {
      console.log("Connected to analysis stream");
    },
    onClose: () => {
      console.log("Disconnected from analysis stream");
    },
  });

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
    setAnalysisContent("");
    setProgress(0);
    setLoading(true);

    // WebSocket will handle the streaming updates
    // Fallback to REST API if WebSocket is not available
    if (!isConnected) {
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
    }
  };

  return (
    <div className="analysis-results-page">
      <div className="page-header">
        <h1>
          <FileText size={24} /> Analysis Results
          {selectedIssue && (
            <span className="connection-status">
              {isConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
            </span>
          )}
        </h1>
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
            <>
              {loading && progress > 0 && (
                <div className="progress-container">
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <div className="progress-text">{progress}% complete</div>
                </div>
              )}
              {loading && progress === 0 ? (
                <div className="loading">Loading analysis...</div>
              ) : (
                <div className="analysis-content markdown-body">
                  <ReactMarkdown>{analysisContent}</ReactMarkdown>
                </div>
              )}
            </>
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
