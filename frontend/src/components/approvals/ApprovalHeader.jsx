/**
 * ApprovalHeader - Header Component for Approvals Center
 * Includes title, real-time indicator, refresh button
 * Memoized to prevent unnecessary re-renders
 */

import React, { memo } from 'react';
import { Button } from '../ui/button';
import { RefreshCw, Menu } from 'lucide-react';

export const ApprovalHeader = memo(({
  isDark,
  wsConnected,
  lastRefresh,
  loading,
  onRefresh,
  onToggleMobileMenu
}) => {
  return (
    <div className="mb-6 md:mb-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className={`text-xl md:text-2xl lg:text-3xl font-semibold tracking-tight mb-1 ${isDark ? 'text-zinc-100' : 'text-zinc-950'}`}>
            Approvals Center
          </h1>
          <div className="flex items-center gap-2 flex-wrap">
            <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
              Review and manage approval requests
            </p>
            {/* Real-time indicator - only show when connected */}
            {wsConnected && (
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Live
              </div>
            )}
          </div>
        </div>
        
        {/* Action buttons - Desktop */}
        <div className="hidden sm:flex items-center gap-2">
          <span className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
            Updated {lastRefresh.toLocaleTimeString()}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            className={`${isDark ? 'border-zinc-600' : ''}`}
            disabled={loading}
            data-testid="refresh-approvals-btn"
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
        
        {/* Mobile menu toggle */}
        <div className="sm:hidden flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            className={`${isDark ? 'border-zinc-600' : ''} flex-1`}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onToggleMobileMenu}
            className={`${isDark ? 'border-zinc-600' : ''}`}
          >
            <Menu className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
});

ApprovalHeader.displayName = 'ApprovalHeader';

export default ApprovalHeader;
