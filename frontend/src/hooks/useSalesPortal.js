import { useLocation } from 'react-router-dom';

/**
 * Hook to detect if we're in the Sales Portal and get correct navigation paths
 */
export const useSalesPortal = () => {
  const location = useLocation();
  const isSalesPortal = location.pathname.startsWith('/sales');
  
  /**
   * Get the correct path based on whether we're in Sales Portal or main app
   */
  const getPath = (mainPath) => {
    if (!isSalesPortal) return mainPath;
    
    // Map main app paths to sales portal paths
    const pathMappings = {
      '/leads': '/sales/leads',
      '/sales-funnel/pricing-plans': '/sales/pricing-plans',
      '/sales-funnel/sow-list': '/sales/sow-list',
      '/sales-funnel/quotations': '/sales/quotations',
      '/sales-funnel/proforma-invoice': '/sales/quotations',
      '/sales-funnel/agreements': '/sales/agreements',
      '/kickoff-requests': '/sales/kickoff-requests',
      '/clients': '/sales/clients',
      '/sales-meetings': '/sales/meetings',
      '/reports': '/sales/reports',
    };
    
    // Check for exact match first
    if (pathMappings[mainPath]) {
      return pathMappings[mainPath];
    }
    
    // Handle dynamic routes
    if (mainPath.startsWith('/sales-funnel/scope-selection/')) {
      return mainPath.replace('/sales-funnel/scope-selection/', '/sales/scope-selection/');
    }
    if (mainPath.startsWith('/sales-funnel/sow-review/')) {
      return mainPath.replace('/sales-funnel/sow-review/', '/sales/sow-review/');
    }
    if (mainPath.startsWith('/sales-funnel/sow/')) {
      return mainPath.replace('/sales-funnel/sow/', '/sales/sow/');
    }
    if (mainPath.startsWith('/sales-funnel/agreement/')) {
      return mainPath.replace('/sales-funnel/agreement/', '/sales/agreement/');
    }
    
    // For any unmatched paths, just return as is
    return mainPath;
  };
  
  return {
    isSalesPortal,
    getPath,
    basePath: isSalesPortal ? '/sales' : ''
  };
};

export default useSalesPortal;
