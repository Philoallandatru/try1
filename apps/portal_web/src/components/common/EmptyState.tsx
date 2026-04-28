import React from "react";
import { AlertCircle } from "lucide-react";

interface EmptyStateProps {
  title: string;
  body: string;
}

export function EmptyState({ title, body }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <AlertCircle size={48} className="empty-icon" />
      <h3>{title}</h3>
      <p>{body}</p>
    </div>
  );
}
