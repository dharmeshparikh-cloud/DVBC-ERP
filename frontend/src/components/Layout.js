import React, { useContext, useState, useEffect, useCallback } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { AuthContext } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { useApprovals } from '../contexts/ApprovalContext';
import { usePermissions } from '../contexts/PermissionContext';
import { Button } from './ui/button';
import NotificationBell from './NotificationBell';
import GlobalSearch from './GlobalSearch';
import { sanitizeDisplayText } from '../utils/sanitize';
import ChangePasswordDialog from './ChangePasswordDialog';
import {
  LayoutDashboard, Users, Briefcase, Calendar, CalendarCheck, Mail, LogOut,
  DollarSign, FileText, FileCheck, ClipboardCheck, UserCog, AlertTriangle,
  User, Shield, UsersRound, Building2, Receipt, BarChart3, ChevronDown,
  GitBranch, CalendarDays, Wallet, Clock, Map, Star, GanttChartSquare, Download, Send, Inbox, Settings,
  Sun, Moon, TrendingUp, Car, BookOpen, Key, Menu, X, Home, UserCircle, Lock, Image, CreditCard, KeyRound,
  FileSignature, Search, Command
} from 'lucide-react';

// Legacy role-based access (kept for backward compatibility)
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
  const { permissions, level, canViewTeamData, canApproveRequests, canViewReports, canManageTeam, isManagerOrAbove, isLeader } = usePermissions();
  const location = useLocation();
  const role = user?.role;
  const isDark = theme === 'dark';
  
  // Department-based access state
  const [departmentAccess, setDepartmentAccess] = useState(null);
  
  // Fetch department access on mount
  useEffect(() => {
    const fetchDepartmentAccess = async () => {
      try {
        const API_URL = process.env.REACT_APP_BACKEND_URL;
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/api/department-access/my-access`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setDepartmentAccess(data);
        }
      } catch (error) {
        console.error('Error fetching department access:', error);
      }
    };
    
    if (user) {
      fetchDepartmentAccess();
    }
  }, [user]);
  
  // Department-based visibility (NEW - Primary method)
  const userDepartments = departmentAccess?.departments || [];
  const hasDepartment = (dept) => userDepartments.includes(dept) || userDepartments.includes('Admin') || role === 'admin';
  
  // NEW SIMPLIFIED PERMISSION FLAGS from API
  const hasReportees = departmentAccess?.has_reportees || false;
  const canManageTeamFlag = departmentAccess?.can_manage_team || false;
  const canEditFlag = departmentAccess?.can_edit !== false; // Default to true if not set
  const isViewOnly = departmentAccess?.is_view_only || false;
  
  // Combined visibility: Department-based OR has team (for approvals)
  const showHR = hasDepartment('HR') || HR_ROLES.includes(role) || hasReportees;
  const showSales = hasDepartment('Sales') || SALES_ROLES_NAV.includes(role);
  const showConsulting = hasDepartment('Consulting') || CONSULTING_ROLES_NAV.includes(role);
  const showFinance = hasDepartment('Finance');
  const showAdmin = hasDepartment('Admin') || ADMIN_ROLES.includes(role);
  const isConsultant = role === 'consultant';
  
  // Permission checks for specific features - now using has_reportees
  const canViewTeamWorkload = hasReportees || hasDepartment('HR') || role === 'admin';
  const canViewApprovals = hasReportees || hasDepartment('Admin') || role === 'admin';
  const canViewHRReports = hasDepartment('HR') || role === 'admin';

  // Mobile state
  const [isMobile, setIsMobile] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Global search state
  const [searchOpen, setSearchOpen] = useState(false);

  // Track which sections are expanded
  const [expanded, setExpanded] = useState({
    workspace: true, hr: true, sales: true, consulting: true, admin: true
  });

  // Change Password Dialog state
  const [showChangePassword, setShowChangePassword] = useState(false);

  // Global search keyboard shortcut (Ctrl+K or Cmd+K)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

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

  // Navigation items with permission requirements - SIMPLIFIED (only main pages)
  const hrItems = [
    { name: 'Employees', href: '/employees', icon: UsersRound, requiresTeamView: false },
    { name: 'Onboarding', href: '/onboarding', icon: UserCog, requiresTeamView: false },
    { name: 'Document Center', href: '/document-center', icon: FileSignature, requiresTeamView: false },
    { name: 'Leave & Attendance', href: '/leave-management', icon: CalendarDays, requiresApproval: true },
    { name: 'CTC & Payroll', href: '/ctc-designer', icon: Wallet, requiresApproval: true },
    { name: 'HR Reports', href: '/reports?category=hr', icon: BarChart3, requiresReports: true },
  ];
  
  // Filter HR items based on permissions
  const filteredHrItems = hrItems.filter(item => {
    // Password Management only for Admin or HR Managers
    if (item.requiresHRorAdmin) {
      return role === 'admin' || role === 'hr_manager' || HR_ROLES.includes(role);
    }
    // Always show basic HR items for HR roles
    if (HR_ROLES.includes(role)) return true;
    // For non-HR roles, check level permissions
    if (item.requiresTeamView && !canViewTeamData()) return false;
    if (item.requiresApproval && !canApproveRequests()) return false;
    if (item.requiresReports && !canViewReports()) return false;
    return true;
  });

  const salesFlowItems = [
    { name: 'Sales Dashboard', href: '/sales-dashboard', icon: BarChart3 },
    { name: 'Leads', href: '/leads', icon: Users },
    { name: 'SOW & Pricing', href: '/sow-pricing', icon: FileText },
    { name: 'Agreements', href: '/agreements', icon: FileCheck },
    { name: 'Payment Verification', href: '/sales-funnel/payment-verification', icon: CreditCard },
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
        { name: 'My Payments', href: '/payments', icon: DollarSign },
      ]
    : [
        { name: 'Projects', href: '/projects', icon: Briefcase },
        { name: 'Team Assignment', href: '/team-assignment', icon: Users },
        { name: 'Timesheets', href: '/timesheets', icon: Clock },
        { name: 'Payments', href: '/payments', icon: DollarSign },
        { name: 'Project Reports', href: '/reports?category=consulting', icon: BarChart3 },
      ];

  const adminItems = [
    { name: 'ERP Workflow', href: '/workflow', icon: Map },
    { name: 'Admin Masters', href: '/admin-masters', icon: Settings },
    { name: 'User Management', href: '/user-management', icon: UserCog },
    { name: 'Role Management', href: '/role-management', icon: Shield },
    { name: 'Dept Access Manager', href: '/department-access', icon: Building2 },
    { name: 'Permission Dashboard', href: '/permission-dashboard', icon: Users },
    { name: 'Permission Config', href: '/permission-manager', icon: Lock },
    { name: 'Approvals Center', href: '/approvals', icon: ClipboardCheck },
    { name: 'Project Payments', href: '/payments', icon: DollarSign },
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
            {expanded.hr && filteredHrItems.map(item => (
              <NavLink 
                key={item.name} 
                item={item} 
                badge={
                  item.name === 'Attendance Approvals' ? pendingCounts.attendance :
                  item.name === 'CTC Designer' ? pendingCounts.ctc : 0
                }
              />
            ))}
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
            {/* Global Search Button */}
            <button
              onClick={() => setSearchOpen(true)}
              data-testid="global-search-btn"
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-all duration-200 ${
                isDark 
                  ? 'bg-zinc-800 border-zinc-700 hover:border-zinc-600 text-zinc-400' 
                  : 'bg-zinc-50 border-zinc-200 hover:border-zinc-300 text-zinc-500'
              }`}
              title="Search (Ctrl+K)"
            >
              <Search className="w-4 h-4" />
              <span className="hidden md:inline text-sm">Search...</span>
              <kbd className="hidden md:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-mono bg-zinc-200 dark:bg-zinc-700 rounded">
                <Command className="w-3 h-3" />K
              </kbd>
            </button>
            
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
