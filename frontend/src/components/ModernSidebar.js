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
import { Link, useLocation, useNavigate } from 'react-router-dom';
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

// Storage keys for scroll persistence
const SIDEBAR_SCROLL_KEY = 'sidebar_scroll_position';
const SIDEBAR_ICON_SCROLL_KEY = 'sidebar_icon_scroll_position';

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
  const navigate = useNavigate();
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
  
  // Keyboard navigation state
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const [isKeyboardNav, setIsKeyboardNav] = useState(false);
  const navItemsRef = useRef([]);
  
  // Refs for hover popup positioning
  const sidebarRef = useRef(null);
  const hoverTimeoutRef = useRef(null);
  const profileMenuRef = useRef(null);
  
  // Refs for scroll persistence
  const expandedNavRef = useRef(null);
  const iconNavRef = useRef(null);
  const isRestoringScroll = useRef(false);

  // Restore scroll position on mount and route changes
  useEffect(() => {
    const restoreScrollPosition = () => {
      isRestoringScroll.current = true;
      
      // Restore expanded panel scroll
      const savedExpandedScroll = sessionStorage.getItem(SIDEBAR_SCROLL_KEY);
      if (savedExpandedScroll && expandedNavRef.current) {
        expandedNavRef.current.scrollTop = parseInt(savedExpandedScroll, 10);
      }
      
      // Restore icon bar scroll
      const savedIconScroll = sessionStorage.getItem(SIDEBAR_ICON_SCROLL_KEY);
      if (savedIconScroll && iconNavRef.current) {
        iconNavRef.current.scrollTop = parseInt(savedIconScroll, 10);
      }
      
      // Reset flag after a short delay
      requestAnimationFrame(() => {
        isRestoringScroll.current = false;
      });
    };
    
    // Restore immediately
    restoreScrollPosition();
    
    // Also restore after a brief delay to handle React re-renders
    const timeoutId = setTimeout(restoreScrollPosition, 50);
    
    return () => clearTimeout(timeoutId);
  }, [location.pathname]);

  // Save scroll position on scroll events
  const handleExpandedScroll = useCallback((e) => {
    if (!isRestoringScroll.current) {
      sessionStorage.setItem(SIDEBAR_SCROLL_KEY, e.target.scrollTop.toString());
    }
  }, []);
  
  const handleIconScroll = useCallback((e) => {
    if (!isRestoringScroll.current) {
      sessionStorage.setItem(SIDEBAR_ICON_SCROLL_KEY, e.target.scrollTop.toString());
    }
  }, []);

  // Toggle section expansion - useCallback to avoid stale closure
  // IMPORTANT: Defined before keyboard navigation useEffect to avoid hoisting issues
  const toggleSection = useCallback((sectionKey) => {
    if (isExpanded) {
      setExpandedSections(prev => ({
        ...prev,
        [sectionKey]: !prev[sectionKey]
      }));
    }
  }, [isExpanded]);

  // Build flat list of all navigable items for keyboard navigation
  const getAllNavItems = useCallback(() => {
    const items = [];
    
    // Dashboard
    items.push({ type: 'link', href: '/', name: isConsultant ? 'My Dashboard' : 'Overview', section: 'dashboard' });
    
    // Workspace items
    if (workspaceItems?.length) {
      items.push({ type: 'section', key: 'workspace', label: 'My Workspace' });
      if (expandedSections.workspace) {
        workspaceItems.forEach(item => {
          items.push({ type: 'link', ...item, section: 'workspace' });
        });
      }
    }
    
    // HR items
    if (showHR && hrItems?.length) {
      items.push({ type: 'section', key: 'hr', label: 'HR' });
      if (expandedSections.hr) {
        hrItems.forEach(item => {
          items.push({ type: 'link', ...item, section: 'hr' });
        });
      }
    }
    
    // Sales items
    if (showSales && salesItems?.length) {
      items.push({ type: 'section', key: 'sales', label: isGuidedSalesMode ? 'My Sales' : 'Sales' });
      if (expandedSections.sales) {
        salesItems.forEach(item => {
          items.push({ type: 'link', ...item, section: 'sales' });
        });
      }
    }
    
    // Consulting items
    if (showConsulting && consultingItems?.length) {
      items.push({ type: 'section', key: 'consulting', label: 'Consulting' });
      if (expandedSections.consulting) {
        consultingItems.forEach(item => {
          items.push({ type: 'link', ...item, section: 'consulting' });
        });
      }
    }
    
    // Admin items
    if (showAdmin && adminItems?.length) {
      items.push({ type: 'section', key: 'admin', label: 'Admin' });
      if (expandedSections.admin) {
        adminItems.forEach(item => {
          items.push({ type: 'link', ...item, section: 'admin' });
        });
      }
    }
    
    return items;
  }, [workspaceItems, hrItems, salesItems, consultingItems, adminItems, showHR, showSales, showConsulting, showAdmin, expandedSections, isConsultant, isGuidedSalesMode]);

  // Keyboard navigation handler
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Only handle if sidebar is focused or keyboard nav is active
      if (!sidebarRef.current?.contains(document.activeElement) && !isKeyboardNav) {
        return;
      }
      
      const navItems = getAllNavItems();
      
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setIsKeyboardNav(true);
          setFocusedIndex(prev => {
            const next = prev < navItems.length - 1 ? prev + 1 : 0;
            return next;
          });
          break;
          
        case 'ArrowUp':
          e.preventDefault();
          setIsKeyboardNav(true);
          setFocusedIndex(prev => {
            const next = prev > 0 ? prev - 1 : navItems.length - 1;
            return next;
          });
          break;
          
        case 'ArrowRight':
          e.preventDefault();
          if (focusedIndex >= 0) {
            const item = navItems[focusedIndex];
            if (item?.type === 'section' && !expandedSections[item.key]) {
              setExpandedSections(prev => ({ ...prev, [item.key]: true }));
            }
          }
          break;
          
        case 'ArrowLeft':
          e.preventDefault();
          if (focusedIndex >= 0) {
            const item = navItems[focusedIndex];
            if (item?.type === 'section' && expandedSections[item.key]) {
              setExpandedSections(prev => ({ ...prev, [item.key]: false }));
            } else if (item?.type === 'link' && item.section) {
              // Collapse parent section
              setExpandedSections(prev => ({ ...prev, [item.section]: false }));
            }
          }
          break;
          
        case 'Enter':
        case ' ':
          e.preventDefault();
          if (focusedIndex >= 0) {
            const item = navItems[focusedIndex];
            if (item?.type === 'section') {
              toggleSection(item.key);
            } else if (item?.type === 'link' && item.href) {
              // Navigate programmatically using react-router
              navigate(item.href);
              setIsKeyboardNav(false);
              setFocusedIndex(-1);
            }
          }
          break;
          
        case 'Home':
          e.preventDefault();
          setIsKeyboardNav(true);
          setFocusedIndex(0);
          break;
          
        case 'End':
          e.preventDefault();
          setIsKeyboardNav(true);
          setFocusedIndex(navItems.length - 1);
          break;
          
        case 'Escape':
          e.preventDefault();
          setIsKeyboardNav(false);
          setFocusedIndex(-1);
          setShowProfileMenu(false);
          setHoveredSection(null);
          break;
          
        case 'Tab':
          // Allow Tab to exit keyboard nav mode
          setIsKeyboardNav(false);
          setFocusedIndex(-1);
          break;
          
        default:
          // Handle letter shortcuts for quick navigation
          if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
            const letter = e.key.toLowerCase();
            const currentIndex = focusedIndex;
            const searchItems = navItems.slice(currentIndex + 1).concat(navItems.slice(0, currentIndex + 1));
            const foundIndex = searchItems.findIndex(item => 
              item.name?.toLowerCase().startsWith(letter) || item.label?.toLowerCase().startsWith(letter)
            );
            if (foundIndex !== -1) {
              const actualIndex = (currentIndex + 1 + foundIndex) % navItems.length;
              setIsKeyboardNav(true);
              setFocusedIndex(actualIndex);
            }
          }
          break;
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [focusedIndex, expandedSections, getAllNavItems, isKeyboardNav, toggleSection, navigate]);

  // Reset keyboard nav when mouse is used
  useEffect(() => {
    const handleMouseMove = () => {
      if (isKeyboardNav) {
        setIsKeyboardNav(false);
      }
    };
    document.addEventListener('mousemove', handleMouseMove);
    return () => document.removeEventListener('mousemove', handleMouseMove);
  }, [isKeyboardNav]);

  // Focus the item when focusedIndex changes
  useEffect(() => {
    if (focusedIndex >= 0 && navItemsRef.current[focusedIndex]) {
      navItemsRef.current[focusedIndex]?.focus();
    }
  }, [focusedIndex]);

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
            title={section.label}
            className={`w-12 h-12 flex items-center justify-center rounded-xl transition-all duration-200 cursor-pointer ${
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
            title={section.label}
            className={`w-12 h-12 flex items-center justify-center rounded-xl transition-all duration-200 relative cursor-pointer ${
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
          {section.items?.map(item => {
            // Handle section header items in popup
            if (item.isHeader) {
              return (
                <div 
                  key={item.name} 
                  className={`px-4 py-1.5 text-[10px] uppercase tracking-wider font-semibold mt-2 first:mt-0 ${
                    isDark ? 'text-zinc-500' : 'text-zinc-400'
                  }`}
                >
                  {item.name.replace(/—/g, '').trim()}
                </div>
              );
            }
            
            return (
              <Link
                key={item.name}
                to={item.href}
                title={item.name}
                className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors cursor-pointer ${
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
            );
          })}
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
          title={`${isOpen ? 'Collapse' : 'Expand'} ${section.label}`}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer ${
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
              // Handle section header items (visual separators)
              if (item.isHeader) {
                return (
                  <div 
                    key={item.name} 
                    className={`px-3 py-1.5 text-[10px] uppercase tracking-wider font-semibold mt-2 first:mt-0 ${
                      isDark ? 'text-zinc-500' : 'text-zinc-400'
                    }`}
                  >
                    {item.name.replace(/—/g, '').trim()}
                  </div>
                );
              }
              
              const ItemIcon = item.icon;
              const active = isActive(item.href);
              const itemBadge = item.name === 'Approvals Center' ? pendingCounts?.total :
                                item.name === 'Attendance Approvals' ? pendingCounts?.attendance :
                                item.name === 'CTC Designer' ? pendingCounts?.ctc : 0;
              
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  title={item.name}
                  data-testid={`nav-${item.name.toLowerCase().replace(/\s+/g, '-')}`}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150 cursor-pointer ${
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
      tabIndex={0}
      role="navigation"
      aria-label="Main navigation"
      className={`flex h-screen sticky top-0 transition-all duration-300 outline-none ${
        isDark ? 'bg-zinc-900' : 'bg-white'
      } ${isKeyboardNav ? 'ring-2 ring-emerald-500 ring-inset' : ''}`}
      data-testid="modern-sidebar"
      onFocus={() => {
        if (focusedIndex === -1) {
          setFocusedIndex(0);
          setIsKeyboardNav(true);
        }
      }}
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
        <div 
          ref={iconNavRef}
          onScroll={handleIconScroll}
          className="flex-1 py-4 px-2.5 space-y-2 overflow-y-auto scrollbar-thin"
        >
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
          <Link
            to="/notifications"
            title="Notifications"
            className={`w-12 h-12 flex items-center justify-center rounded-xl relative transition-colors cursor-pointer ${
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
          </Link>

          {/* Settings */}
          <Link
            to="/settings"
            title="Settings"
            className={`w-12 h-12 flex items-center justify-center rounded-xl transition-colors cursor-pointer ${
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
              title="Profile Menu"
              className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors cursor-pointer ${
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
          <div 
            ref={expandedNavRef}
            onScroll={handleExpandedScroll}
            className="flex-1 overflow-y-auto px-3 py-4 space-y-1 scrollbar-thin"
          >
            {/* Dashboard Link */}
            <Link
              to="/"
              title={isConsultant ? 'My Dashboard' : 'Overview Dashboard'}
              data-testid="nav-dashboard"
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150 cursor-pointer ${
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
              title="View Notifications"
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer ${
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
              title="Get Support"
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer ${
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
              title="App Settings"
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer ${
                isDark 
                  ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50' 
                  : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'
              }`}
            >
              <Settings className="w-4 h-4" strokeWidth={1.5} />
              <span>Settings</span>
            </Link>
            
            {/* Keyboard Navigation Hint */}
            {isKeyboardNav && (
              <div className={`mt-3 pt-3 border-t text-center ${isDark ? 'border-zinc-800' : 'border-zinc-200'}`}>
                <div className={`text-[10px] space-y-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                  <div className="flex items-center justify-center gap-2">
                    <kbd className={`px-1.5 py-0.5 rounded text-[9px] ${isDark ? 'bg-zinc-800' : 'bg-zinc-100'}`}>↑↓</kbd>
                    <span>Navigate</span>
                  </div>
                  <div className="flex items-center justify-center gap-2">
                    <kbd className={`px-1.5 py-0.5 rounded text-[9px] ${isDark ? 'bg-zinc-800' : 'bg-zinc-100'}`}>←→</kbd>
                    <span>Expand/Collapse</span>
                  </div>
                  <div className="flex items-center justify-center gap-2">
                    <kbd className={`px-1.5 py-0.5 rounded text-[9px] ${isDark ? 'bg-zinc-800' : 'bg-zinc-100'}`}>Enter</kbd>
                    <span>Select</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModernSidebar;
