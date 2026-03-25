import React, { useState } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Button } from './ui/button';
import { Sparkles, Loader2, Check, X } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

const AISuggestButton = ({
  contextType = 'notes',
  currentText = '',
  clientName = '',
  company = '',
  meetingType = '',
  additionalContext = '',
  onAccept,
  className,
  size = 'sm',
  variant = 'ghost',
  label = 'AI Suggest',
}) => {
  const [loading, setLoading] = useState(false);
  const [suggestion, setSuggestion] = useState(null);

  const handleSuggest = async (e) => {
    e?.preventDefault();
    e?.stopPropagation();
    if (!currentText?.trim() && !additionalContext?.trim()) {
      toast.info('Type some rough notes first, then click AI Suggest to polish them.');
      return;
    }
    setLoading(true);
    setSuggestion(null);
    try {
      const res = await axios.post(`${API}/ai/suggest`, {
        context_type: contextType,
        rough_text: currentText,
        client_name: clientName,
        company: company,
        meeting_type: meetingType,
        additional_context: additionalContext,
      });
      setSuggestion(res.data.suggestion);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'AI suggestion failed');
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = (e) => {
    e?.preventDefault();
    e?.stopPropagation();
    if (suggestion && onAccept) {
      onAccept(suggestion);
      setSuggestion(null);
    }
  };

  const handleDismiss = (e) => {
    e?.preventDefault();
    e?.stopPropagation();
    setSuggestion(null);
  };

  if (suggestion) {
    return (
      <div className="space-y-2" data-testid="ai-suggestion-preview">
        <div className="text-[11px] font-medium text-amber-600 flex items-center gap-1">
          <Sparkles className="w-3 h-3" /> AI Suggestion
        </div>
        <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-md p-3 text-xs text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap max-h-40 overflow-y-auto">
          {suggestion}
        </div>
        <div className="flex gap-2">
          <Button type="button" size="sm" onClick={handleAccept} className="h-6 px-2 text-[11px] bg-amber-600 hover:bg-amber-700 text-white" data-testid="ai-accept-btn">
            <Check className="w-3 h-3 mr-1" /> Accept
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={handleDismiss} className="h-6 px-2 text-[11px] text-zinc-500" data-testid="ai-dismiss-btn">
            <X className="w-3 h-3 mr-1" /> Dismiss
          </Button>
        </div>
      </div>
    );
  }

  return (
    <Button
      type="button"
      variant={variant}
      size={size}
      onClick={handleSuggest}
      disabled={loading}
      className={cn("h-6 px-2 text-[10px] text-amber-600 hover:text-amber-700 hover:bg-amber-50", className)}
      data-testid={`ai-suggest-${contextType}`}
    >
      {loading ? (
        <><Loader2 className="w-3 h-3 mr-1 animate-spin" /> Polishing...</>
      ) : (
        <><Sparkles className="w-3 h-3 mr-1" /> {label}</>
      )}
    </Button>
  );
};

export default AISuggestButton;
