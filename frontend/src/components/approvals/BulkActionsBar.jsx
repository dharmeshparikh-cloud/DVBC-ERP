/**
 * BulkActionsBar - Bulk Selection Actions Component
 * Shows when items are selected for bulk approve/reject
 */

import React from 'react';
import { Button } from '../../ui/button';
import { CheckSquare, CheckCircle, XCircle } from 'lucide-react';

export const BulkActionsBar = ({
  isDark,
  selectedCount,
  onApproveAll,
  onRejectAll,
  onClear
}) => {
  if (selectedCount === 0) return null;

  return (
    <div className={`mt-4 p-3 rounded-lg border-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 ${
      isDark ? 'bg-orange-900/20 border-orange-600' : 'bg-orange-50 border-orange-300'
    }`}>
      <div className="flex items-center gap-2">
        <CheckSquare className="w-5 h-5 text-orange-500" />
        <span className={`font-medium ${isDark ? 'text-orange-400' : 'text-orange-700'}`}>
          {selectedCount} item{selectedCount > 1 ? 's' : ''} selected
        </span>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <Button
          size="sm"
          onClick={onApproveAll}
          className="bg-emerald-600 hover:bg-emerald-700 text-white"
          data-testid="bulk-approve-btn"
        >
          <CheckCircle className="w-4 h-4 mr-1" />
          Approve All
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={onRejectAll}
          className="border-red-300 text-red-600 hover:bg-red-50"
          data-testid="bulk-reject-btn"
        >
          <XCircle className="w-4 h-4 mr-1" />
          Reject All
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={onClear}
          className={isDark ? 'text-zinc-400' : 'text-zinc-500'}
        >
          Clear
        </Button>
      </div>
    </div>
  );
};

export default BulkActionsBar;
