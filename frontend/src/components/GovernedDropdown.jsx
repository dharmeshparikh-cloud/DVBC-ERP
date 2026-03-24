/**
 * GovernedDropdown.jsx - Reusable dropdown with loading/empty/error states
 * 
 * Step 2: Dropdown Governance Standard
 * Every dropdown MUST show: Loading, Empty, Error states.
 * Must NOT render empty silently.
 * 
 * ADDITIVE component — does not modify any existing select/dropdown.
 */

import React, { useState } from 'react';
import { RefreshCw, AlertTriangle, Loader2, ChevronDown, Search } from 'lucide-react';

export const GovernedDropdown = ({
  label,
  value,
  onChange,
  options = [],
  isLoading = false,
  isError = false,
  error = null,
  onRefresh = null,
  required = false,
  placeholder = 'Select...',
  emptyMessage = 'No data found',
  errorMessage = 'Failed to load data',
  disabled = false,
  className = '',
  valueKey = 'id',
  labelKey = 'name',
  labelFormatter = null,
  'data-testid': testId = '',
}) => {
  const [retryCount, setRetryCount] = useState(0);

  const handleRetry = () => {
    if (onRefresh) {
      console.log(`[GovernedDropdown:${label}] Retry #${retryCount + 1} triggered`);
      setRetryCount(prev => prev + 1);
      onRefresh();
    }
  };

  // Auto-retry once if empty and has refresh capability
  React.useEffect(() => {
    if (!isLoading && !isError && options.length === 0 && onRefresh && retryCount === 0) {
      console.log(`[GovernedDropdown:${label}] Empty on first load, auto-retrying...`);
      const timer = setTimeout(() => {
        setRetryCount(1);
        onRefresh();
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [isLoading, isError, options.length, onRefresh, retryCount, label]);

  return (
    <div className="space-y-1.5">
      {label && (
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-zinc-950">
            {label} {required && <span className="text-red-500">*</span>}
          </label>
          {onRefresh && (
            <button
              type="button"
              onClick={handleRetry}
              disabled={isLoading}
              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 disabled:opacity-50 px-1.5 py-0.5 rounded hover:bg-blue-50 transition-colors"
              data-testid={testId ? `${testId}-refresh` : undefined}
            >
              <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
              {isLoading ? 'Loading...' : 'Refresh'}
            </button>
          )}
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-zinc-50 flex items-center gap-2 text-sm text-zinc-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading...
        </div>
      )}

      {/* Error State */}
      {!isLoading && isError && (
        <div className="w-full px-3 py-2 rounded-sm border border-red-200 bg-red-50 flex items-center justify-between text-sm">
          <span className="flex items-center gap-1.5 text-red-600">
            <AlertTriangle className="w-4 h-4" />
            {errorMessage}
          </span>
          {onRefresh && (
            <button
              type="button"
              onClick={handleRetry}
              className="text-xs text-red-600 hover:text-red-700 underline"
            >
              Retry
            </button>
          )}
        </div>
      )}

      {/* Normal Select */}
      {!isLoading && !isError && (
        <>
          <select
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            required={required}
            disabled={disabled || options.length === 0}
            className={`w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-zinc-100 disabled:cursor-not-allowed ${className}`}
            data-testid={testId}
          >
            <option value="">{options.length === 0 ? emptyMessage : placeholder}</option>
            {options.map((opt) => (
              <option key={opt[valueKey] || opt.id} value={opt[valueKey] || opt.id}>
                {labelFormatter ? labelFormatter(opt) : (opt[labelKey] || opt.name || opt.label || opt.id)}
              </option>
            ))}
          </select>
          
          {/* Empty State Warning */}
          {options.length === 0 && !isLoading && (
            <p className="text-xs text-amber-600 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              {emptyMessage}
              {onRefresh && (
                <button
                  type="button"
                  onClick={handleRetry}
                  className="text-blue-600 hover:underline ml-1"
                >
                  Try refreshing
                </button>
              )}
            </p>
          )}
        </>
      )}
    </div>
  );
};

/**
 * GovernedReadOnlyField - Display auto-filled read-only value
 */
export const GovernedReadOnlyField = ({
  label,
  value,
  placeholder = 'Auto-filled',
  'data-testid': testId = '',
}) => {
  return (
    <div className="space-y-1.5">
      {label && (
        <label className="text-sm font-medium text-zinc-950">{label}</label>
      )}
      <div
        className="h-10 px-3 py-2 rounded-sm border border-zinc-200 bg-zinc-50 text-sm text-zinc-700 flex items-center"
        data-testid={testId}
      >
        {value || <span className="text-zinc-400">{placeholder}</span>}
      </div>
    </div>
  );
};
