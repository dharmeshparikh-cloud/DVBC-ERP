import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Sales Funnel Stage Flow:
 * 1. Lead → 2. Meeting → 3. Pricing Plan → 4. SOW → 5. Quotation → 6. Agreement → 7. Payment → 8. Kickoff → 9. Closed
 * 
 * Role-Based Access:
 * - Sales Executive: Lead, Meeting, Pricing (guided mode)
 * - Sales Manager/Senior: Full pipeline (monitoring mode)
 * - Principal Consultant: Reportees view (monitoring mode)
 * - Admin: Full control
 */

// Stage definitions with prerequisites
export const SALES_STAGES = {
  LEAD: { id: 1, name: 'Lead', path: '/leads', prerequisite: null },
  MEETING: { id: 2, name: 'Meeting', path: '/sales-funnel/meetings', prerequisite: 'LEAD' },
  PRICING: { id: 3, name: 'Pricing Plan', path: '/sales-funnel/pricing-plans', prerequisite: 'MEETING' },
  SOW: { id: 4, name: 'SOW', path: '/sales-funnel/sow', prerequisite: 'PRICING' },
  QUOTATION: { id: 5, name: 'Quotation', path: '/sales-funnel/quotations', prerequisite: 'SOW' },
  AGREEMENT: { id: 6, name: 'Agreement', path: '/agreements', prerequisite: 'QUOTATION' },
  PAYMENT: { id: 7, name: 'Payment', path: '/sales-funnel/payment-verification', prerequisite: 'AGREEMENT' },
  KICKOFF: { id: 8, name: 'Kickoff', path: '/kickoff-requests', prerequisite: 'PAYMENT' },
  CLOSED: { id: 9, name: 'Closed', path: '/projects', prerequisite: 'KICKOFF' }
};

// Stage order for navigation
export const STAGE_ORDER = ['LEAD', 'MEETING', 'PRICING', 'SOW', 'QUOTATION', 'AGREEMENT', 'PAYMENT', 'KICKOFF', 'CLOSED'];

// Role-based stage access configuration
export const ROLE_STAGE_ACCESS = {
  // Sales Executive - Guided mode, limited stages
  executive: {
    mode: 'guided',
    visibleStages: ['LEAD', 'MEETING', 'PRICING'],
    canSkipStages: false,
    sidebarItems: [
      { key: 'my-leads', name: 'My Leads', path: '/leads', stage: 'LEAD' },
      { key: 'todays-tasks', name: "Today's Tasks", path: '/follow-ups', stage: null },
    ]
  },
  
  // Sales Manager - Monitoring mode, full view
  sales_manager: {
    mode: 'monitoring',
    visibleStages: STAGE_ORDER,
    canSkipStages: false,
    sidebarItems: 'full'
  },
  
  // Senior Consultant - Monitoring mode
  senior_consultant: {
    mode: 'monitoring',
    visibleStages: STAGE_ORDER,
    canSkipStages: false,
    sidebarItems: 'full'
  },
  
  // Principal Consultant - Monitoring + Reportees
  principal_consultant: {
    mode: 'monitoring',
    visibleStages: STAGE_ORDER,
    canSkipStages: false,
    sidebarItems: 'full',
    hasReporteesView: true
  },
  
  // Manager - Full monitoring
  manager: {
    mode: 'monitoring',
    visibleStages: STAGE_ORDER,
    canSkipStages: false,
    sidebarItems: 'full'
  },
  
  sr_manager: {
    mode: 'monitoring',
    visibleStages: STAGE_ORDER,
    canSkipStages: false,
    sidebarItems: 'full'
  },
  
  // Admin - Full control
  admin: {
    mode: 'control',
    visibleStages: STAGE_ORDER,
    canSkipStages: true,
    sidebarItems: 'full'
  }
};

// Get missing stages between current and target
export const getMissingStages = (currentStage, targetStage) => {
  const currentIdx = STAGE_ORDER.indexOf(currentStage);
  const targetIdx = STAGE_ORDER.indexOf(targetStage);
  
  if (targetIdx <= currentIdx) return [];
  
  return STAGE_ORDER.slice(currentIdx + 1, targetIdx);
};

// Get stage by path
export const getStageByPath = (path) => {
  for (const [key, stage] of Object.entries(SALES_STAGES)) {
    if (path.startsWith(stage.path)) return key;
  }
  return null;
};

// Get next stage
export const getNextStage = (currentStage) => {
  const idx = STAGE_ORDER.indexOf(currentStage);
  if (idx === -1 || idx >= STAGE_ORDER.length - 1) return null;
  return STAGE_ORDER[idx + 1];
};

// Stage Guard Context
const StageGuardContext = createContext(null);

export const StageGuardProvider = ({ children }) => {
  const navigate = useNavigate();
  const [dialogState, setDialogState] = useState({
    isOpen: false,
    type: null, // 'blocked', 'complete', 'prompt'
    currentStage: null,
    targetStage: null,
    missingStages: [],
    message: '',
    leadId: null
  });
  
  const [leadStages, setLeadStages] = useState({}); // leadId -> currentStage mapping

  // Fetch lead's current stage
  const fetchLeadStage = useCallback(async (leadId) => {
    if (!leadId || leadStages[leadId]) return leadStages[leadId];
    
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/leads/${leadId}/stage`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setLeadStages(prev => ({ ...prev, [leadId]: data.current_stage }));
        return data.current_stage;
      }
    } catch (error) {
      console.error('Error fetching lead stage:', error);
    }
    return 'LEAD';
  }, [leadStages]);

  // Check if user can access a stage
  const canAccessStage = useCallback((targetStage, currentStage, userRole) => {
    const roleConfig = ROLE_STAGE_ACCESS[userRole] || ROLE_STAGE_ACCESS.executive;
    
    // Admin can skip stages
    if (roleConfig.canSkipStages) return true;
    
    // Check if target stage is visible for this role
    if (!roleConfig.visibleStages.includes(targetStage)) return false;
    
    const currentIdx = STAGE_ORDER.indexOf(currentStage);
    const targetIdx = STAGE_ORDER.indexOf(targetStage);
    
    // Can only access current or previous stages
    return targetIdx <= currentIdx;
  }, []);

  // Attempt to navigate to a stage
  const attemptStageNavigation = useCallback(async (targetStage, leadId, userRole) => {
    const currentStage = leadId ? await fetchLeadStage(leadId) : 'LEAD';
    
    if (canAccessStage(targetStage, currentStage, userRole)) {
      navigate(SALES_STAGES[targetStage].path + (leadId ? `?lead=${leadId}` : ''));
      return true;
    }
    
    // Show blocked dialog
    const missingStages = getMissingStages(currentStage, targetStage);
    setDialogState({
      isOpen: true,
      type: 'blocked',
      currentStage,
      targetStage,
      missingStages,
      message: `Complete ${missingStages.map(s => SALES_STAGES[s].name).join(' → ')} before accessing ${SALES_STAGES[targetStage].name}.`,
      leadId
    });
    
    return false;
  }, [fetchLeadStage, canAccessStage, navigate]);

  // Show stage completion prompt
  const showCompletionPrompt = useCallback((completedStage, leadId) => {
    const nextStage = getNextStage(completedStage);
    if (!nextStage) return;
    
    setDialogState({
      isOpen: true,
      type: 'complete',
      currentStage: completedStage,
      targetStage: nextStage,
      missingStages: [],
      message: `${SALES_STAGES[completedStage].name} completed successfully! Ready to proceed to ${SALES_STAGES[nextStage].name}?`,
      leadId
    });
    
    // Update lead stage
    setLeadStages(prev => ({ ...prev, [leadId]: nextStage }));
  }, []);

  // Close dialog
  const closeDialog = useCallback(() => {
    setDialogState(prev => ({ ...prev, isOpen: false }));
  }, []);

  // Navigate to required stage from dialog
  const goToRequiredStage = useCallback(() => {
    const { missingStages, leadId } = dialogState;
    if (missingStages.length > 0) {
      const firstMissing = missingStages[0];
      navigate(SALES_STAGES[firstMissing].path + (leadId ? `?lead=${leadId}` : ''));
    }
    closeDialog();
  }, [dialogState, navigate, closeDialog]);

  // Navigate to next stage from completion prompt
  const proceedToNextStage = useCallback(() => {
    const { targetStage, leadId } = dialogState;
    if (targetStage) {
      navigate(SALES_STAGES[targetStage].path + (leadId ? `?lead=${leadId}` : ''));
    }
    closeDialog();
  }, [dialogState, navigate, closeDialog]);

  // Get visible sidebar items for role
  const getVisibleSidebarItems = useCallback((userRole) => {
    const roleConfig = ROLE_STAGE_ACCESS[userRole] || ROLE_STAGE_ACCESS.executive;
    
    if (roleConfig.sidebarItems === 'full') {
      return null; // Return null to indicate full menu should be shown
    }
    
    return roleConfig.sidebarItems;
  }, []);

  // Check if role is in guided mode
  const isGuidedMode = useCallback((userRole) => {
    const roleConfig = ROLE_STAGE_ACCESS[userRole] || ROLE_STAGE_ACCESS.executive;
    return roleConfig.mode === 'guided';
  }, []);

  // Get role access mode
  const getAccessMode = useCallback((userRole) => {
    const roleConfig = ROLE_STAGE_ACCESS[userRole] || ROLE_STAGE_ACCESS.executive;
    return roleConfig.mode;
  }, []);

  const value = {
    dialogState,
    leadStages,
    fetchLeadStage,
    canAccessStage,
    attemptStageNavigation,
    showCompletionPrompt,
    closeDialog,
    goToRequiredStage,
    proceedToNextStage,
    getVisibleSidebarItems,
    isGuidedMode,
    getAccessMode,
    SALES_STAGES,
    STAGE_ORDER
  };

  return (
    <StageGuardContext.Provider value={value}>
      {children}
    </StageGuardContext.Provider>
  );
};

export const useStageGuard = () => {
  const context = useContext(StageGuardContext);
  if (!context) {
    throw new Error('useStageGuard must be used within a StageGuardProvider');
  }
  return context;
};

export default StageGuardContext;
