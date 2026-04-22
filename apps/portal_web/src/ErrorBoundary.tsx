import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import { getUserFriendlyError } from "./errorMessages";

interface Props {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleReset);
      }

      const friendlyError = getUserFriendlyError(this.state.error);

      return (
        <div className="error-boundary-fallback">
          <div className="error-boundary-content">
            <AlertTriangle size={64} className="error-icon" />
            <h2>{friendlyError.title}</h2>
            <p className="error-message">{friendlyError.message}</p>
            {friendlyError.action && (
              <p className="error-action-hint">{friendlyError.action}</p>
            )}

            {this.state.errorInfo && (
              <details className="error-details">
                <summary>Technical details</summary>
                <pre>{this.state.error.stack}</pre>
                <pre>{this.state.errorInfo.componentStack}</pre>
              </details>
            )}

            <div className="error-actions">
              <button onClick={this.handleReset} type="button">
                <RefreshCw size={16} /> Try again
              </button>
              <button onClick={() => window.location.href = "/"} type="button" className="secondary-action">
                <Home size={16} /> Go home
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
