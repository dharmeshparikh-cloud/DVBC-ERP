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
 * - **SAVED VIEWS** - Save and load custom filter configurations
 * - **EXPORT TO CSV** - Export current page or all data
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
  Calendar, SlidersHorizontal, Eye, MoreHorizontal, Save, 
  FolderOpen, Trash2, Star, Check, FileDown, Lock
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { 
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, 
  DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuLabel 
} from '../ui/dropdown-menu';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../ui/dialog';
import { Label } from '../ui/label';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { cn } from '../../lib/utils';
import { toast } from 'sonner';
import { usePermissions } from '../../contexts/PermissionContext';

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
// SAVED VIEWS HOOK - Persist user's custom views to localStorage
// ═══════════════════════════════════════════════════════════════════

const SAVED_VIEWS_KEY_PREFIX = 'sales_saved_views_';

const useSavedViews = (tableKey) => {
  const storageKey = `${SAVED_VIEWS_KEY_PREFIX}${tableKey}`;
  
  const [savedViews, setSavedViews] = useState(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });
  
  const saveView = useCallback((name, config, isDefault = false) => {
    const newView = {
      id: `view_${Date.now()}`,
      name,
      config,
      isDefault,
      createdAt: new Date().toISOString(),
    };
    
    setSavedViews(prev => {
      // If setting as default, unset other defaults
      const updated = isDefault 
        ? prev.map(v => ({ ...v, isDefault: false }))
        : prev;
      const newViews = [...updated, newView];
      localStorage.setItem(storageKey, JSON.stringify(newViews));
      return newViews;
    });
    
    return newView;
  }, [storageKey]);
  
  const deleteView = useCallback((viewId) => {
    setSavedViews(prev => {
      const newViews = prev.filter(v => v.id !== viewId);
      localStorage.setItem(storageKey, JSON.stringify(newViews));
      return newViews;
    });
  }, [storageKey]);
  
  const setDefaultView = useCallback((viewId) => {
    setSavedViews(prev => {
      const newViews = prev.map(v => ({
        ...v,
        isDefault: v.id === viewId
      }));
      localStorage.setItem(storageKey, JSON.stringify(newViews));
      return newViews;
    });
  }, [storageKey]);
  
  const getDefaultView = useCallback(() => {
    return savedViews.find(v => v.isDefault);
  }, [savedViews]);
  
  return { savedViews, saveView, deleteView, setDefaultView, getDefaultView };
};

// ═══════════════════════════════════════════════════════════════════
// SAVE VIEW DIALOG COMPONENT
// ═══════════════════════════════════════════════════════════════════

const SaveViewDialog = ({ open, onOpenChange, onSave, currentConfig }) => {
  const [viewName, setViewName] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  
  const handleSave = () => {
    if (!viewName.trim()) {
      toast.error('Please enter a view name');
      return;
    }
    onSave(viewName.trim(), currentConfig, isDefault);
    setViewName('');
    setIsDefault(false);
    onOpenChange(false);
    toast.success(`View "${viewName}" saved successfully`);
  };
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Save className="w-5 h-5 text-blue-500" />
            Save Current View
          </DialogTitle>
          <DialogDescription>
            Save your current filters, sorting, and column settings as a reusable view.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="view-name">View Name</Label>
            <Input
              id="view-name"
              placeholder="e.g., My Hot Leads, Overdue Follow-ups"
              value={viewName}
              onChange={(e) => setViewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSave()}
              data-testid="save-view-name-input"
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
              className="w-4 h-4 rounded border-zinc-300"
            />
            <span className="text-sm text-zinc-600">Set as default view</span>
          </label>
          <div className="p-3 bg-zinc-50 rounded-lg text-xs text-zinc-500">
            <p className="font-medium text-zinc-700 mb-1">This view will save:</p>
            <ul className="list-disc list-inside space-y-0.5">
              <li>Active filters ({Object.keys(currentConfig.columnFilters || {}).length} filters)</li>
              <li>Search term: {currentConfig.globalSearch || '(none)'}</li>
              <li>Sort: {currentConfig.sortField} ({currentConfig.sortDirection})</li>
              <li>Page size: {currentConfig.pageSize}</li>
            </ul>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} data-testid="save-view-confirm-btn">
            <Save className="w-4 h-4 mr-2" />
            Save View
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ═══════════════════════════════════════════════════════════════════
// EXPORT DIALOG COMPONENT
// ═══════════════════════════════════════════════════════════════════

const ExportDialog = ({ 
  open, 
  onOpenChange, 
  columns, 
  currentPageData,
  endpoint,
  queryParams,
  queryKey,
  totalItems
}) => {
  const [exportType, setExportType] = useState('current'); // 'current' | 'all'
  const [isExporting, setIsExporting] = useState(false);
  
  const handleExport = async () => {
    setIsExporting(true);
    
    try {
      let dataToExport = currentPageData;
      
      // If exporting all, fetch all data
      if (exportType === 'all' && totalItems > currentPageData.length) {
        const token = localStorage.getItem('token');
        const allDataParams = { ...queryParams, page: 1, page_size: 10000 }; // Fetch up to 10k records
        
        const response = await axios.get(`${API}${endpoint}`, {
          params: allDataParams,
          headers: { Authorization: `Bearer ${token}` }
        });
        
        dataToExport = response.data?.data || response.data?.items || response.data || [];
      }
      
      if (!dataToExport.length) {
        toast.error('No data to export');
        return;
      }
      
      // Build CSV
      const headers = columns.map(c => c.label).join(',');
      const rows = dataToExport.map(row => 
        columns.map(c => {
          let value = row[c.key];
          
          // Format dates
          if (c.type === 'date' || c.key.includes('date') || c.key.includes('_at')) {
            if (value) {
              try {
                value = new Date(value).toLocaleDateString('en-IN');
              } catch {}
            }
          }
          
          // Format currency
          if (c.type === 'currency' || c.key.includes('value') || c.key.includes('amount')) {
            if (value !== null && value !== undefined) {
              value = Number(value);
            }
          }
          
          // Escape commas and quotes for CSV
          if (typeof value === 'string') {
            if (value.includes(',') || value.includes('"') || value.includes('\n')) {
              return `"${value.replace(/"/g, '""')}"`;
            }
          }
          
          return value ?? '';
        }).join(',')
      ).join('\n');
      
      const csv = `${headers}\n${rows}`;
      const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' }); // BOM for Excel
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${queryKey}_export_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
      
      toast.success(`Exported ${dataToExport.length} records to CSV`);
      onOpenChange(false);
    } catch (error) {
      console.error('Export failed:', error);
      toast.error('Failed to export data');
    } finally {
      setIsExporting(false);
    }
  };
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileDown className="w-5 h-5 text-green-500" />
            Export to CSV
          </DialogTitle>
          <DialogDescription>
            Download your data as a CSV file that can be opened in Excel.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-3">
            <Label>What to export?</Label>
            
            <label className={cn(
              "flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors",
              exportType === 'current' ? "border-blue-500 bg-blue-50" : "border-zinc-200 hover:bg-zinc-50"
            )}>
              <input
                type="radio"
                name="exportType"
                value="current"
                checked={exportType === 'current'}
                onChange={() => setExportType('current')}
                className="w-4 h-4"
              />
              <div>
                <p className="font-medium text-sm">Current Page</p>
                <p className="text-xs text-zinc-500">{currentPageData.length} records</p>
              </div>
            </label>
            
            <label className={cn(
              "flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors",
              exportType === 'all' ? "border-blue-500 bg-blue-50" : "border-zinc-200 hover:bg-zinc-50"
            )}>
              <input
                type="radio"
                name="exportType"
                value="all"
                checked={exportType === 'all'}
                onChange={() => setExportType('all')}
                className="w-4 h-4"
              />
              <div>
                <p className="font-medium text-sm">All Matching Records</p>
                <p className="text-xs text-zinc-500">
                  {totalItems} records {totalItems > 10000 && '(max 10,000)'}
                </p>
              </div>
            </label>
          </div>
          
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
            <p className="font-medium">Columns included:</p>
            <p className="mt-1">{columns.map(c => c.label).join(', ')}</p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleExport} 
            disabled={isExporting}
            className="bg-green-600 hover:bg-green-700"
            data-testid="export-confirm-btn"
          >
            {isExporting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
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
  showSavedViews = true, // NEW: Enable saved views feature
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
  // Get export permission from context
  const { canExportData } = usePermissions();
  const hasExportPermission = canExportData();
  
  // State
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(defaultPageSize);
  const [sortField, setSortField] = useState(defaultSort.field);
  const [sortDirection, setSortDirection] = useState(defaultSort.direction);
  const [globalSearch, setGlobalSearch] = useState('');
  const [columnFilters, setColumnFilters] = useState({});
  const [activeQuickView, setActiveQuickView] = useState('all');
  
  // NEW: Saved Views state
  const [showSaveViewDialog, setShowSaveViewDialog] = useState(false);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const { savedViews, saveView, deleteView, setDefaultView, getDefaultView } = useSavedViews(queryKey);
  
  // Load default saved view on mount
  useEffect(() => {
    const defaultView = getDefaultView();
    if (defaultView?.config) {
      applyViewConfig(defaultView.config);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  
  // Apply a saved view configuration
  const applyViewConfig = useCallback((config) => {
    if (config.columnFilters) setColumnFilters(config.columnFilters);
    if (config.globalSearch !== undefined) setGlobalSearch(config.globalSearch);
    if (config.sortField) setSortField(config.sortField);
    if (config.sortDirection) setSortDirection(config.sortDirection);
    if (config.pageSize) setPageSize(config.pageSize);
    if (config.activeQuickView) setActiveQuickView(config.activeQuickView);
    setPage(1);
  }, []);
  
  // Get current view configuration
  const getCurrentConfig = useCallback(() => ({
    columnFilters,
    globalSearch,
    sortField,
    sortDirection,
    pageSize,
    activeQuickView,
  }), [columnFilters, globalSearch, sortField, sortDirection, pageSize, activeQuickView]);
  
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
            
            {/* Saved Views Dropdown */}
            {showSavedViews && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="h-8 px-2 gap-1"
                    data-testid="saved-views-dropdown"
                  >
                    <FolderOpen className="w-4 h-4" />
                    <span className="text-xs hidden sm:inline">Views</span>
                    {savedViews.length > 0 && (
                      <Badge variant="secondary" className="h-4 px-1 text-[10px] ml-1">
                        {savedViews.length}
                      </Badge>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel className="text-xs text-zinc-500">
                    Saved Views
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  
                  {savedViews.length === 0 ? (
                    <div className="px-2 py-3 text-center text-xs text-zinc-400">
                      No saved views yet
                    </div>
                  ) : (
                    savedViews.map(view => (
                      <DropdownMenuItem
                        key={view.id}
                        className="flex items-center justify-between group"
                        onClick={() => {
                          applyViewConfig(view.config);
                          toast.success(`Applied view: ${view.name}`);
                        }}
                      >
                        <div className="flex items-center gap-2">
                          {view.isDefault && (
                            <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                          )}
                          <span className="text-sm">{view.name}</span>
                        </div>
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setDefaultView(view.id);
                              toast.success(`"${view.name}" set as default`);
                            }}
                            className="p-1 hover:bg-zinc-100 rounded"
                            title="Set as default"
                          >
                            <Star className={cn(
                              "w-3 h-3",
                              view.isDefault ? "text-amber-500 fill-amber-500" : "text-zinc-400"
                            )} />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteView(view.id);
                              toast.success(`Deleted view: ${view.name}`);
                            }}
                            className="p-1 hover:bg-red-50 rounded text-zinc-400 hover:text-red-500"
                            title="Delete view"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </DropdownMenuItem>
                    ))
                  )}
                  
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    onClick={() => setShowSaveViewDialog(true)}
                    className="text-blue-600"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    Save Current View
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
            
            {/* Refresh */}
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => refetch()}
              disabled={isFetching}
              className="h-8 px-2"
              title="Refresh"
            >
              <RefreshCw className={cn("w-4 h-4", isFetching && "animate-spin")} />
            </Button>
            
            {/* Export - Enhanced with dialog, RBAC controlled */}
            {showExport && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => hasExportPermission && setShowExportDialog(true)}
                        disabled={!tableData.length || !hasExportPermission}
                        className={cn(
                          "h-8 px-2",
                          !hasExportPermission && "opacity-50 cursor-not-allowed"
                        )}
                        title={hasExportPermission ? "Export to CSV" : "Export permission required"}
                        data-testid="export-csv-btn"
                      >
                        {hasExportPermission ? (
                          <Download className="w-4 h-4" />
                        ) : (
                          <Lock className="w-4 h-4 text-zinc-400" />
                        )}
                      </Button>
                    </span>
                  </TooltipTrigger>
                  {!hasExportPermission && (
                    <TooltipContent>
                      <p>You don't have permission to export data</p>
                    </TooltipContent>
                  )}
                </Tooltip>
              </TooltipProvider>
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
                            {rowActions.filter(action => !action.hidden || !action.hidden(row)).map((action, i) => (
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
      
      {/* Save View Dialog */}
      <SaveViewDialog
        open={showSaveViewDialog}
        onOpenChange={setShowSaveViewDialog}
        onSave={saveView}
        currentConfig={getCurrentConfig()}
      />
      
      {/* Export Dialog */}
      <ExportDialog
        open={showExportDialog}
        onOpenChange={setShowExportDialog}
        columns={columns}
        currentPageData={tableData}
        endpoint={endpoint}
        queryParams={queryParams}
        queryKey={queryKey}
        totalItems={totalItems}
      />
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
// EXPORTS
// ═══════════════════════════════════════════════════════════════════

export { FILTER_TYPES, STATUS_COLORS, QUICK_VIEWS, getStatusColor };
export default SalesDataTable;
