import React, { useState, useContext, useEffect } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import { AuthContext } from '../App';
import NotificationBell from './NotificationBell';
import { useTheme } from '../contexts/ThemeContext';
import { 
  LayoutDashboard, Users, UsersRound, GitBranch, CalendarDays, 
  Clock, Wallet, Receipt, BarChart3, FileText, ChevronDown, ChevronRight,
  LogOut, Menu, X, Sun, Moon, UserPlus, ClipboardCheck, Briefcase,
  AlertCircle, Bell, Key, Home, Calendar, UserCircle
} from 'lucide-react';
import { Button } from './ui/button';
import ChangePasswordDialog from './ChangePasswordDialog';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png";

const HRLayout = () => {
  const { user, logout } = useContext(AuthContext);
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [expanded, setExpanded] = useState({
    employees: true,
    operations: true,
    teamView: user?.role === 'hr_manager',
    selfService: true
  });
  const [showChangePassword, setShowChangePassword] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  const isHRManager = user?.role === 'hr_manager';
  const isHRExecutive = user?.role === 'hr_executive';

  // Detect mobile
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (!mobile) {
        setSidebarOpen(true);
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

  const handleLogout = () => {
    logout();
    navigate('/hr/login');
  };

  const toggleSection = (section) => {
    setExpanded(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const isActive = (href) => {
    if (href === '/hr') return location.pathname === '/hr';
    return location.pathname.startsWith(href);
  };

  const NavLink = ({ item }) => {
    const active = isActive(item.href);
    const Icon = item.icon;
    return (
      <Link
        to={item.href}
        className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
          active 
            ? 'bg-emerald-100 text-emerald-700 font-medium dark:bg-emerald-900/30 dark:text-emerald-400' 
            : 'text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800'
        }`}
        data-testid={`hr-nav-${item.name.toLowerCase().replace(/\s+/g, '-')}`}
      >
        <Icon className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} />
        <span className="truncate">{item.name}</span>
        {item.badge && (
          <span className="ml-auto bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
            {item.badge}
          </span>
        )}
      </Link>
    );
  };

  const SectionHeader = ({ title, section, icon: Icon }) => (
    <button
      onClick={() => toggleSection(section)}
      className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-zinc-400 uppercase tracking-wider hover:text-zinc-600 dark:hover:text-zinc-300"
    >
      <span className="flex items-center gap-2">
        <Icon className="w-3.5 h-3.5" />
        {title}
      </span>
      {expanded[section] ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
    </button>
  );

  // Employee Management Section
  const employeeItems = [
    { name: 'All Employees', href: '/hr/employees', icon: UsersRound },
    { name: 'Onboarding', href: '/hr/onboarding', icon: UserPlus },
    { name: 'Org Chart', href: '/hr/org-chart', icon: GitBranch },
  ];

  // HR Operations Section
  const operationsItems = [
    { name: 'Leave Management', href: '/hr/leave-management', icon: CalendarDays },
    { name: 'Attendance', href: '/hr/attendance', icon: Clock },
    { name: 'CTC Designer', href: '/hr/ctc-designer', icon: Wallet },
    { name: 'Payroll', href: '/hr/payroll', icon: Wallet },
    { name: 'Expenses', href: '/hr/expenses', icon: Receipt },
    { name: 'Approvals', href: '/hr/approvals', icon: ClipboardCheck },
  ];

  // Team View Section - HR Manager Only (Consulting visibility)
  const teamViewItems = [
    { name: 'Team Workload', href: '/hr/team-workload', icon: Briefcase },
    { name: 'Staffing Requests', href: '/hr/staffing-requests', icon: AlertCircle },
    { name: 'Performance Dashboard', href: '/hr/performance-dashboard', icon: BarChart3 },
    { name: 'Attendance Approvals', href: '/hr/attendance-approvals', icon: ClipboardCheck },
  ];

  // Self Service Section
  const selfServiceItems = [
    { name: 'My Attendance', href: '/hr/my-attendance', icon: Clock },
    { name: 'My Leaves', href: '/hr/my-leaves', icon: CalendarDays },
    { name: 'My Salary Slips', href: '/hr/my-salary', icon: FileText },
    { name: 'My Expenses', href: '/hr/my-expenses', icon: Receipt },
    { name: 'My Bank Details', href: '/hr/my-bank-details', icon: Building2 },
  ];

  // Mobile bottom nav items
  const mobileNavItems = [
    { name: 'Home', href: '/hr', icon: Home },
    { name: 'Attendance', href: '/hr/my-attendance', icon: Clock },
    { name: 'Leaves', href: '/hr/my-leaves', icon: Calendar },
    { name: 'Profile', href: '/hr/profile', icon: UserCircle },
  ];

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900 flex" data-testid="hr-layout">
      {/* Mobile Sidebar Overlay */}
      {isMobile && sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        ${isMobile 
          ? `fixed left-0 top-0 h-full z-50 w-72 transform transition-transform duration-300 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`
          : 'w-56 h-screen sticky top-0'
        } 
        bg-white dark:bg-zinc-950 border-r border-zinc-200 dark:border-zinc-800 flex flex-col
      `}>
        {/* Logo */}
        <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
          <Link to="/hr" className="flex items-center gap-2">
            <img 
              src={LOGO_URL} 
              alt="Logo" 
              className={`h-8 object-contain ${isDark ? 'invert' : ''}`}
            />
            <div className="flex flex-col">
              <span className="text-xs font-bold text-emerald-600">HR PORTAL</span>
            </div>
          </Link>
          {isMobile && (
            <button
              onClick={() => setSidebarOpen(false)}
              className={`p-2 rounded-lg ${isDark ? 'hover:bg-zinc-800 text-zinc-400' : 'hover:bg-zinc-100 text-zinc-600'}`}
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {/* Dashboard */}
          <NavLink item={{ name: 'Dashboard', href: '/hr', icon: LayoutDashboard }} />

          {/* Employee Management */}
          <div className="pt-4">
            <SectionHeader title="People" section="employees" icon={Users} />
            {expanded.employees && (
              <div className="mt-1 space-y-0.5">
                {employeeItems.map(item => <NavLink key={item.name} item={item} />)}
              </div>
            )}
          </div>

          {/* HR Operations */}
          <div className="pt-4">
            <SectionHeader title="Operations" section="operations" icon={ClipboardCheck} />
            {expanded.operations && (
              <div className="mt-1 space-y-0.5">
                {operationsItems.map(item => <NavLink key={item.name} item={item} />)}
              </div>
            )}
          </div>

          {/* Team View - HR Manager Only */}
          {isHRManager && (
            <div className="pt-4">
              <SectionHeader title="Team View" section="teamView" icon={Briefcase} />
              {expanded.teamView && (
                <div className="mt-1 space-y-0.5">
                  {teamViewItems.map(item => <NavLink key={item.name} item={item} />)}
                </div>
              )}
            </div>
          )}

          {/* Self Service */}
          <div className="pt-4">
            <SectionHeader title="Self Service" section="selfService" icon={FileText} />
            {expanded.selfService && (
              <div className="mt-1 space-y-0.5">
                {selfServiceItems.map(item => <NavLink key={item.name} item={item} />)}
              </div>
            )}
          </div>

          {/* Reports */}
          <div className="pt-4">
            <NavLink item={{ name: 'HR Reports', href: '/hr/reports', icon: BarChart3 }} />
          </div>
        </nav>

        {/* User Section */}
        <div className="p-3 border-t border-zinc-200 dark:border-zinc-800">
          <>
            <div className="flex items-center gap-2 px-2 py-1.5">
                <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-900 flex items-center justify-center">
                  <span className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
                    {user?.full_name?.charAt(0) || 'H'}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
                    {user?.full_name}
                  </p>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 capitalize">
                    {user?.role?.replace('_', ' ')}
                  </p>
                </div>
              </div>
              <Button
                onClick={() => setShowChangePassword(true)}
                data-testid="hr-change-password-button"
                variant="ghost"
                size="sm"
                className="w-full justify-start mt-1 h-8 text-xs text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-800"
              >
                <Key className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} /> Change Password
              </Button>
              <Button
                onClick={handleLogout}
                data-testid="hr-logout-button"
                variant="ghost"
                size="sm"
                className="w-full justify-start mt-1 h-10 md:h-8 text-sm md:text-xs text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-800"
              >
                <LogOut className="w-4 h-4 md:w-3.5 md:h-3.5 mr-2" strokeWidth={1.5} /> Sign Out
              </Button>
            </>
          <ChangePasswordDialog 
            open={showChangePassword} 
            onOpenChange={setShowChangePassword} 
          />
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 pb-16 md:pb-0">
        {/* Header */}
        <header className="bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800 px-4 md:px-6 py-3 flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center gap-3 md:gap-4">
            {/* Mobile menu button */}
            {isMobile && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSidebarOpen(true)}
                className="p-2"
              >
                <Menu className="w-5 h-5" />
              </Button>
            )}
            <div>
              <h1 className="text-base md:text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                HR Portal
              </h1>
              <p className="text-[10px] md:text-xs text-zinc-500 dark:text-zinc-400 hidden md:block">
                People Operations Management
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 md:gap-3">
            {/* Theme Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleTheme}
              className="p-2"
              data-testid="hr-theme-toggle"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </Button>

            {/* Notifications */}
            <NotificationBell />

            {/* Logout */}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-zinc-600 hover:text-red-600 dark:text-zinc-400"
              data-testid="hr-logout-btn"
            >
              <LogOut className="w-4 h-4 mr-2" />
              <span className="hidden md:inline">Logout</span>
            </Button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>

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

export default HRLayout;
