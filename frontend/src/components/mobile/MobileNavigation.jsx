/**
 * MobileNavigation - Bottom Tab Navigation for Mobile App
 * Memoized to prevent unnecessary re-renders
 */

import React, { memo } from 'react';
import { Home, Clock, Calendar, Receipt, Navigation, User } from 'lucide-react';

const NavItem = memo(({ icon: Icon, label, active, onClick }) => (
  <button
    onClick={onClick}
    className={`flex flex-col items-center justify-center py-1.5 px-1 rounded-lg transition-colors flex-1 min-w-0 ${
      active 
        ? 'text-orange-600 bg-orange-50' 
        : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-50'
    }`}
    data-testid={`nav-${label.toLowerCase()}`}
  >
    <Icon className={`w-5 h-5 ${active ? 'text-orange-600' : ''}`} />
    <span className="text-[10px] mt-0.5 truncate">{label}</span>
  </button>
));

NavItem.displayName = 'NavItem';

export const MobileNavigation = memo(({
  activeTab,
  onTabChange,
  isSalesTeam = false
}) => {
  const tabs = [
    { id: 'home', icon: Home, label: 'Home' },
    { id: 'attendance', icon: Clock, label: 'Attendance' },
    { id: 'leaves', icon: Calendar, label: 'Leaves' },
    { id: 'expenses', icon: Receipt, label: 'Expenses' },
    ...(isSalesTeam ? [{ id: 'travel', icon: Navigation, label: 'Travel' }] : []),
    { id: 'profile', icon: User, label: 'Profile' }
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-zinc-200 shadow-lg z-50 px-safe pb-safe">
      <div className="flex items-center justify-around h-14 max-w-md mx-auto px-2">
        {tabs.map(tab => (
          <NavItem
            key={tab.id}
            icon={tab.icon}
            label={tab.label}
            active={activeTab === tab.id}
            onClick={() => onTabChange(tab.id)}
          />
        ))}
      </div>
    </nav>
  );
});

MobileNavigation.displayName = 'MobileNavigation';

export default MobileNavigation;
