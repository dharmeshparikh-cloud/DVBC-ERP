import React, { createContext, useContext } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const SalesNavigationContext = createContext(null);

export const useSalesNavigation = () => {
  const context = useContext(SalesNavigationContext);
  const navigate = useNavigate();
  const location = useLocation();
  
  const isSalesPortal = location.pathname.startsWith('/sales');
  
  // If not in context (main app), return regular navigate
  if (!context) {
    return {
      navigate,
      isSalesPortal: false,
      getPath: (path) => path
    };
  }
  
  return context;
};

export const SalesNavigationProvider = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const isSalesPortal = location.pathname.startsWith('/sales');
  
  const getPath = (mainPath) => {
    if (!isSalesPortal) return mainPath;
    
    // Direct mappings
    const mappings = {
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
    
    if (mappings[mainPath]) return mappings[mainPath];
    
    // Dynamic route patterns
    const patterns = [
      { from: /^\/sales-funnel\/scope-selection\/(.+)$/, to: '/sales/scope-selection/$1' },
      { from: /^\/sales-funnel\/sow-review\/(.+)$/, to: '/sales/sow-review/$1' },
      { from: /^\/sales-funnel\/sow\/(.+)$/, to: '/sales/sow/$1' },
      { from: /^\/sales-funnel\/agreement\/(.+)$/, to: '/sales/agreement/$1' },
      { from: /^\/sales-funnel\/agreement$/, to: '/sales/agreement' },
    ];
    
    for (const pattern of patterns) {
      if (pattern.from.test(mainPath)) {
        return mainPath.replace(pattern.from, pattern.to);
      }
    }
    
    return mainPath;
  };
  
  const salesNavigate = (path, options) => {
    const targetPath = getPath(path);
    navigate(targetPath, options);
  };
  
  return (
    <SalesNavigationContext.Provider value={{ 
      navigate: salesNavigate, 
      isSalesPortal, 
      getPath,
      rawNavigate: navigate 
    }}>
      {children}
    </SalesNavigationContext.Provider>
  );
};

export default SalesNavigationContext;
