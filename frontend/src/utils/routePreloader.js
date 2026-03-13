/**
 * Route Preloader - Preload components on hover/focus for faster navigation
 * Implements predictive loading based on user intent
 */

// Map of routes to their lazy import functions
const routeImports = {
  '/approvals': () => import('../pages/ApprovalsCenter'),
  '/employees': () => import('../pages/Employees'),
  '/hr-dashboard': () => import('../pages/HRDashboard'),
  '/hr/onboarding': () => import('../pages/HROnboarding'),
  '/go-live-dashboard': () => import('../pages/GoLiveDashboard'),
  '/kickoff': () => import('../pages/KickoffRequests'),
  '/leads': () => import('../pages/Leads'),
  '/sales-dashboard': () => import('../pages/SalesDashboard'),
  '/admin-masters': () => import('../pages/AdminMasters'),
  '/mobile': () => import('../pages/EmployeeMobileApp'),
  '/attendance': () => import('../pages/Attendance'),
  '/leave': () => import('../pages/LeaveManagement'),
  '/payroll': () => import('../pages/Payroll'),
  '/expenses': () => import('../pages/Expenses'),
  '/documents': () => import('../pages/DocumentCenter'),
  '/reports': () => import('../pages/Reports'),
};

// Cache for already preloaded routes
const preloadedRoutes = new Set();

/**
 * Preload a route's component
 * @param {string} route - The route path to preload
 */
export const preloadRoute = (route) => {
  // Normalize route (remove query params, trailing slashes)
  const normalizedRoute = route.split('?')[0].replace(/\/$/, '') || '/';
  
  // Skip if already preloaded
  if (preloadedRoutes.has(normalizedRoute)) return;
  
  // Find matching import function
  const importFn = routeImports[normalizedRoute];
  
  if (importFn) {
    // Mark as preloading
    preloadedRoutes.add(normalizedRoute);
    
    // Trigger the import (webpack will cache it)
    importFn().catch(() => {
      // Remove from cache on error so it can be retried
      preloadedRoutes.delete(normalizedRoute);
    });
  }
};

/**
 * Preload routes based on user role for faster initial navigation
 * @param {string} role - The user's role
 */
export const preloadRoutesByRole = (role) => {
  const roleRoutes = {
    admin: ['/approvals', '/employees', '/hr-dashboard', '/admin-masters', '/reports'],
    hr_manager: ['/hr-dashboard', '/hr/onboarding', '/go-live-dashboard', '/employees', '/attendance'],
    hr_executive: ['/hr-dashboard', '/hr/onboarding', '/attendance', '/leave'],
    sales_manager: ['/sales-dashboard', '/leads', '/kickoff'],
    executive: ['/leads', '/sales-dashboard'],
    principal_consultant: ['/approvals', '/employees', '/reports'],
    consultant: ['/mobile', '/attendance', '/leave', '/expenses'],
  };

  const routesToPreload = roleRoutes[role] || [];
  
  // Delay preloading to not block initial render
  setTimeout(() => {
    routesToPreload.forEach(route => preloadRoute(route));
  }, 2000);
};

/**
 * HOC to add preload on hover capability to links
 */
export const withPreload = (WrappedComponent) => {
  return function PreloadingLink({ to, ...props }) {
    const handleMouseEnter = () => {
      if (to) preloadRoute(to);
    };

    const handleFocus = () => {
      if (to) preloadRoute(to);
    };

    return (
      <WrappedComponent
        to={to}
        onMouseEnter={handleMouseEnter}
        onFocus={handleFocus}
        {...props}
      />
    );
  };
};

/**
 * Hook to enable preloading on navigation intent
 * Use in components that render navigation links
 */
export const usePreloadOnHover = () => {
  return {
    onMouseEnter: (route) => () => preloadRoute(route),
    onFocus: (route) => () => preloadRoute(route),
  };
};

export default {
  preloadRoute,
  preloadRoutesByRole,
  withPreload,
  usePreloadOnHover,
};
