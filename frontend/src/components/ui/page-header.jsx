import React from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import PageRefreshButton from '../PageRefreshButton';

/**
 * PageHeader - Standardized page header with title, subtitle, actions
 * Props:
 * - title: string
 * - subtitle: string
 * - actions: ReactNode (buttons/controls)
 * - onRefresh: () => void (adds refresh button automatically)
 * - loading: boolean (for refresh spinner)
 * - badge: ReactNode (optional badge next to title)
 */
const PageHeader = ({ title, subtitle, actions, onRefresh, loading, badge }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6" data-testid="page-header">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h1 className={`text-xl sm:text-2xl lg:text-3xl font-semibold tracking-tight uppercase truncate ${isDark ? 'text-white' : 'text-zinc-950'}`}>
            {title}
          </h1>
          {badge}
        </div>
        {subtitle && (
          <p className={`text-sm mt-0.5 ${isDark ? 'text-[#B0B0B0]' : 'text-zinc-500'}`}>{subtitle}</p>
        )}
      </div>
      <div className="flex items-center gap-2 flex-wrap flex-shrink-0">
        {onRefresh && <PageRefreshButton onClick={onRefresh} loading={loading} />}
        {actions}
      </div>
    </div>
  );
};

export default PageHeader;
