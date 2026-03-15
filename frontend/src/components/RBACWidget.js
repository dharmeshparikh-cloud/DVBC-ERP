import React, { useState } from 'react';
import { usePermissions } from '../contexts/PermissionContext';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { 
  Shield, ChevronDown, ChevronUp, Check, X, 
  Users, FileText, DollarSign, Settings, Eye,
  UserCheck, Lock, Unlock
} from 'lucide-react';

const RBACWidget = () => {
  const [expanded, setExpanded] = useState(false);
  const { 
    rbacData, 
    level, 
    loading, 
    permissions,
    isAdmin,
    isManagerOrAbove,
    isLeader,
    canApproveRequests,
    canViewReports,
    canManageUsers,
    canManageTeam
  } = usePermissions();

  if (loading) {
    return (
      <Card className="border-zinc-200 shadow-none rounded-sm animate-pulse">
        <CardContent className="py-3">
          <div className="h-4 bg-zinc-200 rounded w-24"></div>
        </CardContent>
      </Card>
    );
  }

  const roleLevel = rbacData?.level || level || 0;
  const roleName = rbacData?.role_name || rbacData?.role || 'Unknown';
  const department = rbacData?.department || 'N/A';

  // Determine access tier badge
  const getAccessTier = () => {
    if (roleLevel >= 100) return { label: 'Full Access', color: 'bg-purple-600', icon: Shield };
    if (roleLevel >= 80) return { label: 'Department Lead', color: 'bg-blue-600', icon: Users };
    if (roleLevel >= 70) return { label: 'Manager', color: 'bg-emerald-600', icon: UserCheck };
    if (roleLevel >= 50) return { label: 'Team Member', color: 'bg-amber-500', icon: Eye };
    return { label: 'Basic', color: 'bg-zinc-500', icon: Lock };
  };

  const tier = getAccessTier();
  const TierIcon = tier.icon;

  // Permission indicators
  const permissionIndicators = [
    { key: 'approve', label: 'Approvals', enabled: canApproveRequests(), icon: Check },
    { key: 'reports', label: 'Reports', enabled: canViewReports(), icon: FileText },
    { key: 'users', label: 'Manage Users', enabled: canManageUsers(), icon: Users },
    { key: 'team', label: 'Team Data', enabled: canManageTeam(), icon: Eye },
  ];

  // Data access scope
  const getDataScope = () => {
    if (isAdmin()) return 'All Company Data';
    if (isLeader()) return 'Department + Team Data';
    if (isManagerOrAbove()) return 'Team Data';
    return 'Own Data Only';
  };

  return (
    <Card 
      className="border-zinc-200 dark:border-[#2A2A2E] dark:bg-[#1A1A1C] shadow-none rounded-sm cursor-pointer hover:border-zinc-300 dark:hover:border-[#333338] transition-colors"
      onClick={() => setExpanded(!expanded)}
      data-testid="rbac-widget"
    >
      <CardContent className="py-3 px-4">
        {/* Collapsed View */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-md ${tier.color} flex items-center justify-center`}>
              <TierIcon className="w-4 h-4 text-white" strokeWidth={2} />
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-800 dark:text-zinc-100">{roleName}</div>
              <div className="text-[10px] text-zinc-500 dark:text-zinc-400">Level {roleLevel}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={`${tier.color} text-white text-[10px] px-2 py-0.5`}>
              {tier.label}
            </Badge>
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-zinc-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-zinc-400" />
            )}
          </div>
        </div>

        {/* Expanded View */}
        {expanded && (
          <div className="mt-4 pt-3 border-t border-zinc-100 dark:border-[#2A2A2E] space-y-3" data-testid="rbac-widget-expanded">
            {/* Department & Data Scope */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-[10px] uppercase tracking-wide text-zinc-400 mb-1">Department</div>
                <div className="text-xs font-medium text-zinc-700 dark:text-zinc-200">{department}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wide text-zinc-400 mb-1">Data Access</div>
                <div className="text-xs font-medium text-zinc-700 dark:text-zinc-200">{getDataScope()}</div>
              </div>
            </div>

            {/* Permission Indicators */}
            <div>
              <div className="text-[10px] uppercase tracking-wide text-zinc-400 mb-2">Permissions</div>
              <div className="grid grid-cols-2 gap-2">
                {permissionIndicators.map((perm) => {
                  const PermIcon = perm.icon;
                  return (
                    <div 
                      key={perm.key}
                      className={`flex items-center gap-1.5 px-2 py-1.5 rounded-sm text-xs ${
                        perm.enabled 
                          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400' 
                          : 'bg-zinc-50 text-zinc-400 dark:bg-[#222226] dark:text-zinc-500'
                      }`}
                    >
                      {perm.enabled ? (
                        <Check className="w-3 h-3" />
                      ) : (
                        <X className="w-3 h-3" />
                      )}
                      {perm.label}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Raw Permissions Preview (for admins/debugging) */}
            {permissions?.raw_permissions && permissions.raw_permissions.length > 0 && (
              <div>
                <div className="text-[10px] uppercase tracking-wide text-zinc-400 mb-1">
                  Active Permissions ({permissions.raw_permissions.length})
                </div>
                <div className="flex flex-wrap gap-1">
                  {permissions.raw_permissions.slice(0, 6).map((perm, idx) => (
                    <Badge 
                      key={idx} 
                      variant="secondary" 
                      className="text-[10px] px-1.5 py-0 bg-zinc-100 text-zinc-600"
                    >
                      {perm}
                    </Badge>
                  ))}
                  {permissions.raw_permissions.length > 6 && (
                    <Badge 
                      variant="secondary" 
                      className="text-[10px] px-1.5 py-0 bg-zinc-100 text-zinc-600"
                    >
                      +{permissions.raw_permissions.length - 6} more
                    </Badge>
                  )}
                </div>
              </div>
            )}

            {/* Security Notice */}
            <div className="flex items-start gap-2 p-2 bg-blue-50 rounded-sm">
              <Lock className="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
              <div className="text-[10px] text-blue-700">
                Your access is managed by RBAC. Contact HR or Admin to request permission changes.
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default RBACWidget;
