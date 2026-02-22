/**
 * Unified Approval Card Component
 * Used across all approval types in ApprovalsCenter
 */

import React from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { 
  CheckCircle, XCircle, Clock, User, Calendar, 
  DollarSign, FileText, Building2, Briefcase, Rocket,
  Eye, ChevronRight, Shield, UserCheck
} from 'lucide-react';

// Type-specific configurations
const APPROVAL_CONFIGS = {
  expense: {
    icon: DollarSign,
    color: 'emerald',
    bgColor: 'bg-emerald-50 dark:bg-emerald-900/20',
    borderColor: 'border-emerald-200 dark:border-emerald-800',
    iconBg: 'bg-emerald-100 dark:bg-emerald-900/40',
    iconColor: 'text-emerald-600'
  },
  ctc: {
    icon: DollarSign,
    color: 'purple',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20',
    borderColor: 'border-purple-200 dark:border-purple-800',
    iconBg: 'bg-purple-100 dark:bg-purple-900/40',
    iconColor: 'text-purple-600'
  },
  kickoff: {
    icon: Rocket,
    color: 'pink',
    bgColor: 'bg-pink-50 dark:bg-pink-900/20',
    borderColor: 'border-pink-200 dark:border-pink-800',
    iconBg: 'bg-pink-100 dark:bg-pink-900/40',
    iconColor: 'text-pink-600'
  },
  agreement: {
    icon: FileText,
    color: 'blue',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    borderColor: 'border-blue-200 dark:border-blue-800',
    iconBg: 'bg-blue-100 dark:bg-blue-900/40',
    iconColor: 'text-blue-600'
  },
  permission: {
    icon: Shield,
    color: 'indigo',
    bgColor: 'bg-indigo-50 dark:bg-indigo-900/20',
    borderColor: 'border-indigo-200 dark:border-indigo-800',
    iconBg: 'bg-indigo-100 dark:bg-indigo-900/40',
    iconColor: 'text-indigo-600'
  },
  bank: {
    icon: Building2,
    color: 'rose',
    bgColor: 'bg-rose-50 dark:bg-rose-900/20',
    borderColor: 'border-rose-200 dark:border-rose-800',
    iconBg: 'bg-rose-100 dark:bg-rose-900/40',
    iconColor: 'text-rose-600'
  },
  goLive: {
    icon: Rocket,
    color: 'emerald',
    bgColor: 'bg-emerald-50 dark:bg-emerald-900/20',
    borderColor: 'border-emerald-200 dark:border-emerald-800',
    iconBg: 'bg-emerald-100 dark:bg-emerald-900/40',
    iconColor: 'text-emerald-600'
  },
  modification: {
    icon: User,
    color: 'orange',
    bgColor: 'bg-orange-50 dark:bg-orange-900/20',
    borderColor: 'border-orange-200 dark:border-orange-800',
    iconBg: 'bg-orange-100 dark:bg-orange-900/40',
    iconColor: 'text-orange-600'
  },
  leave: {
    icon: Calendar,
    color: 'amber',
    bgColor: 'bg-amber-50 dark:bg-amber-900/20',
    borderColor: 'border-amber-200 dark:border-amber-800',
    iconBg: 'bg-amber-100 dark:bg-amber-900/40',
    iconColor: 'text-amber-600'
  },
  default: {
    icon: FileText,
    color: 'zinc',
    bgColor: 'bg-zinc-50 dark:bg-zinc-800',
    borderColor: 'border-zinc-200 dark:border-zinc-700',
    iconBg: 'bg-zinc-100 dark:bg-zinc-700',
    iconColor: 'text-zinc-600'
  }
};

const formatCurrency = (amount) => {
  if (!amount) return '₹0';
  if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)} Cr`;
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)} L`;
  return `₹${amount.toLocaleString('en-IN')}`;
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  });
};

export const ApprovalCard = ({
  type = 'default',
  title,
  subtitle,
  description,
  amount,
  badge,
  badgeVariant = 'default',
  meta = [],
  requiredBy,
  requestedBy,
  requestedAt,
  onApprove,
  onReject,
  onView,
  loading = false,
  children,
  testId
}) => {
  const config = APPROVAL_CONFIGS[type] || APPROVAL_CONFIGS.default;
  const IconComponent = config.icon;

  const getBadgeClasses = (variant) => {
    const variants = {
      default: `bg-${config.color}-100 text-${config.color}-700 dark:bg-${config.color}-900/30 dark:text-${config.color}-400`,
      warning: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
      success: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
      danger: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
      info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
    };
    return variants[variant] || variants.default;
  };

  return (
    <Card 
      className={`${config.bgColor} ${config.borderColor} border rounded-xl overflow-hidden transition-all hover:shadow-md`}
      data-testid={testId}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          {/* Icon */}
          <div className={`${config.iconBg} p-2.5 rounded-xl flex-shrink-0`}>
            <IconComponent className={`w-5 h-5 ${config.iconColor}`} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Header Row */}
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="min-w-0">
                <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                  {title}
                </h3>
                {subtitle && (
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 truncate">
                    {subtitle}
                  </p>
                )}
              </div>
              
              {/* Amount or Badge */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {amount && (
                  <span className={`text-lg font-bold ${config.iconColor}`}>
                    {formatCurrency(amount)}
                  </span>
                )}
                {badge && (
                  <Badge className={getBadgeClasses(badgeVariant)}>
                    {badge}
                  </Badge>
                )}
              </div>
            </div>

            {/* Description */}
            {description && (
              <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-3">
                {description}
              </p>
            )}

            {/* Meta Info */}
            {(meta.length > 0 || requestedBy || requestedAt) && (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400 mb-3">
                {requestedBy && (
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {requestedBy}
                  </span>
                )}
                {requestedAt && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {formatDate(requestedAt)}
                  </span>
                )}
                {meta.map((item, idx) => (
                  <span key={idx} className="flex items-center gap-1">
                    {item.icon && <item.icon className="w-3 h-3" />}
                    {item.label}
                  </span>
                ))}
              </div>
            )}

            {/* Required By Badge */}
            {requiredBy && (
              <div className="flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400 mb-3">
                <Clock className="w-3 h-3" />
                Pending: <strong>{requiredBy}</strong>
              </div>
            )}

            {/* Custom Children */}
            {children}

            {/* Actions */}
            {(onApprove || onReject || onView) && (
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-zinc-200/50 dark:border-zinc-700/50">
                {onView && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={onView}
                    disabled={loading}
                    className="text-zinc-600 dark:text-zinc-400"
                  >
                    <Eye className="w-4 h-4 mr-1" />
                    View
                  </Button>
                )}
                {onReject && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={onReject}
                    disabled={loading}
                    className="text-red-600 border-red-200 hover:bg-red-50 dark:border-red-800 dark:hover:bg-red-900/20"
                  >
                    <XCircle className="w-4 h-4 mr-1" />
                    Reject
                  </Button>
                )}
                {onApprove && (
                  <Button
                    size="sm"
                    onClick={onApprove}
                    disabled={loading}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  >
                    <CheckCircle className="w-4 h-4 mr-1" />
                    Approve
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// Stat Card Component for the summary row
export const StatCard = ({
  label,
  count,
  icon: Icon,
  color = 'zinc',
  onClick,
  active = false,
  isDark = false
}) => {
  const colorClasses = {
    yellow: { text: 'text-yellow-600', bg: 'bg-yellow-500/10', border: 'border-yellow-400' },
    purple: { text: 'text-purple-600', bg: 'bg-purple-500/10', border: 'border-purple-400' },
    indigo: { text: 'text-indigo-600', bg: 'bg-indigo-500/10', border: 'border-indigo-400' },
    orange: { text: 'text-orange-600', bg: 'bg-orange-500/10', border: 'border-orange-400' },
    rose: { text: 'text-rose-600', bg: 'bg-rose-500/10', border: 'border-rose-400' },
    blue: { text: 'text-blue-600', bg: 'bg-blue-500/10', border: 'border-blue-400' },
    pink: { text: 'text-pink-600', bg: 'bg-pink-500/10', border: 'border-pink-400' },
    emerald: { text: 'text-emerald-600', bg: 'bg-emerald-500/10', border: 'border-emerald-400' },
    red: { text: 'text-red-600', bg: 'bg-red-500/10', border: 'border-red-400' },
    zinc: { text: 'text-zinc-600', bg: 'bg-zinc-500/10', border: 'border-zinc-400' }
  };

  const colors = colorClasses[color] || colorClasses.zinc;

  return (
    <button
      onClick={onClick}
      className={`
        w-full p-3 rounded-xl border-2 transition-all text-left
        ${active ? colors.border : 'border-transparent'}
        ${isDark ? 'bg-zinc-800 hover:bg-zinc-700' : 'bg-white hover:bg-zinc-50'}
        ${onClick ? 'cursor-pointer' : 'cursor-default'}
        shadow-sm hover:shadow-md
      `}
    >
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${colors.bg}`}>
          <Icon className={`w-4 h-4 ${colors.text}`} />
        </div>
        <div className="min-w-0">
          <p className={`text-2xl font-bold ${colors.text}`}>{count}</p>
          <p className={`text-[10px] uppercase tracking-wide truncate ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            {label}
          </p>
        </div>
      </div>
    </button>
  );
};

export default ApprovalCard;
