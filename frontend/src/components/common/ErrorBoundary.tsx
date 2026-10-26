import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex-1 flex flex-col items-center justify-center p-8 bg-[var(--bg)] text-[var(--text)] text-center min-h-[300px]">
          <div className="max-w-md w-full p-6 rounded-card bg-[var(--surface)] border border-[var(--border)] flex flex-col items-center gap-4 shadow-lg">
            <div className="w-10 h-10 rounded-full bg-[var(--err)]/10 text-[var(--err)] flex items-center justify-center">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div className="flex flex-col gap-1">
              <h3 className="font-semibold text-base text-[var(--text)]">
                {this.props.fallbackTitle || 'Something went wrong rendering this view'}
              </h3>
              <p className="text-xs text-[var(--muted)] font-mono break-all line-clamp-3">
                {this.state.error?.message || 'Unexpected application error'}
              </p>
            </div>
            <button
              onClick={this.handleReset}
              className="flex items-center gap-2 px-4 py-2 bg-[var(--accent)] text-white text-xs font-semibold rounded-card hover:opacity-90 transition-opacity"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reload page</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
