/**
 * Global Error Boundary Component
 * Catches runtime React errors and displays a fallback UI
 */
import React from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      errorId: null
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { 
      hasError: true, 
      errorId: `ERR-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details
    this.setState({ error, errorInfo });
    
    // Log to console with full details
    console.group('🚨 React Error Boundary Caught Error');
    console.error('Error:', error);
    console.error('Component Stack:', errorInfo?.componentStack);
    console.error('Error ID:', this.state.errorId);
    
    // Safe logging of error object
    if (error && typeof error === 'object') {
      console.error('Error Details:', JSON.stringify(error, Object.getOwnPropertyNames(error), 2));
    }
    console.groupEnd();
    
    // You could also send to error tracking service here
    // sendToErrorTracking(error, errorInfo, this.state.errorId);
  }

  handleRefresh = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  getErrorMessage() {
    const { error } = this.state;
    
    if (!error) return 'An unexpected error occurred';
    
    // Handle "Objects are not valid as React child" specifically
    if (error.message?.includes('Objects are not valid as a React child')) {
      return 'Display Error: The application tried to render an invalid data type. This is usually caused by API response handling issues.';
    }
    
    // Handle "Cannot read properties of undefined" error
    if (error.message?.includes('Cannot read properties of undefined') || 
        error.message?.includes('Cannot read property') ||
        error.message?.includes('is undefined') ||
        error.message?.includes('is null')) {
      return 'Data Loading Error: Some data was not available when the page tried to display it. This usually resolves by refreshing the page.';
    }
    
    // Handle network errors
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
            {/* Header */}
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

            {/* Content */}
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

              {/* Error Details (collapsible) */}
              {process.env.NODE_ENV === 'development' && errorInfo && (
                <details className="bg-zinc-100 dark:bg-zinc-900 rounded-lg">
                  <summary className="px-4 py-2 cursor-pointer text-sm font-medium text-zinc-600 dark:text-zinc-400 flex items-center gap-2">
                    <Bug className="w-4 h-4" />
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

            {/* Actions */}
            <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-700 flex flex-wrap gap-3">
              <button
                onClick={this.handleRefresh}
                className="flex items-center gap-2 px-4 py-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-lg hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh Page
              </button>
              <button
                onClick={this.handleGoHome}
                className="flex items-center gap-2 px-4 py-2 bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-200 rounded-lg hover:bg-zinc-300 dark:hover:bg-zinc-600 transition-colors"
              >
                <Home className="w-4 h-4" />
                Go to Dashboard
              </button>
              <button
                onClick={this.handleReset}
                className="flex items-center gap-2 px-4 py-2 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
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
