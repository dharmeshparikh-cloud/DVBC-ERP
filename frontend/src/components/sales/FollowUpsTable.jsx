/**
 * FollowUpsTable.jsx - Sales Module Governed Table for Follow-ups
 * 
 * Uses SalesDataTable with follow-ups-specific configuration.
 */

import React from 'react';
import { SalesDataTable, FILTER_TYPES, getStatusColor } from './SalesDataTable';
import { CheckCircle, Clock, Phone, Mail, Calendar, AlertCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

// Column configuration for follow-ups table
const FOLLOWUPS_COLUMNS = [
  {
    key: 'entity_name',
    label: 'Related To',
    filterType: FILTER_TYPES.TEXT,
    filterable: true,
    sortable: true,
    width: '180px',
    render: (value, row) => (
      <div>
        <span className="font-medium text-zinc-900">{row.lead_company || row.client_name || value || 'N/A'}</span>
        <div className="flex items-center gap-1 mt-0.5">
          <span className="text-[10px] text-zinc-400 capitalize">{row.entity_type || ''}</span>
          {row.lead_id && <span className="text-[10px] text-blue-500">Linked</span>}
        </div>
      </div>
    )
  },
  {
    key: 'action_type',
    label: 'Action',
    filterType: FILTER_TYPES.DROPDOWN,
    filterable: true,
    sortable: true,
    width: '100px',
    filterOptions: [
      { value: 'call', label: 'Call' },
      { value: 'email', label: 'Email' },
      { value: 'meeting', label: 'Meeting' },
      { value: 'task', label: 'Task' },
      { value: 'reminder', label: 'Reminder' },
    ],
    render: (value) => {
      const icons = {
        call: Phone,
        email: Mail,
        meeting: Calendar,
        reminder: Clock,
      };
      const Icon = icons[value] || Clock;
      return (
        <span className="flex items-center gap-1 text-xs capitalize">
          <Icon className="w-3 h-3" />
          {value || 'Task'}
        </span>
      );
    }
  },
  {
    key: 'notes',
    label: 'Notes',
    filterType: FILTER_TYPES.TEXT,
    filterable: true,
    sortable: false,
    width: '200px',
    render: (value) => (
      <span className="text-xs text-zinc-600 line-clamp-2">{value || '-'}</span>
    )
  },
  {
    key: 'due_date',
    label: 'Due Date',
    filterType: FILTER_TYPES.DATE,
    filterable: true,
    sortable: true,
    width: '120px',
    render: (value, row) => {
      if (!value) return '-';
      const dueDate = new Date(value);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const isOverdue = dueDate < today && row.status === 'open';
      const isDueToday = dueDate.toDateString() === today.toDateString();
      
      return (
        <span className={cn(
          "text-xs px-2 py-0.5 rounded",
          isOverdue && "bg-red-50 text-red-700 font-medium",
          isDueToday && !isOverdue && "bg-yellow-50 text-yellow-700",
          !isOverdue && !isDueToday && "text-zinc-600"
        )}>
          {isOverdue && <AlertCircle className="w-3 h-3 inline mr-1" />}
          {dueDate.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
        </span>
      );
    }
  },
  {
    key: 'priority',
    label: 'Priority',
    filterType: FILTER_TYPES.DROPDOWN,
    filterable: true,
    sortable: true,
    width: '80px',
    filterOptions: [
      { value: 'high', label: 'High' },
      { value: 'medium', label: 'Medium' },
      { value: 'low', label: 'Low' },
    ],
    render: (value) => {
      const colors = {
        high: 'bg-red-50 text-red-700',
        medium: 'bg-yellow-50 text-yellow-700',
        low: 'bg-green-50 text-green-700',
      };
      return (
        <span className={cn("text-xs px-2 py-0.5 rounded capitalize", colors[value] || colors.medium)}>
          {value || 'Medium'}
        </span>
      );
    }
  },
  {
    key: 'client_response',
    label: 'Client',
    filterable: false,
    sortable: false,
    width: '90px',
    render: (value, row) => {
      if (!value && !row.history?.some(h => h.action?.startsWith('client_'))) {
        return <span className="text-[10px] text-zinc-400">—</span>;
      }
      const clientAction = (row.history || []).filter(h => h.action?.startsWith('client_')).pop();
      if (clientAction?.action === 'client_closed') {
        return <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-50 text-green-700 font-medium">Confirmed</span>;
      }
      if (clientAction?.action === 'client_reschedule') {
        return <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 font-medium">Reschedule</span>;
      }
      return <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">{value?.substring(0, 15) || 'Responded'}</span>;
    }
  },
  {
    key: 'status',
    label: 'Status',
    filterType: FILTER_TYPES.DROPDOWN,
    filterable: true,
    sortable: true,
    width: '90px',
    filterOptions: [
      { value: 'open', label: 'Open' },
      { value: 'completed', label: 'Completed' },
      { value: 'cancelled', label: 'Cancelled' },
    ],
    render: (value) => {
      const colors = {
        open: 'bg-blue-50 text-blue-700',
        completed: 'bg-green-50 text-green-700',
        cancelled: 'bg-zinc-100 text-zinc-500',
      };
      return (
        <span className={cn("text-xs px-2 py-0.5 rounded capitalize", colors[value] || colors.open)}>
          {value || 'Open'}
        </span>
      );
    }
  },
];

// Quick views for follow-ups
const FOLLOWUPS_QUICK_VIEWS = [
  { id: 'all', label: 'All Follow-ups', filters: {} },
  { id: 'open', label: 'Open', filters: { status: 'open' } },
  { id: 'today', label: 'Today', filters: { due_date: 'TODAY' } },
  { id: 'overdue', label: 'Overdue', filters: { overdue_only: true } },
  { id: 'high_priority', label: 'High Priority', filters: { priority: 'high', status: 'open' } },
  { id: 'completed', label: 'Completed', filters: { status: 'completed' } },
];

export const FollowUpsTable = ({ 
  onRowClick, 
  onComplete,
  onReschedule,
  className,
  externalFilters = {},
  entityType,
  entityId
}) => {
  
  const handleRowClick = (row) => {
    if (onRowClick) {
      onRowClick(row);
    }
  };
  
  const rowActions = [
    {
      label: 'Mark Complete',
      icon: CheckCircle,
      onClick: (row) => onComplete?.(row),
      className: 'text-green-600',
      hidden: (row) => row.status === 'closed'
    },
    {
      label: 'Reschedule',
      icon: Calendar,
      onClick: (row) => onReschedule?.(row),
      hidden: (row) => row.status === 'closed'
    },
  ];
  
  const filters = { ...externalFilters };
  if (entityType) {
    filters.entity_type = entityType;
  }
  if (entityId) {
    filters.entity_id = entityId;
  }
  
  return (
    <SalesDataTable
      endpoint="/api/follow-ups"
      columns={FOLLOWUPS_COLUMNS}
      queryKey={`sales-followups-table${entityType ? `-${entityType}` : ''}`}
      title="Follow-ups"
      quickViews={FOLLOWUPS_QUICK_VIEWS}
      showQuickViews={true}
      showExport={true}
      showGlobalSearch={true}
      onRowClick={handleRowClick}
      rowActions={rowActions}
      emptyMessage="No follow-ups found."
      defaultSort={{ field: 'due_date', direction: 'asc' }}
      defaultPageSize={20}
      className={className}
      externalFilters={filters}
    />
  );
};

export default FollowUpsTable;
