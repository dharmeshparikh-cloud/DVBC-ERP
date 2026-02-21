import React from 'react';
import { Cloud, CloudOff, Loader2, Save } from 'lucide-react';
import { Button } from './ui/button';
import { format } from 'date-fns';

/**
 * Draft save indicator showing auto-save status
 * Displays: Saving... | Saved at HH:mm | Save now button
 */
const DraftIndicator = ({ saving, lastSaved, onSave }) => {
  return (
    <div className="flex items-center gap-2 text-xs">
      {saving ? (
        <div className="flex items-center gap-1 text-zinc-500">
          <Loader2 className="w-3 h-3 animate-spin" />
          <span>Saving...</span>
        </div>
      ) : lastSaved ? (
        <div className="flex items-center gap-1 text-emerald-600">
          <Cloud className="w-3 h-3" />
          <span>Saved {format(new Date(lastSaved), 'HH:mm')}</span>
        </div>
      ) : (
        <div className="flex items-center gap-1 text-zinc-400">
          <CloudOff className="w-3 h-3" />
          <span>Not saved</span>
        </div>
      )}
      
      {onSave && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onSave}
          disabled={saving}
          className="h-6 px-2 text-xs hover:bg-zinc-100"
          data-testid="save-draft-btn"
        >
          <Save className="w-3 h-3 mr-1" />
          Save
        </Button>
      )}
    </div>
  );
};

export default DraftIndicator;
