import React, { useState } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { Filter, ChevronDown, X } from 'lucide-react';
import { Button } from './button';

/**
 * FilterBar - Responsive filter bar
 * Desktop: horizontal row of filters
 * Mobile: collapsible filter panel with chips
 * 
 * Props:
 * - filters: [{ key, label, value, options: [{value, label}], onChange }]
 * - searchValue: string
 * - onSearchChange: (val) => void
 * - searchPlaceholder: string
 */
const FilterBar = ({ filters = [], searchValue, onSearchChange, searchPlaceholder = 'Search...' }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [showMobileFilters, setShowMobileFilters] = useState(false);

  const activeCount = filters.filter(f => f.value && f.value !== 'all' && f.value !== '').length;
  const inputClass = `h-9 px-3 rounded-sm border text-sm w-full ${
    isDark ? 'bg-[#1A1A1C] border-[#2A2A2E] text-white placeholder:text-zinc-500' : 'bg-white border-zinc-200 text-zinc-900 placeholder:text-zinc-400'
  }`;

  return (
    <div className="mb-4" data-testid="filter-bar">
      {/* Desktop Filters */}
      <div className="hidden md:flex items-center gap-3 flex-wrap">
        {onSearchChange && (
          <div className="relative flex-1 max-w-xs">
            <input
              type="text"
              value={searchValue || ''}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={searchPlaceholder}
              className={inputClass}
              data-testid="filter-search"
            />
          </div>
        )}
        {filters.map(f => (
          <select
            key={f.key}
            value={f.value || 'all'}
            onChange={(e) => f.onChange(e.target.value)}
            className={`${inputClass} w-auto min-w-[120px]`}
            data-testid={`filter-${f.key}`}
          >
            {f.options.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        ))}
      </div>

      {/* Mobile Filters */}
      <div className="md:hidden space-y-2">
        {onSearchChange && (
          <input
            type="text"
            value={searchValue || ''}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            className={inputClass}
            data-testid="filter-search-mobile"
          />
        )}
        {filters.length > 0 && (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowMobileFilters(!showMobileFilters)}
              className="w-full justify-between"
              data-testid="filter-toggle-mobile"
            >
              <span className="flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5" />
                Filters {activeCount > 0 && <span className="px-1.5 py-0.5 rounded-full bg-orange-100 text-orange-700 text-[10px] font-medium">{activeCount}</span>}
              </span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showMobileFilters ? 'rotate-180' : ''}`} />
            </Button>
            {showMobileFilters && (
              <div className={`p-3 rounded-sm border space-y-2 ${isDark ? 'bg-[#1A1A1C] border-[#2A2A2E]' : 'bg-white border-zinc-200'}`}>
                {filters.map(f => (
                  <div key={f.key} className="space-y-1">
                    <label className={`text-xs font-medium ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>{f.label}</label>
                    <select
                      value={f.value || 'all'}
                      onChange={(e) => f.onChange(e.target.value)}
                      className={inputClass}
                      data-testid={`filter-${f.key}-mobile`}
                    >
                      {f.options.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
        {/* Active filter chips */}
        {activeCount > 0 && !showMobileFilters && (
          <div className="flex flex-wrap gap-1.5">
            {filters.filter(f => f.value && f.value !== 'all' && f.value !== '').map(f => (
              <span
                key={f.key}
                className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-medium ${
                  isDark ? 'bg-[#2A2A2E] text-zinc-300' : 'bg-zinc-100 text-zinc-700'
                }`}
              >
                {f.label}: {f.options.find(o => o.value === f.value)?.label || f.value}
                <X className="w-3 h-3 cursor-pointer" onClick={() => f.onChange('all')} />
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default FilterBar;
