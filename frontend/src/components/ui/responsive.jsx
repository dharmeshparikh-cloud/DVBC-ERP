/**
 * Mobile-First Responsive UI Components for NETRA ERP
 * 
 * This file provides standardized responsive components ensuring consistent
 * mobile layouts across all modules (HR, Expenses, Payroll, Dashboard, etc.)
 * 
 * Usage:
 *   import { PageContainer, MetricGrid, MetricCard, ResponsiveHeader, EmptyState } from '../components/ui/responsive';
 */

import React from 'react';
import { cn } from '../../lib/utils';

// =============================================================================
// PAGE CONTAINER
// Ensures consistent padding and bottom navigation safe area
// =============================================================================
export const PageContainer = ({ 
  children, 
  className = '',
  noPadding = false,
  ...props 
}) => (
  <div 
    className={cn(
      'w-full max-w-full',
      !noPadding && 'px-4 md:px-6 lg:px-8',
      'pb-20 md:pb-6', // Bottom nav safe area on mobile
      className
    )}
    {...props}
  >
    {children}
  </div>
);

// =============================================================================
// PAGE HEADER
// Mobile-optimized header with responsive title and actions
// =============================================================================
export const PageHeader = ({ 
  title, 
  subtitle,
  icon: Icon,
  actions,
  backButton,
  className = '' 
}) => (
  <div className={cn(
    'flex flex-col gap-4 mb-6',
    'md:flex-row md:items-center md:justify-between',
    className
  )}>
    <div className="flex items-start gap-3">
      {backButton}
      <div>
        <h1 className="text-xl md:text-2xl lg:text-3xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          {Icon && <Icon className="w-6 h-6 md:w-7 md:h-7 text-zinc-600" />}
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm md:text-base text-zinc-500 dark:text-zinc-400 mt-1">
            {subtitle}
          </p>
        )}
      </div>
    </div>
    
    {/* Actions - stack on mobile, inline on desktop */}
    {actions && (
      <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
        {React.Children.map(actions, (child, index) => 
          child && React.cloneElement(child, {
            className: cn(
              child.props?.className,
              'w-full sm:w-auto', // Full width on mobile
              'min-h-[44px]' // Touch-friendly height
            )
          })
        )}
      </div>
    )}
  </div>
);

// =============================================================================
// METRIC GRID
// Responsive grid for dashboard metric cards
// Desktop: 4 cols | Tablet: 2 cols | Mobile: 2 cols (or 1 for detailed)
// =============================================================================
export const MetricGrid = ({ 
  children, 
  columns = 4, // Default to 4 columns
  className = '' 
}) => {
  const gridCols = {
    2: 'grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-3',
    4: 'grid-cols-2 md:grid-cols-4',
    5: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-5',
    6: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-6',
  };
  
  return (
    <div className={cn(
      'grid gap-3 md:gap-4',
      gridCols[columns] || 'grid-cols-2 md:grid-cols-4',
      className
    )}>
      {children}
    </div>
  );
};

// =============================================================================
// METRIC CARD
// Standardized metric/stat card with responsive sizing
// =============================================================================
export const MetricCard = ({ 
  label, 
  value, 
  icon: Icon,
  color = 'zinc', // 'emerald', 'blue', 'red', 'amber', 'zinc'
  trend,
  trendUp,
  onClick,
  className = '',
  testId,
}) => {
  const colorStyles = {
    emerald: 'bg-emerald-50 border-emerald-100 dark:bg-emerald-950/30 dark:border-emerald-900',
    blue: 'bg-blue-50 border-blue-100 dark:bg-blue-950/30 dark:border-blue-900',
    red: 'bg-red-50 border-red-100 dark:bg-red-950/30 dark:border-red-900',
    amber: 'bg-amber-50 border-amber-100 dark:bg-amber-950/30 dark:border-amber-900',
    purple: 'bg-purple-50 border-purple-100 dark:bg-purple-950/30 dark:border-purple-900',
    zinc: 'bg-zinc-50 border-zinc-100 dark:bg-zinc-800 dark:border-zinc-700',
  };
  
  const iconColors = {
    emerald: 'text-emerald-600 dark:text-emerald-400',
    blue: 'text-blue-600 dark:text-blue-400',
    red: 'text-red-600 dark:text-red-400',
    amber: 'text-amber-600 dark:text-amber-400',
    purple: 'text-purple-600 dark:text-purple-400',
    zinc: 'text-zinc-600 dark:text-zinc-400',
  };
  
  const valueColors = {
    emerald: 'text-emerald-700 dark:text-emerald-300',
    blue: 'text-blue-700 dark:text-blue-300',
    red: 'text-red-700 dark:text-red-300',
    amber: 'text-amber-700 dark:text-amber-300',
    purple: 'text-purple-700 dark:text-purple-300',
    zinc: 'text-zinc-900 dark:text-zinc-100',
  };

  return (
    <div 
      className={cn(
        'p-3 md:p-4 rounded-lg border transition-all',
        colorStyles[color],
        onClick && 'cursor-pointer hover:shadow-md',
        className
      )}
      onClick={onClick}
      data-testid={testId}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs md:text-sm font-medium text-zinc-600 dark:text-zinc-400 truncate">
          {label}
        </span>
        {Icon && <Icon className={cn('w-4 h-4 md:w-5 md:h-5 flex-shrink-0', iconColors[color])} />}
      </div>
      <div className={cn('text-xl md:text-2xl lg:text-3xl font-bold', valueColors[color])}>
        {value}
      </div>
      {trend && (
        <div className={cn(
          'text-xs mt-1',
          trendUp ? 'text-emerald-600' : 'text-red-600'
        )}>
          {trendUp ? '↑' : '↓'} {trend}
        </div>
      )}
    </div>
  );
};

// =============================================================================
// RESPONSIVE TABLE WRAPPER
// Handles horizontal scrolling for tables on mobile
// =============================================================================
export const ResponsiveTable = ({ children, className = '' }) => (
  <div className={cn(
    'w-full overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0',
    'scrollbar-thin scrollbar-thumb-zinc-300 scrollbar-track-transparent',
    className
  )}>
    <div className="min-w-[600px] md:min-w-0">
      {children}
    </div>
  </div>
);

// =============================================================================
// EMPTY STATE
// Standardized empty state with responsive sizing
// =============================================================================
export const EmptyState = ({ 
  icon: Icon,
  title,
  description,
  action,
  className = '' 
}) => (
  <div className={cn(
    'flex flex-col items-center justify-center',
    'py-12 md:py-16 px-4',
    'text-center',
    className
  )}>
    {Icon && (
      <div className="w-16 h-16 md:w-20 md:h-20 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 md:w-10 md:h-10 text-zinc-400" />
      </div>
    )}
    <h3 className="text-base md:text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
      {title}
    </h3>
    {description && (
      <p className="text-sm md:text-base text-zinc-500 dark:text-zinc-400 max-w-sm mb-4">
        {description}
      </p>
    )}
    {action && (
      <div className="w-full sm:w-auto">
        {React.cloneElement(action, {
          className: cn(action.props?.className, 'w-full sm:w-auto min-h-[44px]')
        })}
      </div>
    )}
  </div>
);

// =============================================================================
// RESPONSIVE CARD GRID
// For general card layouts (not metrics)
// =============================================================================
export const CardGrid = ({ 
  children, 
  columns = 3,
  className = '' 
}) => {
  const gridCols = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
  };
  
  return (
    <div className={cn(
      'grid gap-4',
      gridCols[columns] || 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
      className
    )}>
      {children}
    </div>
  );
};

// =============================================================================
// MOBILE ACTION BAR
// Fixed action bar for mobile (above bottom nav)
// =============================================================================
export const MobileActionBar = ({ children, className = '' }) => (
  <div className={cn(
    'fixed bottom-16 left-0 right-0 md:hidden',
    'bg-white dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-800',
    'p-3 flex gap-2',
    'z-30',
    className
  )}>
    {React.Children.map(children, child => 
      child && React.cloneElement(child, {
        className: cn(child.props?.className, 'flex-1 min-h-[44px]')
      })
    )}
  </div>
);

// =============================================================================
// RESPONSIVE FORM ROW
// Responsive form layout - stacks on mobile
// =============================================================================
export const FormRow = ({ children, columns = 2, className = '' }) => {
  const gridCols = {
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
  };
  
  return (
    <div className={cn(
      'grid gap-4',
      gridCols[columns] || 'grid-cols-1 sm:grid-cols-2',
      className
    )}>
      {children}
    </div>
  );
};

// =============================================================================
// SECTION TITLE
// Consistent section headers
// =============================================================================
export const SectionTitle = ({ 
  children, 
  icon: Icon,
  action,
  className = '' 
}) => (
  <div className={cn(
    'flex items-center justify-between mb-4',
    className
  )}>
    <h2 className="text-base md:text-lg font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
      {Icon && <Icon className="w-5 h-5 text-zinc-500" />}
      {children}
    </h2>
    {action}
  </div>
);

// =============================================================================
// FILTER BAR
// Responsive filter/search bar
// =============================================================================
export const FilterBar = ({ children, className = '' }) => (
  <div className={cn(
    'flex flex-col sm:flex-row gap-3 mb-4',
    'items-stretch sm:items-center',
    className
  )}>
    {children}
  </div>
);

// =============================================================================
// TABS WRAPPER
// Responsive tabs that scroll on mobile
// =============================================================================
export const ResponsiveTabs = ({ children, className = '' }) => (
  <div className={cn(
    'overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0 mb-4',
    'scrollbar-none',
    className
  )}>
    <div className="min-w-max md:min-w-0">
      {children}
    </div>
  </div>
);

export default {
  PageContainer,
  PageHeader,
  MetricGrid,
  MetricCard,
  ResponsiveTable,
  EmptyState,
  CardGrid,
  MobileActionBar,
  FormRow,
  SectionTitle,
  FilterBar,
  ResponsiveTabs,
};
