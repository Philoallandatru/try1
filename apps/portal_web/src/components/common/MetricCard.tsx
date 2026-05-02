import React from "react";

interface MetricCardProps {
  label: string;
  value: string;
  warning?: boolean;
}

export function MetricCard({ label, value, warning = false }: MetricCardProps) {
  return (
    <div className={warning ? "metric-card warning" : "metric-card"}>
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
    </div>
  );
}
