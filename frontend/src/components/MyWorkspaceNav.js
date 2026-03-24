import React, { useContext } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { CalendarDays, Calendar, Wallet, Receipt, Briefcase, FileText, UserCog, Star } from 'lucide-react';
import { AuthContext } from '../App';

const NAV_ITEMS = [
  { label: 'Attendance', href: '/my-attendance', icon: CalendarDays },
  { label: 'Leaves', href: '/my-leaves', icon: Calendar },
  { label: 'Salary Slips', href: '/my-salary-slips', icon: Wallet },
  { label: 'Expenses', href: '/my-expenses', icon: Receipt },
  { label: 'Projects', href: '/consulting/my-projects', icon: Briefcase },
  { label: 'Drafts', href: '/my-drafts', icon: FileText },
  { label: 'Details', href: '/my-details', icon: UserCog },
  { label: 'Scorecard', href: '/employee-scorecard', icon: Star, adminOnly: true },
];

// Roles that can access admin-only items like Scorecard
const ADMIN_HR_ROLES = ['admin', 'hr_manager', 'hr_executive', 'manager'];

const MyWorkspaceNav = () => {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { user } = useContext(AuthContext);
  
  // Filter items based on role
  const visibleItems = NAV_ITEMS.filter(item => {
    if (item.adminOnly) {
      return ADMIN_HR_ROLES.includes(user?.role);
    }
    return true;
  });

  return (
    <div className="flex items-center gap-1 mb-5 pb-3 border-b border-zinc-200 overflow-x-auto scrollbar-hide" data-testid="my-workspace-nav">
      {(visibleItems || []).map(item => {
        const Icon = item.icon;
        const isActive = pathname === item.href;
        return (
          <button
            key={item.href}
            onClick={() => navigate(item.href)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-medium whitespace-nowrap transition-colors ${
              isActive
                ? 'bg-zinc-900 text-white'
                : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700'
            }`}
            data-testid={`ws-nav-${item.label.toLowerCase().replace(/\s/g, '-')}`}
          >
            <Icon className="w-3.5 h-3.5" />
            {item.label}
          </button>
        );
      })}
    </div>
  );
};

export default MyWorkspaceNav;
