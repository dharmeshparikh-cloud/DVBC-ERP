import React, { useContext, useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { AuthContext } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Button } from './ui/button';
import NotificationBell from './NotificationBell';
import { sanitizeDisplayText } from '../utils/sanitize';
import { SalesNavigationProvider } from '../context/SalesNavigationContext';
import QuickCheckInModal from './QuickCheckInModal';
import {
  LayoutDashboard, Users, LogOut, DollarSign, FileText, FileCheck, 
  Building2, Calendar, BarChart3, ChevronDown, Send, Clock,
  Umbrella, Receipt, CreditCard, Award, Sun, Moon, Key, Menu, X, Home, UserCircle, CheckCircle2
} from 'lucide-react';
import ChangePasswordDialog from './ChangePasswordDialog';

const SalesLayout = () => {
  const { user, logout } = useContext(AuthContext);
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const isDark = theme === 'dark';

  const [expanded, setExpanded] = useState({
    funnel: true, other: true, workspace: true
  });
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showQuickCheckIn, setShowQuickCheckIn] = useState(false);
  
  // Mobile state
  const [isMobile, setIsMobile] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Detect mobile
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (!mobile) {
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
            ? isDark
              ? 'bg-orange-500/20 text-orange-400 font-medium border border-orange-500/30'
              : 'bg-orange-50 text-orange-700 font-medium border border-orange-200' 
            : isDark
              ? 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
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
      className={`flex items-center justify-between w-full px-3 mb-1 mt-4 text-[11px] font-semibold uppercase tracking-wider transition-colors ${
        isDark ? 'text-zinc-500 hover:text-zinc-300' : 'text-zinc-400 hover:text-zinc-600'
      }`}
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
    { name: 'Team Performance', href: '/sales/team-performance', icon: Award },
  ];

  const workspaceItems = [
    { name: 'My Attendance', href: '/sales/my-attendance', icon: Clock },
    { name: 'My Leaves', href: '/sales/my-leaves', icon: Umbrella },
    { name: 'Salary Slips', href: '/sales/my-salary', icon: CreditCard },
    { name: 'My Expenses', href: '/sales/my-expenses', icon: Receipt },
    { name: 'My Bank Details', href: '/sales/my-bank-details', icon: Building2 },
  ];

  // Mobile bottom nav items
  const mobileNavItems = [
    { name: 'Home', href: '/sales', icon: Home },
    { name: 'Leads', href: '/sales/leads', icon: Users },
    { name: 'Attendance', href: '/sales/my-attendance', icon: Clock },
    { name: 'Profile', href: '/sales/profile', icon: UserCircle },
  ];

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo Header */}
      <div className={`px-5 py-5 border-b flex items-center justify-between ${
        isDark 
          ? 'border-zinc-800 bg-gradient-to-r from-orange-500/10 to-zinc-900' 
          : 'border-zinc-200 bg-gradient-to-r from-orange-50 to-white'
      }`}>
        <div className="flex items-center gap-3">
          <img
            src="https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png"
            alt="Logo" 
            className={`h-10 w-auto ${isDark ? 'brightness-0 invert' : ''}`}
          />
          <div>
            <div className={`text-base font-bold leading-tight ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>DVBC</div>
            <div className="text-[10px] font-semibold text-orange-500 uppercase tracking-wider">Sales Portal</div>
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

        {/* My Workspace */}
        <SectionHeader label="My Workspace" sectionKey="workspace" />
        {expanded.workspace && (
          <div className="space-y-0.5">
            {workspaceItems.map(item => <NavLink key={item.name} item={item} />)}
          </div>
        )}
      </nav>

      {/* User section */}
      <div className={`px-4 py-4 border-t ${isDark ? 'border-zinc-800 bg-zinc-900/50' : 'border-zinc-200 bg-zinc-50'}`}>
        <div className="flex items-center gap-3 mb-3">
          <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold ${
            isDark ? 'bg-orange-500/20 text-orange-400' : 'bg-orange-100 text-orange-700'
          }`}>
            {sanitizeDisplayText(user?.full_name)?.charAt(0) || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <div className={`text-sm font-medium truncate ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
              {sanitizeDisplayText(user?.full_name)}
            </div>
            <div className={`text-xs capitalize truncate ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>
              {user?.role?.replace(/_/g, ' ')}
            </div>
          </div>
        </div>
        <Button
          onClick={() => setShowChangePassword(true)}
          data-testid="sales-change-password-button"
          variant="outline"
          className={`w-full justify-center h-10 md:h-9 text-sm mb-2 ${
            isDark 
              ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 border-zinc-700' 
              : 'text-zinc-600 hover:text-zinc-900 hover:bg-white border-zinc-300'
          }`}
        >
          <Key className="w-4 h-4 mr-2" strokeWidth={1.5} /> Change Password
        </Button>
        <Button 
          onClick={handleLogout} 
          data-testid="sales-logout-button" 
          variant="outline"
          className={`w-full justify-center h-10 md:h-9 text-sm ${
            isDark 
              ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 border-zinc-700' 
              : 'text-zinc-600 hover:text-zinc-900 hover:bg-white border-zinc-300'
          }`}
        >
          <LogOut className="w-4 h-4 mr-2" strokeWidth={1.5} /> Sign Out
        </Button>
        <ChangePasswordDialog 
          open={showChangePassword} 
          onOpenChange={setShowChangePassword} 
        />
      </div>
    </div>
  );

  return (
    <div className={`flex min-h-screen transition-colors duration-200 ${isDark ? 'bg-zinc-950' : 'bg-zinc-50'}`}>
      {/* Desktop Sidebar */}
      <aside className={`hidden md:block w-64 border-r flex-shrink-0 h-screen sticky top-0 shadow-sm transition-colors duration-200 ${
        isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'
      }`} data-testid="sales-sidebar">
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

      {/* Main Content */}
      <main className="flex-1 flex flex-col pb-16 md:pb-0">
        {/* Header */}
        <div className={`flex items-center justify-between px-4 md:px-8 py-3 border-b sticky top-0 z-10 shadow-sm transition-colors duration-200 ${
          isDark ? 'border-zinc-800 bg-zinc-900' : 'border-zinc-200 bg-white'
        }`}>
          {/* Mobile Menu Button */}
          {isMobile && (
            <button
              onClick={() => setSidebarOpen(true)}
              data-testid="sales-mobile-menu-btn"
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
              <span className={`text-sm font-bold text-orange-500`}>Sales</span>
            </div>
          )}
          
          {!isMobile && (
            <div className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>
              Sales Management System
            </div>
          )}
          
          <div className="flex items-center gap-2 md:gap-3 ml-auto">
            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              data-testid="sales-theme-toggle"
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
        <div className={`flex-1 p-4 md:p-8 transition-colors duration-200 ${isDark ? 'bg-zinc-950' : 'bg-zinc-50'}`}>
          <SalesNavigationProvider>
            <Outlet />
          </SalesNavigationProvider>
        </div>
      </main>

      {/* Mobile Bottom Navigation */}
      {isMobile && (
        <nav className={`fixed bottom-0 left-0 right-0 border-t z-30 ${
          isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'
        }`}>
          <div className="flex justify-around items-center h-16 px-2">
            {/* Home */}
            <Link
              to="/sales"
              className={`flex flex-col items-center justify-center flex-1 py-2 ${
                isActive('/sales') 
                  ? 'text-orange-500' 
                  : isDark ? 'text-zinc-500' : 'text-zinc-400'
              }`}
            >
              <Home className="w-5 h-5" strokeWidth={isActive('/sales') ? 2 : 1.5} />
              <span className="text-[10px] mt-1 font-medium">Home</span>
            </Link>
            
            {/* Leads */}
            <Link
              to="/sales/leads"
              className={`flex flex-col items-center justify-center flex-1 py-2 ${
                isActive('/sales/leads') 
                  ? 'text-orange-500' 
                  : isDark ? 'text-zinc-500' : 'text-zinc-400'
              }`}
            >
              <Users className="w-5 h-5" strokeWidth={isActive('/sales/leads') ? 2 : 1.5} />
              <span className="text-[10px] mt-1 font-medium">Leads</span>
            </Link>
            
            {/* Quick Check-in - Center Button */}
            <button
              onClick={() => setShowQuickCheckIn(true)}
              className="flex flex-col items-center justify-center -mt-6"
              data-testid="mobile-quick-checkin-btn"
            >
              <div className="w-14 h-14 rounded-full bg-orange-500 flex items-center justify-center shadow-lg border-4 border-white dark:border-zinc-900">
                <CheckCircle2 className="w-7 h-7 text-white" strokeWidth={2} />
              </div>
              <span className="text-[10px] mt-1 font-medium text-orange-500">Check-in</span>
            </button>
            
            {/* Attendance */}
            <Link
              to="/sales/my-attendance"
              className={`flex flex-col items-center justify-center flex-1 py-2 ${
                isActive('/sales/my-attendance') 
                  ? 'text-orange-500' 
                  : isDark ? 'text-zinc-500' : 'text-zinc-400'
              }`}
            >
              <Clock className="w-5 h-5" strokeWidth={isActive('/sales/my-attendance') ? 2 : 1.5} />
              <span className="text-[10px] mt-1 font-medium">Attendance</span>
            </Link>
            
            {/* Profile */}
            <Link
              to="/sales/profile"
              className={`flex flex-col items-center justify-center flex-1 py-2 ${
                isActive('/sales/profile') 
                  ? 'text-orange-500' 
                  : isDark ? 'text-zinc-500' : 'text-zinc-400'
              }`}
            >
              <UserCircle className="w-5 h-5" strokeWidth={isActive('/sales/profile') ? 2 : 1.5} />
              <span className="text-[10px] mt-1 font-medium">Profile</span>
            </Link>
          </div>
        </nav>
      )}

      {/* Quick Check-in Modal */}
      <QuickCheckInModal 
        isOpen={showQuickCheckIn} 
        onClose={() => setShowQuickCheckIn(false)} 
        user={user} 
      />
    </div>
  );
};

export default SalesLayout;
