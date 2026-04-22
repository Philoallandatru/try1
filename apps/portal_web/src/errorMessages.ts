export interface UserFriendlyError {
  title: string;
  message: string;
  action?: string;
}

export function getUserFriendlyError(error: unknown): UserFriendlyError {
  const errorMessage = error instanceof Error ? error.message : String(error);
  const errorString = errorMessage.toLowerCase();

  // Network errors
  if (errorString.includes("failed to fetch") || errorString.includes("network")) {
    return {
      title: "Connection Error",
      message: "Unable to connect to the server. Please check your network connection.",
      action: "Verify the backend server is running and try again.",
    };
  }

  if (errorString.includes("econnrefused") || errorString.includes("connection refused")) {
    return {
      title: "Server Unavailable",
      message: "The backend server is not responding.",
      action: "Make sure the backend service is running on the correct port.",
    };
  }

  // Authentication errors
  if (errorString.includes("unauthorized") || errorString.includes("401")) {
    return {
      title: "Authentication Required",
      message: "Your session has expired or the token is invalid.",
      action: "Please check your token and try again.",
    };
  }

  if (errorString.includes("forbidden") || errorString.includes("403")) {
    return {
      title: "Access Denied",
      message: "You don't have permission to perform this action.",
      action: "Contact your administrator if you believe this is an error.",
    };
  }

  // Resource errors
  if (errorString.includes("not found") || errorString.includes("404")) {
    return {
      title: "Resource Not Found",
      message: "The requested resource could not be found.",
      action: "Check that the workspace and resource exist.",
    };
  }

  // Validation errors
  if (errorString.includes("validation") || errorString.includes("invalid")) {
    return {
      title: "Invalid Input",
      message: errorMessage,
      action: "Please check your input and try again.",
    };
  }

  // Timeout errors
  if (errorString.includes("timeout") || errorString.includes("timed out")) {
    return {
      title: "Request Timeout",
      message: "The operation took too long to complete.",
      action: "Try again or contact support if the problem persists.",
    };
  }

  // Rate limiting
  if (errorString.includes("too many requests") || errorString.includes("429")) {
    return {
      title: "Too Many Requests",
      message: "You've made too many requests. Please wait a moment.",
      action: "Wait a few seconds and try again.",
    };
  }

  // Server errors
  if (errorString.includes("500") || errorString.includes("internal server error")) {
    return {
      title: "Server Error",
      message: "An unexpected error occurred on the server.",
      action: "Please try again later or contact support.",
    };
  }

  if (errorString.includes("502") || errorString.includes("bad gateway")) {
    return {
      title: "Service Unavailable",
      message: "The server is temporarily unavailable.",
      action: "Please try again in a few moments.",
    };
  }

  if (errorString.includes("503") || errorString.includes("service unavailable")) {
    return {
      title: "Service Unavailable",
      message: "The service is temporarily down for maintenance.",
      action: "Please try again later.",
    };
  }

  // Workspace-specific errors
  if (errorString.includes("workspace")) {
    return {
      title: "Workspace Error",
      message: errorMessage,
      action: "Check that the workspace is properly configured.",
    };
  }

  // File/parsing errors
  if (errorString.includes("parse") || errorString.includes("parsing")) {
    return {
      title: "Parsing Error",
      message: errorMessage,
      action: "Check that the file format is supported and not corrupted.",
    };
  }

  // MinerU errors
  if (errorString.includes("mineru")) {
    return {
      title: "MinerU Error",
      message: errorMessage,
      action: "Verify MinerU is installed and configured correctly.",
    };
  }

  // LLM errors
  if (errorString.includes("llm") || errorString.includes("model")) {
    return {
      title: "LLM Service Error",
      message: errorMessage,
      action: "Check that LM Studio or your LLM backend is running.",
    };
  }

  // Generic error
  return {
    title: "Error",
    message: errorMessage,
    action: "If this problem persists, please contact support.",
  };
}

export function formatErrorForDisplay(error: unknown): string {
  const friendly = getUserFriendlyError(error);
  return `${friendly.title}: ${friendly.message}${friendly.action ? ` ${friendly.action}` : ""}`;
}
