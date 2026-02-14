import React, { useContext } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { AuthContext } from '../App';
import { Button } from './ui/button';
import { LayoutDashboard, Users, Briefcase, Calendar, Mail, LogOut, DollarSign, FileText, FileCheck, ClipboardCheck, UserCog, AlertTriangle } from 'lucide-react';

const Layout = () => {
  const { user, logout } = useContext(AuthContext);
  const location = useLocation();

  const isConsultant = user?.role === 'consultant';
  const isManagerOrAdmin = user?.role === 'manager' || user?.role === 'admin';

  // Navigation items visible based on role
  const getNavigation = () => {
    if (isConsultant) {
      // Consultants see a simplified navigation
      return [
        { name: 'My Dashboard', href: '/', icon: LayoutDashboard },
        { name: 'Projects', href: '/projects', icon: Briefcase },
        { name: 'Meetings', href: '/meetings', icon: Calendar },
      ];
    }
    // Admin, Manager, Executive see full navigation
    return [
      { name: 'Dashboard', href: '/', icon: LayoutDashboard },
      { name: 'Leads', href: '/leads', icon: Users },
      { name: 'Projects', href: '/projects', icon: Briefcase },
      { name: 'Meetings', href: '/meetings', icon: Calendar },
      { name: 'Email Templates', href: '/email-templates', icon: Mail },
    ];
  };

  const navigation = getNavigation();

  const salesFunnelNav = [
    { name: 'Pricing Plans', href: '/sales-funnel/pricing-plans', icon: DollarSign },
    { name: 'Quotations', href: '/sales-funnel/quotations', icon: FileText },
    { name: 'Agreements', href: '/sales-funnel/agreements', icon: FileCheck },
  ];

  const managerNav = [
    { name: 'Approvals', href: '/sales-funnel/approvals', icon: ClipboardCheck },
    { name: 'Consultants', href: '/consultants', icon: UserCog },
  ];

  const isActive = (href) => {
    if (href === '/') return location.pathname === '/';
    return location.pathname.startsWith(href);
  };

  return (
    <div className="flex min-h-screen bg-white">
      <aside className="w-64 border-r border-zinc-200 bg-white" data-testid="sidebar">
        <div className="flex flex-col h-full">
          <div className="p-6 border-b border-zinc-200 flex items-center justify-center">
            <img 
              src="https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png" 
              alt="Logo" 
              className="h-12 w-auto"
            />
          </div>

          <nav className="flex-1 p-4 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  data-testid={`nav-${item.name.toLowerCase().replace(' ', '-')}`}
                  className={`flex items-center gap-3 px-3 py-2 rounded-sm text-sm transition-colors ${
                    active
                      ? 'bg-zinc-100 text-zinc-950 font-medium'
                      : 'text-zinc-600 hover:text-zinc-950 hover:bg-zinc-50'
                  }`}
                >
                  <Icon className="w-4 h-4" strokeWidth={1.5} />
                  {item.name}
                </Link>
              );
            })}
            
            {/* Sales Funnel Section - Not for consultants */}
            {!isConsultant && (
              <div className="pt-4 mt-4 border-t border-zinc-200">
                <div className="px-3 mb-2 text-xs font-medium uppercase tracking-wide text-zinc-400">
                  Sales Funnel
                </div>
                {salesFunnelNav.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.href);
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      data-testid={`nav-${item.name.toLowerCase().replace(' ', '-')}`}
                      className={`flex items-center gap-3 px-3 py-2 rounded-sm text-sm transition-colors ${
                        active
                          ? 'bg-zinc-100 text-zinc-950 font-medium'
                          : 'text-zinc-600 hover:text-zinc-950 hover:bg-zinc-50'
                      }`}
                    >
                      <Icon className="w-4 h-4" strokeWidth={1.5} />
                      {item.name}
                    </Link>
                  );
                })}
              </div>
            )}

            {/* Manager Section - Only visible to managers and admins */}
            {isManagerOrAdmin && (
              <div className="pt-4 mt-4 border-t border-zinc-200">
                <div className="px-3 mb-2 text-xs font-medium uppercase tracking-wide text-zinc-400">
                  Management
                </div>
                {managerNav.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.href);
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      data-testid={`nav-${item.name.toLowerCase().replace(' ', '-')}`}
                      className={`flex items-center gap-3 px-3 py-2 rounded-sm text-sm transition-colors ${
                        active
                          ? 'bg-zinc-100 text-zinc-950 font-medium'
                          : 'text-zinc-600 hover:text-zinc-950 hover:bg-zinc-50'
                      }`}
                    >
                      <Icon className="w-4 h-4" strokeWidth={1.5} />
                      {item.name}
                    </Link>
                  );
                })}
              </div>
            )}
          </nav>

          <div className="p-4 border-t border-zinc-200">
            <div className="mb-3">
              <div className="text-xs font-medium uppercase tracking-wide text-zinc-500 mb-1">
                User
              </div>
              <div className="text-sm text-zinc-950">{user?.full_name}</div>
              <div className="text-xs text-zinc-500 data-text capitalize">{user?.role}</div>
            </div>
            <Button
              onClick={logout}
              data-testid="logout-button"
              variant="ghost"
              className="w-full justify-start text-zinc-600 hover:text-zinc-950 hover:bg-zinc-100 rounded-sm"
            >
              <LogOut className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Sign Out
            </Button>
          </div>
        </div>
      </aside>

      <main className="flex-1">
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
