/**
 * SOWDeliveryTable.jsx - Expandable Row SOW Delivery Table
 * 
 * High-traffic optimized table with:
 * - Expandable rows showing deliverables
 * - Each deliverable has own status/dates/proof
 * - Search & column filters
 * - Add scope/deliverable inline
 * - Virtual scrolling for 100s of items
 */

import React, { useState, useRef, useMemo, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import { toast } from 'sonner';
import { 
  ChevronDown, ChevronRight, Plus, Search, Filter, Eye, Upload, 
  Download, Edit2, Trash2, CheckCircle, Clock, Play, Pause, 
  AlertCircle, RotateCcw, FileText, Loader2, X, Save
} from 'lucide-react';

// Status configurations - Only 4 statuses as per requirement
const STATUSES = {
  open: { label: 'Open', color: 'bg-zinc-100 text-zinc-600', dotColor: 'bg-zinc-400' },
  wip: { label: 'Work in Progress', color: 'bg-blue-100 text-blue-700', dotColor: 'bg-blue-500' },
  not_applicable: { label: 'Not Applicable', color: 'bg-zinc-100 text-zinc-400', dotColor: 'bg-zinc-300' },
  implemented: { label: 'Implemented', color: 'bg-emerald-100 text-emerald-700', dotColor: 'bg-emerald-500' }
};

// Category colors
const CATEGORY_COLORS = {
  'Sales': 'bg-purple-100 text-purple-700',
  'Operations': 'bg-blue-100 text-blue-700',
  'HR': 'bg-pink-100 text-pink-700',
  'Finance': 'bg-green-100 text-green-700',
  'IT': 'bg-cyan-100 text-cyan-700',
  'General': 'bg-zinc-100 text-zinc-600'
};

// Format date for display - DD MMM YYYY format
const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
};

// Format date short - DD MMM
const formatDateShort = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
};

// Format date for input
const formatDateInput = (dateStr) => {
  if (!dateStr) return '';
  return dateStr.substring(0, 10);
};

// Calculate days between dates
const calculateDays = (startDate, endDate) => {
  if (!startDate) return '-';
  const start = new Date(startDate);
  const end = endDate ? new Date(endDate) : new Date();
  const days = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
  return days > 0 ? days : 0;
};

// Status Badge Component
const StatusBadge = ({ status, size = 'sm' }) => {
  const config = STATUSES[status] || STATUSES.open;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor}`} />
      {config.label}
    </span>
  );
};

// Deliverable Row Component
const DeliverableRow = ({ 
  deliverable, 
  scopeId,
  onUpdate, 
  onDelete, 
  onUploadProof,
  onViewProof,
  permissions,
  isUploading
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({
    name: deliverable.name || '',
    start_date: deliverable.start_date || '',
    status: deliverable.status || 'open'
  });
  const fileInputRef = useRef(null);

  const handleSave = () => {
    onUpdate(deliverable.id, editData);
    setIsEditing(false);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onUploadProof(deliverable.id, file);
    }
    e.target.value = '';
  };

  const proofCount = deliverable.proofs?.length || 0;

  return (
    <div className="grid grid-cols-12 gap-2 py-2 px-4 bg-zinc-50/50 border-b border-zinc-100 items-center text-sm hover:bg-zinc-100/50 group">
      {/* Indent + Name */}
      <div className="col-span-4 flex items-center gap-2 pl-8">
        <span className="w-1.5 h-1.5 rounded-full bg-zinc-300" />
        {isEditing ? (
          <Input
            value={editData.name}
            onChange={(e) => setEditData({ ...editData, name: e.target.value })}
            className="h-7 text-sm"
            autoFocus
          />
        ) : (
          <span className="text-zinc-700">{deliverable.name}</span>
        )}
      </div>

      {/* Start Date */}
      <div className="col-span-2">
        {isEditing || permissions.can_edit ? (
          <Input
            type="date"
            value={formatDateInput(editData.start_date || deliverable.start_date)}
            onChange={(e) => {
              const newData = { ...editData, start_date: e.target.value };
              setEditData(newData);
              if (!isEditing) onUpdate(deliverable.id, { start_date: e.target.value });
            }}
            className="h-7 text-xs"
          />
        ) : (
          <span className="text-xs text-zinc-500">{formatDate(deliverable.start_date)}</span>
        )}
      </div>

      {/* End Date */}
      <div className="col-span-1 text-center">
        <span className="text-xs text-zinc-500">
          {deliverable.status === 'implemented' ? formatDate(deliverable.end_date) : '-'}
        </span>
      </div>

      {/* Days */}
      <div className="col-span-1 text-center">
        <span className="text-xs font-medium">
          {calculateDays(deliverable.start_date, deliverable.status === 'implemented' ? deliverable.end_date : null)}
        </span>
      </div>

      {/* Status */}
      <div className="col-span-2">
        {permissions.can_edit ? (
          <Select
            value={deliverable.status || 'open'}
            onValueChange={(val) => onUpdate(deliverable.id, { status: val })}
          >
            <SelectTrigger className="h-7 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(STATUSES).map(([key, config]) => (
                <SelectItem key={key} value={key} className="text-xs">
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor}`} />
                    {config.label}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <StatusBadge status={deliverable.status} />
        )}
      </div>

      {/* Actions */}
      <div className="col-span-2 flex items-center justify-end gap-1">
        {/* View Proof */}
        {proofCount > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
            onClick={() => onViewProof(deliverable)}
          >
            <Eye className="w-3 h-3 mr-1" />
            {proofCount}
          </Button>
        )}

        {/* Upload */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          className="hidden"
          accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.xlsx,.xls"
        />
        {permissions.can_edit && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs opacity-0 group-hover:opacity-100"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            {isUploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
          </Button>
        )}

        {/* Edit/Save */}
        {permissions.can_edit && (
          isEditing ? (
            <Button variant="ghost" size="sm" className="h-6 px-2" onClick={handleSave}>
              <Save className="w-3 h-3 text-emerald-600" />
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 opacity-0 group-hover:opacity-100"
              onClick={() => setIsEditing(true)}
            >
              <Edit2 className="w-3 h-3" />
            </Button>
          )
        )}

        {/* Delete */}
        {permissions.can_edit && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-red-500 opacity-0 group-hover:opacity-100"
            onClick={() => onDelete(deliverable.id)}
          >
            <Trash2 className="w-3 h-3" />
          </Button>
        )}
      </div>
    </div>
  );
};

// Expandable Scope Row Component
const ScopeRow = ({
  scope,
  index,
  isExpanded,
  onToggle,
  onUpdateScope,
  onUpdateDeliverable,
  onAddDeliverable,
  onDeleteDeliverable,
  onUploadProof,
  onViewProof,
  onViewScope,
  permissions,
  uploadingId
}) => {
  const [showAddDeliverable, setShowAddDeliverable] = useState(false);
  const [newDeliverable, setNewDeliverable] = useState('');
  
  const deliverables = scope.deliverables_list || [];
  const completedCount = deliverables.filter(d => d.status === 'implemented').length;
  const categoryColor = CATEGORY_COLORS[scope.category_name] || CATEGORY_COLORS['General'];

  const handleAddDeliverable = () => {
    if (newDeliverable.trim()) {
      onAddDeliverable(scope.id, newDeliverable.trim());
      setNewDeliverable('');
      setShowAddDeliverable(false);
    }
  };

  return (
    <div className="border-b border-zinc-200">
      {/* Main Scope Row */}
      <div 
        className={`grid grid-cols-12 gap-2 py-3 px-4 items-center cursor-pointer hover:bg-zinc-50 ${isExpanded ? 'bg-zinc-50' : ''}`}
        onClick={onToggle}
      >
        {/* Expand + Index + Category + Name */}
        <div className="col-span-4 flex items-center gap-3">
          <button className="p-0.5 hover:bg-zinc-200 rounded">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-zinc-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-zinc-500" />
            )}
          </button>
          <span className="text-xs text-zinc-400 w-6">{index + 1}</span>
          <Badge className={`text-[10px] px-1.5 py-0 ${categoryColor}`}>
            {scope.category_name || 'General'}
          </Badge>
          <span className="font-medium text-zinc-800 truncate">{scope.name}</span>
        </div>

        {/* Start Date */}
        <div className="col-span-2" onClick={(e) => e.stopPropagation()}>
          {permissions.can_edit ? (
            <Input
              type="date"
              value={formatDateInput(scope.start_date)}
              onChange={(e) => onUpdateScope(scope.id, { start_date: e.target.value })}
              className="h-7 text-xs"
            />
          ) : (
            <span className="text-sm">{formatDate(scope.start_date)}</span>
          )}
        </div>

        {/* End Date */}
        <div className="col-span-1 text-center">
          <span className="text-sm text-zinc-500">
            {scope.status === 'implemented' ? formatDate(scope.end_date) : '-'}
          </span>
        </div>

        {/* Days */}
        <div className="col-span-1 text-center">
          <span className={`text-sm font-medium ${scope.status === 'implemented' ? 'text-emerald-600' : ''}`}>
            {calculateDays(scope.start_date, scope.status === 'implemented' ? scope.end_date : null)}
          </span>
        </div>

        {/* Status */}
        <div className="col-span-2" onClick={(e) => e.stopPropagation()}>
          {permissions.can_edit ? (
            <Select
              value={scope.status || 'open'}
              onValueChange={(val) => onUpdateScope(scope.id, { status: val })}
            >
              <SelectTrigger className="h-7 text-xs">
                <StatusBadge status={scope.status || 'open'} />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(STATUSES).map(([key, config]) => (
                  <SelectItem key={key} value={key} className="text-xs">
                    <div className="flex items-center gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor}`} />
                      {config.label}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <StatusBadge status={scope.status} />
          )}
        </div>

        {/* Actions */}
        <div className="col-span-2 flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
          {/* Deliverables count */}
          <span className="text-xs text-zinc-400 mr-2">
            {completedCount}/{deliverables.length} items
          </span>
          
          {/* View */}
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={() => onViewScope(scope)}
          >
            <Eye className="w-3.5 h-3.5 mr-1" />
            View
          </Button>
        </div>
      </div>

      {/* Expanded Content - Deliverables */}
      {isExpanded && (
        <div className="border-t border-zinc-100">
          {/* Deliverables Header */}
          <div className="grid grid-cols-12 gap-2 py-2 px-4 bg-zinc-100/50 text-xs font-medium text-zinc-500">
            <div className="col-span-4 pl-8">Deliverable</div>
            <div className="col-span-2">Start Date</div>
            <div className="col-span-1 text-center">End</div>
            <div className="col-span-1 text-center">Days</div>
            <div className="col-span-2">Status</div>
            <div className="col-span-2 text-right">Actions</div>
          </div>

          {/* Deliverable Rows */}
          {deliverables.length === 0 ? (
            <div className="py-4 px-4 pl-12 text-sm text-zinc-400 italic">
              No deliverables defined. Click "Add" to create one.
            </div>
          ) : (
            deliverables.map((deliverable) => (
              <DeliverableRow
                key={deliverable.id}
                deliverable={deliverable}
                scopeId={scope.id}
                onUpdate={(id, data) => onUpdateDeliverable(scope.id, id, data)}
                onDelete={(id) => onDeleteDeliverable(scope.id, id)}
                onUploadProof={(id, file) => onUploadProof(scope.id, id, file)}
                onViewProof={onViewProof}
                permissions={permissions}
                isUploading={uploadingId === deliverable.id}
              />
            ))
          )}

          {/* Add Deliverable */}
          {permissions.can_edit && (
            <div className="py-2 px-4 pl-12 border-t border-zinc-100">
              {showAddDeliverable ? (
                <div className="flex items-center gap-2">
                  <Input
                    value={newDeliverable}
                    onChange={(e) => setNewDeliverable(e.target.value)}
                    placeholder="Enter deliverable name..."
                    className="h-7 text-sm flex-1"
                    autoFocus
                    onKeyDown={(e) => e.key === 'Enter' && handleAddDeliverable()}
                  />
                  <Button size="sm" className="h-7" onClick={handleAddDeliverable}>
                    <Plus className="w-3 h-3 mr-1" /> Add
                  </Button>
                  <Button size="sm" variant="ghost" className="h-7" onClick={() => setShowAddDeliverable(false)}>
                    <X className="w-3 h-3" />
                  </Button>
                </div>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs text-zinc-500 hover:text-zinc-700"
                  onClick={() => setShowAddDeliverable(true)}
                >
                  <Plus className="w-3 h-3 mr-1" /> Add Deliverable
                </Button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Main SOW Delivery Table Component
const SOWDeliveryTable = ({
  scopes = [],
  onUpdateScope,
  onAddScope,
  onUpdateDeliverable,
  onAddDeliverable,
  onDeleteDeliverable,
  onUploadProof,
  permissions = { can_edit: true },
  isLoading = false
}) => {
  const [expandedRows, setExpandedRows] = useState(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showAddScope, setShowAddScope] = useState(false);
  const [newScope, setNewScope] = useState({ name: '', category: 'General' });
  const [viewProofModal, setViewProofModal] = useState({ open: false, item: null });
  const [viewScopeModal, setViewScopeModal] = useState({ open: false, scope: null });
  const [uploadingId, setUploadingId] = useState(null);

  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set(scopes.map(s => s.category_name || 'General'));
    return ['all', ...Array.from(cats)];
  }, [scopes]);

  // Filter scopes
  const filteredScopes = useMemo(() => {
    return scopes.filter(scope => {
      const matchesSearch = !searchTerm || 
        scope.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        scope.deliverables_list?.some(d => d.name?.toLowerCase().includes(searchTerm.toLowerCase()));
      const matchesCategory = categoryFilter === 'all' || scope.category_name === categoryFilter;
      const matchesStatus = statusFilter === 'all' || scope.status === statusFilter;
      return matchesSearch && matchesCategory && matchesStatus;
    });
  }, [scopes, searchTerm, categoryFilter, statusFilter]);

  // Toggle row expansion
  const toggleRow = useCallback((scopeId) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(scopeId)) {
        next.delete(scopeId);
      } else {
        next.add(scopeId);
      }
      return next;
    });
  }, []);

  // Expand all / Collapse all
  const expandAll = () => setExpandedRows(new Set(filteredScopes.map(s => s.id)));
  const collapseAll = () => setExpandedRows(new Set());

  // Handle add scope
  const handleAddScope = () => {
    if (newScope.name.trim()) {
      onAddScope(newScope);
      setNewScope({ name: '', category: 'General' });
      setShowAddScope(false);
    }
  };

  // Handle proof upload
  const handleUploadProof = async (scopeId, deliverableId, file) => {
    setUploadingId(deliverableId);
    try {
      await onUploadProof(scopeId, deliverableId, file);
    } finally {
      setUploadingId(null);
    }
  };

  // Stats
  const stats = useMemo(() => {
    const total = scopes.length;
    const completed = scopes.filter(s => s.status === 'implemented').length;
    const inProgress = scopes.filter(s => s.status === 'wip').length;
    const totalDeliverables = scopes.reduce((acc, s) => acc + (s.deliverables_list?.length || 0), 0);
    const completedDeliverables = scopes.reduce((acc, s) => 
      acc + (s.deliverables_list?.filter(d => d.status === 'implemented')?.length || 0), 0);
    return { total, completed, inProgress, totalDeliverables, completedDeliverables };
  }, [scopes]);

  // CSV Download Function
  const downloadCSV = useCallback((scopeData) => {
    const rows = [
      ['#', 'Category', 'Scope', 'Deliverable', 'Start Date', 'End Date', 'Days', 'Status']
    ];
    
    scopeData.forEach((scope, idx) => {
      const scopeStatus = STATUSES[scope.status]?.label || scope.status;
      const scopeStartDate = scope.start_date ? formatDate(scope.start_date) : '-';
      const scopeEndDate = scope.end_date ? formatDate(scope.end_date) : '-';
      const scopeDays = calculateDays(scope.start_date, scope.status === 'implemented' ? scope.end_date : null);
      
      // Add scope row
      rows.push([
        idx + 1,
        scope.category_name || 'General',
        scope.name,
        '',  // No deliverable for scope row
        scopeStartDate,
        scopeEndDate,
        scopeDays,
        scopeStatus
      ]);
      
      // Add deliverable rows
      const deliverables = scope.deliverables_list || [];
      deliverables.forEach((d) => {
        const dStatus = STATUSES[d.status]?.label || d.status;
        const dStartDate = d.start_date ? formatDate(d.start_date) : '-';
        const dEndDate = d.end_date ? formatDate(d.end_date) : '-';
        const dDays = calculateDays(d.start_date, d.status === 'implemented' ? d.end_date : null);
        
        rows.push([
          '',  // No index for deliverable
          '',  // No category for deliverable
          '',  // Scope name already shown
          d.name,
          dStartDate,
          dEndDate,
          dDays,
          dStatus
        ]);
      });
    });
    
    // Convert to CSV string
    const csvContent = rows.map(row => 
      row.map(cell => {
        const str = String(cell || '');
        // Escape quotes and wrap in quotes if contains comma
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
          return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
      }).join(',')
    ).join('\n');
    
    // Download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `sow_delivery_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    toast.success('CSV downloaded successfully');
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-zinc-50 rounded-lg p-3 border border-zinc-200">
          <p className="text-xs text-zinc-500 uppercase tracking-wide">Scopes</p>
          <p className="text-xl font-semibold text-zinc-800">{stats.completed}/{stats.total}</p>
        </div>
        <div className="bg-zinc-50 rounded-lg p-3 border border-zinc-200">
          <p className="text-xs text-zinc-500 uppercase tracking-wide">Deliverables</p>
          <p className="text-xl font-semibold text-zinc-800">{stats.completedDeliverables}/{stats.totalDeliverables}</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
          <p className="text-xs text-blue-600 uppercase tracking-wide">In Progress</p>
          <p className="text-xl font-semibold text-blue-700">{stats.inProgress}</p>
        </div>
        <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-200">
          <p className="text-xs text-emerald-600 uppercase tracking-wide">Completed</p>
          <p className="text-xl font-semibold text-emerald-700">{stats.completed}</p>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
          <Input
            placeholder="Search scopes or deliverables..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 h-9"
          />
        </div>
        
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-[150px] h-9">
            <Filter className="w-3.5 h-3.5 mr-2 text-zinc-400" />
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            {categories.map(cat => (
              <SelectItem key={cat} value={cat}>
                {cat === 'all' ? 'All Categories' : cat}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[140px] h-9">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            {Object.entries(STATUSES).map(([key, config]) => (
              <SelectItem key={key} value={key}>{config.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex items-center gap-1 ml-auto">
          <Button variant="ghost" size="sm" onClick={expandAll} className="text-xs">
            Expand All
          </Button>
          <Button variant="ghost" size="sm" onClick={collapseAll} className="text-xs">
            Collapse All
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => downloadCSV(scopes)}
            className="text-xs ml-2"
          >
            <Download className="w-3.5 h-3.5 mr-1" />
            Export CSV
          </Button>
        </div>

        {permissions.can_edit && (
          <Button onClick={() => setShowAddScope(true)} className="h-9">
            <Plus className="w-4 h-4 mr-1" /> Add Scope
          </Button>
        )}
      </div>

      {/* Table */}
      <Card className="border-zinc-200 overflow-hidden">
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-2 py-2.5 px-4 bg-zinc-100 border-b border-zinc-200 text-xs font-semibold text-zinc-600 uppercase tracking-wide">
          <div className="col-span-4">Scope</div>
          <div className="col-span-2">Start Date</div>
          <div className="col-span-1 text-center">End</div>
          <div className="col-span-1 text-center">Days</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-2 text-right">Actions</div>
        </div>

        {/* Table Body */}
        <div className="max-h-[600px] overflow-y-auto">
          {filteredScopes.length === 0 ? (
            <div className="py-12 text-center text-zinc-400">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No scopes found</p>
              {permissions.can_edit && (
                <Button 
                  variant="link" 
                  className="mt-2 text-sm"
                  onClick={() => setShowAddScope(true)}
                >
                  Add your first scope
                </Button>
              )}
            </div>
          ) : (
            filteredScopes.map((scope, index) => (
              <ScopeRow
                key={scope.id}
                scope={scope}
                index={index}
                isExpanded={expandedRows.has(scope.id)}
                onToggle={() => toggleRow(scope.id)}
                onUpdateScope={onUpdateScope}
                onUpdateDeliverable={onUpdateDeliverable}
                onAddDeliverable={onAddDeliverable}
                onDeleteDeliverable={onDeleteDeliverable}
                onUploadProof={handleUploadProof}
                onViewProof={(item) => setViewProofModal({ open: true, item })}
                onViewScope={(scope) => setViewScopeModal({ open: true, scope })}
                permissions={permissions}
                uploadingId={uploadingId}
              />
            ))
          )}
        </div>
      </Card>

      {/* Showing X of Y */}
      <div className="text-xs text-zinc-500 text-right">
        Showing {filteredScopes.length} of {scopes.length} scopes
      </div>

      {/* Add Scope Dialog */}
      <Dialog open={showAddScope} onOpenChange={setShowAddScope}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New Scope</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium">Scope Name</label>
              <Input
                value={newScope.name}
                onChange={(e) => setNewScope({ ...newScope, name: e.target.value })}
                placeholder="Enter scope name..."
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Category</label>
              <Select value={newScope.category} onValueChange={(v) => setNewScope({ ...newScope, category: v })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.keys(CATEGORY_COLORS).map(cat => (
                    <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddScope(false)}>Cancel</Button>
            <Button onClick={handleAddScope}>Add Scope</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Proof Modal */}
      <Dialog open={viewProofModal.open} onOpenChange={(open) => setViewProofModal({ open, item: null })}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Proofs: {viewProofModal.item?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 max-h-80 overflow-y-auto py-4">
            {viewProofModal.item?.proofs?.map((proof, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-zinc-50 rounded-lg border">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-zinc-400" />
                  <div>
                    <p className="text-sm font-medium">{proof.file_name}</p>
                    <p className="text-xs text-zinc-500">{proof.uploaded_by_name}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => window.open(proof.file_url, '_blank')}>
                    <Eye className="w-3.5 h-3.5 mr-1" /> View
                  </Button>
                  <Button variant="ghost" size="sm" asChild>
                    <a href={proof.file_url} download={proof.file_name}>
                      <Download className="w-3.5 h-3.5" />
                    </a>
                  </Button>
                </div>
              </div>
            ))}
            {(!viewProofModal.item?.proofs || viewProofModal.item.proofs.length === 0) && (
              <p className="text-center text-zinc-400 py-4">No proofs uploaded</p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* View Scope Detail Modal */}
      <Dialog open={viewScopeModal.open} onOpenChange={(open) => setViewScopeModal({ open, scope: null })}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Badge className={CATEGORY_COLORS[viewScopeModal.scope?.category_name] || ''}>
                {viewScopeModal.scope?.category_name}
              </Badge>
              {viewScopeModal.scope?.name}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-zinc-500">Status</p>
                <StatusBadge status={viewScopeModal.scope?.status} />
              </div>
              <div>
                <p className="text-xs text-zinc-500">Start Date</p>
                <p className="font-medium">{formatDate(viewScopeModal.scope?.start_date)}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500">End Date</p>
                <p className="font-medium">{formatDate(viewScopeModal.scope?.end_date)}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500">Days</p>
                <p className="font-medium">{calculateDays(viewScopeModal.scope?.start_date, viewScopeModal.scope?.end_date)}</p>
              </div>
            </div>
            
            <div>
              <p className="text-xs text-zinc-500 mb-2">Deliverables ({viewScopeModal.scope?.deliverables_list?.length || 0})</p>
              <div className="space-y-2">
                {viewScopeModal.scope?.deliverables_list?.map((d, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-zinc-50 rounded">
                    <span className="text-sm">{d.name}</span>
                    <StatusBadge status={d.status} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SOWDeliveryTable;
