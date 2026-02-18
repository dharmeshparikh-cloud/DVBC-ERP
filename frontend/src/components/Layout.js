import React, { useContext, useState, useEffect } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { AuthContext } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { useApprovals } from '../contexts/ApprovalContext';
import { Button } from './ui/button';
import NotificationBell from './NotificationBell';
import { sanitizeDisplayText } from '../utils/sanitize';
import ChangePasswordDialog from './ChangePasswordDialog';
import {
  LayoutDashboard, Users, Briefcase, Calendar, CalendarCheck, Mail, LogOut,
  DollarSign, FileText, FileCheck, ClipboardCheck, UserCog, AlertTriangle,
  User, Shield, UsersRound, Building2, Receipt, BarChart3, ChevronDown,
  GitBranch, CalendarDays, Wallet, Clock, Map, Star, GanttChartSquare, Download, Send, Inbox, Settings,
  Sun, Moon, TrendingUp, Car, BookOpen, Key, Menu, X, Home, UserCircle
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
  const { pendingCounts } = useApprovals();
  const location = useLocation();
  const role = user?.role;
  const isDark = theme === 'dark';

  const showHR = HR_ROLES.includes(role);
  const showSales = SALES_ROLES_NAV.includes(role);
  const showConsulting = CONSULTING_ROLES_NAV.includes(role);
  const showAdmin = ADMIN_ROLES.includes(role);
  const isConsultant = role === 'consultant';

  // Mobile state
  const [isMobile, setIsMobile] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Track which sections are expanded
  const [expanded, setExpanded] = useState({
    workspace: true, hr: true, sales: true, consulting: true, admin: true
  });

  // Change Password Dialog state
  const [showChangePassword, setShowChangePassword] = useState(false);

  // Detect mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth >= 768) {
        setSidebarOpen(false);
      }
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Close sidebar on navigation (mobile)
  useEffect(() => {
    if (isMobile) {
      setSidebarOpen(false);
    }
  }, [location.pathname, isMobile]);

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

  const NavLink = ({ item, badge }) => {
    const Icon = item.icon;
    const active = isActive(item.href);
    return (
      <Link
        to={item.href}
        data-testid={`nav-${item.name.toLowerCase().replace(/\s+/g, '-')}`}
        className={`flex items-center gap-2.5 px-3 py-2 md:py-1.5 rounded-md md:rounded-sm text-sm md:text-[13px] transition-colors ${
          active 
            ? isDark 
              ? 'bg-zinc-800 text-zinc-100 font-medium' 
              : 'bg-zinc-100 text-zinc-950 font-medium' 
            : isDark 
              ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50' 
              : 'text-zinc-600 hover:text-zinc-950 hover:bg-zinc-50'
        }`}
      >
        <Icon className="w-4 h-4 md:w-3.5 md:h-3.5 flex-shrink-0" strokeWidth={1.5} />
        <span className="truncate flex-1">{item.name}</span>
        {badge > 0 && (
          <span className="ml-auto flex-shrink-0 bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center animate-pulse">
            {badge > 99 ? '99+' : badge}
          </span>
        )}
      </Link>
    );
  };

  const SectionHeader = ({ label, sectionKey }) => (
    <button
      onClick={() => toggle(sectionKey)}
      className={`w-full flex items-center justify-between px-3 py-2 mt-3 mb-1 text-[10px] md:text-[10px] font-semibold uppercase tracking-wider rounded-sm transition-colors ${
        isDark ? 'text-zinc-500 hover:text-zinc-300' : 'text-zinc-400 hover:text-zinc-600'
      }`}
    >
      <span>{label}</span>
      <ChevronDown className={`w-3 h-3 transition-transform ${expanded[sectionKey] ? '' : '-rotate-90'}`} />
    </button>
  );

  // Navigation items
  const hrItems = [
    { name: 'Employees', href: '/employees', icon: UsersRound },
    { name: 'Onboarding', href: '/onboarding', icon: UserCog },
    { name: 'Onboarding Tutorials', href: '/tutorials', icon: BookOpen },
    { name: 'Org Chart', href: '/org-chart', icon: GitBranch },
    { name: 'Leave Mgmt', href: '/leave-management', icon: CalendarDays },
    { name: 'Attendance', href: '/attendance', icon: Clock },
    { name: 'Attendance Approvals', href: '/attendance-approvals', icon: ClipboardCheck },
    { name: 'CTC Designer', href: '/ctc-designer', icon: DollarSign },
    { name: 'Payroll', href: '/payroll', icon: Wallet },
    { name: 'Expenses', href: '/expenses', icon: Receipt },
    { name: 'Travel Reimbursement', href: '/travel-reimbursement', icon: Car },
    { name: 'Team Workload', href: '/team-workload', icon: Briefcase },
    { name: 'Staffing Requests', href: '/staffing-requests', icon: AlertTriangle },
    { name: 'Performance', href: '/performance-dashboard', icon: TrendingUp },
    { name: 'HR Reports', href: '/reports?category=hr', icon: BarChart3 },
  ];

  const salesFlowItems = [
    { name: 'Sales Dashboard', href: '/sales-dashboard', icon: BarChart3 },
    { name: 'Leads', href: '/leads', icon: Users },
    { name: 'SOW & Pricing', href: '/sow-pricing', icon: FileText },
    { name: 'Agreements', href: '/agreements', icon: FileCheck },
    { name: 'Clients', href: '/clients', icon: Building2 },
    { name: 'Invoices', href: '/invoices', icon: Receipt },
    { name: 'Sales Reports', href: '/reports?category=sales', icon: BarChart3 },
  ];

  const salesOtherItems = [
    { name: 'Calendar', href: '/calendar', icon: Calendar },
    { name: 'Mailbox', href: '/mailbox', icon: Mail },
    { name: 'Follow-ups', href: '/follow-ups', icon: CalendarCheck },
  ];

  const consultingItems = isConsultant
    ? [
        { name: 'My Schedule', href: '/my-schedule', icon: Calendar },
        { name: 'Timesheets', href: '/timesheets', icon: Clock },
        { name: 'My Clients', href: '/my-clients', icon: Building2 },
      ]
    : [
        { name: 'Projects', href: '/projects', icon: Briefcase },
        { name: 'Team Assignment', href: '/team-assignment', icon: Users },
        { name: 'Timesheets', href: '/timesheets', icon: Clock },
        { name: 'Project Reports', href: '/reports?category=consulting', icon: BarChart3 },
      ];

  const adminItems = [
    { name: 'ERP Workflow', href: '/workflow', icon: Map },
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
    { name: 'My Bank Details', href: '/my-bank-details', icon: Building2 },
    { name: 'Mobile App', href: '/mobile-app', icon: Download },
  ];

  // Mobile bottom nav items
  const mobileNavItems = [
    { name: 'Home', href: '/', icon: Home },
    { name: 'Attendance', href: '/my-attendance', icon: Clock },
    { name: 'Leaves', href: '/my-leaves', icon: Calendar },
    { name: 'Profile', href: '/profile', icon: UserCircle },
  ];

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className={`px-4 md:px-5 py-4 border-b flex items-center justify-between ${isDark ? 'border-zinc-800' : 'border-zinc-200'}`}>
        <div className="flex items-center gap-3">
          <img
            src="https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png"
            alt="Logo" 
            className={`h-8 md:h-9 w-auto ${isDark ? 'brightness-0 invert' : ''}`}
          />
          <div>
            <div className={`text-sm font-bold leading-none ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>DVBC - NETRA</div>
          </div>
        </div>
        {/* Close button on mobile */}
        {isMobile && (
          <button
            onClick={() => setSidebarOpen(false)}
            className={`p-2 rounded-lg ${isDark ? 'hover:bg-zinc-800 text-zinc-400' : 'hover:bg-zinc-100 text-zinc-600'}`}
          >
            <X className="w-5 h-5" />
          </button>
        )}
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
            {expanded.admin && adminItems.map(item => (
              <NavLink 
                key={item.name} 
                item={item} 
                badge={item.name === 'Approvals Center' ? pendingCounts.total : 0}
              />
            ))}
          </>
        )}
      </nav>

      {/* User section */}
      <div className={`px-3 py-3 border-t ${isDark ? 'border-zinc-800' : 'border-zinc-200'}`}>
        <Link to="/profile" className={`flex items-center gap-2 rounded-md md:rounded-sm px-2 py-2 md:py-1.5 -mx-1 ${
          isDark ? 'hover:bg-zinc-800' : 'hover:bg-zinc-50'
        }`}>
          <div className={`w-8 h-8 md:w-7 md:h-7 rounded-full flex items-center justify-center text-sm md:text-xs font-medium ${
            isDark ? 'bg-zinc-700 text-zinc-200' : 'bg-zinc-200 text-zinc-700'
          }`}>
            {sanitizeDisplayText(user?.full_name)?.charAt(0) || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <div className={`text-sm md:text-xs font-medium truncate ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
              {sanitizeDisplayText(user?.full_name)}
            </div>
            <div className={`text-xs md:text-[10px] capitalize truncate ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>
              {user?.role?.replace(/_/g, ' ')}
            </div>
          </div>
        </Link>
        <Button 
          onClick={() => setShowChangePassword(true)} 
          data-testid="change-password-button" 
          variant="ghost" 
          size="sm"
          className={`w-full justify-start rounded-md md:rounded-sm mt-1 h-10 md:h-8 text-sm md:text-xs ${
            isDark 
              ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800' 
              : 'text-zinc-500 hover:text-zinc-950 hover:bg-zinc-100'
          }`}>
          <Key className="w-4 h-4 md:w-3.5 md:h-3.5 mr-2" strokeWidth={1.5} /> Change Password
        </Button>
        <Button onClick={logout} data-testid="logout-button" variant="ghost" size="sm"
          className={`w-full justify-start rounded-md md:rounded-sm mt-1 h-10 md:h-8 text-sm md:text-xs ${
            isDark 
              ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800' 
              : 'text-zinc-500 hover:text-zinc-950 hover:bg-zinc-100'
          }`}>
          <LogOut className="w-4 h-4 md:w-3.5 md:h-3.5 mr-2" strokeWidth={1.5} /> Sign Out
        </Button>
        
        {/* Change Password Dialog */}
        <ChangePasswordDialog 
          open={showChangePassword} 
          onOpenChange={setShowChangePassword} 
        />
      </div>
    </div>
  );

  return (
    <div className={`flex min-h-screen transition-colors duration-200 ${isDark ? 'bg-zinc-950' : 'bg-white'}`}>
      {/* Desktop Sidebar */}
      <aside className={`hidden md:block w-60 border-r flex-shrink-0 h-screen sticky top-0 transition-colors duration-200 ${
        isDark ? 'border-zinc-800 bg-zinc-900' : 'border-zinc-200 bg-white'
      }`} data-testid="sidebar">
        <SidebarContent />
      </aside>

      {/* Mobile Sidebar Overlay */}
      {isMobile && sidebarOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setSidebarOpen(false)}
          />
          {/* Sidebar */}
          <aside className={`fixed left-0 top-0 w-72 h-full z-50 transition-colors duration-200 ${
            isDark ? 'bg-zinc-900' : 'bg-white'
          }`}>
            <SidebarContent />
          </aside>
        </>
      )}

      <main className="flex-1 flex flex-col pb-16 md:pb-0">
        {/* Header */}
        <div className={`flex items-center justify-between px-4 md:px-8 py-3 border-b sticky top-0 z-10 transition-colors duration-200 ${
          isDark ? 'border-zinc-800 bg-zinc-900' : 'border-zinc-100 bg-white'
        }`}>
          {/* Mobile Menu Button */}
          {isMobile && (
            <button
              onClick={() => setSidebarOpen(true)}
              data-testid="mobile-menu-btn"
              className={`p-2 rounded-lg ${isDark ? 'hover:bg-zinc-800 text-zinc-400' : 'hover:bg-zinc-100 text-zinc-600'}`}
            >
              <Menu className="w-5 h-5" />
            </button>
          )}
          
          {/* Mobile Logo */}
          {isMobile && (
            <div className="flex items-center gap-2">
              <img
                src="https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png"
                alt="Logo" 
                className={`h-6 w-auto ${isDark ? 'brightness-0 invert' : ''}`}
              />
              <span className={`text-sm font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>DVBC</span>
            </div>
          )}

          <div className="flex items-center gap-2 md:gap-3 ml-auto">
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
        </div>

        {/* Main Content */}
        <div className={`flex-1 p-4 md:p-8 transition-colors duration-200 ${isDark ? 'bg-zinc-950' : 'bg-zinc-50'}`}>
          <Outlet />
        </div>
      </main>

      {/* Mobile Bottom Navigation */}
      {isMobile && (
        <nav className={`fixed bottom-0 left-0 right-0 border-t z-30 ${
          isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'
        }`}>
          <div className="flex justify-around items-center h-16 px-2">
            {mobileNavItems.map(item => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex flex-col items-center justify-center flex-1 py-2 ${
                    active 
                      ? 'text-emerald-600' 
                      : isDark ? 'text-zinc-500' : 'text-zinc-400'
                  }`}
                >
                  <Icon className="w-5 h-5" strokeWidth={active ? 2 : 1.5} />
                  <span className="text-[10px] mt-1 font-medium">{item.name}</span>
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </div>
  );
};

export default Layout;
