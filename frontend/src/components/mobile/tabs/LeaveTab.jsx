/**
 * LeaveTab - Mobile Leave Management Tab
 * Shows leave balance and recent requests
 * Extracted from EmployeeMobileApp.js for better maintainability
 */

import React, { memo } from 'react';
import { Coffee, AlertCircle, TrendingUp, Plus, Calendar } from 'lucide-react';

export const LeaveTab = memo(({
  leaveBalance,
  onApplyLeave
}) => {
  return (
    <div className="space-y-4 pb-24">
      <div className="grid grid-cols-3 gap-3">
        {leaveBalance && [
          { type: 'Casual', data: leaveBalance.casual, color: 'blue', icon: Coffee },
          { type: 'Sick', data: leaveBalance.sick, color: 'red', icon: AlertCircle },
          { type: 'Earned', data: leaveBalance.earned, color: 'emerald', icon: TrendingUp },
        ].map((item, i) => (
          <div key={i} className={`bg-gradient-to-br from-${item.color}-500 to-${item.color}-600 rounded-2xl p-4 text-white`}>
            <item.icon className="w-6 h-6 mb-2 opacity-80" />
            <p className="text-3xl font-bold">{item.data?.available || 0}</p>
            <p className="text-xs opacity-80">{item.type}</p>
          </div>
        ))}
      </div>

      <button 
        onClick={onApplyLeave}
        onTouchEnd={(e) => { e.preventDefault(); onApplyLeave(); }}
        className="w-full py-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-2xl font-semibold shadow-lg flex items-center justify-center gap-2 active:scale-95 transition touch-manipulation cursor-pointer"
        style={{ WebkitTapHighlightColor: 'transparent', touchAction: 'manipulation' }}
        data-testid="apply-leave-btn"
      >
        <Plus className="w-5 h-5" />
        Apply for Leave
      </button>

      <div className="bg-white rounded-2xl shadow-sm border border-zinc-100 overflow-hidden">
        <div className="p-4 border-b border-zinc-100">
          <h3 className="font-semibold text-zinc-900">Recent Requests</h3>
        </div>
        <div className="p-8 text-center text-zinc-500">
          <Calendar className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
          <p>No recent leave requests</p>
        </div>
      </div>
    </div>
  );
});

LeaveTab.displayName = 'LeaveTab';

export default LeaveTab;
