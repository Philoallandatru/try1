import React from "react";
import { CheckCircle2, XCircle } from "lucide-react";

interface StepperProps {
  steps: Array<{ label: string; ok: boolean }>;
}

export function Stepper({ steps }: StepperProps) {
  return (
    <div className="stepper">
      {steps.map((step, index) => (
        <div key={index} className="step">
          <div className={step.ok ? "step-icon ok" : "step-icon"}>
            {step.ok ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
          </div>
          <span>{step.label}</span>
        </div>
      ))}
    </div>
  );
}
