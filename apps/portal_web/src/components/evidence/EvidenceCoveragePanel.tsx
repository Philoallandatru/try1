import React from "react";
import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

export interface EvidenceCoverage {
  jira_found: boolean;
  confluence_count: number;
  spec_count: number;
  missing: string[];
}

interface EvidenceCoveragePanelProps {
  coverage: EvidenceCoverage;
  verificationText?: string;
}

export function EvidenceCoveragePanel({ coverage, verificationText }: EvidenceCoveragePanelProps) {
  return (
    <div className="evidence-coverage-panel">
      <p className="eyebrow">Evidence Coverage</p>
      <div className="coverage-grid">
        <div className="coverage-item">
          {coverage.jira_found ? (
            <CheckCircle2 size={16} className="ok" />
          ) : (
            <XCircle size={16} className="error" />
          )}
          <span>Jira Issue</span>
        </div>
        <div className="coverage-item">
          {coverage.confluence_count > 0 ? (
            <CheckCircle2 size={16} className="ok" />
          ) : (
            <AlertTriangle size={16} className="warn" />
          )}
          <span>{coverage.confluence_count} Confluence pages</span>
        </div>
        <div className="coverage-item">
          {coverage.spec_count > 0 ? (
            <CheckCircle2 size={16} className="ok" />
          ) : (
            <AlertTriangle size={16} className="warn" />
          )}
          <span>{coverage.spec_count} Spec citations</span>
        </div>
      </div>
      {coverage.missing.length > 0 && (
        <div className="missing-evidence">
          <p className="eyebrow">Missing Evidence</p>
          <ul>
            {coverage.missing.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
