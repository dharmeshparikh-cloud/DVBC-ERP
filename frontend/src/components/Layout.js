import React, { useContext } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { AuthContext } from '../App';
import { Button } from './ui/button';
import {
  LayoutDashboard, Users, Briefcase, Calendar, CalendarCheck, Mail, LogOut,
  DollarSign, FileText, FileCheck, ClipboardCheck, UserCog, AlertTriangle,
  User, Shield, UsersRound, Building2, Receipt, BarChart3, ChevronRight
} from 'lucide-react';

// Role groups per domain
const HR_ROLES = ['admin', 'hr_manager', 'hr_executive', 'manager'];
const SALES_ROLES_NAV = ['admin', 'executive', 'account_manager', 'manager'];
const CONSULTING_ROLES_NAV = [
  'admin', 'project_manager', 'consultant', 'principal_consultant',
  'lean_consultant', 'lead_consultant', 'senior_consultant',
  'subject_matter_expert', 'manager'
];
const ADMIN_ROLES = ['admin', 'manager'];

const Layout = () => {
  const { user, logout } = useContext(AuthContext);
  const location = useLocation();
  const role = user?.role;

  const showHR = HR_ROLES.includes(role);
  const showSales = SALES_ROLES_NAV.includes(role);
  const showConsulting = CONSULTING_ROLES_NAV.includes(role);
  const showAdmin = ADMIN_ROLES.includes(role);
  const isConsultant = role === 'consultant';

  const isActive = (href) => {
    if (href === '/') return location.pathname === '/';
    // Handle query params in href
    const [path] = href.split('?');
    if (location.pathname.startsWith(path) && path !== '/') {
      // If href has query params, also check those
      if (href.includes('?')) {
        return location.pathname.startsWith(path) && location.search.includes(href.split('?')[1]);
      }
      return true;
    }
    return false;
  };

  const NavLink = ({ item, indent = false, flowStep = false }) => {
    const Icon = item.icon;
    const active = isActive(item.href);
    return (
      <Link
        to={item.href}
        data-testid={`nav-${item.name.toLowerCase().replace(/\s+/g, '-')}`}
        className={`flex items-center gap-3 py-2 rounded-sm text-sm transition-colors ${indent ? 'pl-6 pr-3' : 'px-3'} ${
          active ? 'bg-zinc-100 text-zinc-950 font-medium' : 'text-zinc-600 hover:text-zinc-950 hover:bg-zinc-50'
        }`}
      >
        {flowStep && (
          <div className="flex items-center">
            <ChevronRight className="w-3 h-3 text-zinc-300 -ml-1 mr-0.5" strokeWidth={2} />
          </div>
        )}
        <Icon className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} />
        <span className="truncate">{item.name}</span>
      </Link>
    );
  };

  const SectionHeader = ({ label }) => (
    <div className="px-3 mb-1.5 mt-5 text-[10px] font-semibold uppercase tracking-widest text-zinc-400">
      {label}
    </div>
  );

  // Sales Flow branch items (Lead → Pricing → Quotation → Agreement)
  const salesFlowItems = [
    { name: 'Leads', href: '/leads', icon: Users },
    { name: 'Pricing Plans', href: '/sales-funnel/pricing-plans', icon: DollarSign },
    { name: 'Quotations', href: '/sales-funnel/quotations', icon: FileText },
    { name: 'Agreements', href: '/sales-funnel/agreements', icon: FileCheck },
  ];

  const salesOtherItems = [
    { name: 'Clients', href: '/clients', icon: Building2 },
    { name: 'Sales Meetings', href: '/sales-meetings', icon: Calendar },
    { name: 'Sales Reports', href: '/reports?category=sales', icon: BarChart3 },
  ];

  const hrItems = [
    { name: 'Employees', href: '/employees', icon: UsersRound },
    { name: 'Expenses', href: '/expenses', icon: Receipt },
    { name: 'HR Reports', href: '/reports?category=hr', icon: BarChart3 },
  ];

  const consultingItems = isConsultant
    ? [
        { name: 'Projects', href: '/projects', icon: Briefcase },
        { name: 'Consulting Meetings', href: '/consulting-meetings', icon: CalendarCheck },
      ]
    : [
        { name: 'Projects', href: '/projects', icon: Briefcase },
        { name: 'Consulting Meetings', href: '/consulting-meetings', icon: CalendarCheck },
        { name: 'Consultants', href: '/consultants', icon: UserCog },
        { name: 'Handover Alerts', href: '/handover-alerts', icon: AlertTriangle },
        { name: 'Consulting Reports', href: '/reports?category=operations', icon: BarChart3 },
      ];

  const adminItems = [
    { name: 'User Management', href: '/user-management', icon: Shield },
    { name: 'Approvals Center', href: '/approvals', icon: ClipboardCheck },
    { name: 'Email Templates', href: '/email-templates', icon: Mail },
  ];

  return (
    <div className="flex min-h-screen bg-white">
      <aside className="w-64 border-r border-zinc-200 bg-white flex-shrink-0 h-screen sticky top-0" data-testid="sidebar">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-zinc-200 flex items-center justify-center">
            <img
              src="https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png"
              alt="Logo" className="h-12 w-auto"
            />
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-2 overflow-y-auto" data-testid="nav-container">
            {/* Dashboard - always visible */}
            <NavLink item={{ name: isConsultant ? 'My Dashboard' : 'Dashboard', href: '/', icon: LayoutDashboard }} />

            {/* ─── HR ─── */}
            {showHR && (
              <>
                <SectionHeader label="HR" />
                {hrItems.map(item => <NavLink key={item.name} item={item} />)}
              </>
            )}

            {/* ─── SALES ─── */}
            {showSales && (
              <>
                <SectionHeader label="Sales" />
                {/* Sales Flow Branch */}
                <div className="relative ml-3 pl-3 border-l-2 border-zinc-200 space-y-0.5" data-testid="sales-flow-branch">
                  <div className="absolute -left-[5px] top-0 w-2 h-2 rounded-full bg-zinc-300" />
                  {salesFlowItems.map((item, idx) => (
                    <div key={item.name} className="relative">
                      {idx > 0 && (
                        <div className="absolute -left-[17px] top-1/2 w-3 h-px bg-zinc-200" />
                      )}
                      <NavLink item={item} flowStep={idx > 0} />
                    </div>
                  ))}
                  <div className="absolute -left-[5px] bottom-0 w-2 h-2 rounded-full bg-zinc-300" />
                </div>
                {/* Other Sales Items */}
                <div className="mt-1 space-y-0.5">
                  {salesOtherItems.map(item => <NavLink key={item.name} item={item} />)}
                </div>
              </>
            )}

            {/* ─── CONSULTING ─── */}
            {showConsulting && (
              <>
                <SectionHeader label="Consulting" />
                {consultingItems.map(item => <NavLink key={item.name} item={item} />)}
              </>
            )}

            {/* ─── ADMIN ─── */}
            {showAdmin && (
              <>
                <SectionHeader label="Admin" />
                {adminItems.map(item => <NavLink key={item.name} item={item} />)}
              </>
            )}
          </nav>

          {/* User section */}
          <div className="p-4 border-t border-zinc-200">
            <div className="mb-3">
              <Link to="/profile" className="block hover:bg-zinc-50 rounded-sm p-1 -m-1">
                <div className="text-sm text-zinc-950">{user?.full_name}</div>
                <div className="text-xs text-zinc-500 capitalize">{user?.role?.replace(/_/g, ' ')}</div>
              </Link>
            </div>
            <div className="space-y-1">
              <Link to="/profile"
                className="flex items-center w-full px-3 py-2 text-sm rounded-sm text-zinc-600 hover:text-zinc-950 hover:bg-zinc-100">
                <User className="w-4 h-4 mr-2" strokeWidth={1.5} /> My Profile
              </Link>
              <Button onClick={logout} data-testid="logout-button" variant="ghost"
                className="w-full justify-start text-zinc-600 hover:text-zinc-950 hover:bg-zinc-100 rounded-sm">
                <LogOut className="w-4 h-4 mr-2" strokeWidth={1.5} /> Sign Out
              </Button>
            </div>
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
