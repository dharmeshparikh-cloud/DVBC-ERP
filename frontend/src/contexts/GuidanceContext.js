import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API } from '../App';

const GuidanceContext = createContext();

// Workflow definitions with steps
export const WORKFLOWS = {
  // ========== ATTENDANCE ==========
  attendance_checkin: {
    id: 'attendance_checkin',
    title: 'Daily Check-in',
    description: 'Mark your attendance for the day',
    steps: [
      { id: 1, title: 'Go to My Attendance', route: '/my-attendance', action: 'Navigate to attendance page' },
      { id: 2, title: 'Click Check-in', action: 'Click the Check-in button' },
      { id: 3, title: 'Confirm Location', action: 'Allow location or enter manually' },
      { id: 4, title: 'Done!', action: 'Your attendance is recorded' }
    ]
  },
  attendance_regularize: {
    id: 'attendance_regularize',
    title: 'Regularize Attendance',
    description: 'Request attendance correction',
    steps: [
      { id: 1, title: 'Go to My Attendance', route: '/my-attendance' },
      { id: 2, title: 'Find Missing Day', action: 'Locate the day to regularize' },
      { id: 3, title: 'Click Regularize', action: 'Submit regularization request' },
      { id: 4, title: 'Add Reason', action: 'Provide reason for correction' },
      { id: 5, title: 'Submit', action: 'Wait for manager approval' }
    ]
  },

  // ========== LEAVE MANAGEMENT ==========
  leave_request: {
    id: 'leave_request',
    title: 'Apply for Leave',
    description: 'Submit a leave request',
    steps: [
      { id: 1, title: 'Go to My Leaves', route: '/my-leaves' },
      { id: 2, title: 'Click Apply Leave', action: 'Open leave application form' },
      { id: 3, title: 'Select Leave Type', action: 'Choose casual/sick/earned leave' },
      { id: 4, title: 'Pick Dates', action: 'Select start and end date' },
      { id: 5, title: 'Add Reason', action: 'Provide reason (optional but recommended)' },
      { id: 6, title: 'Submit', action: 'Request sent to reporting manager' }
    ]
  },

  // ========== EXPENSES ==========
  expense_submit: {
    id: 'expense_submit',
    title: 'Submit Expense',
    description: 'Claim an expense for reimbursement',
    steps: [
      { id: 1, title: 'Go to My Expenses', route: '/my-expenses' },
      { id: 2, title: 'Click New Expense', action: 'Start a new expense claim' },
      { id: 3, title: 'Select Category', action: 'Travel/Food/Office Supplies/Other' },
      { id: 4, title: 'Enter Amount', action: 'Add expense amount' },
      { id: 5, title: 'Upload Receipt', action: 'Attach receipt image (recommended)' },
      { id: 6, title: 'Submit for Approval', action: 'HR will review (Admin for ₹2000+)' }
    ]
  },

  // ========== HR ONBOARDING ==========
  employee_onboarding: {
    id: 'employee_onboarding',
    title: 'Onboard New Employee',
    description: 'Complete employee onboarding process',
    steps: [
      { id: 1, title: 'Go to Onboarding', route: '/onboarding' },
      { id: 2, title: 'Add Basic Info', action: 'Name, email, phone, department' },
      { id: 3, title: 'Set Employment Details', action: 'Joining date, designation, reporting manager' },
      { id: 4, title: 'Create CTC Structure', route: '/ctc-designer', action: 'Design salary breakup' },
      { id: 5, title: 'Submit CTC for Approval', action: 'Admin approves CTC' },
      { id: 6, title: 'Generate Offer Letter', route: '/document-center', action: 'Create offer document' },
      { id: 7, title: 'Create Portal Access', action: 'Generate login credentials' },
      { id: 8, title: 'Submit Go-Live', route: '/go-live-dashboard', action: 'Request admin approval to activate' }
    ]
  },

  // ========== PERMISSIONS ==========
  permission_change: {
    id: 'permission_change',
    title: 'Change Employee Permissions',
    description: 'Modify employee access and permissions',
    steps: [
      { id: 1, title: 'Go to Employee Permissions', route: '/employee-permissions' },
      { id: 2, title: 'Search Employee', action: 'Find employee by name/ID' },
      { id: 3, title: 'Click Edit Permissions', action: 'Open permission editor' },
      { id: 4, title: 'Modify Access', action: 'Toggle modules/features' },
      { id: 5, title: 'Submit for Approval', action: 'Admin reviews changes' }
    ]
  },

  // ========== APPROVALS ==========
  approval_process: {
    id: 'approval_process',
    title: 'Process Approvals',
    description: 'Review and approve pending requests',
    steps: [
      { id: 1, title: 'Go to Approvals Center', route: '/approvals' },
      { id: 2, title: 'Review Pending Items', action: 'Check details of each request' },
      { id: 3, title: 'Approve or Reject', action: 'Click approve/reject with comments' },
      { id: 4, title: 'Bulk Actions', action: 'Select multiple items for batch processing' }
    ]
  },

  // ========== SALES FLOW ==========
  sales_lead_to_quotation: {
    id: 'sales_lead_to_quotation',
    title: 'Lead to Quotation',
    description: 'Convert a lead into a quotation',
    steps: [
      { id: 1, title: 'Go to Leads', route: '/leads' },
      { id: 2, title: 'Create/Select Lead', action: 'Add new or pick existing lead' },
      { id: 3, title: 'Qualify Lead', action: 'Update status and add notes' },
      { id: 4, title: 'Create Quotation', route: '/quotation-builder', action: 'Start quotation from lead' },
      { id: 5, title: 'Add Line Items', action: 'Services, products, pricing' },
      { id: 6, title: 'Set Terms', action: 'Payment terms, validity, T&C' },
      { id: 7, title: 'Preview & Send', action: 'Generate PDF, email to client' }
    ]
  },
  sales_quotation_to_agreement: {
    id: 'sales_quotation_to_agreement',
    title: 'Quotation to Agreement',
    description: 'Convert approved quotation to agreement',
    steps: [
      { id: 1, title: 'Go to Quotations', route: '/quotations' },
      { id: 2, title: 'Select Approved Quotation', action: 'Pick quotation with client approval' },
      { id: 3, title: 'Convert to Agreement', action: 'Click Convert to Agreement' },
      { id: 4, title: 'Set Agreement Terms', action: 'Milestones, payment schedule' },
      { id: 5, title: 'Submit for Approval', action: 'Internal approval workflow' },
      { id: 6, title: 'Generate Agreement Doc', route: '/agreements', action: 'Create formal agreement' }
    ]
  },
  sales_agreement_to_kickoff: {
    id: 'sales_agreement_to_kickoff',
    title: 'Agreement to Kickoff',
    description: 'Hand over project to consulting team',
    steps: [
      { id: 1, title: 'Go to Agreements', route: '/agreements' },
      { id: 2, title: 'Verify First Payment', action: 'Ensure advance is received' },
      { id: 3, title: 'Create Kickoff Request', route: '/kickoff-requests', action: 'Fill project details' },
      { id: 4, title: 'Assign PM', action: 'Select project manager' },
      { id: 5, title: 'Submit Kickoff', action: 'PM receives notification' },
      { id: 6, title: 'PM Accepts', action: 'Project officially starts' }
    ]
  },

  // ========== MEETINGS & TASKS ==========
  schedule_meeting: {
    id: 'schedule_meeting',
    title: 'Schedule a Meeting',
    description: 'Create and schedule a meeting',
    steps: [
      { id: 1, title: 'Go to Meetings', route: '/meetings' },
      { id: 2, title: 'Click New Meeting', action: 'Open meeting form' },
      { id: 3, title: 'Set Title & Agenda', action: 'What is this meeting about?' },
      { id: 4, title: 'Pick Date & Time', action: 'Schedule the meeting' },
      { id: 5, title: 'Add Participants', action: 'Internal team + clients' },
      { id: 6, title: 'Send Invites', action: 'Notifications sent to all' }
    ]
  },
  create_task: {
    id: 'create_task',
    title: 'Create a Task',
    description: 'Assign task to team member',
    steps: [
      { id: 1, title: 'Go to Tasks', route: '/tasks' },
      { id: 2, title: 'Click New Task', action: 'Open task form' },
      { id: 3, title: 'Set Title & Description', action: 'What needs to be done?' },
      { id: 4, title: 'Assign To', action: 'Select team member' },
      { id: 5, title: 'Set Due Date', action: 'When should it be completed?' },
      { id: 6, title: 'Set Priority', action: 'High/Medium/Low' },
      { id: 7, title: 'Create Task', action: 'Assignee gets notification' }
    ]
  },
  create_followup: {
    id: 'create_followup',
    title: 'Create Follow-up',
    description: 'Schedule a follow-up for lead/client',
    steps: [
      { id: 1, title: 'Go to Follow-ups', route: '/follow-ups' },
      { id: 2, title: 'Click New Follow-up', action: 'Open follow-up form' },
      { id: 3, title: 'Select Lead/Client', action: 'Who to follow up with?' },
      { id: 4, title: 'Set Date & Time', action: 'When to follow up?' },
      { id: 5, title: 'Add Notes', action: 'What to discuss?' },
      { id: 6, title: 'Save', action: 'Reminder will be sent' }
    ]
  },

  // ========== MASTERS ==========
  manage_masters: {
    id: 'manage_masters',
    title: 'Manage Master Data',
    description: 'Configure dropdowns and system settings',
    steps: [
      { id: 1, title: 'Go to Masters', route: '/masters' },
      { id: 2, title: 'Select Category', action: 'Departments/Designations/Leave Types/etc.' },
      { id: 3, title: 'Add/Edit/Delete', action: 'Manage master records' },
      { id: 4, title: 'Save Changes', action: 'Updates reflect across system' }
    ]
  }
};

// Page-specific tips
export const PAGE_TIPS = {
  '/': {
    firstVisit: 'Welcome to your Dashboard! This is your central hub for all activities.',
    tips: ['Click on any card to dive deeper', 'Use the sidebar to navigate']
  },
  '/my-attendance': {
    firstVisit: 'Track your daily attendance here. Check-in when you start work.',
    tips: ['Regularize missing days', 'View monthly summary']
  },
  '/my-leaves': {
    firstVisit: 'Apply for leaves and track your leave balance.',
    tips: ['Check balance before applying', 'Add reason for faster approval']
  },
  '/my-expenses': {
    firstVisit: 'Submit expense claims for reimbursement.',
    tips: ['Attach receipts for faster processing', 'Expenses under ₹2000 are approved by HR']
  },
  '/leads': {
    firstVisit: 'Manage your sales leads here. Track from first contact to conversion.',
    tips: ['Update lead status regularly', 'Add follow-up reminders']
  },
  '/quotation-builder': {
    firstVisit: 'Create professional quotations with line items and terms.',
    tips: ['Use templates for faster creation', 'Preview before sending']
  },
  '/approvals': {
    firstVisit: 'Review and action all pending approvals in one place.',
    tips: ['Use bulk actions for efficiency', 'Real-time notifications keep you updated']
  },
  '/onboarding': {
    firstVisit: 'Onboard new employees step by step.',
    tips: ['Complete all steps for Go-Live', 'CTC must be approved before activation']
  },
  '/chat': {
    firstVisit: 'Real-time messaging with your team.',
    tips: ['Create group channels for projects', 'Direct messages are private']
  },
  '/ai-assistant': {
    firstVisit: 'Ask me anything about your ERP data!',
    tips: ['Try: "Show my leave balance"', 'Try: "Pending approvals summary"']
  }
};

// New features tracking
export const NEW_FEATURES = [
  { id: 'bulk_approvals', path: '/approvals', label: 'Bulk Actions', since: '2026-02-21' },
  { id: 'realtime_notifications', path: '*', label: 'Real-time Notifications', since: '2026-02-21' },
  { id: 'email_actions', path: '*', label: 'Email Approve/Reject', since: '2026-02-21' },
  { id: 'ai_assistant', path: '/ai-assistant', label: 'AI Assistant', since: '2026-02-21' },
  { id: 'team_chat', path: '/chat', label: 'Team Chat', since: '2026-02-21' }
];

export const GuidanceProvider = ({ children }) => {
  const [guidanceState, setGuidanceState] = useState({
    dismissed_tips: [],
    seen_features: [],
    workflow_progress: {},
    dont_show_tips: false
  });
  const [loading, setLoading] = useState(true);
  const [activeWorkflow, setActiveWorkflow] = useState(null);
  const [showHelpPanel, setShowHelpPanel] = useState(false);
  const [smartRecommendations, setSmartRecommendations] = useState({
    totalPending: 0,
    items: []
  });

  // Load smart recommendations from pending approvals
  useEffect(() => {
    const loadSmartRecommendations = async () => {
      const token = localStorage.getItem('token');
      if (!token) return;

      try {
        const headers = { Authorization: `Bearer ${token}` };
        
        // Fetch pending counts in parallel
        const [leaveRes, expenseRes, attendanceRes, ctcRes, bankRes] = await Promise.allSettled([
          axios.get(`${API}/leave-requests?status=pending`, { headers }),
          axios.get(`${API}/expenses?status=pending`, { headers }),
          axios.get(`${API}/hr/pending-attendance-approvals`, { headers }),
          axios.get(`${API}/ctc/pending-approvals`, { headers }),
          axios.get(`${API}/hr/bank-change-requests`, { headers })
        ]);

        const leaveCount = leaveRes.status === 'fulfilled' ? (leaveRes.value.data?.length || 0) : 0;
        const expenseCount = expenseRes.status === 'fulfilled' ? (expenseRes.value.data?.length || 0) : 0;
        const attendanceCount = attendanceRes.status === 'fulfilled' ? (attendanceRes.value.data?.length || 0) : 0;
        const ctcCount = ctcRes.status === 'fulfilled' ? (ctcRes.value.data?.length || 0) : 0;
        const bankCount = bankRes.status === 'fulfilled' ? (bankRes.value.data?.length || 0) : 0;

        const items = [];
        
        if (leaveCount > 0) {
          items.push({
            icon: 'leaves',
            title: 'Leave Requests',
            description: `${leaveCount} leave request${leaveCount > 1 ? 's' : ''} awaiting approval`,
            count: leaveCount,
            route: '/approvals',
            priority: leaveCount > 3 ? 'high' : 'medium'
          });
        }
        
        if (expenseCount > 0) {
          items.push({
            icon: 'expenses',
            title: 'Expense Claims',
            description: `${expenseCount} expense${expenseCount > 1 ? 's' : ''} pending review`,
            count: expenseCount,
            route: '/expense-approvals',
            priority: expenseCount > 5 ? 'high' : 'medium'
          });
        }
        
        if (attendanceCount > 0) {
          items.push({
            icon: 'attendance',
            title: 'Attendance Regularization',
            description: `${attendanceCount} attendance request${attendanceCount > 1 ? 's' : ''} pending`,
            count: attendanceCount,
            route: '/approvals',
            priority: 'medium'
          });
        }
        
        if (ctcCount > 0) {
          items.push({
            icon: 'ctc',
            title: 'CTC Approvals',
            description: `${ctcCount} CTC structure${ctcCount > 1 ? 's' : ''} need approval`,
            count: ctcCount,
            route: '/approvals',
            priority: 'high'
          });
        }
        
        if (bankCount > 0) {
          items.push({
            icon: 'bank',
            title: 'Bank Change Requests',
            description: `${bankCount} bank detail change${bankCount > 1 ? 's' : ''} pending`,
            count: bankCount,
            route: '/approvals',
            priority: 'medium'
          });
        }

        // Sort by priority (high first)
        items.sort((a, b) => {
          const priorityOrder = { high: 0, medium: 1, low: 2 };
          return priorityOrder[a.priority] - priorityOrder[b.priority];
        });

        setSmartRecommendations({
          totalPending: leaveCount + expenseCount + attendanceCount + ctcCount + bankCount,
          items
        });
      } catch (error) {
        console.error('Failed to load smart recommendations:', error);
      }
    };

    loadSmartRecommendations();
    
    // Refresh every 60 seconds
    const interval = setInterval(loadSmartRecommendations, 60000);
    return () => clearInterval(interval);
  }, []);

  // Load guidance state from backend
  useEffect(() => {
    const loadGuidanceState = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const res = await axios.get(`${API}/my/guidance-state`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setGuidanceState(res.data);
      } catch (error) {
        console.error('Failed to load guidance state:', error);
      } finally {
        setLoading(false);
      }
    };

    loadGuidanceState();
  }, []);

  // Save guidance state to backend
  const saveGuidanceState = useCallback(async (newState) => {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      await axios.post(`${API}/my/guidance-state`, newState, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setGuidanceState(newState);
    } catch (error) {
      console.error('Failed to save guidance state:', error);
    }
  }, []);

  // Dismiss a tip
  const dismissTip = useCallback((tipId) => {
    const newState = {
      ...guidanceState,
      dismissed_tips: [...new Set([...guidanceState.dismissed_tips, tipId])]
    };
    saveGuidanceState(newState);
  }, [guidanceState, saveGuidanceState]);

  // Mark feature as seen
  const markFeatureSeen = useCallback((featureId) => {
    if (guidanceState.seen_features.includes(featureId)) return;
    
    const newState = {
      ...guidanceState,
      seen_features: [...guidanceState.seen_features, featureId]
    };
    saveGuidanceState(newState);
  }, [guidanceState, saveGuidanceState]);

  // Update workflow progress
  const updateWorkflowProgress = useCallback((workflowId, stepId) => {
    const newState = {
      ...guidanceState,
      workflow_progress: {
        ...guidanceState.workflow_progress,
        [workflowId]: stepId
      }
    };
    saveGuidanceState(newState);
  }, [guidanceState, saveGuidanceState]);

  // Start a workflow
  const startWorkflow = useCallback((workflowId) => {
    const workflow = WORKFLOWS[workflowId];
    if (workflow) {
      setActiveWorkflow(workflow);
      updateWorkflowProgress(workflowId, 1);
    }
  }, [updateWorkflowProgress]);

  // Complete workflow step
  const completeWorkflowStep = useCallback((workflowId, stepId) => {
    updateWorkflowProgress(workflowId, stepId + 1);
  }, [updateWorkflowProgress]);

  // Close workflow
  const closeWorkflow = useCallback(() => {
    setActiveWorkflow(null);
  }, []);

  // Check if tip is dismissed
  const isTipDismissed = useCallback((tipId) => {
    return guidanceState.dismissed_tips.includes(tipId);
  }, [guidanceState.dismissed_tips]);

  // Check if feature is new (not seen yet)
  const isFeatureNew = useCallback((featureId) => {
    return !guidanceState.seen_features.includes(featureId);
  }, [guidanceState.seen_features]);

  // Toggle don't show tips
  const toggleDontShowTips = useCallback(() => {
    const newState = {
      ...guidanceState,
      dont_show_tips: !guidanceState.dont_show_tips
    };
    saveGuidanceState(newState);
  }, [guidanceState, saveGuidanceState]);

  // Get relevant workflows for current page
  const getWorkflowsForPage = useCallback((pathname) => {
    return Object.values(WORKFLOWS).filter(w => 
      w.steps.some(s => s.route === pathname)
    );
  }, []);

  const value = {
    guidanceState,
    loading,
    activeWorkflow,
    showHelpPanel,
    setShowHelpPanel,
    dismissTip,
    markFeatureSeen,
    startWorkflow,
    completeWorkflowStep,
    closeWorkflow,
    isTipDismissed,
    isFeatureNew,
    toggleDontShowTips,
    getWorkflowsForPage,
    WORKFLOWS,
    PAGE_TIPS,
    NEW_FEATURES
  };

  return (
    <GuidanceContext.Provider value={value}>
      {children}
    </GuidanceContext.Provider>
  );
};

export const useGuidance = () => {
  const context = useContext(GuidanceContext);
  if (!context) {
    throw new Error('useGuidance must be used within GuidanceProvider');
  }
  return context;
};

export default GuidanceContext;
