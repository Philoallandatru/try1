import React from "react";
import ReactMarkdown from "react-markdown";
import { z } from "zod";
import { RunTab } from "./RunTabs";

// Import schemas from main.tsx (will need to be extracted later)
type DeepAnalysisPayload = {
  issue_summary?: string;
  answer?: { text?: string };
};

type LLMVerification = {
  backend: string;
  mode: string;
  verification_text: string;
  created_at?: string;
};

type ArtifactInventoryItem = {
  artifact_type: string;
  status?: string;
  exists?: boolean;
  stale?: boolean;
  path?: string;
};

interface RunTabPanelProps {
  activeTab: RunTab;
  payload: DeepAnalysisPayload;
  sectionOutputs: Record<string, unknown>;
  confluenceCitations: Record<string, unknown>[];
  specCitations: Record<string, unknown>[];
  verification?: LLMVerification;
  verificationHistory: LLMVerification[];
  artifacts?: ArtifactInventoryItem[];
}

function sectionText(section: unknown): string {
  if (!section || typeof section !== "object") {
    return "No section output available.";
  }
  const answer = (section as { answer?: { text?: string } }).answer;
  return answer?.text || "No section answer available.";
}

function firstLine(text: string): string {
  return text.split("\n")[0] || text;
}

export function RunTabPanel({
  activeTab,
  payload,
  sectionOutputs,
  confluenceCitations,
  specCitations,
  verification,
  verificationHistory,
  artifacts,
}: RunTabPanelProps) {
  if (activeTab === "summary") {
    const issueDataText = payload.issue_summary ? String(payload.issue_summary) : null;
    return (
      <section className="tab-panel">
        {issueDataText && (
          <>
            <p className="eyebrow">Jira Issue</p>
            <div className="document-content markdown-content">
              <ReactMarkdown>{issueDataText}</ReactMarkdown>
            </div>
          </>
        )}
        <p className="eyebrow">Analysis Summary</p>
        <div className="markdown-content">
          <ReactMarkdown>{payload.answer?.text || "No summary text available."}</ReactMarkdown>
        </div>
      </section>
    );
  }

  if (activeTab === "verification") {
    return (
      <section className="tab-panel">
        <p className="eyebrow">LLM Verification</p>
        {verification ? (
          <div className="verification-card">
            <strong>{verification.backend} / {verification.mode}</strong>
            <p>{verification.verification_text}</p>
          </div>
        ) : (
          <p>No LLM verification artifact yet.</p>
        )}
        {verificationHistory.length > 0 && (
          <div className="history-list">
            <p className="eyebrow">History</p>
            {verificationHistory.slice().reverse().map((item, index) => (
              <div className="history-row" key={`${item.created_at || "unknown"}-${index}`}>
                <strong>{item.backend} / {item.created_at || "unknown time"}</strong>
                <span>{firstLine(item.verification_text)}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    );
  }

  if (activeTab === "evidence") {
    const citations = [...confluenceCitations, ...specCitations];
    return (
      <section className="tab-panel">
        <p className="eyebrow">Evidence</p>
        {citations.slice(0, 12).map((citation, index) => (
          <div className="citation" key={index}>
            <strong>{String(citation.title || citation.document || citation.document_id || "Evidence")}</strong>
            <span>page {String(citation.page ?? "-")} / {String(citation.section ?? citation.clause ?? "-")}</span>
          </div>
        ))}
        {!citations.length && <p>No evidence citations returned.</p>}
      </section>
    );
  }

  if (activeTab === "artifacts") {
    return (
      <section className="tab-panel">
        <p className="eyebrow">Artifacts</p>
        {(artifacts || []).map((artifact) => (
          <div className="artifact-row" key={artifact.artifact_type}>
            <strong>{artifact.artifact_type}</strong>
            <span>{artifact.status || "unknown"} / {artifact.exists ? "exists" : "missing"}{artifact.stale ? " / stale" : ""}</span>
            <small>{artifact.path || "-"}</small>
          </div>
        ))}
        {!artifacts?.length && <p>No artifact inventory available.</p>}
      </section>
    );
  }

  return (
    <section className="tab-panel">
      <p className="eyebrow">{activeTab.replace("_", " ")}</p>
      <div className="markdown-content">
        <ReactMarkdown>{sectionText(sectionOutputs[activeTab])}</ReactMarkdown>
      </div>
    </section>
  );
}
