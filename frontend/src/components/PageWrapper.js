/**
 * PageWrapper Component
 * Wraps all ERP pages with error boundary and data safety
 * 
 * Usage:
 *   import PageWrapper from '../components/PageWrapper';
 *   
 *   const MyPage = () => (
 *     <PageWrapper pageName="EmployeeList">
 *       <ActualPageContent />
 *     </PageWrapper>
 *   );
 */
import React from 'react';
import ErrorBoundary from './ErrorBoundary';

/**
 * Page-level Error Boundary with context
 */
class PageErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ error, errorInfo });
    
    const { pageName } = this.props;
    
    // Enhanced logging for array errors
    const isArrayError = error?.message?.includes('is not a function') ||
                         error?.message?.includes('is not iterable') ||
                         error?.message?.includes('Cannot read properties of undefined') ||
                         error?.message?.includes('Cannot read properties of null');
    
    console.group(`🚨 Page Error: ${pageName}`);
    console.error('Error:', error?.message);
    
    if (isArrayError) {
      console.warn(
        '⚠️ This looks like an array safety issue!\n' +
        'Common causes:\n' +
        '  1. API returned null/undefined instead of []\n' +
        '  2. State not initialized as array (useState(null) instead of useState([]))\n' +
        '  3. Missing optional chaining on .map()/.filter()/.reduce()\n' +
        '  4. API returned object instead of array\n\n' +
        'Fix: Use ensureArray() from utils/arraySafety.js or || [] fallback'
      );
    }
    
    console.error('Component Stack:', errorInfo?.componentStack);
    console.groupEnd();
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      const { pageName, fallback } = this.props;
      const { error } = this.state;
      
      const isArrayError = error?.message?.includes('is not a function') ||
                           error?.message?.includes('is not iterable');
      
      if (fallback) {
        return fallback;
      }
      
      return (
        <div className="min-h-[400px] flex items-center justify-center">
          <div className="text-center p-8 max-w-md">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            
            <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
              {isArrayError ? 'Data Loading Error' : 'Something went wrong'}
            </h3>
            
            <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-4">
              {isArrayError 
                ? `Unable to display ${pageName} due to a data format issue. This has been logged for review.`
                : `An error occurred while loading ${pageName}. Please try again.`
              }
            </p>
            
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleRetry}
                className="px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-zinc-200 text-zinc-700 rounded-lg hover:bg-zinc-300 transition-colors"
              >
                Refresh Page
              </button>
            </div>
            
            {process.env.NODE_ENV === 'development' && (
              <details className="mt-4 text-left">
                <summary className="text-xs text-zinc-500 cursor-pointer">
                  Technical Details
                </summary>
                <pre className="mt-2 p-2 bg-zinc-100 dark:bg-zinc-800 rounded text-xs overflow-auto max-h-32">
                  {error?.message}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Main PageWrapper component
 */
const PageWrapper = ({ 
  children, 
  pageName = 'Page',
  fallback = null,
  className = ''
}) => {
  return (
    <ErrorBoundary>
      <PageErrorBoundary pageName={pageName} fallback={fallback}>
        <div className={className}>
          {children}
        </div>
      </PageErrorBoundary>
    </ErrorBoundary>
  );
};

export default PageWrapper;
