/**
 * MeetingsTable.jsx - Sales Module Governed Table for Meetings
 * 
 * Uses SalesDataTable with meetings-specific configuration.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { SalesDataTable, FILTER_TYPES } from './SalesDataTable';
import { Eye, Edit, FileText, Calendar, Video, MapPin } from 'lucide-react';

// Column configuration for meetings table
const MEETINGS_COLUMNS = [
  {
    key: 'title',
    label: 'Meeting',
    filterType: FILTER_TYPES.TEXT,
    filterable: true,
    sortable: true,
    width: '200px',
    render: (value, row) => (
      <div>
        <span className="font-medium text-zinc-900">{value || 'Untitled Meeting'}</span>
        {row.client_name && (
          <span className="text-xs text-zinc-500 block">{row.client_name}</span>
        )}
      </div>
    )
  },
  {
    key: 'type',
    label: 'Type',
    filterType: FILTER_TYPES.DROPDOWN,
    filterable: true,
    sortable: true,
    width: '100px',
    filterOptions: [
      { value: 'sales', label: 'Sales' },
      { value: 'consulting', label: 'Consulting' },
      { value: 'discovery', label: 'Discovery' },
      { value: 'demo', label: 'Demo' },
      { value: 'follow_up', label: 'Follow-up' },
    ],
    render: (value) => (
      <span className="text-xs text-zinc-600 capitalize">{value || '-'}</span>
    )
  },
  {
    key: 'mode',
    label: 'Mode',
    filterType: FILTER_TYPES.DROPDOWN,
    filterable: true,
    sortable: true,
    width: '80px',
    filterOptions: [
      { value: 'online', label: 'Online' },
      { value: 'offline', label: 'Offline' },
      { value: 'in-person', label: 'In-Person' },
    ],
    render: (value) => (
      <span className="flex items-center gap-1 text-xs">
        {value === 'online' ? <Video className="w-3 h-3" /> : <MapPin className="w-3 h-3" />}
        <span className="capitalize">{value || 'Online'}</span>
      </span>
    )
  },
  {
    key: 'status',
    label: 'Status',
    filterType: FILTER_TYPES.DROPDOWN,
    filterable: true,
    sortable: true,
    width: '100px',
    filterOptions: [
      { value: 'scheduled', label: 'Scheduled' },
      { value: 'completed', label: 'Completed' },
      { value: 'cancelled', label: 'Cancelled' },
      { value: 'rescheduled', label: 'Rescheduled' },
    ],
    type: 'status'
  },
  {
    key: 'meeting_date',
    label: 'Date',
    filterType: FILTER_TYPES.DATE,
    filterable: true,
    sortable: true,
    width: '120px',
    type: 'date'
  },
  {
    key: 'mom_generated',
    label: 'MOM',
    filterType: FILTER_TYPES.BOOLEAN,
    filterable: true,
    sortable: true,
    width: '60px',
    render: (value) => (
      <span className={`px-2 py-0.5 text-xs rounded ${value ? 'bg-green-50 text-green-700' : 'bg-zinc-100 text-zinc-500'}`}>
        {value ? 'Yes' : 'No'}
      </span>
    )
  },
  {
    key: 'project_name',
    label: 'Project',
    filterType: FILTER_TYPES.TEXT,
    filterable: true,
    sortable: true,
    width: '150px',
    render: (value) => (
      <span className="text-xs text-zinc-600">{value || '-'}</span>
    )
  },
];

// Quick views for meetings
const MEETINGS_QUICK_VIEWS = [
  { id: 'all', label: 'All Meetings', filters: {} },
  { id: 'scheduled', label: 'Scheduled', filters: { status: 'scheduled' } },
  { id: 'today', label: 'Today', filters: { date_from: 'TODAY', date_to: 'TODAY' } },
  { id: 'pending_mom', label: 'Pending MOM', filters: { mom_generated: 'false' } },
  { id: 'completed', label: 'Completed', filters: { status: 'completed' } },
];

export const MeetingsTable = ({ 
  onRowClick, 
  onEdit,
  onAddMOM,
  className,
  externalFilters = {},
  leadId
}) => {
  const navigate = useNavigate();
  
  const handleRowClick = (row) => {
    if (onRowClick) {
      onRowClick(row);
    }
  };
  
  const rowActions = [
    {
      label: 'View Details',
      icon: Eye,
      onClick: (row) => onRowClick?.(row) || navigate(`/meetings/${row.id}`)
    },
    {
      label: 'Add/Edit MOM',
      icon: FileText,
      onClick: (row) => onAddMOM?.(row)
    },
    {
      label: 'Reschedule',
      icon: Calendar,
      onClick: (row) => onEdit?.(row)
    },
  ];
  
  const filters = { ...externalFilters };
  if (leadId) {
    filters.lead_id = leadId;
  }
  
  return (
    <SalesDataTable
      endpoint="/api/meetings"
      columns={MEETINGS_COLUMNS}
      queryKey={`sales-meetings-table${leadId ? `-${leadId}` : ''}`}
      title="Sales Meetings"
      quickViews={MEETINGS_QUICK_VIEWS}
      showQuickViews={true}
      showExport={true}
      showGlobalSearch={true}
      onRowClick={handleRowClick}
      rowActions={rowActions}
      emptyMessage="No meetings found."
      defaultSort={{ field: 'meeting_date', direction: 'desc' }}
      defaultPageSize={20}
      className={className}
      externalFilters={filters}
    />
  );
};

export default MeetingsTable;
