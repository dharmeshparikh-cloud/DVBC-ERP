import React, { useState } from 'react';
import { Card, CardContent } from './ui/card';
import { 
  Lock, Unlock, RefreshCw, Eye, EyeOff, Maximize2, Minimize2,
  ChevronDown, ChevronUp, Settings2
} from 'lucide-react';

/**
 * LockableCard - A card component with presentation lock controls
 * 
 * Features:
 * - Lock/Unlock toggle to freeze data
 * - Expandable control panel
 * - Auto-refresh toggle
 * - Visibility toggle
 * - Fullscreen toggle
 */
const LockableCard = ({ 
  children, 
  className = '', 
  title,
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
    return (
      <div 
        className={`${className} flex items-center justify-center border-2 border-dashed ${
          isDark ? 'border-zinc-700 bg-zinc-900/50' : 'border-zinc-300 bg-zinc-100/50'
        } rounded-lg cursor-pointer`}
        onClick={() => setIsVisible(true)}
      >
        <div className="text-center p-4">
          <EyeOff className={`w-6 h-6 mx-auto mb-2 ${isDark ? 'text-zinc-600' : 'text-zinc-400'}`} />
          <p className={`text-xs ${isDark ? 'text-zinc-600' : 'text-zinc-400'}`}>Click to show</p>
        </div>
      </div>
    );
  }

  const fullscreenClasses = isFullscreen 
    ? 'fixed inset-4 z-50 col-span-12 row-span-6' 
    : className;

  return (
    <>
      {/* Fullscreen backdrop */}
      {isFullscreen && (
        <div 
          className="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm"
          onClick={handleFullscreenToggle}
        />
      )}
      
      <Card className={`${fullscreenClasses} relative group transition-all duration-200 ${
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
                {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                {isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
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
