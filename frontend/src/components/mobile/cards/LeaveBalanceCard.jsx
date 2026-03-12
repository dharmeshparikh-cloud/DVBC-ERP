/**
 * LeaveBalanceCard - Leave Balance Display Card
 */

import React from 'react';
import { Card, CardContent } from '../../ui/card';
import { Calendar, Sun, Heart, Briefcase } from 'lucide-react';

const LeaveItem = ({ type, balance, icon: Icon, color }) => (
  <div className="flex items-center justify-between p-2 bg-white rounded-lg border">
    <div className="flex items-center gap-2">
      <div className={`p-1.5 rounded-lg ${color}`}>
        <Icon className="w-4 h-4 text-white" />
      </div>
      <span className="text-sm text-zinc-600">{type}</span>
    </div>
    <span className="font-semibold text-zinc-900">{balance}</span>
  </div>
);

export const LeaveBalanceCard = ({
  leaveBalance,
  onApplyLeave
}) => {
  const casual = leaveBalance?.casual || leaveBalance?.CL || { balance: 0 };
  const sick = leaveBalance?.sick || leaveBalance?.SL || { balance: 0 };
  const earned = leaveBalance?.earned || leaveBalance?.EL || { balance: 0 };

  return (
    <Card className="border-zinc-200">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-zinc-900 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-blue-500" />
            Leave Balance
          </h3>
          <button
            onClick={onApplyLeave}
            className="text-sm text-orange-600 font-medium hover:text-orange-700"
            data-testid="apply-leave-btn"
          >
            + Apply
          </button>
        </div>
        
        <div className="space-y-2">
          <LeaveItem 
            type="Casual Leave" 
            balance={casual.balance || casual.remaining || 0}
            icon={Sun}
            color="bg-amber-500"
          />
          <LeaveItem 
            type="Sick Leave" 
            balance={sick.balance || sick.remaining || 0}
            icon={Heart}
            color="bg-red-500"
          />
          <LeaveItem 
            type="Earned Leave" 
            balance={earned.balance || earned.remaining || 0}
            icon={Briefcase}
            color="bg-blue-500"
          />
        </div>
      </CardContent>
    </Card>
  );
};

export default LeaveBalanceCard;
