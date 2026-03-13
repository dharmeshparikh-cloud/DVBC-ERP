/**
 * PageLoadingSkeleton - Enhanced loading state for lazy-loaded pages
 * Provides visual feedback while components are loading
 */

import React from 'react';

// Simple spinning loader
export const Spinner = ({ size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16'
  };

  return (
    <div className={`animate-spin rounded-full border-2 border-orange-500 border-t-transparent ${sizeClasses[size]} ${className}`} />
  );
};

// Full page loading state
export const PageLoadingSkeleton = ({ message = 'Loading...' }) => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <Spinner size="lg" />
      <p className="text-zinc-500 text-sm animate-pulse">{message}</p>
    </div>
  );
};

// Dashboard skeleton
export const DashboardSkeleton = () => {
  return (
    <div className="p-6 space-y-6 animate-pulse">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div className="h-8 w-48 bg-zinc-200 dark:bg-zinc-700 rounded" />
        <div className="h-10 w-32 bg-zinc-200 dark:bg-zinc-700 rounded" />
      </div>
      
      {/* Stats cards skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white dark:bg-zinc-800 rounded-xl p-4 border border-zinc-200 dark:border-zinc-700">
            <div className="h-4 w-24 bg-zinc-200 dark:bg-zinc-700 rounded mb-3" />
            <div className="h-8 w-16 bg-zinc-200 dark:bg-zinc-700 rounded" />
          </div>
        ))}
      </div>
      
      {/* Table skeleton */}
      <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700">
        <div className="p-4 border-b border-zinc-200 dark:border-zinc-700">
          <div className="h-6 w-32 bg-zinc-200 dark:bg-zinc-700 rounded" />
        </div>
        <div className="divide-y divide-zinc-200 dark:divide-zinc-700">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="p-4 flex items-center gap-4">
              <div className="h-10 w-10 bg-zinc-200 dark:bg-zinc-700 rounded-full" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-48 bg-zinc-200 dark:bg-zinc-700 rounded" />
                <div className="h-3 w-32 bg-zinc-200 dark:bg-zinc-700 rounded" />
              </div>
              <div className="h-8 w-20 bg-zinc-200 dark:bg-zinc-700 rounded" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Table skeleton
export const TableSkeleton = ({ rows = 5, columns = 4 }) => {
  return (
    <div className="animate-pulse">
      {/* Header */}
      <div className="flex gap-4 p-4 bg-zinc-100 dark:bg-zinc-800 rounded-t-lg">
        {Array(columns).fill(0).map((_, i) => (
          <div key={i} className="h-4 flex-1 bg-zinc-200 dark:bg-zinc-700 rounded" />
        ))}
      </div>
      {/* Rows */}
      <div className="divide-y divide-zinc-200 dark:divide-zinc-700">
        {Array(rows).fill(0).map((_, i) => (
          <div key={i} className="flex gap-4 p-4">
            {Array(columns).fill(0).map((_, j) => (
              <div key={j} className="h-4 flex-1 bg-zinc-100 dark:bg-zinc-800 rounded" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

// Card skeleton
export const CardSkeleton = ({ count = 3 }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
      {Array(count).fill(0).map((_, i) => (
        <div key={i} className="bg-white dark:bg-zinc-800 rounded-xl p-6 border border-zinc-200 dark:border-zinc-700">
          <div className="h-5 w-32 bg-zinc-200 dark:bg-zinc-700 rounded mb-4" />
          <div className="space-y-3">
            <div className="h-4 w-full bg-zinc-200 dark:bg-zinc-700 rounded" />
            <div className="h-4 w-3/4 bg-zinc-200 dark:bg-zinc-700 rounded" />
          </div>
          <div className="mt-4 flex gap-2">
            <div className="h-8 w-20 bg-zinc-200 dark:bg-zinc-700 rounded" />
            <div className="h-8 w-20 bg-zinc-200 dark:bg-zinc-700 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
};

// Form skeleton
export const FormSkeleton = ({ fields = 4 }) => {
  return (
    <div className="space-y-6 animate-pulse max-w-2xl">
      {Array(fields).fill(0).map((_, i) => (
        <div key={i} className="space-y-2">
          <div className="h-4 w-24 bg-zinc-200 dark:bg-zinc-700 rounded" />
          <div className="h-10 w-full bg-zinc-100 dark:bg-zinc-800 rounded border border-zinc-200 dark:border-zinc-700" />
        </div>
      ))}
      <div className="pt-4">
        <div className="h-10 w-32 bg-orange-200 dark:bg-orange-900/30 rounded" />
      </div>
    </div>
  );
};

export default PageLoadingSkeleton;
