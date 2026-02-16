import React from 'react';
import { Button } from './ui/button';
import { LayoutGrid, List } from 'lucide-react';

/**
 * Reusable View Toggle Component
 * Allows switching between Card and List views
 * 
 * Usage:
 * const [viewMode, setViewMode] = useState('card');
 * <ViewToggle viewMode={viewMode} onChange={setViewMode} />
 */
const ViewToggle = ({ viewMode, onChange, className = '' }) => {
  return (
    <div className={`flex items-center gap-1 p-1 bg-zinc-100 rounded-sm ${className}`} data-testid="view-toggle">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onChange('card')}
        className={`h-8 px-3 rounded-sm transition-colors ${
          viewMode === 'card' 
            ? 'bg-white shadow-sm text-zinc-900' 
            : 'text-zinc-500 hover:text-zinc-700 hover:bg-transparent'
        }`}
        data-testid="view-toggle-card"
      >
        <LayoutGrid className="w-4 h-4 mr-1.5" strokeWidth={1.5} />
        <span className="text-xs font-medium">Card</span>
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onChange('list')}
        className={`h-8 px-3 rounded-sm transition-colors ${
          viewMode === 'list' 
            ? 'bg-white shadow-sm text-zinc-900' 
            : 'text-zinc-500 hover:text-zinc-700 hover:bg-transparent'
        }`}
        data-testid="view-toggle-list"
      >
        <List className="w-4 h-4 mr-1.5" strokeWidth={1.5} />
        <span className="text-xs font-medium">List</span>
      </Button>
    </div>
  );
};

export default ViewToggle;
