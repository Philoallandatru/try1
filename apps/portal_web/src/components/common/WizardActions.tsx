import React from "react";
import { ChevronRight } from "lucide-react";

interface WizardActionsProps {
  canProceed: boolean;
  onBack?: () => void;
  submitLabel?: string;
  submitIcon?: React.ReactNode;
}

export function WizardActions({
  canProceed,
  onBack,
  submitLabel = "Continue",
  submitIcon = <ChevronRight size={16} />,
}: WizardActionsProps) {
  return (
    <div className="wizard-actions">
      {onBack && (
        <button type="button" onClick={onBack} className="secondary-button">
          Back
        </button>
      )}
      <button type="submit" disabled={!canProceed} className="primary-button">
        {submitIcon} {submitLabel}
      </button>
    </div>
  );
}
