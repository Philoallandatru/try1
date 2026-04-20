import { useState, useEffect } from "react";
import { Calendar, FileText, TrendingUp, Clock, Loader2, RefreshCw } from "lucide-react";

interface ReportSection {
  title: string;
  content: string;
  order: number;
}

interface DailyReport {
  date: string;
  mode: string;
  sections: ReportSection[];
  total_issues: number;
}

interface DailyReportPageProps {
  workspaceDir: string;
}

export function DailyReportPage({ workspaceDir }: DailyReportPageProps) {
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [mode, setMode] = useState<"fast" | "full">("fast");
  const [report, setReport] = useState<DailyReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/analysis/daily-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_dir: workspaceDir,
          date: selectedDate,
          mode: mode,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to generate report: ${response.statusText}`);
      }

      const data = await response.json();
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate report");
      console.error("Report generation failed:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Auto-generate report on mount
    generateReport();
  }, []);

  return (
    <div className="daily-report-page">
      <div className="page-header">
        <h1>
          <Calendar size={24} /> Daily Report
        </h1>
        <p>Generate and view daily analysis reports from the knowledge base</p>
      </div>

      <div className="report-controls">
        <div className="control-group">
          <label>
            <Calendar size={16} />
            Date
          </label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            max={new Date().toISOString().split("T")[0]}
          />
        </div>

        <div className="control-group">
          <label>
            <Clock size={16} />
            Mode
          </label>
          <select value={mode} onChange={(e) => setMode(e.target.value as "fast" | "full")}>
            <option value="fast">Fast (&lt; 5s)</option>
            <option value="full">Full (&lt; 30s)</option>
          </select>
        </div>

        <button
          className="generate-button"
          onClick={generateReport}
          disabled={loading}
        >
          {loading ? (
            <>
              <Loader2 size={16} className="spinner" />
              Generating...
            </>
          ) : (
            <>
              <RefreshCw size={16} />
              Generate Report
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
        </div>
      )}

      {report && (
        <div className="report-container">
          <div className="report-header">
            <h2>
              <FileText size={20} />
              Daily Report - {report.date}
            </h2>
            <div className="report-meta">
              <span className="badge">
                <TrendingUp size={14} />
                {report.total_issues} issues analyzed
              </span>
              <span className="badge">
                <Clock size={14} />
                {report.mode} mode
              </span>
            </div>
          </div>

          {report.sections.length === 0 ? (
            <div className="empty-state">
              <p>No analysis data available for this date.</p>
              <p>Try analyzing some issues first, then generate a report.</p>
            </div>
          ) : (
            <div className="report-content">
              {report.sections
                .sort((a, b) => a.order - b.order)
                .map((section, index) => (
                  <div key={index} className="report-section">
                    <h3>{section.title}</h3>
                    <div className="section-content">
                      {section.content.split("\n").map((line, i) => {
                        if (line.trim().startsWith("- **")) {
                          // Parse markdown list items with bold issue IDs
                          const match = line.match(/- \*\*([^*]+)\*\*: (.+)/);
                          if (match) {
                            const [, issueId, rest] = match;
                            return (
                              <div key={i} className="issue-item">
                                <span className="issue-id">{issueId}</span>
                                <span className="issue-text">{rest}</span>
                              </div>
                            );
                          }
                        }
                        return line.trim() ? <p key={i}>{line}</p> : null;
                      })}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {!report && !loading && !error && (
        <div className="empty-state">
          <FileText size={48} />
          <p>Select a date and click "Generate Report" to view the daily analysis summary.</p>
        </div>
      )}
    </div>
  );
}
