/**
 * SOWTable.jsx - Sales Module Governed Table for Statements of Work
 * 
 * Uses SalesDataTable with SOW-specific configuration.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { SalesDataTable, FILTER_TYPES } from './SalesDataTable';
import { Eye, Edit, FileText, Calendar, Users, Download } from 'lucide-react';

// Column configuration for SOW table
const SOW_COLUMNS = [
  {
    key: 'sow_number',
    label: 'SOW #',
    filterType: FILTER_TYPES.TEXT,
    filterable: true,
    sortable: true,
    width: '120px',
    render: (value, row) => (
      <div>
        <span className="font-medium text-zinc-900">{value || row.title || 'N/A'}</span>
        {row.version && (
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
    key: 'category',
    label: 'Category',
    filterType: FILTER_TYPES.DROPDOWN,
    filterable: true,
    sortable: true,
    width: '120px',
    filterOptions: [
      { value: 'sales', label: 'Sales' },
      { value: 'hr', label: 'HR' },
      { value: 'operations', label: 'Operations' },
      { value: 'training', label: 'Training' },
      { value: 'analytics', label: 'Analytics' },
      { value: 'digital_marketing', label: 'Digital Marketing' },
    ],
    render: (value) => (
      <span className="text-xs text-zinc-600 capitalize">{value?.replace('_', ' ') || '-'}</span>
    )
  },
  {
    key: 'items_count',
    label: 'Items',
    filterType: FILTER_TYPES.NUMBER,
    filterable: false,
    sortable: true,
    width: '70px',
    render: (value, row) => (
      <span className="text-sm text-zinc-600">{row.items?.length || value || 0}</span>
    )
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
      { value: 'pending_review', label: 'Pending Review' },
      { value: 'approved', label: 'Approved' },
      { value: 'in_progress', label: 'In Progress' },
      { value: 'completed', label: 'Completed' },
      { value: 'rejected', label: 'Rejected' },
    ],
    type: 'status'
  },
  {
    key: 'start_date',
    label: 'Start Date',
    filterType: FILTER_TYPES.DATE,
    filterable: true,
    sortable: true,
    width: '100px',
    type: 'date'
  },
  {
    key: 'end_date',
    label: 'End Date',
    filterType: FILTER_TYPES.DATE,
    filterable: true,
    sortable: true,
    width: '100px',
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

// Quick views for SOW
const SOW_QUICK_VIEWS = [
  { id: 'all', label: 'All SOWs', filters: {} },
  { id: 'draft', label: 'Drafts', filters: { status: 'draft' } },
  { id: 'pending', label: 'Pending Review', filters: { status: 'pending_review' } },
  { id: 'approved', label: 'Approved', filters: { status: 'approved' } },
  { id: 'in_progress', label: 'In Progress', filters: { status: 'in_progress' } },
  { id: 'completed', label: 'Completed', filters: { status: 'completed' } },
];

export const SOWTable = ({ 
  onRowClick, 
  onEdit,
  onView,
  className,
  externalFilters = {},
  leadId,
  pricingPlanId
}) => {
  const navigate = useNavigate();
  
  const handleRowClick = (row) => {
    if (onRowClick) {
      onRowClick(row);
    } else {
      // Navigate to SOW builder with the SOW ID
      navigate(`/sales-funnel/sow/${row.pricing_plan_id || row.id}?lead_id=${row.lead_id || ''}`);
    }
  };
  
  const rowActions = [
    {
      label: 'View/Edit',
      icon: Eye,
      onClick: (row) => handleRowClick(row)
    },
    {
      label: 'Edit Items',
      icon: Edit,
      onClick: (row) => onEdit?.(row) || handleRowClick(row)
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
      endpoint="/api/enhanced-sow/list"
      columns={SOW_COLUMNS}
      queryKey={`sales-sow-table${leadId ? `-${leadId}` : ''}${pricingPlanId ? `-${pricingPlanId}` : ''}`}
      title="Statements of Work"
      quickViews={SOW_QUICK_VIEWS}
      showQuickViews={true}
      showExport={true}
      showGlobalSearch={true}
      onRowClick={handleRowClick}
      rowActions={rowActions}
      emptyMessage="No SOWs found."
      defaultSort={{ field: 'created_at', direction: 'desc' }}
      defaultPageSize={20}
      className={className}
      externalFilters={filters}
    />
  );
};

export default SOWTable;
