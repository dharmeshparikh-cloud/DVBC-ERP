/**
 * SalesDataTable.jsx - Unified Excel-like DataTable for Sales Module
 * 
 * MANDATORY for all Sales tables. Provides:
 * - Column filters (Excel-style dropdown)
 * - Global search
 * - Sorting (ASC/DESC)
 * - Multi-filter (AND logic)
 * - Server-side pagination
 * - Filter chips
 * - Clear filters
 * - Sticky header
 * - Debounce (300ms)
 * - Color coding for status
 * - Quick views
 * 
 * DO NOT use manual <table> with .map() in Sales module.
 * ALL Sales tables MUST use this component.
 */

import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { 
  ChevronUp, ChevronDown, Search, X, Filter, RefreshCw, 
  ChevronLeft, ChevronRight, Download, Loader2, AlertCircle,
  Calendar, SlidersHorizontal, Eye, MoreHorizontal
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { 
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, 
  DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuLabel 
} from '../ui/dropdown-menu';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';

const API = process.env.REACT_APP_BACKEND_URL;

// ═══════════════════════════════════════════════════════════════════
// FILTER TYPES
// ═══════════════════════════════════════════════════════════════════

const FILTER_TYPES = {
  TEXT: 'text',           // contains / startsWith
  NUMBER: 'number',       // range (min/max)
  DATE: 'date',           // between (from/to)
  DROPDOWN: 'dropdown',   // status / stage / owner
  BOOLEAN: 'boolean',     // yes/no
  MULTI_SELECT: 'multi_select', // multiple values
};

// ═══════════════════════════════════════════════════════════════════
// COLOR CODING FOR SALES
// ═══════════════════════════════════════════════════════════════════

const STATUS_COLORS = {
  // Pipeline stages
  new: 'bg-blue-50 text-blue-700 border-blue-200',
  meeting: 'bg-purple-50 text-purple-700 border-purple-200',
  pricing_plan: 'bg-amber-50 text-amber-700 border-amber-200',
  sow: 'bg-orange-50 text-orange-700 border-orange-200',
  quotation: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  agreement: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  payment: 'bg-teal-50 text-teal-700 border-teal-200',
  kickoff_request: 'bg-lime-50 text-lime-700 border-lime-200',
  kick_accept: 'bg-green-50 text-green-700 border-green-200',
  closed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  
  // Status indicators
  overdue: 'bg-red-50 text-red-700 border-red-200',
  due_today: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  progressing: 'bg-green-50 text-green-700 border-green-200',
  paused: 'bg-zinc-100 text-zinc-600 border-zinc-200',
  lost: 'bg-red-100 text-red-800 border-red-300',
  
  // Generic
  pending: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  rejected: 'bg-red-50 text-red-700 border-red-200',
  draft: 'bg-zinc-50 text-zinc-600 border-zinc-200',
  active: 'bg-green-50 text-green-700 border-green-200',
};

const getStatusColor = (status, rowData = {}) => {
  // Check for overdue based on date fields
  if (rowData.next_followup_date || rowData.due_date) {
    const dueDate = new Date(rowData.next_followup_date || rowData.due_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (dueDate < today) return STATUS_COLORS.overdue;
    if (dueDate.toDateString() === today.toDateString()) return STATUS_COLORS.due_today;
  }
  
  return STATUS_COLORS[status?.toLowerCase()] || STATUS_COLORS.draft;
};

// ═══════════════════════════════════════════════════════════════════
// QUICK VIEWS FOR SALES
// ═══════════════════════════════════════════════════════════════════

const QUICK_VIEWS = [
  { id: 'all', label: 'All', filters: {} },
  { id: 'my_leads', label: 'My Leads', filters: { assigned_to: 'CURRENT_USER' } },
  { id: 'today_followups', label: 'Today Follow-ups', filters: { due_date: 'TODAY' } },
  { id: 'hot_deals', label: 'Hot Deals (>5L)', filters: { deal_value_min: 500000 } },
  { id: 'stuck_deals', label: 'Stuck (>7 days)', filters: { days_since_activity: 7 } },
  { id: 'overdue', label: 'Overdue', filters: { status: 'overdue' } },
];

// ═══════════════════════════════════════════════════════════════════
// DEBOUNCE HOOK
// ═══════════════════════════════════════════════════════════════════

const useDebounce = (value, delay = 300) => {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  
  return debouncedValue;
};

// ═══════════════════════════════════════════════════════════════════
// FILTER CHIP COMPONENT
// ═══════════════════════════════════════════════════════════════════

const FilterChip = ({ label, value, onRemove }) => (
  <Badge 
    variant="secondary" 
    className="flex items-center gap-1 px-2 py-1 text-xs bg-zinc-100 hover:bg-zinc-200"
  >
    <span className="text-zinc-500">{label}:</span>
    <span className="font-medium text-zinc-700">{value}</span>
    <button onClick={onRemove} className="ml-1 hover:text-red-500">
      <X className="w-3 h-3" />
    </button>
  </Badge>
);

// ═══════════════════════════════════════════════════════════════════
// COLUMN FILTER DROPDOWN
// ═══════════════════════════════════════════════════════════════════

const ColumnFilter = ({ column, value, onChange, options = [] }) => {
  const [localValue, setLocalValue] = useState(value || '');
  const [isOpen, setIsOpen] = useState(false);
  
  const handleApply = () => {
    onChange(localValue);
    setIsOpen(false);
  };
  
  const handleClear = () => {
    setLocalValue('');
    onChange('');
    setIsOpen(false);
  };
  
  if (column.filterType === FILTER_TYPES.DROPDOWN || column.filterType === FILTER_TYPES.MULTI_SELECT) {
    return (
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <button className={cn(
            "p-1 rounded hover:bg-zinc-100 transition-colors",
            value ? "text-blue-600" : "text-zinc-400"
          )}>
            <Filter className="w-3 h-3" />
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-48 p-2" align="start">
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {(column.filterOptions || options || []).map(opt => (
              <label key={opt.value || opt} className="flex items-center gap-2 p-1 hover:bg-zinc-50 rounded cursor-pointer text-sm">
                <input
                  type={column.filterType === FILTER_TYPES.MULTI_SELECT ? "checkbox" : "radio"}
                  name={column.key}
                  value={opt.value || opt}
                  checked={localValue === (opt.value || opt)}
                  onChange={(e) => setLocalValue(e.target.value)}
                  className="w-3 h-3"
                />
                <span>{opt.label || opt}</span>
              </label>
            ))}
          </div>
          <div className="flex gap-1 mt-2 pt-2 border-t">
            <Button size="sm" variant="ghost" onClick={handleClear} className="flex-1 h-7 text-xs">Clear</Button>
            <Button size="sm" onClick={handleApply} className="flex-1 h-7 text-xs">Apply</Button>
          </div>
        </PopoverContent>
      </Popover>
    );
  }
  
  if (column.filterType === FILTER_TYPES.NUMBER) {
    return (
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <button className={cn(
            "p-1 rounded hover:bg-zinc-100 transition-colors",
            value ? "text-blue-600" : "text-zinc-400"
          )}>
            <Filter className="w-3 h-3" />
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-40 p-2" align="start">
          <div className="space-y-2">
            <Input
              type="number"
              placeholder="Min"
              value={localValue.min || ''}
              onChange={(e) => setLocalValue({ ...localValue, min: e.target.value })}
              className="h-7 text-xs"
            />
            <Input
              type="number"
              placeholder="Max"
              value={localValue.max || ''}
              onChange={(e) => setLocalValue({ ...localValue, max: e.target.value })}
              className="h-7 text-xs"
            />
          </div>
          <div className="flex gap-1 mt-2 pt-2 border-t">
            <Button size="sm" variant="ghost" onClick={handleClear} className="flex-1 h-7 text-xs">Clear</Button>
            <Button size="sm" onClick={handleApply} className="flex-1 h-7 text-xs">Apply</Button>
          </div>
        </PopoverContent>
      </Popover>
    );
  }
  
  if (column.filterType === FILTER_TYPES.DATE) {
    return (
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <button className={cn(
            "p-1 rounded hover:bg-zinc-100 transition-colors",
            value ? "text-blue-600" : "text-zinc-400"
          )}>
            <Calendar className="w-3 h-3" />
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-44 p-2" align="start">
          <div className="space-y-2">
            <div>
              <label className="text-xs text-zinc-500">From</label>
              <Input
                type="date"
                value={localValue.from || ''}
                onChange={(e) => setLocalValue({ ...localValue, from: e.target.value })}
                className="h-7 text-xs"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-500">To</label>
              <Input
                type="date"
                value={localValue.to || ''}
                onChange={(e) => setLocalValue({ ...localValue, to: e.target.value })}
                className="h-7 text-xs"
              />
            </div>
          </div>
          <div className="flex gap-1 mt-2 pt-2 border-t">
            <Button size="sm" variant="ghost" onClick={handleClear} className="flex-1 h-7 text-xs">Clear</Button>
            <Button size="sm" onClick={handleApply} className="flex-1 h-7 text-xs">Apply</Button>
          </div>
        </PopoverContent>
      </Popover>
    );
  }
  
  // Default: Text filter
  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <button className={cn(
          "p-1 rounded hover:bg-zinc-100 transition-colors",
          value ? "text-blue-600" : "text-zinc-400"
        )}>
          <Filter className="w-3 h-3" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-48 p-2" align="start">
        <Input
          placeholder={`Filter ${column.label}...`}
          value={localValue}
          onChange={(e) => setLocalValue(e.target.value)}
          className="h-8 text-sm"
          onKeyDown={(e) => e.key === 'Enter' && handleApply()}
        />
        <div className="flex gap-1 mt-2">
          <Button size="sm" variant="ghost" onClick={handleClear} className="flex-1 h-7 text-xs">Clear</Button>
          <Button size="sm" onClick={handleApply} className="flex-1 h-7 text-xs">Apply</Button>
        </div>
      </PopoverContent>
    </Popover>
  );
};

// ═══════════════════════════════════════════════════════════════════
// MAIN SALES DATATABLE COMPONENT
// ═══════════════════════════════════════════════════════════════════

export const SalesDataTable = ({
  // Required
  endpoint,
  columns,
  queryKey,
  
  // Optional
  title,
  defaultPageSize = 20,
  defaultSort = { field: 'created_at', direction: 'desc' },
  quickViews = QUICK_VIEWS,
  showQuickViews = true,
  showExport = true,
  showGlobalSearch = true,
  onRowClick,
  rowActions,
  emptyMessage = 'No data found',
  className,
  stickyHeader = true,
  
  // Custom renderers
  renderCell,
  renderActions,
  
  // Additional filters from parent
  externalFilters = {},
  
  // Callbacks
  onDataLoad,
  onError,
}) => {
  // State
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(defaultPageSize);
  const [sortField, setSortField] = useState(defaultSort.field);
  const [sortDirection, setSortDirection] = useState(defaultSort.direction);
  const [globalSearch, setGlobalSearch] = useState('');
  const [columnFilters, setColumnFilters] = useState({});
  const [activeQuickView, setActiveQuickView] = useState('all');
  
  // Debounced search
  const debouncedSearch = useDebounce(globalSearch, 300);
  const debouncedFilters = useDebounce(columnFilters, 300);
  
  // Build query params
  const queryParams = useMemo(() => {
    const params = {
      page,
      page_size: pageSize,
      sort_field: sortField,
      sort_direction: sortDirection,
      ...externalFilters,
    };
    
    if (debouncedSearch) {
      params.search = debouncedSearch;
    }
    
    // Add column filters
    Object.entries(debouncedFilters).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        if (typeof value === 'object') {
          // Range filters
          if (value.min) params[`${key}_min`] = value.min;
          if (value.max) params[`${key}_max`] = value.max;
          if (value.from) params[`${key}_from`] = value.from;
          if (value.to) params[`${key}_to`] = value.to;
        } else {
          params[key] = value;
        }
      }
    });
    
    // Quick view filters
    const quickView = quickViews.find(v => v.id === activeQuickView);
    if (quickView?.filters) {
      Object.entries(quickView.filters).forEach(([key, value]) => {
        if (value === 'CURRENT_USER') {
          params[key] = localStorage.getItem('user_id') || '';
        } else if (value === 'TODAY') {
          params[key] = new Date().toISOString().split('T')[0];
        } else {
          params[key] = value;
        }
      });
    }
    
    return params;
  }, [page, pageSize, sortField, sortDirection, debouncedSearch, debouncedFilters, activeQuickView, externalFilters, quickViews]);
  
  // Fetch data
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: [queryKey, queryParams],
    queryFn: async () => {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}${endpoint}`, {
        params: queryParams,
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
    keepPreviousData: true,
    onSuccess: onDataLoad,
    onError,
  });
  
  // Extract data and pagination info
  const tableData = useMemo(() => {
    if (Array.isArray(data)) return data;
    return data?.data || data?.items || data?.results || [];
  }, [data]);
  
  const totalItems = data?.total || data?.total_count || tableData.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  
  // Handle sort
  const handleSort = useCallback((field) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
    setPage(1);
  }, [sortField]);
  
  // Handle column filter change
  const handleFilterChange = useCallback((columnKey, value) => {
    setColumnFilters(prev => ({
      ...prev,
      [columnKey]: value
    }));
    setPage(1);
  }, []);
  
  // Clear all filters
  const clearAllFilters = useCallback(() => {
    setColumnFilters({});
    setGlobalSearch('');
    setActiveQuickView('all');
    setPage(1);
  }, []);
  
  // Export to CSV
  const handleExport = useCallback(() => {
    if (!tableData.length) return;
    
    const headers = columns.map(c => c.label).join(',');
    const rows = tableData.map(row => 
      columns.map(c => {
        const value = row[c.key];
        // Escape commas and quotes
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value ?? '';
      }).join(',')
    ).join('\n');
    
    const csv = `${headers}\n${rows}`;
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${queryKey}_export_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  }, [tableData, columns, queryKey]);
  
  // Active filters count
  const activeFiltersCount = Object.values(columnFilters).filter(v => v !== '' && v !== null).length;
  
  // Render cell value
  const renderCellValue = (row, column) => {
    // Custom renderer
    if (renderCell) {
      const custom = renderCell(row, column);
      if (custom !== undefined) return custom;
    }
    
    // Column-specific renderer
    if (column.render) {
      return column.render(row[column.key], row);
    }
    
    const value = row[column.key];
    
    // Status badge
    if (column.type === 'status' || column.key === 'status' || column.key === 'stage') {
      return (
        <span className={cn(
          "px-2 py-0.5 text-xs font-medium rounded border",
          getStatusColor(value, row)
        )}>
          {value?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || '-'}
        </span>
      );
    }
    
    // Date formatting
    if (column.type === 'date' || column.key.includes('date') || column.key.includes('_at')) {
      if (!value) return '-';
      try {
        return new Date(value).toLocaleDateString('en-IN', { 
          day: '2-digit', month: 'short', year: 'numeric' 
        });
      } catch {
        return value;
      }
    }
    
    // Currency formatting
    if (column.type === 'currency' || column.key.includes('value') || column.key.includes('amount')) {
      if (value === null || value === undefined) return '-';
      return `₹${Number(value).toLocaleString('en-IN')}`;
    }
    
    // Boolean
    if (column.type === 'boolean') {
      return value ? 'Yes' : 'No';
    }
    
    return value ?? '-';
  };
  
  return (
    <div className={cn("border border-zinc-200 rounded-lg bg-white", className)}>
      {/* Header */}
      <div className="p-3 border-b border-zinc-100 space-y-3">
        {/* Title & Actions Row */}
        <div className="flex items-center justify-between gap-3">
          {title && (
            <h3 className="font-semibold text-zinc-900">{title}</h3>
          )}
          
          <div className="flex items-center gap-2 ml-auto">
            {/* Global Search */}
            {showGlobalSearch && (
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                <Input
                  placeholder="Search..."
                  value={globalSearch}
                  onChange={(e) => setGlobalSearch(e.target.value)}
                  className="pl-8 h-8 w-48 text-sm"
                  data-testid="sales-table-search"
                />
                {globalSearch && (
                  <button 
                    onClick={() => setGlobalSearch('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2"
                  >
                    <X className="w-3 h-3 text-zinc-400 hover:text-zinc-600" />
                  </button>
                )}
              </div>
            )}
            
            {/* Refresh */}
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => refetch()}
              disabled={isFetching}
              className="h-8 px-2"
            >
              <RefreshCw className={cn("w-4 h-4", isFetching && "animate-spin")} />
            </Button>
            
            {/* Export */}
            {showExport && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={handleExport}
                disabled={!tableData.length}
                className="h-8 px-2"
              >
                <Download className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
        
        {/* Quick Views */}
        {showQuickViews && quickViews.length > 0 && (
          <div className="flex items-center gap-1 overflow-x-auto pb-1">
            {quickViews.map(view => (
              <button
                key={view.id}
                onClick={() => {
                  setActiveQuickView(view.id);
                  setPage(1);
                }}
                className={cn(
                  "px-3 py-1 text-xs font-medium rounded-full whitespace-nowrap transition-colors",
                  activeQuickView === view.id
                    ? "bg-zinc-900 text-white"
                    : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
                )}
                data-testid={`quick-view-${view.id}`}
              >
                {view.label}
              </button>
            ))}
          </div>
        )}
        
        {/* Active Filter Chips */}
        {(activeFiltersCount > 0 || globalSearch) && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-zinc-500">Filters:</span>
            {globalSearch && (
              <FilterChip 
                label="Search" 
                value={globalSearch} 
                onRemove={() => setGlobalSearch('')} 
              />
            )}
            {Object.entries(columnFilters).map(([key, value]) => {
              if (!value || value === '') return null;
              const column = columns.find(c => c.key === key);
              const displayValue = typeof value === 'object' 
                ? Object.values(value).filter(Boolean).join(' - ')
                : value;
              return (
                <FilterChip
                  key={key}
                  label={column?.label || key}
                  value={displayValue}
                  onRemove={() => handleFilterChange(key, '')}
                />
              );
            })}
            <button
              onClick={clearAllFilters}
              className="text-xs text-red-500 hover:text-red-700 underline"
            >
              Clear all
            </button>
          </div>
        )}
      </div>
      
      {/* Table */}
      <div className="overflow-x-auto min-w-0">
        <table className="w-full text-sm min-w-[800px]">
          <thead className={cn(
            "bg-zinc-50 border-b border-zinc-200",
            stickyHeader && "sticky top-0 z-10"
          )}>
            <tr>
              {columns.map(column => (
                <th 
                  key={column.key}
                  className="text-left px-3 py-2 text-xs uppercase tracking-wide text-zinc-500 font-medium"
                  style={{ width: column.width }}
                >
                  <div className="flex items-center gap-1">
                    {/* Sort button */}
                    {column.sortable !== false && (
                      <button
                        onClick={() => handleSort(column.key)}
                        className="flex items-center gap-1 hover:text-zinc-700"
                      >
                        <span>{column.label}</span>
                        {sortField === column.key ? (
                          sortDirection === 'asc' 
                            ? <ChevronUp className="w-3 h-3" />
                            : <ChevronDown className="w-3 h-3" />
                        ) : (
                          <div className="w-3 h-3" />
                        )}
                      </button>
                    )}
                    {column.sortable === false && <span>{column.label}</span>}
                    
                    {/* Column filter */}
                    {column.filterable !== false && column.filterType && (
                      <ColumnFilter
                        column={column}
                        value={columnFilters[column.key]}
                        onChange={(value) => handleFilterChange(column.key, value)}
                      />
                    )}
                  </div>
                </th>
              ))}
              {(rowActions || renderActions) && (
                <th className="text-center px-3 py-2 text-xs uppercase tracking-wide text-zinc-500 font-medium w-20">
                  Actions
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={columns.length + (rowActions ? 1 : 0)} className="text-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto text-zinc-400" />
                  <p className="text-sm text-zinc-500 mt-2">Loading...</p>
                </td>
              </tr>
            ) : isError ? (
              <tr>
                <td colSpan={columns.length + (rowActions ? 1 : 0)} className="text-center py-12">
                  <AlertCircle className="w-6 h-6 mx-auto text-red-400" />
                  <p className="text-sm text-red-500 mt-2">
                    {error?.message || 'Failed to load data'}
                  </p>
                  <Button variant="ghost" size="sm" onClick={() => refetch()} className="mt-2">
                    Retry
                  </Button>
                </td>
              </tr>
            ) : tableData.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (rowActions ? 1 : 0)} className="text-center py-12">
                  <Eye className="w-6 h-6 mx-auto text-zinc-300" />
                  <p className="text-sm text-zinc-500 mt-2">{emptyMessage}</p>
                </td>
              </tr>
            ) : (
              tableData.map((row, idx) => (
                <tr
                  key={row.id || idx}
                  onClick={() => onRowClick?.(row)}
                  className={cn(
                    "border-b border-zinc-100 hover:bg-zinc-50 transition-colors",
                    onRowClick && "cursor-pointer"
                  )}
                  data-testid={`sales-table-row-${row.id || idx}`}
                >
                  {columns.map(column => (
                    <td 
                      key={column.key}
                      className={cn(
                        "px-3 py-2.5 text-zinc-700",
                        column.className
                      )}
                    >
                      {renderCellValue(row, column)}
                    </td>
                  ))}
                  {(rowActions || renderActions) && (
                    <td className="px-3 py-2.5 text-center" onClick={(e) => e.stopPropagation()}>
                      {renderActions ? renderActions(row) : (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                              <MoreHorizontal className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {rowActions.map((action, i) => (
                              <DropdownMenuItem
                                key={i}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  action.onClick(row);
                                }}
                                className={action.className}
                              >
                                {action.icon && <action.icon className="w-4 h-4 mr-2" />}
                                {action.label}
                              </DropdownMenuItem>
                            ))}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      
      {/* Pagination */}
      {tableData.length > 0 && (
        <div className="flex items-center justify-between px-3 py-2 border-t border-zinc-100 bg-zinc-50/50">
          <div className="text-xs text-zinc-500">
            Showing {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, totalItems)} of {totalItems}
          </div>
          
          <div className="flex items-center gap-2">
            {/* Page size selector */}
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              className="h-7 px-2 text-xs border border-zinc-200 rounded bg-white"
            >
              {[10, 20, 50, 100].map(size => (
                <option key={size} value={size}>{size} / page</option>
              ))}
            </select>
            
            {/* Page navigation */}
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="h-7 w-7 p-0"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              
              <span className="text-xs text-zinc-600 px-2">
                Page {page} of {totalPages || 1}
              </span>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="h-7 w-7 p-0"
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
// EXPORTS
// ═══════════════════════════════════════════════════════════════════

export { FILTER_TYPES, STATUS_COLORS, QUICK_VIEWS, getStatusColor };
export default SalesDataTable;
