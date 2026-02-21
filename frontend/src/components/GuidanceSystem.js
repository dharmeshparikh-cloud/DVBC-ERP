import React, { useState, useContext, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { useGuidance, WORKFLOWS, PAGE_TIPS } from '../contexts/GuidanceContext';
import { useApprovals } from '../contexts/ApprovalContext';
import { useTheme } from '../contexts/ThemeContext';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { 
  HelpCircle, X, ChevronRight, ChevronLeft, CheckCircle2, 
  Circle, ArrowRight, Sparkles, MessageSquare, Lightbulb,
  Navigation, List, Send, Loader2, Bot, Bell, AlertCircle,
  ClipboardCheck, Calendar, Receipt, Users, Clock
} from 'lucide-react';

// Floating Help Button Component with Smart Badge
export const FloatingHelpButton = () => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const { setShowHelpPanel, showHelpPanel, smartRecommendations } = useGuidance();
  const [pulse, setPulse] = useState(true);

  // Calculate total pending items for badge
  const totalPending = smartRecommendations?.totalPending || 0;

  // Stop pulsing after first interaction
  useEffect(() => {
    if (showHelpPanel) {
      setPulse(false);
    }
  }, [showHelpPanel]);

  return (
    <button
      onClick={() => setShowHelpPanel(true)}
      data-testid="floating-help-btn"
      className={`
        fixed bottom-6 right-6 z-50
        w-14 h-14 rounded-full shadow-lg
        flex items-center justify-center
        transition-all duration-300 hover:scale-110
        ${isDark 
          ? 'bg-gradient-to-br from-orange-500 to-orange-600 hover:from-orange-400 hover:to-orange-500' 
          : 'bg-gradient-to-br from-orange-500 to-orange-600 hover:from-orange-400 hover:to-orange-500'
        }
        ${pulse && totalPending === 0 ? 'animate-pulse' : ''}
      `}
      title={totalPending > 0 ? `${totalPending} items need attention` : "Need help? Click here!"}
    >
      <HelpCircle className="w-7 h-7 text-white" />
      
      {/* Smart Badge - shows pending items count */}
      {totalPending > 0 && (
        <span className="absolute -top-1 -right-1 w-6 h-6 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center shadow-md animate-bounce">
          {totalPending > 9 ? '9+' : totalPending}
        </span>
      )}
      
      {/* Ripple effect when no pending items */}
      {pulse && totalPending === 0 && (
        <span className="absolute inset-0 rounded-full bg-orange-400 animate-ping opacity-30" />
      )}
    </button>
  );
};

// Help Panel Component
export const HelpPanel = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  
  const { 
    showHelpPanel, 
    setShowHelpPanel, 
    startWorkflow,
    getWorkflowsForPage,
    PAGE_TIPS
  } = useGuidance();

  const [activeTab, setActiveTab] = useState('workflows');
  const [aiQuery, setAiQuery] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResponse, setAiResponse] = useState(null);
  const [suggestedRoute, setSuggestedRoute] = useState(null);

  const currentPageTips = PAGE_TIPS[location.pathname];
  const relevantWorkflows = getWorkflowsForPage(location.pathname);

  // Get all workflows grouped by category
  const workflowCategories = {
    'Daily Tasks': ['attendance_checkin', 'attendance_regularize', 'leave_request', 'expense_submit'],
    'Sales Flow': ['sales_lead_to_quotation', 'sales_quotation_to_agreement', 'sales_agreement_to_kickoff'],
    'HR & Onboarding': ['employee_onboarding', 'permission_change', 'approval_process'],
    'Meetings & Tasks': ['schedule_meeting', 'create_task', 'create_followup'],
    'Administration': ['manage_masters']
  };

  // Handle AI query
  const handleAskAI = async () => {
    if (!aiQuery.trim()) return;
    
    setAiLoading(true);
    setAiResponse(null);
    setSuggestedRoute(null);

    try {
      const token = localStorage.getItem('token');
      const res = await axios.post(`${API}/ai/guidance-help`, {
        query: aiQuery,
        current_page: location.pathname,
        user_role: user?.role
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setAiResponse(res.data.response);
      
      // Check if AI suggested a route
      if (res.data.suggested_route) {
        setSuggestedRoute(res.data.suggested_route);
      }
      
      // Auto-navigate if configured
      if (res.data.auto_navigate && res.data.suggested_route) {
        setTimeout(() => {
          navigate(res.data.suggested_route);
          setShowHelpPanel(false);
        }, 2000);
      }
    } catch (error) {
      console.error('AI help error:', error);
      setAiResponse('Sorry, I encountered an error. Please try again or navigate manually.');
    } finally {
      setAiLoading(false);
    }
  };

  // Start workflow and navigate
  const handleStartWorkflow = (workflowId) => {
    const workflow = WORKFLOWS[workflowId];
    if (workflow) {
      startWorkflow(workflowId);
      const firstStep = workflow.steps[0];
      if (firstStep.route) {
        navigate(firstStep.route);
      }
      setShowHelpPanel(false);
    }
  };

  // Navigate to suggested route
  const handleNavigateToSuggested = () => {
    if (suggestedRoute) {
      navigate(suggestedRoute);
      setShowHelpPanel(false);
    }
  };

  // Quick action suggestions based on role
  const getQuickActions = () => {
    const baseActions = [
      { label: 'Check my attendance', query: 'How do I check in for today?' },
      { label: 'Apply for leave', query: 'How do I apply for leave?' },
      { label: 'Submit an expense', query: 'How do I submit an expense claim?' }
    ];

    if (['admin', 'hr_manager', 'hr_executive'].includes(user?.role)) {
      baseActions.push(
        { label: 'Onboard an employee', query: 'How do I onboard a new employee?' },
        { label: 'Approve pending items', query: 'Take me to pending approvals' }
      );
    }

    if (['admin', 'manager', 'account_manager', 'executive'].includes(user?.role)) {
      baseActions.push(
        { label: 'Create a quotation', query: 'How do I create a quotation?' },
        { label: 'Convert lead to client', query: 'How do I convert a lead to quotation?' }
      );
    }

    return baseActions.slice(0, 5);
  };

  return (
    <Dialog open={showHelpPanel} onOpenChange={setShowHelpPanel}>
      <DialogContent className={`${isDark ? 'bg-zinc-900 border-zinc-700' : ''} max-w-2xl max-h-[85vh] overflow-hidden flex flex-col`}>
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className={`text-xl font-semibold flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            How can I help you?
          </DialogTitle>
        </DialogHeader>

        {/* Tabs */}
        <div className={`flex border-b ${isDark ? 'border-zinc-700' : 'border-zinc-200'} -mx-6 px-6`}>
          {[
            { id: 'ai', label: 'Ask AI', icon: Bot },
            { id: 'workflows', label: 'Step-by-Step Guides', icon: List },
            { id: 'tips', label: 'Page Tips', icon: Lightbulb }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-orange-500 text-orange-600'
                  : `border-transparent ${isDark ? 'text-zinc-400 hover:text-zinc-200' : 'text-zinc-500 hover:text-zinc-700'}`
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-4 -mx-6 px-6">
          
          {/* AI Tab */}
          {activeTab === 'ai' && (
            <div className="space-y-4">
              {/* Quick Actions */}
              <div>
                <p className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                  Quick actions:
                </p>
                <div className="flex flex-wrap gap-2">
                  {getQuickActions().map((action, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setAiQuery(action.query);
                        handleAskAI();
                      }}
                      className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                        isDark 
                          ? 'border-zinc-600 hover:bg-zinc-800 text-zinc-300' 
                          : 'border-zinc-200 hover:bg-zinc-50 text-zinc-600'
                      }`}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* AI Input */}
              <div className={`flex gap-2 p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                <input
                  type="text"
                  value={aiQuery}
                  onChange={(e) => setAiQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAskAI()}
                  placeholder="Ask me anything... (e.g., 'How do I create a quotation?')"
                  className={`flex-1 bg-transparent border-none outline-none text-sm ${
                    isDark ? 'text-zinc-100 placeholder:text-zinc-500' : 'text-zinc-900 placeholder:text-zinc-400'
                  }`}
                />
                <Button
                  size="sm"
                  onClick={handleAskAI}
                  disabled={aiLoading || !aiQuery.trim()}
                  className="bg-orange-500 hover:bg-orange-600 text-white"
                >
                  {aiLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </Button>
              </div>

              {/* AI Response */}
              {aiResponse && (
                <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-blue-50'}`}>
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <p className={`text-sm whitespace-pre-wrap ${isDark ? 'text-zinc-200' : 'text-zinc-700'}`}>
                        {aiResponse}
                      </p>
                      
                      {/* Navigation suggestion */}
                      {suggestedRoute && (
                        <Button
                          size="sm"
                          onClick={handleNavigateToSuggested}
                          className="mt-3 bg-blue-600 hover:bg-blue-700 text-white"
                        >
                          <Navigation className="w-4 h-4 mr-2" />
                          Take me there
                          <ArrowRight className="w-4 h-4 ml-2" />
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Workflows Tab */}
          {activeTab === 'workflows' && (
            <div className="space-y-6">
              {/* Relevant workflows for current page */}
              {relevantWorkflows.length > 0 && (
                <div>
                  <p className={`text-sm font-medium mb-2 flex items-center gap-2 ${isDark ? 'text-orange-400' : 'text-orange-600'}`}>
                    <Sparkles className="w-4 h-4" />
                    Suggested for this page
                  </p>
                  <div className="space-y-2">
                    {relevantWorkflows.map(workflow => (
                      <WorkflowCard
                        key={workflow.id}
                        workflow={workflow}
                        onStart={() => handleStartWorkflow(workflow.id)}
                        isDark={isDark}
                        highlighted
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* All workflows by category */}
              {Object.entries(workflowCategories).map(([category, workflowIds]) => (
                <div key={category}>
                  <p className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                    {category}
                  </p>
                  <div className="space-y-2">
                    {workflowIds.map(id => {
                      const workflow = WORKFLOWS[id];
                      if (!workflow) return null;
                      return (
                        <WorkflowCard
                          key={id}
                          workflow={workflow}
                          onStart={() => handleStartWorkflow(id)}
                          isDark={isDark}
                        />
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Tips Tab */}
          {activeTab === 'tips' && (
            <div className="space-y-4">
              {currentPageTips ? (
                <>
                  <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-amber-50'}`}>
                    <div className="flex items-start gap-3">
                      <Lightbulb className={`w-5 h-5 flex-shrink-0 ${isDark ? 'text-amber-400' : 'text-amber-500'}`} />
                      <div>
                        <p className={`text-sm font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                          About this page
                        </p>
                        <p className={`text-sm mt-1 ${isDark ? 'text-zinc-300' : 'text-zinc-600'}`}>
                          {currentPageTips.firstVisit}
                        </p>
                      </div>
                    </div>
                  </div>

                  {currentPageTips.tips && currentPageTips.tips.length > 0 && (
                    <div>
                      <p className={`text-sm font-medium mb-2 ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                        Pro Tips:
                      </p>
                      <ul className="space-y-2">
                        {currentPageTips.tips.map((tip, idx) => (
                          <li
                            key={idx}
                            className={`flex items-center gap-2 text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}
                          >
                            <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                            {tip}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <div className={`text-center py-8 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                  <Lightbulb className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No specific tips for this page.</p>
                  <p className="text-sm mt-1">Try the AI assistant for help!</p>
                </div>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Workflow Card Component
const WorkflowCard = ({ workflow, onStart, isDark, highlighted = false }) => (
  <div
    className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
      highlighted
        ? isDark ? 'border-orange-600 bg-orange-900/20' : 'border-orange-300 bg-orange-50'
        : isDark ? 'border-zinc-700 hover:border-zinc-600' : 'border-zinc-200 hover:border-zinc-300'
    }`}
    onClick={onStart}
  >
    <div className="flex items-center justify-between">
      <div>
        <h4 className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
          {workflow.title}
        </h4>
        <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
          {workflow.description}
        </p>
        <p className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
          {workflow.steps.length} steps
        </p>
      </div>
      <ChevronRight className={`w-5 h-5 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`} />
    </div>
  </div>
);

// Active Workflow Overlay
export const WorkflowOverlay = () => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const { activeWorkflow, closeWorkflow, guidanceState, completeWorkflowStep } = useGuidance();

  if (!activeWorkflow) return null;

  const currentStepIndex = (guidanceState.workflow_progress[activeWorkflow.id] || 1) - 1;
  const currentStep = activeWorkflow.steps[currentStepIndex];
  const isLastStep = currentStepIndex >= activeWorkflow.steps.length - 1;

  const handleNext = () => {
    if (isLastStep) {
      closeWorkflow();
    } else {
      completeWorkflowStep(activeWorkflow.id, currentStepIndex + 1);
      const nextStep = activeWorkflow.steps[currentStepIndex + 1];
      if (nextStep?.route) {
        navigate(nextStep.route);
      }
    }
  };

  const handlePrev = () => {
    if (currentStepIndex > 0) {
      const prevStepIndex = currentStepIndex - 1;
      completeWorkflowStep(activeWorkflow.id, prevStepIndex);
      const prevStep = activeWorkflow.steps[prevStepIndex];
      if (prevStep?.route) {
        navigate(prevStep.route);
      }
    }
  };

  return (
    <div className={`
      fixed bottom-24 right-6 z-50 w-80
      rounded-xl shadow-2xl border overflow-hidden
      ${isDark ? 'bg-zinc-900 border-zinc-700' : 'bg-white border-zinc-200'}
    `}>
      {/* Header */}
      <div className={`px-4 py-3 ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <List className="w-4 h-4 text-orange-500" />
            <span className={`text-sm font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
              {activeWorkflow.title}
            </span>
          </div>
          <button onClick={closeWorkflow} className={isDark ? 'text-zinc-400 hover:text-zinc-200' : 'text-zinc-500 hover:text-zinc-700'}>
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center gap-1 mt-2">
          {activeWorkflow.steps.map((_, idx) => (
            <div
              key={idx}
              className={`h-1 flex-1 rounded-full ${
                idx < currentStepIndex 
                  ? 'bg-emerald-500' 
                  : idx === currentStepIndex 
                    ? 'bg-orange-500' 
                    : isDark ? 'bg-zinc-700' : 'bg-zinc-200'
              }`}
            />
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className={`
            w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
            ${isDark ? 'bg-orange-900/50 text-orange-400' : 'bg-orange-100 text-orange-600'}
          `}>
            {currentStepIndex + 1}
          </div>
          <div className="flex-1">
            <h4 className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
              {currentStep.title}
            </h4>
            {currentStep.action && (
              <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                {currentStep.action}
              </p>
            )}
          </div>
        </div>

        {/* Steps preview */}
        <div className="mt-4 space-y-2">
          {activeWorkflow.steps.map((step, idx) => (
            <div
              key={idx}
              className={`flex items-center gap-2 text-sm ${
                idx < currentStepIndex 
                  ? isDark ? 'text-emerald-400' : 'text-emerald-600'
                  : idx === currentStepIndex
                    ? isDark ? 'text-orange-400 font-medium' : 'text-orange-600 font-medium'
                    : isDark ? 'text-zinc-500' : 'text-zinc-400'
              }`}
            >
              {idx < currentStepIndex ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : idx === currentStepIndex ? (
                <Circle className="w-4 h-4 fill-current" />
              ) : (
                <Circle className="w-4 h-4" />
              )}
              <span className="truncate">{step.title}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className={`px-4 py-3 flex items-center justify-between ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
        <Button
          variant="outline"
          size="sm"
          onClick={handlePrev}
          disabled={currentStepIndex === 0}
          className={isDark ? 'border-zinc-600' : ''}
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Back
        </Button>
        <Button
          size="sm"
          onClick={handleNext}
          className="bg-orange-500 hover:bg-orange-600 text-white"
        >
          {isLastStep ? (
            <>
              <CheckCircle2 className="w-4 h-4 mr-1" />
              Done
            </>
          ) : (
            <>
              Next
              <ChevronRight className="w-4 h-4 ml-1" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
};

// Smart Tip Component
export const SmartTip = ({ tipId, children, position = 'bottom' }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const { isTipDismissed, dismissTip, guidanceState } = useGuidance();
  const [show, setShow] = useState(false);

  useEffect(() => {
    // Show tip after a short delay if not dismissed
    if (!isTipDismissed(tipId) && !guidanceState.dont_show_tips) {
      const timer = setTimeout(() => setShow(true), 1500);
      return () => clearTimeout(timer);
    }
  }, [tipId, isTipDismissed, guidanceState.dont_show_tips]);

  if (!show) return null;

  const handleDismiss = () => {
    setShow(false);
    dismissTip(tipId);
  };

  const positionClasses = {
    top: 'bottom-full mb-2',
    bottom: 'top-full mt-2',
    left: 'right-full mr-2',
    right: 'left-full ml-2'
  };

  return (
    <div className={`absolute ${positionClasses[position]} z-50 animate-in fade-in slide-in-from-bottom-2`}>
      <div className={`
        p-3 rounded-lg shadow-lg max-w-xs
        ${isDark ? 'bg-amber-900/90 border border-amber-700' : 'bg-amber-50 border border-amber-200'}
      `}>
        <div className="flex items-start gap-2">
          <Lightbulb className={`w-4 h-4 flex-shrink-0 mt-0.5 ${isDark ? 'text-amber-400' : 'text-amber-500'}`} />
          <div className="flex-1">
            <p className={`text-sm ${isDark ? 'text-amber-100' : 'text-amber-900'}`}>
              {children}
            </p>
          </div>
          <button onClick={handleDismiss} className={isDark ? 'text-amber-400 hover:text-amber-200' : 'text-amber-500 hover:text-amber-700'}>
            <X className="w-4 h-4" />
          </button>
        </div>
        <button
          onClick={handleDismiss}
          className={`text-xs mt-2 ${isDark ? 'text-amber-400' : 'text-amber-600'} hover:underline`}
        >
          Don't show this again
        </button>
      </div>
    </div>
  );
};

// New Feature Badge
export const NewFeatureBadge = ({ featureId }) => {
  const { isFeatureNew, markFeatureSeen } = useGuidance();

  useEffect(() => {
    // Mark as seen after 3 seconds of being visible
    if (isFeatureNew(featureId)) {
      const timer = setTimeout(() => markFeatureSeen(featureId), 3000);
      return () => clearTimeout(timer);
    }
  }, [featureId, isFeatureNew, markFeatureSeen]);

  if (!isFeatureNew(featureId)) return null;

  return (
    <span className="ml-2 px-1.5 py-0.5 text-[10px] font-bold uppercase bg-orange-500 text-white rounded animate-pulse">
      New
    </span>
  );
};

export default { FloatingHelpButton, HelpPanel, WorkflowOverlay, SmartTip, NewFeatureBadge };
