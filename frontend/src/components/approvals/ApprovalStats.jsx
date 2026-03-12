/**
 * ApprovalStats - Statistics Cards Component
 * Displays approval counts in a responsive grid
 */

import React from 'react';
import { Card, CardContent } from '../../ui/card';
import { 
  Clock, DollarSign, CreditCard, Rocket, Shield, 
  Receipt, Send, CheckCircle, XCircle, User, FileText, Play
} from 'lucide-react';

const StatCard = ({ label, value, icon: Icon, color, isDark, className = '' }) => (
  <Card className={`${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'} shadow-none rounded-lg ${className}`}>
    <CardContent className="p-2.5 md:p-4">
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <p className={`text-[10px] md:text-xs uppercase truncate ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            {label}
          </p>
          <p className={`text-lg md:text-2xl font-semibold text-${color}-600`}>{value}</p>
        </div>
        <Icon className={`w-5 h-5 md:w-8 md:h-8 text-${color}-500/30 flex-shrink-0`} />
      </div>
    </CardContent>
  </Card>
);

export const ApprovalStats = ({
  isDark,
  isAdmin,
  isHR,
  isManager,
  isSC,
  isPC,
  totalPending,
  ctcApprovals,
  bankApprovals,
  goLiveApprovals,
  permissionApprovals,
  modificationApprovals,
  profileChangeApprovals,
  agreementApprovals,
  kickoffApprovals,
  expenseApprovals,
  myRequests
}) => {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2 md:gap-4 mb-6">
      {/* Total Pending */}
      <StatCard
        label="Pending"
        value={totalPending}
        icon={Clock}
        color="yellow"
        isDark={isDark}
      />

      {/* CTC - Admin only */}
      {isAdmin && (
        <StatCard
          label="CTC"
          value={ctcApprovals?.length || 0}
          icon={DollarSign}
          color="purple"
          isDark={isDark}
        />
      )}

      {/* Bank Changes - HR/Admin */}
      {(isHR || isAdmin) && (
        <StatCard
          label="Bank"
          value={bankApprovals?.length || 0}
          icon={CreditCard}
          color="amber"
          isDark={isDark}
        />
      )}

      {/* Go-Live - Admin */}
      {isAdmin && (
        <StatCard
          label="Go-Live"
          value={goLiveApprovals?.length || 0}
          icon={Rocket}
          color="emerald"
          isDark={isDark}
        />
      )}

      {/* Permissions - Admin */}
      {isAdmin && (
        <StatCard
          label="Perm"
          value={permissionApprovals?.length || 0}
          icon={Shield}
          color="indigo"
          isDark={isDark}
        />
      )}

      {/* Modifications - Admin */}
      {isAdmin && modificationApprovals?.length > 0 && (
        <StatCard
          label="Modify"
          value={modificationApprovals.length}
          icon={FileText}
          color="teal"
          isDark={isDark}
        />
      )}

      {/* Profile Changes - HR */}
      {isHR && profileChangeApprovals?.length > 0 && (
        <StatCard
          label="Profile"
          value={profileChangeApprovals.length}
          icon={User}
          color="pink"
          isDark={isDark}
        />
      )}

      {/* Agreements - Manager/Admin */}
      {(isManager || isAdmin) && agreementApprovals?.length > 0 && (
        <StatCard
          label="Agreement"
          value={agreementApprovals.length}
          icon={FileText}
          color="cyan"
          isDark={isDark}
        />
      )}

      {/* Kickoffs - SC/PC/Admin */}
      {(isSC || isPC || isAdmin) && kickoffApprovals?.length > 0 && (
        <StatCard
          label="Kickoff"
          value={kickoffApprovals.length}
          icon={Play}
          color="orange"
          isDark={isDark}
        />
      )}

      {/* Expenses - Manager/HR */}
      {(isManager || isHR) && (
        <StatCard
          label="Expense"
          value={expenseApprovals?.length || 0}
          icon={Receipt}
          color="emerald"
          isDark={isDark}
        />
      )}

      {/* My Requests */}
      <StatCard
        label="My Req"
        value={myRequests?.length || 0}
        icon={Send}
        color="blue"
        isDark={isDark}
      />

      {/* Approved */}
      <StatCard
        label="Done"
        value={myRequests?.filter(r => r.overall_status === 'approved').length || 0}
        icon={CheckCircle}
        color="emerald"
        isDark={isDark}
      />

      {/* Rejected */}
      <StatCard
        label="Rejected"
        value={myRequests?.filter(r => r.overall_status === 'rejected').length || 0}
        icon={XCircle}
        color="red"
        isDark={isDark}
        className="hidden sm:block"
      />
    </div>
  );
};

export default ApprovalStats;
