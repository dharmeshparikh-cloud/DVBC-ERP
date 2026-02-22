import React, { useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useStageGuard, ROLE_STAGE_ACCESS, SALES_STAGES, STAGE_ORDER } from '../contexts/StageGuardContext';
import { 
  Users, FileText, FileCheck, CreditCard, Briefcase, BarChart3, 
  CalendarCheck, Building2, Receipt, Target, ArrowRight, CheckCircle2,
  Circle, Lock
} from 'lucide-react';
import { Button } from './ui/button';

/**
 * GuidedSalesSidebar - Renders sales sidebar based on user role and current stage
 * 
 * Modes:
 * - guided: Shows limited items with "Move to Next Stage" button
 * - monitoring: Shows full pipeline for managers
 * - control: Full access for admins
 */

// Full sales menu items (for monitoring/control modes)
const FULL_SALES_ITEMS = [
  { key: 'sales-dashboard', name: 'Sales Dashboard', path: '/sales-dashboard', icon: BarChart3, stage: null },
  { key: 'leads', name: 'Leads', path: '/leads', icon: Users, stage: 'LEAD' },
  { key: 'team-leads', name: 'Team Leads', path: '/manager-leads', icon: Users, stage: null, managerOnly: true },
  { key: 'target-management', name: 'Target Management', path: '/target-management', icon: Target, managerOnly: true },
  { key: 'meetings', name: 'Sales Meetings', path: '/sales-funnel/meetings', icon: CalendarCheck, stage: 'MEETING' },
  { key: 'pricing-plans', name: 'SOW & Pricing', path: '/sales-funnel/pricing-plans', icon: FileText, stage: 'PRICING' },
  { key: 'sow', name: 'SOW Generator', path: '/sales-funnel/sow', icon: FileText, stage: 'SOW' },
  { key: 'quotations', name: 'Quotations', path: '/sales-funnel/quotations', icon: Receipt, stage: 'QUOTATION' },
  { key: 'agreements', name: 'Agreements', path: '/agreements', icon: FileCheck, stage: 'AGREEMENT' },
  { key: 'payment-verification', name: 'Payment Verification', path: '/sales-funnel/payment-verification', icon: CreditCard, stage: 'PAYMENT' },
  { key: 'kickoff-requests', name: 'Kickoff Requests', path: '/kickoff-requests', icon: Briefcase, stage: 'KICKOFF' },
  { key: 'clients', name: 'Clients', path: '/clients', icon: Building2, stage: null },
  { key: 'invoices', name: 'Invoices', path: '/invoices', icon: Receipt, stage: null },
  { key: 'follow-ups', name: 'Lead Follow-ups', path: '/follow-ups', icon: CalendarCheck, stage: null },
  { key: 'sales-reports', name: 'Sales Reports', path: '/reports?category=sales', icon: BarChart3, stage: null },
];

// Guided mode items for sales executives
const GUIDED_SALES_ITEMS = [
  { key: 'my-leads', name: 'My Leads', path: '/leads', icon: Users, stage: 'LEAD' },
  { key: 'todays-tasks', name: "Today's Follow-ups", path: '/follow-ups', icon: CalendarCheck, stage: null },
];

const GuidedSalesSidebar = ({ 
  user, 
  isDark, 
  expanded, 
  isActive,
  NavLink,
  currentLeadId = null 
}) => {
  const location = useLocation();
  const { 
    getAccessMode, 
    isGuidedMode,
    leadStages,
    attemptStageNavigation 
  } = useStageGuard();

  const userRole = user?.role || 'executive';
  const accessMode = getAccessMode(userRole);
  const roleConfig = ROLE_STAGE_ACCESS[userRole] || ROLE_STAGE_ACCESS.executive;

  // Get current lead's stage
  const currentLeadStage = leadStages[currentLeadId] || 'LEAD';
  const currentStageIdx = STAGE_ORDER.indexOf(currentLeadStage);

  // Filter items based on role and mode
  const visibleItems = useMemo(() => {
    if (accessMode === 'guided') {
      return GUIDED_SALES_ITEMS;
    }

    // For monitoring/control modes, filter based on role
    return FULL_SALES_ITEMS.filter(item => {
      // Manager-only items
      if (item.managerOnly && !['admin', 'manager', 'sr_manager', 'sales_manager', 'principal_consultant'].includes(userRole)) {
        return false;
      }
      return true;
    });
  }, [accessMode, userRole]);

  // Get next stage for guided mode
  const nextStage = useMemo(() => {
    if (currentStageIdx < STAGE_ORDER.length - 1) {
      return STAGE_ORDER[currentStageIdx + 1];
    }
    return null;
  }, [currentStageIdx]);

  // Render stage indicator for monitoring mode
  const StageIndicator = ({ stage }) => {
    if (!stage) return null;
    
    const stageIdx = STAGE_ORDER.indexOf(stage);
    const isCompleted = stageIdx < currentStageIdx;
    const isCurrent = stageIdx === currentStageIdx;
    const isLocked = stageIdx > currentStageIdx;

    if (isCompleted) {
      return <CheckCircle2 className="w-3 h-3 text-emerald-500" />;
    }
    if (isCurrent) {
      return <Circle className="w-3 h-3 text-amber-500 fill-amber-500" />;
    }
    if (isLocked && accessMode !== 'control') {
      return <Lock className="w-3 h-3 text-zinc-400" />;
    }
    return <Circle className="w-3 h-3 text-zinc-300" />;
  };

  // Handle stage click with validation
  const handleStageClick = (item, e) => {
    if (!item.stage) return; // Non-stage items navigate normally
    
    const stageIdx = STAGE_ORDER.indexOf(item.stage);
    
    // If trying to access a future stage
    if (stageIdx > currentStageIdx && accessMode !== 'control') {
      e.preventDefault();
      attemptStageNavigation(item.stage, currentLeadId, userRole);
    }
  };

  return (
    <>
      {visibleItems.map(item => (
        <div key={item.key} className="relative">
          {accessMode !== 'guided' && item.stage && (
            <div className="absolute left-2 top-1/2 -translate-y-1/2 z-10">
              <StageIndicator stage={item.stage} />
            </div>
          )}
          <Link
            to={item.path}
            onClick={(e) => handleStageClick(item, e)}
            data-testid={`nav-${item.key}`}
            className={`flex items-center gap-2.5 px-3 py-2 md:py-1.5 rounded-md md:rounded-sm text-sm md:text-[13px] transition-colors ${
              accessMode !== 'guided' && item.stage ? 'pl-7' : ''
            } ${
              isActive(item.path)
                ? isDark 
                  ? 'bg-zinc-800 text-zinc-100 font-medium' 
                  : 'bg-zinc-100 text-zinc-950 font-medium' 
                : isDark 
                  ? 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50' 
                  : 'text-zinc-600 hover:text-zinc-950 hover:bg-zinc-50'
            }`}
          >
            <item.icon className="w-4 h-4 md:w-3.5 md:h-3.5 flex-shrink-0" strokeWidth={1.5} />
            <span className="truncate flex-1">{item.name}</span>
          </Link>
        </div>
      ))}

      {/* Move to Next Stage Button (Guided Mode Only) */}
      {accessMode === 'guided' && nextStage && currentLeadId && (
        <div className="mt-3 px-2">
          <Button
            onClick={() => attemptStageNavigation(nextStage, currentLeadId, userRole)}
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white text-sm"
            data-testid="move-to-next-stage-btn"
          >
            <span>Move to {SALES_STAGES[nextStage]?.name}</span>
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      )}

      {/* Stage Progress (Guided Mode Only) */}
      {accessMode === 'guided' && (
        <div className="mt-4 px-3">
          <div className={`text-xs font-medium mb-2 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
            Your Progress
          </div>
          <div className="flex items-center gap-1">
            {roleConfig.visibleStages.map((stage, idx) => {
              const stageIdx = STAGE_ORDER.indexOf(stage);
              const isCompleted = stageIdx < currentStageIdx;
              const isCurrent = stageIdx === currentStageIdx;
              
              return (
                <React.Fragment key={stage}>
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      isCompleted 
                        ? 'bg-emerald-500 text-white' 
                        : isCurrent 
                          ? 'bg-amber-500 text-white' 
                          : isDark 
                            ? 'bg-zinc-700 text-zinc-400' 
                            : 'bg-zinc-200 text-zinc-500'
                    }`}
                    title={SALES_STAGES[stage]?.name}
                  >
                    {isCompleted ? '✓' : idx + 1}
                  </div>
                  {idx < roleConfig.visibleStages.length - 1 && (
                    <div className={`flex-1 h-0.5 ${isCompleted ? 'bg-emerald-500' : isDark ? 'bg-zinc-700' : 'bg-zinc-200'}`} />
                  )}
                </React.Fragment>
              );
            })}
          </div>
          <div className={`text-[10px] mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
            Current: {SALES_STAGES[STAGE_ORDER[currentStageIdx]]?.name || 'Lead'}
          </div>
        </div>
      )}
    </>
  );
};

export default GuidedSalesSidebar;
