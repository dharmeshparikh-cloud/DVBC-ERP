/**
 * AgreementsTable.jsx - Sales Module Governed Table for Agreements
 * 
 * Uses SalesDataTable with agreements-specific configuration.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { SalesDataTable, FILTER_TYPES } from './SalesDataTable';
import { Eye, Download, Send, Lock, FileText } from 'lucide-react';

// Column configuration for agreements table
const AGREEMENTS_COLUMNS = [
  {
    key: 'agreement_number',
    label: 'Agreement #',
    filterType: FILTER_TYPES.TEXT,
    filterable: true,
    sortable: true,
    width: '140px',
    render: (value, row) => (
      <div className="flex items-center gap-1">
        <span className="font-medium text-zinc-900">{value || 'N/A'}</span>
        {row.status === 'finalized' && (
          <Lock className="w-3 h-3 text-amber-500" title="Locked - cannot be modified" />
        )}
      </div>
    )
  },
  {
    key: 'client_name',
    label: 'Client',
    filterType: FILTER_TYPES.TEXT,
    filterable: true,
    sortable: true,
    width: '180px',
    render: (value, row) => (
      <span className="text-sm text-zinc-700">{value || row.company_name || '-'}</span>
    )
  },
  {
    key: 'agreement_type',
    label: 'Type',
    filterType: FILTER_TYPES.DROPDOWN,
    filterable: true,
    sortable: true,
    width: '100px',
    filterOptions: [
      { value: 'new', label: 'New' },
      { value: 'renewal', label: 'Renewal' },
      { value: 'amendment', label: 'Amendment' },
    ],
    render: (value) => (
      <span className="text-xs text-zinc-600 capitalize">{value || 'New'}</span>
    )
  },
  {
    key: 'project_tenure_months',
    label: 'Tenure',
    filterType: FILTER_TYPES.NUMBER,
    filterable: true,
    sortable: true,
    width: '90px',
    render: (value) => (
      <span className="text-sm text-zinc-600">{value || 12} months</span>
    )
  },
  {
    key: 'total_value',
    label: 'Value',
    filterType: FILTER_TYPES.NUMBER,
    filterable: true,
    sortable: true,
    width: '120px',
    type: 'currency'
  },
  {
    key: 'status',
    label: 'Status',
    filterType: FILTER_TYPES.DROPDOWN,
    filterable: true,
    sortable: true,
    width: '110px',
    filterOptions: [
      { value: 'draft', label: 'Draft' },
      { value: 'pending_signature', label: 'Pending Signature' },
      { value: 'active', label: 'Active' },
      { value: 'finalized', label: 'Finalized' },
      { value: 'expired', label: 'Expired' },
      { value: 'terminated', label: 'Terminated' },
    ],
    type: 'status'
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

// Quick views for agreements
const AGREEMENTS_QUICK_VIEWS = [
  { id: 'all', label: 'All Agreements', filters: {} },
  { id: 'draft', label: 'Drafts', filters: { status: 'draft' } },
  { id: 'pending', label: 'Pending Signature', filters: { status: 'pending_signature' } },
  { id: 'active', label: 'Active', filters: { status: 'active' } },
  { id: 'finalized', label: 'Finalized', filters: { status: 'finalized' } },
  { id: 'high_value', label: 'High Value (>10L)', filters: { value_min: 1000000 } },
];

export const AgreementsTable = ({ 
  onRowClick, 
  onEdit,
  onDownload,
  onSendEmail,
  className,
  externalFilters = {},
  leadId
}) => {
  const navigate = useNavigate();
  
  const handleRowClick = (row) => {
    if (onRowClick) {
      onRowClick(row);
    } else {
      navigate(`/sales-funnel/agreement/${row.id}`);
    }
  };
  
  const rowActions = [
    {
      label: 'View',
      icon: Eye,
      onClick: (row) => handleRowClick(row)
    },
    {
      label: 'Download PDF',
      icon: Download,
      onClick: (row) => onDownload?.(row.id, 'pdf')
    },
    {
      label: 'Send Email',
      icon: Send,
      onClick: (row) => onSendEmail?.(row)
    },
  ];
  
  const filters = { ...externalFilters };
  if (leadId) {
    filters.lead_id = leadId;
  }
  
  return (
    <SalesDataTable
      endpoint="/api/agreements"
      columns={AGREEMENTS_COLUMNS}
      queryKey={`sales-agreements-table${leadId ? `-${leadId}` : ''}`}
      title="Agreements"
      quickViews={AGREEMENTS_QUICK_VIEWS}
      showQuickViews={true}
      showExport={true}
      showGlobalSearch={true}
      onRowClick={handleRowClick}
      rowActions={rowActions}
      emptyMessage="No agreements found."
      defaultSort={{ field: 'created_at', direction: 'desc' }}
      defaultPageSize={20}
      className={className}
      externalFilters={filters}
    />
  );
};

export default AgreementsTable;
