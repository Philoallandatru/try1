import React from "react";

interface ListPanelProps {
  title: string;
  children: React.ReactNode;
}

export function ListPanel({ title, children }: ListPanelProps) {
  return (
    <div className="list-panel">
      <p className="eyebrow">{title}</p>
      <div className="list-content">{children}</div>
    </div>
  );
}
