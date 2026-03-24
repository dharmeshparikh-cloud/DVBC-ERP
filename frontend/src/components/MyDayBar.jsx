/**
 * MyDayBar.jsx - Daily workflow tracker for consultants
 * 
 * Shows: Attendance → Today's Meetings → Overdue MOMs → Pending Expenses → Weekly Progress
 * Contextual reminders for missed steps in the daily flow.
 * ADDITIVE component — placed above existing meeting list.
 * 
 * ENHANCED: Clickable cards that navigate to respective pages, show "Completed" when done.
 * NEW: Smart Suggestions - AI-powered recommendations for next actions.
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { 
  Clock, CheckCircle2, XCircle, Calendar, FileText, 
  Receipt, AlertTriangle, ArrowRight, TrendingUp,
  CircleDot, ExternalLink, Sparkles, ChevronRight,
  Send, CheckSquare, Wallet, Trophy, CalendarCheck
} from 'lucide-react';

const MyDayBar = () => {
  const navigate = useNavigate();
  const [showAllSuggestions, setShowAllSuggestions] = useState(false);
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['my-day-summary'],
    queryFn: async () => {
      const res = await axios.get(`${API}/my-day/summary`);
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="mb-6 p-4 bg-zinc-50 border border-zinc-200 rounded-lg animate-pulse">
        <div className="h-5 bg-zinc-200 rounded w-48 mb-3" />
        <div className="flex gap-4">
          <div className="h-16 bg-zinc-200 rounded flex-1" />
          <div className="h-16 bg-zinc-200 rounded flex-1" />
          <div className="h-16 bg-zinc-200 rounded flex-1" />
          <div className="h-16 bg-zinc-200 rounded flex-1" />
        </div>
      </div>
    );
  }

  if (error || !data) return null;

  const { attendance, today, action_required, weekly_progress, greeting, smart_suggestions = [] } = data;
  const hasUrgentActions = !attendance.is_checked_in || 
    action_required.overdue_moms.count > 0 || 
    action_required.missing_expenses.count > 0;

  // Navigation handlers
  const handleNavigate = (path) => {
    navigate(path);
  };

  return (
    <div className="mb-6 space-y-3" data-testid="my-day-bar">
      {/* Greeting & Date */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-900" data-testid="my-day-greeting">
          {greeting}
        </h2>
        <div className="flex items-center gap-2">
          <Badge className="bg-zinc-100 text-zinc-600 text-xs font-normal">
            <Calendar className="w-3 h-3 mr-1" />
            {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'short' })}
          </Badge>
          {weekly_progress.completion_pct > 0 && (
            <Badge className="bg-emerald-50 text-emerald-700 text-xs font-normal">
              <TrendingUp className="w-3 h-3 mr-1" />
              Week: {weekly_progress.completion_pct}%
            </Badge>
          )}
        </div>
      </div>

      {/* Action Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Attendance Card - Clickable */}
        <ActionCard
          icon={attendance.is_checked_in ? CheckCircle2 : Clock}
          label="Attendance"
          value={attendance.is_checked_in ? `In at ${formatTime(attendance.check_in_time)}` : 'Not marked'}
          status={attendance.is_checked_in ? 'success' : 'danger'}
          testId="my-day-attendance"
          onClick={() => handleNavigate('/my-attendance')}
          isComplete={attendance.is_checked_in}
          actionText={attendance.is_checked_in ? 'Completed' : 'Check In'}
        />

        {/* Today's Meetings Card - Clickable */}
        <ActionCard
          icon={Calendar}
          label="Today"
          value={today.total_meetings === 0 
            ? 'No meetings' 
            : `${today.total_meetings} meeting${today.total_meetings > 1 ? 's' : ''}`}
          subtitle={today.next_meeting ? `Next: ${today.next_meeting.time}` : null}
          status={today.total_meetings > 0 ? 'info' : 'neutral'}
          testId="my-day-today"
          onClick={() => handleNavigate('/consulting-meetings')}
          isComplete={today.total_meetings === 0}
          actionText={today.total_meetings > 0 ? 'View' : 'No Action'}
        />

        {/* Overdue MOMs Card - Clickable */}
        <ActionCard
          icon={action_required.overdue_moms.count > 0 ? AlertTriangle : FileText}
          label="MOM Status"
          value={action_required.overdue_moms.count === 0 
            ? 'All clear' 
            : `${action_required.overdue_moms.count} overdue`}
          status={action_required.overdue_moms.count > 0 ? 'warning' : 'success'}
          testId="my-day-mom"
          onClick={() => handleNavigate('/consulting-meetings')}
          isComplete={action_required.overdue_moms.count === 0}
          actionText={action_required.overdue_moms.count > 0 ? 'Record Now' : 'Completed'}
        />

        {/* Expenses Card - Clickable */}
        <ActionCard
          icon={Receipt}
          label="Expenses"
          value={action_required.pending_expenses === 0 && action_required.missing_expenses.count === 0
            ? 'All clear' 
            : action_required.pending_expenses > 0 
              ? `${action_required.pending_expenses} pending`
              : 'None pending'}
          subtitle={action_required.missing_expenses.count > 0 
            ? `${action_required.missing_expenses.count} meeting${action_required.missing_expenses.count > 1 ? 's' : ''} need expense` 
            : null}
          status={action_required.missing_expenses.count > 0 ? 'warning' : (action_required.pending_expenses > 0 ? 'info' : 'success')}
          testId="my-day-expenses"
          onClick={() => handleNavigate('/my-expenses')}
          isComplete={action_required.pending_expenses === 0 && action_required.missing_expenses.count === 0}
          actionText={action_required.missing_expenses.count > 0 ? 'File Expense' : (action_required.pending_expenses > 0 ? 'View' : 'Completed')}
        />
      </div>

      {/* Contextual Reminders — only shown when actions needed */}
      {hasUrgentActions && (
        <div className="flex flex-wrap gap-2" data-testid="my-day-reminders">
          {!attendance.is_checked_in && (
            <ReminderChip 
              color="red" 
              icon={XCircle} 
              text="Mark attendance" 
              testId="reminder-attendance"
              onClick={() => handleNavigate('/my-attendance')}
            />
          )}
          {action_required.overdue_moms.count > 0 && (
            <ReminderChip 
              color="amber" 
              icon={FileText} 
              text={`${action_required.overdue_moms.count} MOM${action_required.overdue_moms.count > 1 ? 's' : ''} overdue — record now`}
              testId="reminder-mom"
              onClick={() => handleNavigate('/consulting-meetings')}
            />
          )}
          {action_required.missing_expenses.count > 0 && (
            <ReminderChip 
              color="amber" 
              icon={Receipt} 
              text={`File expense for in-person meeting${action_required.missing_expenses.count > 1 ? 's' : ''}`}
              testId="reminder-expense"
              onClick={() => handleNavigate('/my-expenses')}
            />
          )}
          {action_required.pending_client_send.count > 0 && (
            <ReminderChip 
              color="blue" 
              icon={ArrowRight} 
              text={`${action_required.pending_client_send.count} MOM not sent to client`}
              testId="reminder-client-send"
              onClick={() => handleNavigate('/consulting-meetings')}
            />
          )}
          {action_required.open_tasks > 0 && (
            <ReminderChip 
              color="purple" 
              icon={CircleDot} 
              text={`${action_required.open_tasks} open action item${action_required.open_tasks > 1 ? 's' : ''}`}
              testId="reminder-tasks"
              onClick={() => handleNavigate('/consulting-meetings')}
            />
          )}
        </div>
      )}

      {/* Smart Suggestions - AI-powered recommendations */}
      {smart_suggestions.length > 0 && (
        <div className="bg-gradient-to-r from-violet-50 via-purple-50 to-fuchsia-50 border border-violet-200 rounded-lg p-3" data-testid="my-day-suggestions">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="p-1 bg-violet-100 rounded">
                <Sparkles className="w-3.5 h-3.5 text-violet-600" />
              </div>
              <span className="text-sm font-medium text-violet-900">Smart Suggestions</span>
              <Badge className="bg-violet-100 text-violet-700 text-[10px] px-1.5 py-0 h-4">
                AI
              </Badge>
            </div>
            {smart_suggestions.length > 2 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs text-violet-600 hover:text-violet-800 hover:bg-violet-100 px-2"
                onClick={() => setShowAllSuggestions(!showAllSuggestions)}
              >
                {showAllSuggestions ? 'Show less' : `+${smart_suggestions.length - 2} more`}
              </Button>
            )}
          </div>
          
          <div className="space-y-2">
            {(showAllSuggestions ? smart_suggestions : smart_suggestions.slice(0, 2)).map((suggestion) => (
              <SuggestionCard
                key={suggestion.id}
                suggestion={suggestion}
                onAction={() => suggestion.action_path && handleNavigate(suggestion.action_path)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Weekly Progress Bar */}
      {weekly_progress.total_meetings > 0 && (
        <div className="flex items-center gap-3 px-3 py-2 bg-zinc-50 border border-zinc-200 rounded-lg" data-testid="my-day-weekly">
          <span className="text-xs text-zinc-500 whitespace-nowrap">This Week</span>
          <div className="flex-1 h-2 bg-zinc-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-emerald-500 rounded-full transition-all duration-500"
              style={{ width: `${weekly_progress.completion_pct}%` }}
            />
          </div>
          <span className="text-xs text-zinc-600 whitespace-nowrap">
            {weekly_progress.delivered}/{weekly_progress.total_meetings} delivered
            {weekly_progress.mom_recorded > 0 && ` · ${weekly_progress.mom_recorded} MOMs`}
          </span>
        </div>
      )}
    </div>
  );
};

// === Sub-components ===

const ACTION_STYLES = {
  success: 'bg-emerald-50 border-emerald-200 hover:bg-emerald-100',
  danger: 'bg-red-50 border-red-200 hover:bg-red-100',
  warning: 'bg-amber-50 border-amber-200 hover:bg-amber-100',
  info: 'bg-blue-50 border-blue-200 hover:bg-blue-100',
  neutral: 'bg-zinc-50 border-zinc-200 hover:bg-zinc-100',
};

const ICON_STYLES = {
  success: 'text-emerald-600',
  danger: 'text-red-600',
  warning: 'text-amber-600',
  info: 'text-blue-600',
  neutral: 'text-zinc-400',
};

const ActionCard = ({ icon: Icon, label, value, subtitle, status = 'neutral', testId, onClick, isComplete, actionText }) => (
  <div 
    className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all duration-200 ${ACTION_STYLES[status]}`} 
    data-testid={testId}
    onClick={onClick}
    role="button"
    tabIndex={0}
    onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
  >
    <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${ICON_STYLES[status]}`} />
    <div className="min-w-0 flex-1">
      <div className="flex items-center justify-between">
        <p className="text-[11px] text-zinc-500 uppercase tracking-wide">{label}</p>
        {isComplete && (
          <Badge className="bg-emerald-100 text-emerald-700 text-[10px] px-1.5 py-0 h-4">
            <CheckCircle2 className="w-2.5 h-2.5 mr-0.5" />
            Done
          </Badge>
        )}
      </div>
      <p className="text-sm font-medium text-zinc-900 truncate">{value}</p>
      {subtitle && <p className="text-[11px] text-zinc-500 truncate">{subtitle}</p>}
      {actionText && !isComplete && (
        <div className="flex items-center gap-1 mt-1">
          <span className="text-[10px] font-medium text-zinc-600">{actionText}</span>
          <ExternalLink className="w-2.5 h-2.5 text-zinc-400" />
        </div>
      )}
    </div>
  </div>
);

const CHIP_COLORS = {
  red: 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100',
  amber: 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100',
  blue: 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100',
  purple: 'bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100',
};

const ReminderChip = ({ color, icon: Icon, text, testId, onClick }) => (
  <div 
    className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border cursor-pointer transition-all duration-200 ${CHIP_COLORS[color]}`} 
    data-testid={testId}
    onClick={onClick}
    role="button"
    tabIndex={0}
    onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
  >
    <Icon className="w-3 h-3" />
    {text}
    <ArrowRight className="w-3 h-3 ml-0.5" />
  </div>
);

// === Smart Suggestion Components ===

const SUGGESTION_ICONS = {
  'clock': Clock,
  'calendar': Calendar,
  'calendar-check': CalendarCheck,
  'file-text': FileText,
  'send': Send,
  'check-square': CheckSquare,
  'receipt': Receipt,
  'wallet': Wallet,
  'trophy': Trophy,
  'trending-up': TrendingUp,
};

const PRIORITY_STYLES = {
  high: {
    border: 'border-l-red-500',
    bg: 'bg-white',
    iconBg: 'bg-red-100',
    iconColor: 'text-red-600',
    badge: 'bg-red-100 text-red-700',
  },
  medium: {
    border: 'border-l-amber-500',
    bg: 'bg-white',
    iconBg: 'bg-amber-100',
    iconColor: 'text-amber-600',
    badge: 'bg-amber-100 text-amber-700',
  },
  low: {
    border: 'border-l-blue-500',
    bg: 'bg-white',
    iconBg: 'bg-blue-100',
    iconColor: 'text-blue-600',
    badge: 'bg-blue-100 text-blue-700',
  },
  info: {
    border: 'border-l-emerald-500',
    bg: 'bg-white',
    iconBg: 'bg-emerald-100',
    iconColor: 'text-emerald-600',
    badge: 'bg-emerald-100 text-emerald-700',
  },
};

const SuggestionCard = ({ suggestion, onAction }) => {
  const Icon = SUGGESTION_ICONS[suggestion.icon] || Sparkles;
  const style = PRIORITY_STYLES[suggestion.priority] || PRIORITY_STYLES.low;
  
  return (
    <div 
      className={`flex items-start gap-3 p-2.5 rounded-lg border border-l-4 ${style.border} ${style.bg} cursor-pointer hover:shadow-sm transition-all duration-200`}
      onClick={onAction}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onAction?.()}
      data-testid={`suggestion-${suggestion.id}`}
    >
      <div className={`p-1.5 rounded ${style.iconBg} shrink-0`}>
        <Icon className={`w-4 h-4 ${style.iconColor}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-zinc-900 truncate">{suggestion.title}</p>
          {suggestion.priority === 'high' && (
            <Badge className={`${style.badge} text-[9px] px-1 py-0 h-3.5`}>
              Priority
            </Badge>
          )}
        </div>
        <p className="text-xs text-zinc-500 mt-0.5 line-clamp-1">{suggestion.description}</p>
      </div>
      {suggestion.action && (
        <div className="flex items-center shrink-0">
          <span className="text-xs font-medium text-violet-600 mr-1">{suggestion.action}</span>
          <ChevronRight className="w-3.5 h-3.5 text-violet-400" />
        </div>
      )}
    </div>
  );
};

const formatTime = (time) => {
  if (!time) return '--';
  try {
    if (time.includes('T') || time.includes(':')) {
      const d = new Date(time.includes('T') ? time : `2000-01-01T${time}`);
      return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
    }
    return time;
  } catch {
    return time;
  }
};

export default MyDayBar;
