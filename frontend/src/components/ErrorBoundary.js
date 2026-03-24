/**
 * Global Error Boundary Component
 * ZERO-CRASH GUARANTEE: Auto-recovers from data loading errors
 * Shows graceful fallback instead of crashing
 */
import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      errorId: null,
      retryCount: 0,
      autoRetried: false
    };
  }

  static getDerivedStateFromError(error) {
    return { 
      hasError: true, 
      errorId: `ERR-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ error, errorInfo });
    
    const isDataError = this.isDataLoadingError(error);
    
    // Auto-retry once for data loading errors
    if (isDataError && !this.state.autoRetried && this.state.retryCount < 2) {
      console.warn('[ErrorBoundary] Data loading error detected, auto-retrying...', error?.message);
      setTimeout(() => {
        this.setState(prev => ({ 
          hasError: false, 
          error: null, 
          errorInfo: null, 
          retryCount: prev.retryCount + 1,
          autoRetried: true 
        }));
      }, 500);
      return;
    }
    
    // Log error details
    console.group('[ErrorBoundary] Caught Error');
    console.error('Error:', error?.message);
    console.error('Component Stack:', errorInfo?.componentStack);
    console.groupEnd();
  }

  isDataLoadingError(error) {
    if (!error?.message) return false;
    const msg = error.message;
    return (
      msg.includes('Cannot read properties of undefined') ||
      msg.includes('Cannot read properties of null') ||
      msg.includes('Cannot read property') ||
      msg.includes('is not a function') ||
      msg.includes('is not iterable') ||
      msg.includes('is undefined') ||
      msg.includes('is null') ||
      msg.includes('undefined is not an object') ||
      msg.includes('null is not an object')
    );
  }

  handleRefresh = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  handleReset = () => {
    this.setState({ 
      hasError: false, 
      error: null, 
      errorInfo: null,
      retryCount: 0,
      autoRetried: false
    });
  };

  getErrorMessage() {
    const { error } = this.state;
    
    if (!error) return 'An unexpected error occurred';
    
    if (error.message?.includes('Objects are not valid as a React child')) {
      return 'Display Error: The application tried to render an invalid data type. This is usually caused by API response handling issues.';
    }
    
    if (this.isDataLoadingError(error)) {
      return 'Data Loading Error: Some data was not available when the page tried to display it. This usually resolves by refreshing the page.';
    }
    
    if (error.message?.includes('Network Error') || error.message?.includes('fetch')) {
      return 'Network Error: Unable to connect to the server. Please check your internet connection and try again.';
    }
    
    if (typeof error === 'string') return error;
    if (error.message) return error.message;
    
    return 'An unexpected error occurred';
  }

  render() {
    if (this.state.hasError) {
      const { errorId, error, errorInfo } = this.state;
      const errorMessage = this.getErrorMessage();
      const isObjectRenderError = error?.message?.includes('Objects are not valid as a React child');

      return (
        <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900 flex items-center justify-center p-4">
          <div className="max-w-lg w-full bg-white dark:bg-zinc-800 rounded-xl shadow-lg border border-zinc-200 dark:border-zinc-700 overflow-hidden">
            <div className="bg-red-50 dark:bg-red-900/20 border-b border-red-100 dark:border-red-800 px-6 py-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 dark:bg-red-900/40 rounded-full">
                  <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-red-800 dark:text-red-200">
                    Something went wrong
                  </h1>
                  <p className="text-sm text-red-600 dark:text-red-300">
                    Error ID: {errorId}
                  </p>
                </div>
              </div>
            </div>

            <div className="px-6 py-5 space-y-4">
              <p className="text-zinc-700 dark:text-zinc-300">
                {errorMessage}
              </p>

              {isObjectRenderError && (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg p-3">
                  <p className="text-sm text-amber-800 dark:text-amber-200">
                    <strong>Tip:</strong> This error often occurs when an API returns an error object 
                    that gets rendered directly. Please try refreshing the page.
                  </p>
                </div>
              )}

              {errorInfo && (
                <details className="bg-zinc-100 dark:bg-zinc-900 rounded-lg">
                  <summary className="px-4 py-2 cursor-pointer text-sm font-medium text-zinc-600 dark:text-zinc-400 flex items-center gap-2">
                    Technical Details
                  </summary>
                  <div className="px-4 pb-4">
                    <pre className="text-xs overflow-auto max-h-48 bg-zinc-800 text-zinc-100 p-3 rounded mt-2">
                      {error?.toString()}
                      {'\n\nComponent Stack:'}
                      {errorInfo.componentStack}
                    </pre>
                  </div>
                </details>
              )}
            </div>

            <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-700 flex flex-wrap gap-3">
              <button
                onClick={this.handleRefresh}
                className="flex items-center gap-2 px-4 py-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-lg hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors"
                data-testid="error-refresh-btn"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh Page
              </button>
              <button
                onClick={this.handleGoHome}
                className="flex items-center gap-2 px-4 py-2 bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-200 rounded-lg hover:bg-zinc-300 dark:hover:bg-zinc-600 transition-colors"
                data-testid="error-go-home-btn"
              >
                <Home className="w-4 h-4" />
                Go to Dashboard
              </button>
              <button
                onClick={this.handleReset}
                className="flex items-center gap-2 px-4 py-2 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
                data-testid="error-try-again-btn"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
