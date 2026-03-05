/**
 * ModernSidebar Component
 * 
 * A modern dual-panel sidebar with:
 * - Collapsed icon bar (70px)
 * - Expandable navigation panel (240px)
 * - Hover-based submenu popups when collapsed
 * - Profile dropdown menu
 * - Notification badge support
 * - Light/Dark mode support
 * 
 * This is a UI-only replacement - preserves all existing routes and permissions.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { useApprovals } from '../contexts/ApprovalContext';
import { sanitizeDisplayText } from '../utils/sanitize';
import {
  LayoutDashboard, Users, Briefcase, Calendar, CalendarCheck, Mail, LogOut,
  DollarSign, FileText, FileCheck, ClipboardCheck, UserCog, AlertTriangle,
  User, Shield, UsersRound, Building2, Receipt, BarChart3, ChevronDown,
  GitBranch, CalendarDays, Wallet, Clock, Map, Star, GanttChartSquare, Download, Send, Inbox, Settings,
  Sun, Moon, TrendingUp, Car, BookOpen, Key, Menu, X, Home, UserCircle, Lock, Image, CreditCard, KeyRound,
  FileSignature, Search, Command, Rocket, CheckCircle2, MessageCircle, Bot, MailCheck, Target, ArrowRight, Circle,
  HelpCircle, ArrowRightLeft, ChevronRight, Bell, MoreVertical, PanelLeftClose, PanelLeft
} from 'lucide-react';

// Icon mapping for menu sections
const SECTION_ICONS = {
  dashboard: LayoutDashboard,
  workspace: User,
  hr: UsersRound,
  sales: TrendingUp,
  consulting: Briefcase,
  admin: Settings,
  notifications: Bell,
  support: HelpCircle,
  settings: Settings,
};

const ModernSidebar = ({
  user,
  logout,
  onChangePassword,
  // Section visibility flags
  showHR,
  showSales,
  showConsulting,
  showAdmin,
  isConsultant,
  isManagerOrAbove,
  isGuidedSalesMode,
  // Navigation items
  workspaceItems,
  hrItems,
  salesItems,
  consultingItems,
  adminItems,
  // Pending counts for badges
  pendingCounts,
}) => {
  const { theme } = useTheme();
  const location = useLocation();
  const isDark = theme === 'dark';
  
  // Sidebar state
  const [isExpanded, setIsExpanded] = useState(true);
  const [hoveredSection, setHoveredSection] = useState(null);
  const [expandedSections, setExpandedSections] = useState({
    workspace: true,
    hr: true,
    sales: true,
    consulting: true,
    admin: true,
  });
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  
  // Refs for hover popup positioning
  const sidebarRef = useRef(null);
  const hoverTimeoutRef = useRef(null);
  const profileMenuRef = useRef(null);

  // Close profile menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (profileMenuRef.current && !profileMenuRef.current.contains(e.target)) {
        setShowProfileMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Check if a route is active
  const isActive = useCallback((href) => {
    if (href === '/') return location.pathname === '/';
    const [path] = href.split('?');
    if (location.pathname.startsWith(path) && path !== '/') {
      if (href.includes('?')) {
        return location.pathname.startsWith(path) && location.search.includes(href.split('?')[1]);
      }
      return true;
    }
    return false;
  }, [location.pathname, location.search]);

  // Handle section hover (for collapsed sidebar)
  const handleSectionHover = (sectionKey) => {
    if (!isExpanded) {
      clearTimeout(hoverTimeoutRef.current);
      setHoveredSection(sectionKey);
    }
  };

  const handleSectionLeave = () => {
    if (!isExpanded) {
      hoverTimeoutRef.current = setTimeout(() => {
        setHoveredSection(null);
      }, 150);
    }
  };

  // Toggle section expansion
  const toggleSection = (sectionKey) => {
    if (isExpanded) {
      setExpandedSections(prev => ({
        ...prev,
        [sectionKey]: !prev[sectionKey]
      }));
    }
  };

  // Build menu sections
  const menuSections = [
    {
      key: 'dashboard',
      label: 'Dashboard',
      icon: LayoutDashboard,
      items: [{ name: isConsultant ? 'My Dashboard' : 'Dashboard', href: '/', icon: LayoutDashboard }],
      show: true,
      single: true, // Single item, no submenu needed
    },
    {
      key: 'workspace',
      label: 'My Workspace',
      icon: User,
      items: workspaceItems,
      show: true,
    },
    {
      key: 'hr',
      label: 'HR',
      icon: UsersRound,
      items: hrItems,
      show: showHR,
    },
    {
      key: 'sales',
      label: isGuidedSalesMode ? 'My Sales' : 'Sales',
      icon: TrendingUp,
      items: salesItems,
      show: showSales,
    },
    {
      key: 'consulting',
      label: 'Consulting',
      icon: Briefcase,
      items: consultingItems,
      show: showConsulting,
    },
    {
      key: 'admin',
      label: 'Admin',
      icon: Settings,
      items: adminItems,
      show: showAdmin,
    },
  ];

  // Get badge count for a section
  const getSectionBadge = (sectionKey) => {
    if (sectionKey === 'admin') return pendingCounts?.total || 0;
    if (sectionKey === 'hr') return (pendingCounts?.attendance || 0) + (pendingCounts?.ctc || 0);
    return 0;
  };

  // Icon Bar Item Component
  const IconBarItem = ({ section }) => {
    const Icon = section.icon;
    const badge = getSectionBadge(section.key);
    const isCurrentSection = section.items?.some(item => isActive(item.href));
    
    return (
      <div
        className="relative"
        onMouseEnter={() => handleSectionHover(section.key)}
        onMouseLeave={handleSectionLeave}
      >
        {section.single ? (
          <Link
            to={section.items[0].href}
            className={`w-12 h-12 flex items-center justify-center rounded-xl transition-all duration-200 ${
              isActive(section.items[0].href)
                ? isDark 
                  ? 'bg-emerald-600 text-white' 
                  : 'bg-emerald-500 text-white'
                : isDark
                  ? 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100'
                  : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900'
            }`}
            data-testid={`icon-${section.key}`}
          >
            <Icon className="w-5 h-5" strokeWidth={1.5} />
          </Link>
        ) : (
          <button
            onClick={() => isExpanded && toggleSection(section.key)}
            className={`w-12 h-12 flex items-center justify-center rounded-xl transition-all duration-200 relative ${
              isCurrentSection || hoveredSection === section.key
                ? isDark 
                  ? 'bg-zinc-800 text-zinc-100' 
                  : 'bg-zinc-100 text-zinc-900'
                : isDark
                  ? 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100'
                  : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900'
            }`}
            data-testid={`icon-${section.key}`}
          >
            <Icon className="w-5 h-5" strokeWidth={1.5} />
            {badge > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-emerald-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                {badge > 9 ? '9+' : badge}
              </span>
            )}
          </button>
        )}
      </div>
    );
  };

  // Hover Popup for collapsed sidebar
  const HoverPopup = ({ section }) => {
    if (hoveredSection !== section.key || isExpanded || section.single) return null;
    
    return (
      <div 
        className={`absolute left-full ml-2 top-0 z-50 min-w-[200px] rounded-xl shadow-xl border transition-all duration-200 ${
          isDark 
            ? 'bg-zinc-900 border-zinc-800' 
            : 'bg-white border-zinc-200'
        }`}
        onMouseEnter={() => handleSectionHover(section.key)}
        onMouseLeave={handleSectionLeave}
      >
        <div className={`px-4 py-3 border-b ${isDark ? 'border-zinc-800' : 'border-zinc-100'}`}>
          <span className={`text-sm font-semibold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            {section.label}
          </span>
        </div>
        <div className="py-2 max-h-[400px] overflow-y-auto">
          {section.items?.map(item => (
            <Link
              key={item.name}
              to={item.href}
              className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                isActive(item.href)
                  ? isDark 
                    ? 'bg-zinc-800 text-emerald-400' 
                    : 'bg-emerald-50 text-emerald-600'
                  : isDark
                    ? 'text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100'
                    : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'
              }`}
            >
              {isActive(item.href) && (
                <span className={`w-1.5 h-1.5 rounded-full ${isDark ? 'bg-emerald-400' : 'bg-emerald-500'}`} />
              )}
              <span>{item.name}</span>
              <ChevronRight className="w-4 h-4 ml-auto opacity-50" />
            </Link>
          ))}
        </div>
      </div>
    );
  };

  // Expanded Panel Section Component
  const ExpandedSection = ({ section }) => {
    if (!section.show || section.single) return null;
    
    const Icon = section.icon;
    const isOpen = expandedSections[section.key];
    const badge = getSectionBadge(section.key);
    
    return (
      <div className="mb-1">
        <button
          onClick={() => toggleSection(section.key)}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
            isDark 
              ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50' 
              : 'text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50'
          }`}
        >
          <div className="flex items-center gap-2">
            <Icon className="w-4 h-4" strokeWidth={1.5} />
            <span className="font-medium">{section.label}</span>
          </div>
          <div className="flex items-center gap-2">
            {badge > 0 && (
              <span className="bg-emerald-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
                {badge}
              </span>
            )}
            <ChevronDown 
              className={`w-4 h-4 transition-transform duration-200 ${isOpen ? '' : '-rotate-90'}`} 
            />
          </div>
        </button>
        
        {isOpen && (
          <div className="ml-2 mt-1 space-y-0.5">
            {section.items?.map(item => {
              const ItemIcon = item.icon;
              const active = isActive(item.href);
              const itemBadge = item.name === 'Approvals Center' ? pendingCounts?.total :
                                item.name === 'Attendance Approvals' ? pendingCounts?.attendance :
                                item.name === 'CTC Designer' ? pendingCounts?.ctc : 0;
              
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  data-testid={`nav-${item.name.toLowerCase().replace(/\s+/g, '-')}`}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150 ${
                    active 
                      ? isDark 
                        ? 'bg-zinc-800 text-zinc-100 font-medium' 
                        : 'bg-zinc-100 text-zinc-900 font-medium' 
                      : isDark 
                        ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50' 
                        : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
                  }`}
                >
                  {active && (
                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${isDark ? 'bg-emerald-400' : 'bg-emerald-500'}`} />
                  )}
                  <ItemIcon className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} />
                  <span className="truncate flex-1">{item.name}</span>
                  {itemBadge > 0 && (
                    <span className="ml-auto flex-shrink-0 bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center animate-pulse">
                      {itemBadge > 99 ? '99+' : itemBadge}
                    </span>
                  )}
                  {typeof item.badge === 'string' && item.badge && (
                    <span className="ml-auto flex-shrink-0 bg-emerald-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  return (
    <div 
      ref={sidebarRef}
      className={`flex h-screen sticky top-0 transition-all duration-300 ${
        isDark ? 'bg-zinc-900' : 'bg-white'
      }`}
      data-testid="modern-sidebar"
    >
      {/* Icon Bar - Always visible */}
      <div 
        className={`w-[70px] flex flex-col border-r flex-shrink-0 ${
          isDark ? 'bg-zinc-950 border-zinc-800' : 'bg-zinc-50 border-zinc-200'
        }`}
      >
        {/* Logo/Toggle */}
        <div className="h-16 flex items-center justify-center border-b border-inherit">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors ${
              isDark 
                ? 'hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100' 
                : 'hover:bg-zinc-200 text-zinc-500 hover:text-zinc-900'
            }`}
            data-testid="toggle-sidebar"
            title={isExpanded ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {isExpanded ? (
              <PanelLeftClose className="w-5 h-5" />
            ) : (
              <PanelLeft className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Navigation Icons */}
        <div className="flex-1 py-4 px-2.5 space-y-2 overflow-y-auto">
          {menuSections.filter(s => s.show).map(section => (
            <div key={section.key} className="relative">
              <IconBarItem section={section} />
              <HoverPopup section={section} />
            </div>
          ))}
        </div>

        {/* Bottom Icons */}
        <div className={`py-4 px-2.5 space-y-2 border-t ${isDark ? 'border-zinc-800' : 'border-zinc-200'}`}>
          {/* Notifications */}
          <button
            className={`w-12 h-12 flex items-center justify-center rounded-xl relative transition-colors ${
              isDark
                ? 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100'
                : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900'
            }`}
            data-testid="icon-notifications"
          >
            <Bell className="w-5 h-5" strokeWidth={1.5} />
            {(pendingCounts?.total || 0) > 0 && (
              <span className="absolute top-1 right-1 w-5 h-5 bg-emerald-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                {pendingCounts.total > 9 ? '9+' : pendingCounts.total}
              </span>
            )}
          </button>

          {/* Settings */}
          <Link
            to="/settings"
            className={`w-12 h-12 flex items-center justify-center rounded-xl transition-colors ${
              isDark
                ? 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100'
                : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900'
            }`}
            data-testid="icon-settings"
          >
            <Settings className="w-5 h-5" strokeWidth={1.5} />
          </Link>

          {/* Profile */}
          <div className="relative" ref={profileMenuRef}>
            <button
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${
                showProfileMenu
                  ? isDark ? 'bg-zinc-800' : 'bg-zinc-100'
                  : isDark
                    ? 'hover:bg-zinc-800'
                    : 'hover:bg-zinc-100'
              }`}
              data-testid="profile-menu-trigger"
            >
              <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold ${
                isDark ? 'bg-zinc-700 text-zinc-200' : 'bg-zinc-200 text-zinc-700'
              }`}>
                {sanitizeDisplayText(user?.full_name)?.charAt(0) || 'U'}
              </div>
            </button>

            {/* Profile Dropdown */}
            {showProfileMenu && (
              <div 
                className={`absolute bottom-full left-0 mb-2 w-56 rounded-xl shadow-xl border z-50 ${
                  isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'
                }`}
              >
                {/* User Info Header */}
                <div className={`px-4 py-3 border-b ${isDark ? 'border-zinc-800' : 'border-zinc-100'}`}>
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold ${
                      isDark ? 'bg-zinc-700 text-zinc-200' : 'bg-zinc-200 text-zinc-700'
                    }`}>
                      {sanitizeDisplayText(user?.full_name)?.charAt(0) || 'U'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className={`text-sm font-semibold truncate ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                        {sanitizeDisplayText(user?.full_name)}
                      </div>
                      <div className={`text-xs capitalize truncate ${isDark ? 'text-zinc-500' : 'text-zinc-500'}`}>
                        {user?.role?.replace(/_/g, ' ')}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Menu Items */}
                <div className="py-2">
                  <Link
                    to="/profile"
                    onClick={() => setShowProfileMenu(false)}
                    className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                      isDark
                        ? 'text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100'
                        : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'
                    }`}
                  >
                    <User className="w-4 h-4" />
                    <span>View your profile</span>
                    <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded ${
                      isDark ? 'bg-zinc-800 text-zinc-500' : 'bg-zinc-100 text-zinc-400'
                    }`}>⌘+P</span>
                  </Link>
                  
                  <button
                    onClick={() => {
                      setShowProfileMenu(false);
                      onChangePassword?.();
                    }}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                      isDark
                        ? 'text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100'
                        : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'
                    }`}
                  >
                    <Key className="w-4 h-4" />
                    <span>Account settings</span>
                    <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded ${
                      isDark ? 'bg-zinc-800 text-zinc-500' : 'bg-zinc-100 text-zinc-400'
                    }`}>⌘+S</span>
                  </button>

                  <Link
                    to="/help"
                    onClick={() => setShowProfileMenu(false)}
                    className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                      isDark
                        ? 'text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100'
                        : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'
                    }`}
                  >
                    <HelpCircle className="w-4 h-4" />
                    <span>What's new?</span>
                    <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded ${
                      isDark ? 'bg-zinc-800 text-zinc-500' : 'bg-zinc-100 text-zinc-400'
                    }`}>⌘+U</span>
                  </Link>
                </div>

                {/* Logout */}
                <div className={`py-2 border-t ${isDark ? 'border-zinc-800' : 'border-zinc-100'}`}>
                  <button
                    onClick={() => {
                      setShowProfileMenu(false);
                      logout?.();
                    }}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                      isDark
                        ? 'text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100'
                        : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'
                    }`}
                    data-testid="logout-button"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Log out</span>
                    <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded ${
                      isDark ? 'bg-zinc-800 text-zinc-500' : 'bg-zinc-100 text-zinc-400'
                    }`}>⇧+⌘+Q</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Expanded Panel */}
      <div 
        className={`transition-all duration-300 overflow-hidden border-r ${
          isDark ? 'border-zinc-800' : 'border-zinc-200'
        } ${isExpanded ? 'w-[240px]' : 'w-0'}`}
      >
        <div className="w-[240px] h-full flex flex-col">
          {/* Header with User Info */}
          <div className={`h-16 px-4 flex items-center gap-3 border-b ${
            isDark ? 'border-zinc-800' : 'border-zinc-200'
          }`}>
            <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0 ${
              isDark ? 'bg-zinc-700 text-zinc-200' : 'bg-zinc-200 text-zinc-700'
            }`}>
              {sanitizeDisplayText(user?.full_name)?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className={`text-sm font-semibold truncate ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                {sanitizeDisplayText(user?.full_name)}
              </div>
              <div className={`text-xs text-zinc-500 truncate`}>
                {user?.email || user?.employee_id}
              </div>
            </div>
            <button className={`p-1 rounded ${isDark ? 'hover:bg-zinc-800' : 'hover:bg-zinc-100'}`}>
              <MoreVertical className={`w-4 h-4 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`} />
            </button>
          </div>

          {/* Search */}
          <div className={`px-3 py-3 border-b ${isDark ? 'border-zinc-800' : 'border-zinc-200'}`}>
            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
              isDark ? 'bg-zinc-800' : 'bg-zinc-100'
            }`}>
              <Search className={`w-4 h-4 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`} />
              <span className={`text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Search</span>
            </div>
          </div>

          {/* Navigation Sections */}
          <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
            {/* Dashboard Link */}
            <Link
              to="/"
              data-testid="nav-dashboard"
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150 ${
                isActive('/') 
                  ? isDark 
                    ? 'bg-zinc-800 text-zinc-100 font-medium' 
                    : 'bg-zinc-100 text-zinc-900 font-medium' 
                  : isDark 
                    ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50' 
                    : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
              }`}
            >
              <LayoutDashboard className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} />
              <span>{isConsultant ? 'My Dashboard' : 'Overview'}</span>
            </Link>

            {/* Sections */}
            {menuSections.filter(s => s.show && !s.single).map(section => (
              <ExpandedSection key={section.key} section={section} />
            ))}
          </div>

          {/* Bottom Actions */}
          <div className={`px-3 py-3 border-t space-y-1 ${isDark ? 'border-zinc-800' : 'border-zinc-200'}`}>
            <Link
              to="/notifications"
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                isDark 
                  ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50' 
                  : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
              }`}
            >
              <Bell className="w-4 h-4" strokeWidth={1.5} />
              <span>Notifications</span>
              {(pendingCounts?.total || 0) > 0 && (
                <span className="ml-auto bg-emerald-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                  {pendingCounts.total}
                </span>
              )}
            </Link>
            
            <Link
              to="/help"
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                isDark 
                  ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50' 
                  : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
              }`}
            >
              <HelpCircle className="w-4 h-4" strokeWidth={1.5} />
              <span>Support</span>
            </Link>
            
            <Link
              to="/settings"
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                isDark 
                  ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50' 
                  : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
              }`}
            >
              <Settings className="w-4 h-4" strokeWidth={1.5} />
              <span>Settings</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModernSidebar;
