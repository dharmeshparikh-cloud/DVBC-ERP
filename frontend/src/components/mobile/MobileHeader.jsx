/**
 * MobileHeader - Header Component for Mobile App
 * Shows user greeting, date, and quick status
 */

import React from 'react';
import { Bell, Sun, Moon } from 'lucide-react';

export const MobileHeader = ({
  userName,
  currentTime,
  onNotificationClick
}) => {
  const greeting = (() => {
    const hour = currentTime.getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 17) return 'Good Afternoon';
    return 'Good Evening';
  })();

  const formattedDate = currentTime.toLocaleDateString('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });

  const getGreetingIcon = () => {
    const hour = currentTime.getHours();
    if (hour >= 6 && hour < 18) return <Sun className="w-5 h-5 text-yellow-500" />;
    return <Moon className="w-5 h-5 text-indigo-400" />;
  };

  return (
    <header className="bg-gradient-to-r from-orange-500 to-orange-600 text-white px-4 py-4 pb-6 rounded-b-2xl shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {getGreetingIcon()}
          <span className="text-sm opacity-90">{greeting}</span>
        </div>
        <button 
          onClick={onNotificationClick}
          className="relative p-2 rounded-full bg-white/20 hover:bg-white/30 transition-colors"
          data-testid="notification-btn"
        >
          <Bell className="w-5 h-5" />
          {/* Notification badge - can be made dynamic */}
        </button>
      </div>
      
      <div>
        <h1 className="text-xl font-semibold mb-0.5">
          {userName || 'Employee'}
        </h1>
        <p className="text-sm opacity-80">{formattedDate}</p>
      </div>
    </header>
  );
};

export default MobileHeader;
