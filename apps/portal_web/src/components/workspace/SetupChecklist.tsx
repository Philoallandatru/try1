import React from "react";
import { CheckCircle2, AlertCircle } from "lucide-react";

export interface SetupItem {
  label: string;
  ok: boolean;
  detail?: string;
  target?: string;
}

interface SetupChecklistProps {
  items: SetupItem[];
  onNavigate: (page: string) => void;
}

export function SetupChecklist({ items, onNavigate }: SetupChecklistProps) {
  const complete = items.filter((item) => item.ok).length;

  return (
    <div className="setup-checklist">
      <div className="setup-header">
        <div>
          <p className="eyebrow">Setup Checklist</p>
          <strong>{complete} / {items.length} ready</strong>
        </div>
        <span className={complete === items.length ? "setup-badge ready" : "setup-badge"}>
          {complete === items.length ? (
            <><CheckCircle2 size={14} /> Ready</>
          ) : (
            <><AlertCircle size={14} /> Action needed</>
          )}
        </span>
      </div>
      <div className="setup-items">
        {items.map((item, index) => (
          <div key={index} className="setup-item">
            <div className="setup-item-status">
              {item.ok ? (
                <CheckCircle2 size={16} className="ok" />
              ) : (
                <AlertCircle size={16} className="warn" />
              )}
            </div>
            <div className="setup-item-content">
              <strong>{item.label}</strong>
              {item.detail && <p>{item.detail}</p>}
            </div>
            {!item.ok && item.target && (
              <button
                type="button"
                onClick={() => onNavigate(item.target!)}
                className="setup-item-action"
              >
                Configure
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
