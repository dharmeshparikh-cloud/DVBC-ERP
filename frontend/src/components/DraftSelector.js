import React from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { FileText, Clock, Trash2, Plus, FolderOpen } from 'lucide-react';

const DraftSelector = ({ 
  drafts, 
  loading,
  loadingDrafts,
  onSelect,
  onLoadDraft,
  onDelete,
  onDeleteDraft,
  onNewDraft,
  isOpen,
  onClose,
  title = "Your Drafts",
  description = "Continue where you left off or start fresh"
}) => {
  // Normalize props — support both naming conventions
  const handleSelect = onSelect || onLoadDraft;
  const handleDelete = onDelete || onDeleteDraft;
  const isLoading = loading || loadingDrafts;

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)} days ago`;
    return date.toLocaleDateString();
  };

  const getStepLabel = (step, draftType) => {
    if (draftType === 'onboarding') {
      const steps = ['Import', 'Personal', 'Employment', 'Documents', 'Bank', 'Review'];
      return steps[step] || `Step ${step + 1}`;
    }
    if (draftType === 'lead') return 'Lead Details';
    return `Step ${step + 1}`;
  };

  const draftCards = (
    <div className="space-y-3">
      {isLoading ? (
        <div className="text-center py-6 text-zinc-500">Loading drafts...</div>
      ) : !drafts || drafts.length === 0 ? (
        <div className="text-center py-6">
          <FileText className="w-10 h-10 mx-auto text-zinc-300 mb-2" />
          <p className="text-zinc-500 text-sm">No drafts found</p>
        </div>
      ) : (
        drafts.map((draft) => (
          <div
            key={draft.id}
            role="button"
            tabIndex={0}
            className="cursor-pointer rounded-lg border bg-card text-card-foreground shadow-sm hover:border-orange-300 transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              handleSelect?.(draft);
            }}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSelect?.(draft); }}
            data-testid={`draft-card-${draft.id}`}
          >
            <div className="p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText className="w-4 h-4 text-orange-500 flex-shrink-0" />
                    <span className="font-medium truncate">{draft.title}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-zinc-500">
                    <Badge variant="outline" className="text-xs">
                      {getStepLabel(draft.step, draft.draft_type)}
                    </Badge>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDate(draft.updated_at)}
                    </span>
                  </div>
                </div>
                {handleDelete && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-500 hover:text-red-700 hover:bg-red-50"
                    onClick={(e) => {
                      e.stopPropagation();
                      e.preventDefault();
                      handleDelete(draft.id);
                    }}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );

  // Inline mode: no Dialog wrapper (used when embedded inside another Dialog)
  if (isOpen === undefined || isOpen === null) {
    return draftCards;
  }

  // Dialog mode: full dialog wrapper
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col" onPointerDownOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FolderOpen className="w-5 h-5 text-orange-500" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto py-4">
          {draftCards}
        </div>

        <div className="border-t pt-4 flex justify-between">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          {onNewDraft && (
            <Button onClick={onNewDraft} className="bg-orange-500 hover:bg-orange-600">
              <Plus className="w-4 h-4 mr-2" />
              Start New
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Inline draft indicator component
export const DraftIndicator = ({ saving, lastSaved, onSave }) => {
  const formatLastSaved = () => {
    if (!lastSaved) return null;
    const diff = Date.now() - lastSaved.getTime();
    if (diff < 60000) return 'Saved just now';
    if (diff < 3600000) return `Saved ${Math.floor(diff / 60000)} min ago`;
    return `Saved at ${lastSaved.toLocaleTimeString()}`;
  };

  return (
    <div className="flex items-center gap-2 text-sm">
      {saving ? (
        <span className="text-orange-500 flex items-center gap-1">
          <span className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
          Saving...
        </span>
      ) : lastSaved ? (
        <span className="text-zinc-400 flex items-center gap-1">
          <span className="w-2 h-2 bg-emerald-500 rounded-full" />
          {formatLastSaved()}
        </span>
      ) : null}
      {onSave && (
        <Button variant="ghost" size="sm" onClick={onSave} disabled={saving}>
          Save Draft
        </Button>
      )}
    </div>
  );
};

export default DraftSelector;
