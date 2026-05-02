import React from "react";

export type RunTab = "summary" | "rca" | "spec_impact" | "decision_brief" | "evidence" | "verification" | "artifacts";

interface RunTabsProps {
  activeTab: RunTab;
  onSelect: (tab: RunTab) => void;
}

export function RunTabs({ activeTab, onSelect }: RunTabsProps) {
  const tabs: { id: RunTab; label: string }[] = [
    { id: "summary", label: "Summary" },
    { id: "rca", label: "RCA" },
    { id: "spec_impact", label: "Spec Impact" },
    { id: "decision_brief", label: "Decision Brief" },
    { id: "evidence", label: "Evidence" },
    { id: "verification", label: "Verification" },
    { id: "artifacts", label: "Artifacts" },
  ];

  return (
    <div className="run-tabs" role="tablist" aria-label="Run detail tabs">
      {tabs.map((tab) => (
        <button
          className={activeTab === tab.id ? "active" : ""}
          key={tab.id}
          onClick={() => onSelect(tab.id)}
          role="tab"
          type="button"
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
