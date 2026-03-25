/**
 * ProformaInvoiceTable.jsx - Sales Module Governed Table for Proforma Invoices / Quotations
 * 
 * Uses SalesDataTable with proforma-specific configuration.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { SalesDataTable, FILTER_TYPES } from './SalesDataTable';
import { Eye, Download, Send, Printer, FileText } from 'lucide-react';

// Column configuration for proforma invoices table
const PROFORMA_COLUMNS = [
  {
    key: 'invoice_number',
    label: 'Invoice #',
    filterType: FILTER_TYPES.TEXT,
    filterable: true,
    sortable: true,
    width: '130px',
    render: (value, row) => (
      <div>
        <span className="font-medium text-zinc-900">{value || row.quotation_number || 'N/A'}</span>
        {row.version && row.version > 1 && (
          <span className="text-xs text-zinc-400 ml-1">v{row.version}</span>
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
    key: 'total_amount',
    label: 'Amount',
    filterType: FILTER_TYPES.NUMBER,
    filterable: true,
    sortable: true,
    width: '130px',
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
    key: 'pricing_plan_name',
    label: 'Pricing Plan',
    filterType: FILTER_TYPES.TEXT,
    filterable: true,
    sortable: true,
    width: '150px',
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

// Quick views for proforma invoices
const PROFORMA_QUICK_VIEWS = [
  { id: 'all', label: 'All Invoices', filters: {} },
  { id: 'draft', label: 'Drafts', filters: { status: 'draft' } },
  { id: 'sent', label: 'Sent', filters: { status: 'sent' } },
  { id: 'pending', label: 'Awaiting Response', filters: { status: 'viewed' } },
  { id: 'accepted', label: 'Accepted', filters: { status: 'accepted' } },
  { id: 'high_value', label: 'High Value (>5L)', filters: { value_min: 500000 } },
];

export const ProformaInvoiceTable = ({ 
  onRowClick, 
  onView,
  onDownload,
  onSend,
  onPrint,
  className,
  externalFilters = {},
  leadId,
  pricingPlanId
}) => {
  const navigate = useNavigate();
  
  const handleRowClick = (row) => {
    if (onRowClick) {
      onRowClick(row);
    } else if (onView) {
      onView(row);
    }
  };
  
  const rowActions = [
    {
      label: 'View',
      icon: Eye,
      onClick: (row) => onView?.(row) || handleRowClick(row)
    },
    {
      label: 'Download PDF',
      icon: Download,
      onClick: (row) => onDownload?.(row)
    },
    {
      label: 'Send to Client',
      icon: Send,
      onClick: (row) => onSend?.(row)
    },
    {
      label: 'Print',
      icon: Printer,
      onClick: (row) => onPrint?.(row)
    },
  ];
  
  const filters = { ...externalFilters };
  if (leadId) {
    filters.lead_id = leadId;
  }
  if (pricingPlanId) {
    filters.pricing_plan_id = pricingPlanId;
  }
  
  return (
    <SalesDataTable
      endpoint="/api/quotations"
      columns={PROFORMA_COLUMNS}
      queryKey={`sales-proforma-table${leadId ? `-${leadId}` : ''}${pricingPlanId ? `-${pricingPlanId}` : ''}`}
      title="Proforma Invoices"
      quickViews={PROFORMA_QUICK_VIEWS}
      showQuickViews={true}
      showExport={true}
      showGlobalSearch={true}
      onRowClick={handleRowClick}
      rowActions={rowActions}
      emptyMessage="No proforma invoices found."
      defaultSort={{ field: 'created_at', direction: 'desc' }}
      defaultPageSize={20}
      className={className}
      externalFilters={filters}
    />
  );
};

export default ProformaInvoiceTable;
