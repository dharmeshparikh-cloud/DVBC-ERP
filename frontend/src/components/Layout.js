import React, { useContext, useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { AuthContext } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Button } from './ui/button';
import NotificationBell from './NotificationBell';
import { sanitizeDisplayText } from '../utils/sanitize';
import {
  LayoutDashboard, Users, Briefcase, Calendar, CalendarCheck, Mail, LogOut,
  DollarSign, FileText, FileCheck, ClipboardCheck, UserCog, AlertTriangle,
  User, Shield, UsersRound, Building2, Receipt, BarChart3, ChevronDown,
  GitBranch, CalendarDays, Wallet, Clock, Map, Star, GanttChartSquare, Download, Send, Inbox, Settings,
  Sun, Moon
} from 'lucide-react';

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
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const role = user?.role;
  const isDark = theme === 'dark';

  const showHR = HR_ROLES.includes(role);
  const showSales = SALES_ROLES_NAV.includes(role);
  const showConsulting = CONSULTING_ROLES_NAV.includes(role);
  const showAdmin = ADMIN_ROLES.includes(role);
  const isConsultant = role === 'consultant';

  // Track which sections are expanded - all open by default
  const [expanded, setExpanded] = useState({
    workspace: true, hr: true, sales: true, consulting: true, admin: true
  });

  const toggle = (key) => setExpanded(prev => ({ ...prev, [key]: !prev[key] }));

  const isActive = (href) => {
    if (href === '/') return location.pathname === '/';
    const [path] = href.split('?');
    if (location.pathname.startsWith(path) && path !== '/') {
      if (href.includes('?')) {
        return location.pathname.startsWith(path) && location.search.includes(href.split('?')[1]);
      }
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
        data-testid={`nav-${item.name.toLowerCase().replace(/\s+/g, '-')}`}
        className={`flex items-center gap-2.5 px-3 py-1.5 rounded-sm text-[13px] transition-colors ${
          active 
            ? isDark 
              ? 'bg-zinc-800 text-zinc-100 font-medium' 
              : 'bg-zinc-100 text-zinc-950 font-medium' 
            : isDark 
              ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50' 
              : 'text-zinc-600 hover:text-zinc-950 hover:bg-zinc-50'
        }`}
      >
        <Icon className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.5} />
        <span className="truncate">{item.name}</span>
      </Link>
    );
  };

  const SectionHeader = ({ label, sectionKey }) => (
    <button
      onClick={() => toggle(sectionKey)}
      className={`flex items-center justify-between w-full px-3 mb-0.5 mt-3 text-[10px] font-semibold uppercase tracking-widest transition-colors ${
        isDark ? 'text-zinc-500 hover:text-zinc-300' : 'text-zinc-400 hover:text-zinc-600'
      }`}
      data-testid={`section-${sectionKey}`}
    >
      {label}
      <ChevronDown className={`w-3 h-3 transition-transform ${expanded[sectionKey] ? '' : '-rotate-90'}`} />
    </button>
  );

  const salesFlowItems = [
    { name: 'Leads', href: '/leads', icon: Users },
    { name: 'Pricing Plans', href: '/sales-funnel/pricing-plans', icon: DollarSign },
    { name: 'SOW List', href: '/sales-funnel/sow-list', icon: FileText },
    { name: 'Proforma Invoice', href: '/sales-funnel/proforma-invoice', icon: FileText },
    { name: 'Agreements', href: '/sales-funnel/agreements', icon: FileCheck },
    { name: 'Kickoff Requests', href: '/kickoff-requests', icon: Send },
  ];

  const salesOtherItems = [
    { name: 'My Clients', href: '/clients', icon: Building2 },
    { name: 'Sales Meetings', href: '/sales-meetings', icon: Calendar },
    { name: 'Sales Reports', href: '/reports?category=sales', icon: BarChart3 },
  ];

  const hrItems = [
    { name: 'Employees', href: '/employees', icon: UsersRound },
    { name: 'Org Chart', href: '/org-chart', icon: GitBranch },
    { name: 'Leave Mgmt', href: '/leave-management', icon: CalendarDays },
    { name: 'Attendance', href: '/attendance', icon: Clock },
    { name: 'Payroll', href: '/payroll', icon: Wallet },
    { name: 'Expenses', href: '/expenses', icon: Receipt },
    { name: 'Team Workload', href: '/team-workload', icon: Briefcase },
    { name: 'Staffing Requests', href: '/staffing-requests', icon: AlertTriangle },
    { name: 'Performance', href: '/performance-dashboard', icon: TrendingUp },
    { name: 'HR Reports', href: '/reports?category=hr', icon: BarChart3 },
  ];

  const consultingItems = isConsultant
    ? [
        { name: 'My Projects', href: '/consulting/my-projects', icon: Briefcase },
        { name: 'SOW Changes', href: '/consulting/sow-changes', icon: FileText },
        { name: 'Payment Schedule', href: '/consulting/payments', icon: DollarSign },
        { name: 'Projects', href: '/projects', icon: Briefcase },
        { name: 'Project Roadmap', href: '/project-roadmap', icon: Map },
        { name: 'Gantt Chart', href: '/gantt-chart', icon: GanttChartSquare },
        { name: 'Meetings', href: '/consulting-meetings', icon: CalendarCheck },
      ]
    : [
        { name: 'My Projects', href: '/consulting/my-projects', icon: Briefcase },
        { name: 'SOW Changes', href: '/consulting/sow-changes', icon: FileText },
        { name: 'Kickoff Inbox', href: '/kickoff-requests', icon: Inbox },
        { name: 'Payment Reminders', href: '/consulting/payments', icon: DollarSign },
        { name: 'Projects', href: '/projects', icon: Briefcase },
        { name: 'Project Roadmap', href: '/project-roadmap', icon: Map },
        { name: 'Gantt Chart', href: '/gantt-chart', icon: GanttChartSquare },
        { name: 'Meetings', href: '/consulting-meetings', icon: CalendarCheck },
        { name: 'Performance', href: '/consultant-performance', icon: Star },
        { name: 'Consultants', href: '/consultants', icon: UserCog },
        { name: 'Handover Alerts', href: '/handover-alerts', icon: AlertTriangle },
        { name: 'Reports', href: '/reports?category=operations', icon: BarChart3 },
      ];

  const adminItems = [
    { name: 'User Management', href: '/user-management', icon: Shield },
    { name: 'Permission Manager', href: '/permission-manager', icon: UserCog },
    { name: 'Admin Masters', href: '/admin-masters', icon: Settings },
    { name: 'Approvals Center', href: '/approvals', icon: ClipboardCheck },
    { name: 'Email Templates', href: '/email-templates', icon: Mail },
    { name: 'Security Audit', href: '/security-audit', icon: Shield },
    { name: 'Downloads', href: '/downloads', icon: Download },
  ];

  const workspaceItems = [
    { name: 'My Attendance', href: '/my-attendance', icon: CalendarDays },
    { name: 'My Leaves', href: '/my-leaves', icon: Calendar },
    { name: 'My Salary Slips', href: '/my-salary-slips', icon: Wallet },
    { name: 'My Expenses', href: '/my-expenses', icon: Receipt },
  ];

  return (
    <div className={`flex min-h-screen transition-colors duration-200 ${isDark ? 'bg-zinc-950' : 'bg-white'}`}>
      <aside className={`w-60 border-r flex-shrink-0 h-screen sticky top-0 transition-colors duration-200 ${
        isDark ? 'border-zinc-800 bg-zinc-900' : 'border-zinc-200 bg-white'
      }`} data-testid="sidebar">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className={`px-5 py-4 border-b flex items-center gap-3 ${isDark ? 'border-zinc-800' : 'border-zinc-200'}`}>
            <img
              src="https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png"
              alt="Logo" 
              className={`h-9 w-auto ${isDark ? 'brightness-0 invert' : ''}`}
            />
            <div>
              <div className={`text-sm font-bold leading-none ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>DVBC - NETRA</div>
            </div>
          </div>

          {/* Scrollable Navigation */}
          <nav className="flex-1 px-2 py-1.5 overflow-y-auto scrollbar-thin" data-testid="nav-container">
            <NavLink item={{ name: isConsultant ? 'My Dashboard' : 'Dashboard', href: '/', icon: LayoutDashboard }} />

            {/* MY WORKSPACE */}
            <SectionHeader label="My Workspace" sectionKey="workspace" />
            {expanded.workspace && workspaceItems.map(item => <NavLink key={item.name} item={item} />)}

            {/* HR */}
            {showHR && (
              <>
                <SectionHeader label="HR" sectionKey="hr" />
                {expanded.hr && hrItems.map(item => <NavLink key={item.name} item={item} />)}
              </>
            )}

            {/* SALES */}
            {showSales && (
              <>
                <SectionHeader label="Sales" sectionKey="sales" />
                {expanded.sales && (
                  <>
                    {salesFlowItems.map(item => <NavLink key={item.name} item={item} />)}
                    <div className={`my-0.5 mx-3 border-t ${isDark ? 'border-zinc-800' : 'border-zinc-100'}`} />
                    {salesOtherItems.map(item => <NavLink key={item.name} item={item} />)}
                  </>
                )}
              </>
            )}

            {/* CONSULTING */}
            {showConsulting && (
              <>
                <SectionHeader label="Consulting" sectionKey="consulting" />
                {expanded.consulting && consultingItems.map(item => <NavLink key={item.name} item={item} />)}
              </>
            )}

            {/* ADMIN */}
            {showAdmin && (
              <>
                <SectionHeader label="Admin" sectionKey="admin" />
                {expanded.admin && adminItems.map(item => <NavLink key={item.name} item={item} />)}
              </>
            )}
          </nav>

          {/* User section */}
          <div className={`px-3 py-3 border-t ${isDark ? 'border-zinc-800' : 'border-zinc-200'}`}>
            <Link to="/profile" className={`flex items-center gap-2 rounded-sm px-2 py-1.5 -mx-1 ${
              isDark ? 'hover:bg-zinc-800' : 'hover:bg-zinc-50'
            }`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium ${
                isDark ? 'bg-zinc-700 text-zinc-200' : 'bg-zinc-200 text-zinc-700'
              }`}>
                {sanitizeDisplayText(user?.full_name)?.charAt(0) || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <div className={`text-xs font-medium truncate ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                  {sanitizeDisplayText(user?.full_name)}
                </div>
                <div className={`text-[10px] capitalize truncate ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>
                  {user?.role?.replace(/_/g, ' ')}
                </div>
              </div>
            </Link>
            <Button onClick={logout} data-testid="logout-button" variant="ghost" size="sm"
              className={`w-full justify-start rounded-sm mt-1 h-8 text-xs ${
                isDark 
                  ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800' 
                  : 'text-zinc-500 hover:text-zinc-950 hover:bg-zinc-100'
              }`}>
              <LogOut className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> Sign Out
            </Button>
          </div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col">
        <div className={`flex items-center justify-end gap-3 px-8 py-3 border-b sticky top-0 z-10 transition-colors duration-200 ${
          isDark ? 'border-zinc-800 bg-zinc-900' : 'border-zinc-100 bg-white'
        }`}>
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            data-testid="theme-toggle"
            className={`p-2 rounded-lg transition-all duration-200 ${
              isDark 
                ? 'bg-zinc-800 hover:bg-zinc-700 text-amber-400' 
                : 'bg-zinc-100 hover:bg-zinc-200 text-zinc-600'
            }`}
            title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <NotificationBell />
        </div>
        <div className={`flex-1 p-8 transition-colors duration-200 ${isDark ? 'bg-zinc-950' : 'bg-zinc-50'}`}>
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
