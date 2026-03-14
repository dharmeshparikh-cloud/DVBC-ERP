import React from 'react';
import { Button } from './ui/button';
import { RefreshCw } from 'lucide-react';

/**
 * Reusable refresh button for ERP pages.
 * Props:
 * - onClick: callback to trigger data refresh
 * - loading: boolean for spinner state
 * - className: optional extra classes
 */
const PageRefreshButton = ({ onClick, loading = false, className = '' }) => {
  return (
    <Button
      onClick={onClick}
      variant="outline"
      size="sm"
      className={`gap-1.5 ${className}`}
      disabled={loading}
      data-testid="page-refresh-btn"
    >
      <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
      Refresh
    </Button>
  );
};

export default PageRefreshButton;
