import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { 
  Lock, Unlock, RefreshCw, Eye, EyeOff, Maximize2, Minimize2,
  ChevronDown, ChevronUp, Settings2, X
} from 'lucide-react';

/**
 * LockableCard - A card component with presentation lock controls
 * 
 * Features:
 * - Lock/Unlock toggle to freeze data
 * - Expandable control panel
 * - Auto-refresh toggle
 * - Visibility toggle
 * - Fullscreen toggle with rich drill-down content
 */
const LockableCard = ({ 
  children, 
  className = '', 
  title,
  expandedContent,
  onRefresh,
  refreshInterval = null,
  isDark = false,
  cardId,
  lockedValues = {},
  onLockChange
}) => {
  const [isLocked, setIsLocked] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [isVisible, setIsVisible] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const handleLockToggle = () => {
    const newLockState = !isLocked;
    setIsLocked(newLockState);
    if (onLockChange) {
      onLockChange(cardId, { 
        locked: newLockState, 
        autoRefresh: newLockState ? false : autoRefresh,
        values: newLockState ? lockedValues : null 
      });
    }
    // When locking, also disable auto-refresh
    if (newLockState) {
      setAutoRefresh(false);
    }
  };

  const handleAutoRefreshToggle = () => {
    if (!isLocked) {
      setAutoRefresh(!autoRefresh);
    }
  };

  const handleFullscreenToggle = () => {
    setIsFullscreen(!isFullscreen);
  };

  if (!isVisible) {
    // Extract grid classes but override background colors
    const gridClasses = className.match(/col-span-\d+|row-span-\d+/g)?.join(' ') || '';
    return (
      <div 
        className={`${gridClasses} flex items-center justify-center border border-transparent rounded-xl cursor-pointer transition-all duration-300 hover:scale-[1.02] bg-gradient-to-br from-slate-100 via-blue-50 to-indigo-100 hover:from-slate-200 hover:via-blue-100 hover:to-indigo-200 shadow-sm`}
        onClick={() => setIsVisible(true)}
      >
        <div className="text-center p-4">
          <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-white/80 flex items-center justify-center shadow-sm">
            <EyeOff className="w-5 h-5 text-slate-500" />
          </div>
          <p className="text-sm text-slate-600 font-medium">Click to show</p>
          <p className="text-xs text-slate-400 mt-1">Card hidden</p>
        </div>
      </div>
    );
  }

  // Fullscreen with rich drill-down content
  if (isFullscreen) {
    return (
      <>
        {/* Fullscreen backdrop */}
        <div 
          className="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm"
          onClick={handleFullscreenToggle}
        />
        
        {/* Fullscreen card */}
        <div className={`fixed inset-6 z-50 rounded-2xl shadow-2xl overflow-hidden ${
          isDark ? 'bg-zinc-900' : 'bg-white'
        }`}>
          {/* Header */}
          <div className={`flex items-center justify-between px-6 py-4 border-b ${
            isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200 bg-zinc-50'
          }`}>
            <h2 className={`text-xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
              {title || 'Detailed View'}
            </h2>
            <div className="flex items-center gap-2">
              {/* Lock toggle in fullscreen */}
              <button
                onClick={handleLockToggle}
                className={`p-2 rounded-lg transition-colors ${
                  isLocked
                    ? 'bg-orange-500/20 text-orange-500'
                    : isDark ? 'hover:bg-zinc-700 text-zinc-400' : 'hover:bg-zinc-200 text-zinc-600'
                }`}
                title={isLocked ? 'Unlock Data' : 'Lock Data'}
              >
                {isLocked ? <Lock className="w-5 h-5" /> : <Unlock className="w-5 h-5" />}
              </button>
              <button
                onClick={handleFullscreenToggle}
                className={`p-2 rounded-lg transition-colors ${
                  isDark ? 'hover:bg-zinc-700 text-zinc-400' : 'hover:bg-zinc-200 text-zinc-600'
                }`}
                title="Exit Fullscreen"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
          
          {/* Content */}
          <div className={`p-6 overflow-auto h-[calc(100%-70px)] ${isLocked ? 'pointer-events-none' : ''}`}>
            {expandedContent || (
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <div className={`text-6xl mb-4 ${isDark ? 'text-zinc-700' : 'text-zinc-300'}`}>📊</div>
                  <p className={`text-lg ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                    Detailed view coming soon
                  </p>
                </div>
              </div>
            )}
          </div>
          
          {/* Lock indicator */}
          {isLocked && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
              <div className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white text-sm rounded-full shadow-lg">
                <Lock className="w-4 h-4" />
                <span>Data Locked for Presentation</span>
              </div>
            </div>
          )}
        </div>
      </>
    );
  }

  return (
    <>
      <Card className={`${className} relative group transition-all duration-200 ${
        isLocked ? 'ring-2 ring-orange-500/50' : ''
      }`}>
        {/* Lock indicator badge */}
        {isLocked && (
          <div className="absolute top-2 left-2 z-20">
            <div className="flex items-center gap-1 px-2 py-1 bg-orange-500 text-white text-xs rounded-full shadow-lg">
              <Lock className="w-3 h-3" />
              <span>Locked</span>
            </div>
          </div>
        )}

        {/* Control button - appears on hover or when expanded */}
        <div className={`absolute top-2 right-2 z-20 transition-opacity duration-200 ${
          isExpanded ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
        }`}>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={`p-1.5 rounded-lg transition-colors ${
              isDark 
                ? 'bg-zinc-800/90 hover:bg-zinc-700 text-zinc-300' 
                : 'bg-white/90 hover:bg-zinc-100 text-zinc-600 shadow-sm'
            }`}
            title="Card Settings"
          >
            <Settings2 className="w-4 h-4" />
          </button>
        </div>

        {/* Expandable Control Panel */}
        {isExpanded && (
          <div className={`absolute top-10 right-2 z-30 w-48 rounded-lg shadow-xl border overflow-hidden ${
            isDark 
              ? 'bg-zinc-800 border-zinc-700' 
              : 'bg-white border-zinc-200'
          }`}>
            {/* Header */}
            <div className={`px-3 py-2 border-b ${isDark ? 'border-zinc-700 bg-zinc-900/50' : 'border-zinc-100 bg-zinc-50'}`}>
              <p className={`text-xs font-semibold ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                Presentation Controls
              </p>
            </div>
            
            {/* Controls */}
            <div className="p-2 space-y-1">
              {/* Lock Toggle */}
              <button
                onClick={handleLockToggle}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors ${
                  isLocked
                    ? 'bg-orange-500/20 text-orange-500'
                    : isDark 
                      ? 'hover:bg-zinc-700 text-zinc-300' 
                      : 'hover:bg-zinc-100 text-zinc-700'
                }`}
              >
                <span className="flex items-center gap-2">
                  {isLocked ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                  Lock Data
                </span>
                <div className={`w-8 h-4 rounded-full transition-colors ${
                  isLocked ? 'bg-orange-500' : isDark ? 'bg-zinc-600' : 'bg-zinc-300'
                }`}>
                  <div className={`w-3 h-3 rounded-full bg-white shadow transition-transform mt-0.5 ${
                    isLocked ? 'translate-x-4 ml-0.5' : 'translate-x-0.5'
                  }`} />
                </div>
              </button>

              {/* Auto Refresh Toggle */}
              <button
                onClick={handleAutoRefreshToggle}
                disabled={isLocked}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors ${
                  isLocked 
                    ? 'opacity-50 cursor-not-allowed' 
                    : isDark 
                      ? 'hover:bg-zinc-700 text-zinc-300' 
                      : 'hover:bg-zinc-100 text-zinc-700'
                }`}
              >
                <span className="flex items-center gap-2">
                  <RefreshCw className={`w-4 h-4 ${autoRefresh && !isLocked ? 'animate-spin' : ''}`} />
                  Auto Refresh
                </span>
                <div className={`w-8 h-4 rounded-full transition-colors ${
                  autoRefresh && !isLocked ? 'bg-green-500' : isDark ? 'bg-zinc-600' : 'bg-zinc-300'
                }`}>
                  <div className={`w-3 h-3 rounded-full bg-white shadow transition-transform mt-0.5 ${
                    autoRefresh && !isLocked ? 'translate-x-4 ml-0.5' : 'translate-x-0.5'
                  }`} />
                </div>
              </button>

              {/* Visibility Toggle */}
              <button
                onClick={() => setIsVisible(false)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                  isDark 
                    ? 'hover:bg-zinc-700 text-zinc-300' 
                    : 'hover:bg-zinc-100 text-zinc-700'
                }`}
              >
                <EyeOff className="w-4 h-4" />
                Hide Card
              </button>

              {/* Fullscreen Toggle */}
              <button
                onClick={handleFullscreenToggle}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                  isDark 
                    ? 'hover:bg-zinc-700 text-zinc-300' 
                    : 'hover:bg-zinc-100 text-zinc-700'
                }`}
              >
                <Maximize2 className="w-4 h-4" />
                Expand Details
              </button>
            </div>

            {/* Footer hint */}
            <div className={`px-3 py-2 border-t ${isDark ? 'border-zinc-700' : 'border-zinc-100'}`}>
              <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                {isLocked ? '🔒 Data frozen for presentation' : 'Lock to freeze data'}
              </p>
            </div>
          </div>
        )}

        {/* Card Content */}
        <div className={`h-full ${isLocked ? 'pointer-events-none' : ''}`}>
          {children}
        </div>

        {/* Click outside to close panel */}
        {isExpanded && (
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsExpanded(false)}
          />
        )}
      </Card>
    </>
  );
};

export default LockableCard;
