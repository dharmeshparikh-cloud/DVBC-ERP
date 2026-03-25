/**
 * LeadsTable.jsx - Sales Module Governed Table for Leads
 * 
 * Uses SalesDataTable with leads-specific configuration.
 * DO NOT use manual <table> rendering for leads.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { SalesDataTable, FILTER_TYPES } from './SalesDataTable';
import { Eye, Edit, Phone, Mail, Pause, Play, MoreHorizontal } from 'lucide-react';
import { Badge } from '../ui/badge';

// Column configuration for leads table
const LEADS_COLUMNS = [
  {
    key: 'company',
    label: 'Company',
    filterType: FILTER_TYPES.TEXT,
    filterable: true,
    sortable: true,
    width: '180px',
    render: (value, row) => (
      <div>
        <span className="font-medium text-zinc-900">{value || 'N/A'}</span>
        {row.first_name && (
          <span className="text-xs text-zinc-500 block">
            {row.first_name} {row.last_name}
          </span>
        )}
      </div>
    )
  },
  {
    key: 'email',
    label: 'Contact',
    filterType: FILTER_TYPES.TEXT,
    filterable: true,
    sortable: false,
    width: '180px',
    render: (value, row) => (
      <div className="text-xs">
        {value && (
          <span className="flex items-center gap-1 text-zinc-600">
            <Mail className="w-3 h-3" />{value}
          </span>
        )}
        {row.phone && (
          <span className="flex items-center gap-1 text-zinc-500 mt-0.5">
            <Phone className="w-3 h-3" />{row.phone}
          </span>
        )}
      </div>
    )
  },
  {
    key: 'status',
    label: 'Stage',
    filterType: FILTER_TYPES.DROPDOWN,
    filterable: true,
    sortable: true,
    width: '120px',
    filterOptions: [
      { value: 'new', label: 'New' },
      { value: 'meeting', label: 'Meeting' },
      { value: 'pricing_plan', label: 'Pricing Plan' },
      { value: 'sow', label: 'SOW' },
      { value: 'quotation', label: 'Quotation' },
      { value: 'agreement', label: 'Agreement' },
      { value: 'payment', label: 'Payment' },
      { value: 'kickoff_request', label: 'Kickoff Request' },
      { value: 'kick_accept', label: 'Kick Accept' },
      { value: 'closed', label: 'Closed' },
      { value: 'paused', label: 'Paused' },
      { value: 'lost', label: 'Lost' },
    ],
    type: 'status'
  },
  {
    key: 'deal_value',
    label: 'Deal Value',
    filterType: FILTER_TYPES.NUMBER,
    filterable: true,
    sortable: true,
    width: '120px',
    type: 'currency'
  },
  {
    key: 'source',
    label: 'Source',
    filterType: FILTER_TYPES.DROPDOWN,
    filterable: true,
    sortable: true,
    width: '100px',
    filterOptions: [
      { value: 'referral', label: 'Referral' },
      { value: 'website', label: 'Website' },
      { value: 'linkedin', label: 'LinkedIn' },
      { value: 'cold_call', label: 'Cold Call' },
      { value: 'event', label: 'Event' },
      { value: 'partner', label: 'Partner' },
      { value: 'other', label: 'Other' },
    ],
    render: (value) => (
      <span className="text-xs text-zinc-600 capitalize">{value || '-'}</span>
    )
  },
  {
    key: 'industry',
    label: 'Industry',
    filterType: FILTER_TYPES.DROPDOWN,
    filterable: true,
    sortable: true,
    width: '120px',
    filterOptions: [
      { value: 'Manufacturing', label: 'Manufacturing' },
      { value: 'IT/Software', label: 'IT/Software' },
      { value: 'Healthcare', label: 'Healthcare' },
      { value: 'Finance/Banking', label: 'Finance/Banking' },
      { value: 'Retail', label: 'Retail' },
      { value: 'Consulting', label: 'Consulting' },
      { value: 'Other', label: 'Other' },
    ],
    render: (value) => (
      <span className="text-xs text-zinc-600">{value || '-'}</span>
    )
  },
  {
    key: 'created_at',
    label: 'Created',
    filterType: FILTER_TYPES.DATE,
    filterable: true,
    sortable: true,
    width: '100px',
    type: 'date'
  },
];

// Quick views for leads
const LEADS_QUICK_VIEWS = [
  { id: 'all', label: 'All Leads', filters: {} },
  { id: 'my_leads', label: 'My Leads', filters: { assigned_to: 'CURRENT_USER' } },
  { id: 'new', label: 'New', filters: { status: 'new' } },
  { id: 'hot_deals', label: 'Hot Deals (>5L)', filters: { deal_value_min: 500000 } },
  { id: 'stuck_deals', label: 'Stuck (>7 days)', filters: { days_since_activity: 7 } },
  { id: 'meeting', label: 'In Meeting', filters: { status: 'meeting' } },
  { id: 'closing', label: 'Closing', filters: { status: 'agreement' } },
];

export const LeadsTable = ({ 
  onRowClick, 
  onEdit, 
  onPause,
  onResume,
  className,
  externalFilters = {}
}) => {
  const navigate = useNavigate();
  
  const handleRowClick = (row) => {
    if (onRowClick) {
      onRowClick(row);
    } else {
      navigate(`/sales-funnel/lead/${row.id}`);
    }
  };
  
  const rowActions = [
    {
      label: 'View Pipeline',
      icon: Eye,
      onClick: (row) => navigate(`/sales-funnel/lead/${row.id}`)
    },
    {
      label: 'Edit Lead',
      icon: Edit,
      onClick: (row) => onEdit?.(row)
    },
    {
      label: 'Pause Lead',
      icon: Pause,
      onClick: (row) => onPause?.(row),
      className: 'text-yellow-600'
    },
  ];
  
  return (
    <SalesDataTable
      endpoint="/api/leads"
      columns={LEADS_COLUMNS}
      queryKey="sales-leads-table"
      title="Sales Leads"
      quickViews={LEADS_QUICK_VIEWS}
      showQuickViews={true}
      showExport={true}
      showGlobalSearch={true}
      onRowClick={handleRowClick}
      rowActions={rowActions}
      emptyMessage="No leads found. Create your first lead to get started."
      defaultSort={{ field: 'created_at', direction: 'desc' }}
      defaultPageSize={20}
      className={className}
      externalFilters={externalFilters}
    />
  );
};

export default LeadsTable;
