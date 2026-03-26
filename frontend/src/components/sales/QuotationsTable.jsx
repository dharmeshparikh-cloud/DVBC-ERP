/**
 * QuotationsTable.jsx - Sales Module Governed Table for Quotations
 * 
 * Uses SalesDataTable with quotations-specific configuration.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { SalesDataTable, FILTER_TYPES } from './SalesDataTable';
import { Eye, Edit, Send, Download, FileText } from 'lucide-react';

// Column configuration for quotations table
const QUOTATIONS_COLUMNS = [
  {
    key: 'title',
    label: 'Quotation',
    filterType: FILTER_TYPES.TEXT,
    filterable: true,
    sortable: true,
    width: '200px',
    render: (value, row) => (
      <div>
        <span className="font-medium text-zinc-900">{value || 'Quotation'}</span>
        {row.quotation_number && (
          <span className="text-xs text-zinc-500 block">#{row.quotation_number}</span>
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
    width: '150px',
    render: (value) => (
      <span className="text-sm text-zinc-700">{value || '-'}</span>
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
    width: '100px',
    filterOptions: [
      { value: 'draft', label: 'Draft' },
      { value: 'sent', label: 'Sent' },
      { value: 'viewed', label: 'Viewed' },
      { value: 'accepted', label: 'Accepted' },
      { value: 'rejected', label: 'Rejected' },
      { value: 'expired', label: 'Expired' },
      { value: 'finalized', label: 'Finalized' },
    ],
    type: 'status'
  },
  {
    key: 'valid_until',
    label: 'Valid Until',
    filterType: FILTER_TYPES.DATE,
    filterable: true,
    sortable: true,
    width: '110px',
    type: 'date'
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

// Quick views for quotations
const QUOTATIONS_QUICK_VIEWS = [
  { id: 'all', label: 'All Quotations', filters: {} },
  { id: 'draft', label: 'Drafts', filters: { status: 'draft' } },
  { id: 'sent', label: 'Sent', filters: { status: 'sent' } },
  { id: 'pending', label: 'Pending Response', filters: { status: 'viewed' } },
  { id: 'accepted', label: 'Accepted', filters: { status: 'accepted' } },
  { id: 'hot', label: 'High Value (>10L)', filters: { value_min: 1000000 } },
];

export const QuotationsTable = ({ 
  onRowClick, 
  onEdit,
  onSend,
  onDownload,
  className,
  externalFilters = {},
  leadId
}) => {
  const navigate = useNavigate();
  
  const handleRowClick = (row) => {
    if (onRowClick) {
      onRowClick(row);
    } else {
      navigate(`/sales-funnel/proforma-invoices?id=${row.id}`);
    }
  };
  
  const rowActions = [
    {
      label: 'View',
      icon: Eye,
      onClick: (row) => handleRowClick(row)
    },
    {
      label: 'Edit',
      icon: Edit,
      onClick: (row) => onEdit?.(row)
    },
    {
      label: 'Send to Client',
      icon: Send,
      onClick: (row) => onSend?.(row)
    },
    {
      label: 'Download PDF',
      icon: Download,
      onClick: (row) => onDownload?.(row)
    },
  ];
  
  const filters = { ...externalFilters };
  if (leadId) {
    filters.lead_id = leadId;
  }
  
  return (
    <SalesDataTable
      endpoint="/api/quotations"
      columns={QUOTATIONS_COLUMNS}
      queryKey={`sales-quotations-table${leadId ? `-${leadId}` : ''}`}
      title="Quotations"
      quickViews={QUOTATIONS_QUICK_VIEWS}
      showQuickViews={true}
      showExport={true}
      showGlobalSearch={true}
      onRowClick={handleRowClick}
      rowActions={rowActions}
      emptyMessage="No quotations found."
      defaultSort={{ field: 'created_at', direction: 'desc' }}
      defaultPageSize={20}
      className={className}
      externalFilters={filters}
    />
  );
};

export default QuotationsTable;
