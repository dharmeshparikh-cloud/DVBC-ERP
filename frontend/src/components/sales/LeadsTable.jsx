/**
 * LeadsTable.jsx - Sales Module Governed Table for Leads
 * 
 * Uses SalesDataTable with leads-specific configuration.
 * DO NOT use manual <table> rendering for leads.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { SalesDataTable, FILTER_TYPES } from './SalesDataTable';
import { Eye, Edit, Phone, Mail, Pause, Play, ExternalLink, ArrowRightLeft } from 'lucide-react';
import { Badge } from '../ui/badge';

// Funnel stage mapping - uses LEAD DB STATUS values (not funnel step IDs)
// Backend auto-syncs lead.status based on funnel progress:
//   lead_capture → new, record_meeting → contacted, pricing_plan/sow → qualified,
//   quotation → proposal, agreement/payment/kickoff → agreement, project → closed
const FUNNEL_STAGES = [
  { key: 'new', label: 'New Lead', color: 'bg-zinc-400' },
  { key: 'contacted', label: 'Meeting', color: 'bg-orange-500' },
  { key: 'qualified', label: 'Pricing/SOW', color: 'bg-amber-500' },
  { key: 'proposal', label: 'Proforma Invoice', color: 'bg-cyan-500' },
  { key: 'agreement', label: 'Agreement', color: 'bg-blue-500' },
  { key: 'closed', label: 'Complete', color: 'bg-emerald-500' },
];

const getFunnelStageIndex = (status) => {
  const idx = FUNNEL_STAGES.findIndex(s => s.key === status);
  return idx >= 0 ? idx : 0;
};

const getFunnelStageInfo = (status) => {
  return FUNNEL_STAGES.find(s => s.key === status) || FUNNEL_STAGES[0];
};

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
      { value: 'quotation', label: 'Proforma Invoice' },
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
    key: 'funnel_progress',
    label: 'Funnel',
    filterable: false,
    sortable: false,
    width: '140px',
    render: (value, row) => {
      const stageInfo = getFunnelStageInfo(row.status);
      const stageIdx = getFunnelStageIndex(row.status);
      const totalStages = FUNNEL_STAGES.length;
      const percentage = Math.round(((stageIdx + 1) / totalStages) * 100);
      
      if (row.status === 'paused') {
        return (
          <span className="text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-700 font-medium">
            Paused
          </span>
        );
      }
      if (row.status === 'lost') {
        return (
          <span className="text-xs px-2 py-0.5 rounded bg-red-50 text-red-700 font-medium">
            Lost
          </span>
        );
      }
      
      return (
        <div className="flex flex-col gap-1 min-w-[110px]">
          <div className="h-1.5 w-full bg-zinc-100 rounded-full overflow-hidden">
            <div
              className={`h-full ${stageInfo.color} transition-all duration-300`}
              style={{ width: `${percentage}%` }}
            />
          </div>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-medium ${stageInfo.color.replace('bg-', 'text-').replace('-500', '-600').replace('-400', '-500')}`}>
              {stageInfo.label}
            </span>
            <span className="text-[10px] text-zinc-400">{stageIdx + 1}/{totalStages}</span>
          </div>
        </div>
      );
    }
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
  onReassign,
  className,
  externalFilters = {}
}) => {
  const navigate = useNavigate();
  
  const handleRowClick = (row) => {
    if (onRowClick) {
      onRowClick(row);
    } else {
      navigate(`/sales-funnel-onboarding?leadId=${row.id}`);
    }
  };
  
  const rowActions = [
    {
      label: 'View Pipeline',
      icon: Eye,
      onClick: (row) => navigate(`/sales-funnel-onboarding?leadId=${row.id}`)
    },
    {
      label: 'Edit Lead',
      icon: Edit,
      onClick: (row) => onEdit?.(row)
    },
    {
      label: 'Reassign Lead',
      icon: ArrowRightLeft,
      onClick: (row) => onReassign?.(row),
      className: 'text-blue-600'
    },
    {
      label: (row) => row?.status === 'paused' ? 'Resume Lead' : 'Pause Lead',
      icon: (row) => row?.status === 'paused' ? Play : Pause,
      onClick: (row) => row?.status === 'paused' ? onResume?.(row) : onPause?.(row),
      className: (row) => row?.status === 'paused' ? 'text-emerald-600' : 'text-yellow-600'
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
