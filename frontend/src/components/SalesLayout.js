import React, { useContext, useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { AuthContext } from '../App';
import { Button } from './ui/button';
import NotificationBell from './NotificationBell';
import { sanitizeDisplayText } from '../utils/sanitize';
import { SalesNavigationProvider } from '../context/SalesNavigationContext';
import {
  LayoutDashboard, Users, LogOut, DollarSign, FileText, FileCheck, 
  Building2, Calendar, BarChart3, ChevronDown, Send, Clock,
  Umbrella, Receipt, CreditCard
} from 'lucide-react';

const SalesLayout = () => {
  const { user, logout } = useContext(AuthContext);
  const location = useLocation();
  const navigate = useNavigate();

  const [expanded, setExpanded] = useState({
    funnel: true, other: true
  });

  const toggle = (key) => setExpanded(prev => ({ ...prev, [key]: !prev[key] }));

  const handleLogout = () => {
    logout();
    navigate('/sales/login');
  };

  const isActive = (href) => {
    if (href === '/sales' || href === '/sales/') return location.pathname === '/sales' || location.pathname === '/sales/';
    const [path] = href.split('?');
    if (location.pathname.startsWith(path) && path !== '/sales' && path !== '/sales/') {
      return true;
    }
    return false;
  };

  const NavLink = ({ item }) => {
    const Icon = item.icon;
    const active = isActive(item.href);
    return (
      <Link
        to={item.href}
        data-testid={`sales-nav-${item.name.toLowerCase().replace(/\s+/g, '-')}`}
        className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
          active 
            ? 'bg-orange-50 text-orange-700 font-medium border border-orange-200' 
            : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
        }`}
      >
        <Icon className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} />
        <span className="truncate">{item.name}</span>
      </Link>
    );
  };

  const SectionHeader = ({ label, sectionKey }) => (
    <button
      onClick={() => toggle(sectionKey)}
      className="flex items-center justify-between w-full px-3 mb-1 mt-4 text-[11px] font-semibold uppercase tracking-wider text-zinc-400 hover:text-zinc-600 transition-colors"
      data-testid={`sales-section-${sectionKey}`}
    >
      {label}
      <ChevronDown className={`w-3.5 h-3.5 transition-transform ${expanded[sectionKey] ? '' : '-rotate-90'}`} />
    </button>
  );

  const salesFunnelItems = [
    { name: 'Leads', href: '/sales/leads', icon: Users },
    { name: 'Pricing Plans', href: '/sales/pricing-plans', icon: DollarSign },
    { name: 'SOW List', href: '/sales/sow-list', icon: FileText },
    { name: 'Quotations', href: '/sales/quotations', icon: FileText },
    { name: 'Agreements', href: '/sales/agreements', icon: FileCheck },
    { name: 'Kickoff Requests', href: '/sales/kickoff-requests', icon: Send },
  ];

  const salesOtherItems = [
    { name: 'My Clients', href: '/sales/clients', icon: Building2 },
    { name: 'Sales Meetings', href: '/sales/meetings', icon: Calendar },
    { name: 'Sales Reports', href: '/sales/reports', icon: BarChart3 },
  ];

  return (
    <div className="flex min-h-screen bg-zinc-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-zinc-200 flex-shrink-0 h-screen sticky top-0 shadow-sm" data-testid="sales-sidebar">
        <div className="flex flex-col h-full">
          {/* Logo Header */}
          <div className="px-5 py-5 border-b border-zinc-200 bg-gradient-to-r from-orange-50 to-white">
            <div className="flex items-center gap-3">
              <img
                src="https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png"
                alt="Logo" className="h-10 w-auto"
              />
              <div>
                <div className="text-base font-bold text-zinc-900 leading-tight">DVBC</div>
                <div className="text-[10px] font-semibold text-orange-600 uppercase tracking-wider">Sales Portal</div>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-2 overflow-y-auto" data-testid="sales-nav-container">
            {/* Dashboard */}
            <NavLink item={{ name: 'Sales Dashboard', href: '/sales', icon: LayoutDashboard }} />

            {/* Sales Funnel */}
            <SectionHeader label="Sales Funnel" sectionKey="funnel" />
            {expanded.funnel && (
              <div className="space-y-0.5">
                {salesFunnelItems.map(item => <NavLink key={item.name} item={item} />)}
              </div>
            )}

            {/* Other */}
            <SectionHeader label="Other" sectionKey="other" />
            {expanded.other && (
              <div className="space-y-0.5">
                {salesOtherItems.map(item => <NavLink key={item.name} item={item} />)}
              </div>
            )}
          </nav>

          {/* User section */}
          <div className="px-4 py-4 border-t border-zinc-200 bg-zinc-50">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 rounded-full bg-orange-100 flex items-center justify-center text-sm font-semibold text-orange-700">
                {sanitizeDisplayText(user?.full_name)?.charAt(0) || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-zinc-900 truncate">{sanitizeDisplayText(user?.full_name)}</div>
                <div className="text-xs text-zinc-500 capitalize truncate">{user?.role?.replace(/_/g, ' ')}</div>
              </div>
            </div>
            <Button 
              onClick={handleLogout} 
              data-testid="sales-logout-button" 
              variant="outline"
              className="w-full justify-center text-zinc-600 hover:text-zinc-900 hover:bg-white border-zinc-300 h-9 text-sm"
            >
              <LogOut className="w-4 h-4 mr-2" strokeWidth={1.5} /> Sign Out
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        <div className="flex items-center justify-between px-8 py-4 border-b border-zinc-200 bg-white sticky top-0 z-10 shadow-sm">
          <div className="text-sm text-zinc-500">
            Sales Management System
          </div>
          <NotificationBell />
        </div>
        <div className="flex-1 p-8">
          <SalesNavigationProvider>
            <Outlet />
          </SalesNavigationProvider>
        </div>
      </main>
    </div>
  );
};

export default SalesLayout;
