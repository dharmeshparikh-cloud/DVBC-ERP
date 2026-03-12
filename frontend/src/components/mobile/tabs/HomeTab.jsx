/**
 * HomeTab - Mobile Dashboard Home Tab
 * Shows today's attendance, quick actions, and summary
 */

import React from 'react';
import { Card, CardContent } from '../../ui/card';
import { 
  Receipt, Calendar, Navigation, TrendingUp, 
  ChevronRight, Coffee, Timer, Wallet 
} from 'lucide-react';
import { AttendanceCard } from '../cards/AttendanceCard';
import { LeaveBalanceCard } from '../cards/LeaveBalanceCard';

const QuickActionButton = ({ icon: Icon, label, onClick, color = 'orange' }) => (
  <button
    onClick={onClick}
    className="flex flex-col items-center justify-center p-3 bg-white rounded-xl border border-zinc-200 hover:border-zinc-300 hover:shadow-sm transition-all"
    data-testid={`quick-action-${label.toLowerCase().replace(' ', '-')}`}
  >
    <div className={`p-2 rounded-lg bg-${color}-100 mb-1`}>
      <Icon className={`w-5 h-5 text-${color}-600`} />
    </div>
    <span className="text-xs text-zinc-600">{label}</span>
  </button>
);

const StatItem = ({ label, value, icon: Icon, color }) => (
  <div className="flex items-center gap-2 p-2 bg-white rounded-lg border flex-1">
    <Icon className={`w-4 h-4 text-${color}-500`} />
    <div>
      <p className="text-[10px] text-zinc-400 uppercase">{label}</p>
      <p className="text-sm font-semibold text-zinc-900">{value}</p>
    </div>
  </div>
);

export const HomeTab = ({
  // Attendance
  checkInStatus,
  isCheckedIn,
  isCheckedOut,
  onCheckIn,
  onCheckOut,
  // Leave
  leaveBalance,
  onApplyLeave,
  // Quick Actions
  onExpenseClick,
  onTravelClick,
  isSalesTeam,
  // Stats
  monthlyStats
}) => {
  const workHoursToday = checkInStatus?.work_hours || 0;
  const expensesThisMonth = monthlyStats?.expenses || 0;

  return (
    <div className="space-y-4 pb-20">
      {/* Today's Attendance Card */}
      <AttendanceCard
        checkInStatus={checkInStatus}
        isCheckedIn={isCheckedIn}
        isCheckedOut={isCheckedOut}
        onCheckIn={onCheckIn}
        onCheckOut={onCheckOut}
      />

      {/* Quick Stats */}
      <div className="flex gap-2">
        <StatItem 
          label="Today" 
          value={`${workHoursToday.toFixed(1)} hrs`} 
          icon={Timer} 
          color="blue" 
        />
        <StatItem 
          label="This Month" 
          value={`₹${expensesThisMonth.toLocaleString()}`} 
          icon={Wallet} 
          color="emerald" 
        />
      </div>

      {/* Leave Balance */}
      <LeaveBalanceCard
        leaveBalance={leaveBalance}
        onApplyLeave={onApplyLeave}
      />

      {/* Quick Actions */}
      <div>
        <h3 className="text-sm font-semibold text-zinc-700 mb-2">Quick Actions</h3>
        <div className="grid grid-cols-3 gap-2">
          <QuickActionButton 
            icon={Receipt} 
            label="Expense" 
            onClick={onExpenseClick}
            color="emerald"
          />
          <QuickActionButton 
            icon={Calendar} 
            label="Leave" 
            onClick={onApplyLeave}
            color="blue"
          />
          {isSalesTeam && (
            <QuickActionButton 
              icon={Navigation} 
              label="Travel" 
              onClick={onTravelClick}
              color="purple"
            />
          )}
        </div>
      </div>

      {/* Recent Activity - Placeholder */}
      <Card className="border-zinc-200">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-zinc-900 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-orange-500" />
              Recent Activity
            </h3>
            <button className="text-xs text-orange-600">View All</button>
          </div>
          <div className="text-sm text-zinc-500 text-center py-4">
            Your recent activities will appear here
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default HomeTab;
