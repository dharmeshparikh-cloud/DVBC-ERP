import React, { useState } from 'react';
import { AlertTriangle, XCircle, Info, ChevronDown, ChevronUp, ExternalLink, Copy, RefreshCw } from 'lucide-react';
import { Button } from './ui/button';
import { useNavigate } from 'react-router-dom';

/**
 * Detailed Error Display Component
 * Shows error with root cause, action items, and technical details
 */
export const ErrorDisplay = ({ error, onDismiss, onRetry }) => {
  const [showTechnical, setShowTechnical] = useState(false);
  const navigate = useNavigate();

  if (!error) return null;

  const getTypeColor = (type) => {
    switch (type) {
      case 'authorization':
      case 'permission':
        return 'border-red-500 bg-red-50 dark:bg-red-950';
      case 'validation':
      case 'business_rule':
        return 'border-amber-500 bg-amber-50 dark:bg-amber-950';
      case 'not_found':
        return 'border-blue-500 bg-blue-50 dark:bg-blue-950';
      default:
        return 'border-zinc-500 bg-zinc-50 dark:bg-zinc-900';
    }
  };

  const getIcon = (type) => {
    switch (type) {
      case 'authorization':
      case 'permission':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'validation':
      case 'business_rule':
        return <AlertTriangle className="w-5 h-5 text-amber-500" />;
      default:
        return <Info className="w-5 h-5 text-blue-500" />;
    }
  };

  const handleAction = () => {
    if (error.actionPath) {
      navigate(error.actionPath);
      onDismiss?.();
    } else if (error.actionType === 'login') {
      window.location.href = '/';
    } else if (error.actionType === 'retry' && onRetry) {
      onRetry();
    }
  };

  const copyTechnicalDetails = () => {
    const details = JSON.stringify(error.technical, null, 2);
    navigator.clipboard.writeText(details);
  };

  return (
    <div className={`rounded-lg border-l-4 p-4 mb-4 ${getTypeColor(error.type)}`} data-testid="error-display">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          {getIcon(error.type)}
          <div>
            <h4 className="font-semibold text-zinc-900 dark:text-zinc-100">{error.title}</h4>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">{error.message}</p>
          </div>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="text-zinc-400 hover:text-zinc-600">
            <XCircle className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Root Cause */}
      {error.rootCause && (
        <div className="mt-3 ml-8 p-2 bg-white/50 dark:bg-black/20 rounded text-sm">
          <span className="font-medium text-zinc-700 dark:text-zinc-300">📍 Root Cause: </span>
          <span className="text-zinc-600 dark:text-zinc-400">{error.rootCause}</span>
        </div>
      )}

      {/* Action */}
      {error.action && (
        <div className="mt-3 ml-8 flex items-center gap-2">
          <span className="text-sm font-medium text-emerald-700 dark:text-emerald-400">✅ Action Required:</span>
          {error.actionPath ? (
            <Button 
              size="sm" 
              variant="outline" 
              onClick={handleAction}
              className="text-xs"
              data-testid="error-action-btn"
            >
              {error.action} <ExternalLink className="w-3 h-3 ml-1" />
            </Button>
          ) : error.actionType === 'retry' && onRetry ? (
            <Button 
              size="sm" 
              variant="outline" 
              onClick={onRetry}
              className="text-xs"
            >
              <RefreshCw className="w-3 h-3 mr-1" /> Retry
            </Button>
          ) : (
            <span className="text-sm text-zinc-600 dark:text-zinc-400">{error.action}</span>
          )}
        </div>
      )}

      {/* Technical Details (Collapsible) */}
      {error.technical && (
        <div className="mt-3 ml-8">
          <button 
            onClick={() => setShowTechnical(!showTechnical)}
            className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-700"
          >
            {showTechnical ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            Technical Details
          </button>
          
          {showTechnical && (
            <div className="mt-2 p-2 bg-zinc-100 dark:bg-zinc-800 rounded text-xs font-mono relative">
              <button 
                onClick={copyTechnicalDetails}
                className="absolute top-1 right-1 p-1 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded"
                title="Copy to clipboard"
              >
                <Copy className="w-3 h-3" />
              </button>
              <div className="space-y-1">
                <p><span className="text-zinc-500">Status:</span> {error.technical.status}</p>
                <p><span className="text-zinc-500">Endpoint:</span> {error.technical.endpoint}</p>
                <p><span className="text-zinc-500">Method:</span> {error.technical.method}</p>
                <p><span className="text-zinc-500">Time:</span> {error.technical.timestamp}</p>
                {error.detail && <p><span className="text-zinc-500">Detail:</span> {error.detail}</p>}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Inline Error Message (smaller, for form fields)
 */
export const InlineError = ({ message, rootCause }) => {
  if (!message) return null;
  
  return (
    <div className="mt-1 text-sm text-red-600 dark:text-red-400" data-testid="inline-error">
      <p>{message}</p>
      {rootCause && (
        <p className="text-xs text-red-500/70 mt-0.5">💡 {rootCause}</p>
      )}
    </div>
  );
};

export default ErrorDisplay;
