import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';

/**
 * PortalRedirect - Redirects old portal URLs to Main ERP equivalents
 * 
 * /sales/leads → /leads
 * /sales/pricing-plans → /sales-funnel/pricing-plans
 * /hr/employees → /employees
 * 
 * Preserves query strings and maintains backward compatibility.
 */

// Mapping of portal-specific paths to their Main ERP equivalents
const SALES_PATH_MAP = {
  '': '/sales-dashboard',  // /sales → /sales-dashboard
  'leads': '/leads',
  'pricing-plans': '/sales-funnel/pricing-plans',
  'sow': '/sales-funnel/sow-list',
  'sow-list': '/sales-funnel/sow-list',
  'quotations': '/sales-funnel/quotations',
  'agreements': '/sales-funnel/agreements',
  'payment-verification': '/sales-funnel/payment-verification',
  'kickoff-requests': '/kickoff-requests',
  'manager-leads': '/manager-leads',
  'team-leads': '/team-leads',
  'clients': '/clients',
  'meetings': '/sales-meetings',
  'reports': '/reports?category=sales',
  'team-performance': '/team-performance',
  'my-attendance': '/my-attendance',
  'my-leaves': '/my-leaves',
  'my-salary': '/my-salary-slips',
  'my-expenses': '/my-expenses',
  'my-details': '/my-details',
  'my-drafts': '/my-drafts',
  'my-bank-details': '/my-details',
};

const HR_PATH_MAP = {
  '': '/hr-dashboard',  // /hr → /hr-dashboard
  'employees': '/employees',
  'onboarding': '/onboarding',
  'password-management': '/password-management',
  'go-live': '/go-live',
  'org-chart': '/org-chart',
  'leave-management': '/leave-management',
  'attendance': '/attendance',
  'payroll': '/payroll',
  'ctc-designer': '/ctc-designer',
  'document-center': '/document-center',
  'document-builder': '/document-builder',
  'letter-management': '/letter-management',
  'reports': '/reports?category=hr',
  'notifications': '/notifications',
  'employee-permissions': '/employee-permissions',
  'my-attendance': '/my-attendance',
  'my-leaves': '/my-leaves',
  'my-salary': '/my-salary-slips',
  'my-expenses': '/my-expenses',
  'my-details': '/my-details',
  'my-drafts': '/my-drafts',
  'my-bank-details': '/my-details',
};

export const SalesPortalRedirect = () => {
  const location = useLocation();
  
  // Extract path after /sales/
  const salesPath = location.pathname.replace(/^\/sales\/?/, '');
  
  // Check for dynamic routes (with IDs)
  if (salesPath.startsWith('sow/') && salesPath !== 'sow/') {
    // /sales/sow/:id → /sales-funnel/sow/:id
    const id = salesPath.replace('sow/', '');
    return <Navigate to={`/sales-funnel/sow/${id}${location.search}`} replace />;
  }
  
  if (salesPath.startsWith('scope-selection/')) {
    const id = salesPath.replace('scope-selection/', '');
    return <Navigate to={`/sales-funnel/scope-selection/${id}${location.search}`} replace />;
  }
  
  if (salesPath.startsWith('sow-review/')) {
    const id = salesPath.replace('sow-review/', '');
    return <Navigate to={`/sales-funnel/sow-review/${id}${location.search}`} replace />;
  }
  
  if (salesPath.startsWith('agreement/')) {
    const id = salesPath.replace('agreement/', '');
    return <Navigate to={`/sales-funnel/agreement/${id}${location.search}`} replace />;
  }
  
  // Static path mapping
  const mainERPPath = SALES_PATH_MAP[salesPath];
  
  if (mainERPPath) {
    return <Navigate to={`${mainERPPath}${location.search}`} replace />;
  }
  
  // Fallback: strip /sales and try direct path
  return <Navigate to={`/${salesPath}${location.search}`} replace />;
};

export const HRPortalRedirect = () => {
  const location = useLocation();
  
  // Extract path after /hr/
  const hrPath = location.pathname.replace(/^\/hr\/?/, '');
  
  // Static path mapping
  const mainERPPath = HR_PATH_MAP[hrPath];
  
  if (mainERPPath) {
    return <Navigate to={`${mainERPPath}${location.search}`} replace />;
  }
  
  // Fallback: strip /hr and try direct path
  return <Navigate to={`/${hrPath}${location.search}`} replace />;
};

export default { SalesPortalRedirect, HRPortalRedirect };
