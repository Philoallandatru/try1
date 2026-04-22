import React from "react";

export function SkeletonBox({ width = "100%", height = "20px" }: { width?: string; height?: string }) {
  return <div className="skeleton-box" style={{ width, height }} />;
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton-text">
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonBox key={i} width={i === lines - 1 ? "60%" : "100%"} height="16px" />
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <SkeletonBox width="100%" height="120px" />
      <div className="skeleton-card-content">
        <SkeletonBox width="70%" height="24px" />
        <SkeletonText lines={2} />
      </div>
    </div>
  );
}

export function SkeletonList({ items = 5 }: { items?: number }) {
  return (
    <div className="skeleton-list">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="skeleton-list-item">
          <SkeletonBox width="40px" height="40px" />
          <div className="skeleton-list-content">
            <SkeletonBox width="60%" height="18px" />
            <SkeletonBox width="40%" height="14px" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="skeleton-table">
      <div className="skeleton-table-header">
        {Array.from({ length: columns }).map((_, i) => (
          <SkeletonBox key={i} width="100%" height="20px" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="skeleton-table-row">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <SkeletonBox key={colIndex} width="100%" height="16px" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonPage() {
  return (
    <div className="skeleton-page">
      <div className="skeleton-page-header">
        <SkeletonBox width="200px" height="32px" />
        <SkeletonBox width="300px" height="16px" />
      </div>
      <div className="skeleton-page-content">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    </div>
  );
}
