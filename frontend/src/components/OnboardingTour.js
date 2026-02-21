import React, { useState, useEffect, useContext, useCallback } from 'react';
import Joyride, { STATUS, ACTIONS, EVENTS } from 'react-joyride';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { 
  Sparkles, X, ChevronRight, ChevronLeft, 
  Bell, Wifi, MousePointerClick, Mail, 
  LayoutDashboard, Users, Briefcase, FileText,
  DollarSign, Calendar, MessageSquare, Bot
} from 'lucide-react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';

// Role-specific tour configurations
const getTourSteps = (role, isDark) => {
  const baseSteps = [
    // Welcome step
    {
      target: 'body',
      content: (
        <div className="text-center py-4">
          <Sparkles className="w-12 h-12 mx-auto mb-4 text-orange-500" />
          <h2 className="text-xl font-bold mb-2">Welcome to NETRA!</h2>
          <p className="text-sm text-zinc-500">
            Let's take a quick tour to help you get started with your new workspace.
          </p>
        </div>
      ),
      placement: 'center',
      disableBeacon: true,
      styles: {
        options: { width: 400 }
      }
    },
    // Dashboard
    {
      target: '[data-tour="dashboard-link"]',
      content: (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <LayoutDashboard className="w-5 h-5 text-orange-500" />
            <h3 className="font-semibold">Your Dashboard</h3>
          </div>
          <p className="text-sm">
            Your central hub with key metrics, recent activities, and quick actions tailored to your role.
          </p>
        </div>
      ),
      placement: 'right',
      disableBeacon: true
    },
    // Notification Bell
    {
      target: '[data-tour="notification-bell"]',
      content: (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Bell className="w-5 h-5 text-orange-500" />
            <h3 className="font-semibold">Real-time Notifications</h3>
          </div>
          <p className="text-sm mb-2">
            Stay updated with instant notifications for approvals, mentions, and important updates.
          </p>
          <div className="bg-zinc-100 dark:bg-zinc-800 rounded-lg p-2 text-xs">
            <span className="font-medium">Tip:</span> The badge shows unread count. Click to see all notifications.
          </div>
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true
    },
    // WebSocket Status
    {
      target: '[data-tour="ws-status"]',
      content: (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Wifi className="w-5 h-5 text-emerald-500" />
            <h3 className="font-semibold">Live Connection Status</h3>
          </div>
          <p className="text-sm mb-2">
            This indicator shows your real-time connection status:
          </p>
          <ul className="text-xs space-y-1">
            <li className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span><strong>Green (Live)</strong> - Updates arrive instantly</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-zinc-400" />
              <span><strong>Gray (Offline)</strong> - Reconnecting...</span>
            </li>
          </ul>
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true
    },
    // One-click Actions
    {
      target: '[data-tour="notification-panel"]',
      content: (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <MousePointerClick className="w-5 h-5 text-blue-500" />
            <h3 className="font-semibold">One-Click Actions</h3>
          </div>
          <p className="text-sm mb-2">
            Many notifications have quick action buttons - approve leave requests, respond to messages, or jump to relevant pages directly.
          </p>
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-2 text-xs text-blue-700 dark:text-blue-300">
            No need to navigate - take action right from the notification!
          </div>
        </div>
      ),
      placement: 'left',
      disableBeacon: true
    },
    // Email Actions
    {
      target: '[data-tour="notification-bell"]',
      content: (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Mail className="w-5 h-5 text-purple-500" />
            <h3 className="font-semibold">Email Action Links</h3>
          </div>
          <p className="text-sm mb-2">
            For approval requests, you'll also receive emails with secure one-click links:
          </p>
          <ul className="text-xs space-y-1 mb-2">
            <li>✓ Approve or reject without logging in</li>
            <li>✓ Links expire after 24 hours for security</li>
            <li>✓ Works on mobile email apps</li>
          </ul>
          <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-2 text-xs text-purple-700 dark:text-purple-300">
            Check your inbox for approval emails with action buttons!
          </div>
        </div>
      ),
      placement: 'bottom',
      disableBeacon: true
    }
  ];

  // Role-specific steps
  const roleSteps = {
    admin: [
      {
        target: '[data-tour="hr-section"]',
        content: (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Users className="w-5 h-5 text-indigo-500" />
              <h3 className="font-semibold">HR Management</h3>
            </div>
            <p className="text-sm">
              As an Admin, you have full access to employee management, onboarding, CTC structures, and Go-Live approvals.
            </p>
          </div>
        ),
        placement: 'right',
        disableBeacon: true
      },
      {
        target: '[data-tour="approvals-link"]',
        content: (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-5 h-5 text-orange-500" />
              <h3 className="font-semibold">Approvals Center</h3>
            </div>
            <p className="text-sm mb-2">
              Review and approve CTC structures, Go-Live requests, permission changes, and more.
            </p>
            <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-2 text-xs text-orange-700 dark:text-orange-300">
              <strong>New:</strong> Bulk approve multiple items at once!
            </div>
          </div>
        ),
        placement: 'right',
        disableBeacon: true
      }
    ],
    hr_manager: [
      {
        target: '[data-tour="hr-section"]',
        content: (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Users className="w-5 h-5 text-indigo-500" />
              <h3 className="font-semibold">HR Management</h3>
            </div>
            <p className="text-sm">
              Manage employees, track attendance, process leaves, handle onboarding, and create CTC structures.
            </p>
          </div>
        ),
        placement: 'right',
        disableBeacon: true
      },
      {
        target: '[data-tour="expense-approvals"]',
        content: (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="w-5 h-5 text-emerald-500" />
              <h3 className="font-semibold">Expense Approvals</h3>
            </div>
            <p className="text-sm">
              Review and approve employee expense claims. Expenses under ₹2000 can be approved directly by HR.
            </p>
          </div>
        ),
        placement: 'right',
        disableBeacon: true
      }
    ],
    hr_executive: [
      {
        target: '[data-tour="hr-section"]',
        content: (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Users className="w-5 h-5 text-indigo-500" />
              <h3 className="font-semibold">HR Operations</h3>
            </div>
            <p className="text-sm">
              Handle day-to-day HR operations including attendance, leave management, and employee onboarding.
            </p>
          </div>
        ),
        placement: 'right',
        disableBeacon: true
      }
    ],
    manager: [
      {
        target: '[data-tour="sales-section"]',
        content: (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Briefcase className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold">Sales & CRM</h3>
            </div>
            <p className="text-sm">
              Manage leads, create quotations, track agreements, and monitor your sales pipeline.
            </p>
          </div>
        ),
        placement: 'right',
        disableBeacon: true
      },
      {
        target: '[data-tour="approvals-link"]',
        content: (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-5 h-5 text-orange-500" />
              <h3 className="font-semibold">Team Approvals</h3>
            </div>
            <p className="text-sm">
              Review and approve leave requests and other submissions from your team members.
            </p>
          </div>
        ),
        placement: 'right',
        disableBeacon: true
      }
    ],
    account_manager: [
      {
        target: '[data-tour="sales-section"]',
        content: (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Briefcase className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold">Account Management</h3>
            </div>
            <p className="text-sm">
              Manage client relationships, create quotations, track project agreements, and request kickoffs.
            </p>
          </div>
        ),
        placement: 'right',
        disableBeacon: true
      }
    ],
    project_manager: [
      {
        target: '[data-tour="projects-link"]',
        content: (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Calendar className="w-5 h-5 text-purple-500" />
              <h3 className="font-semibold">Project Management</h3>
            </div>
            <p className="text-sm">
              Manage your assigned projects, track milestones, handle kickoff requests, and monitor team utilization.
            </p>
          </div>
        ),
        placement: 'right',
        disableBeacon: true
      }
    ],
    employee: [
      {
        target: '[data-tour="my-workspace"]',
        content: (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <LayoutDashboard className="w-5 h-5 text-blue-500" />
              <h3 className="font-semibold">My Workspace</h3>
            </div>
            <p className="text-sm">
              Access your attendance, leaves, salary slips, expenses, and personal information all in one place.
            </p>
          </div>
        ),
        placement: 'right',
        disableBeacon: true
      }
    ]
  };

  // Communication tools (for everyone)
  const communicationSteps = [
    {
      target: '[data-tour="chat-link"]',
      content: (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <MessageSquare className="w-5 h-5 text-blue-500" />
            <h3 className="font-semibold">Team Chat</h3>
          </div>
          <p className="text-sm">
            Real-time messaging with your colleagues. Send direct messages or create group channels.
          </p>
        </div>
      ),
      placement: 'right',
      disableBeacon: true
    },
    {
      target: '[data-tour="ai-assistant-link"]',
      content: (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Bot className="w-5 h-5 text-purple-500" />
            <h3 className="font-semibold">AI Assistant</h3>
          </div>
          <p className="text-sm mb-2">
            Ask questions about your ERP data - attendance trends, leave balances, project status, and more.
          </p>
          <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-2 text-xs text-purple-700 dark:text-purple-300">
            The AI respects your role permissions - you'll only see data you're authorized to access.
          </div>
        </div>
      ),
      placement: 'right',
      disableBeacon: true
    }
  ];

  // Final step
  const finalStep = {
    target: 'body',
    content: (
      <div className="text-center py-4">
        <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-orange-400 to-orange-600 rounded-full flex items-center justify-center">
          <Sparkles className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-xl font-bold mb-2">You're All Set!</h2>
        <p className="text-sm text-zinc-500 mb-4">
          You've completed the tour. Explore the app and reach out if you need any help.
        </p>
        <div className="bg-zinc-100 dark:bg-zinc-800 rounded-lg p-3 text-xs">
          <span className="font-medium">Pro Tip:</span> You can replay this tour anytime from your profile settings.
        </div>
      </div>
    ),
    placement: 'center',
    disableBeacon: true,
    styles: {
      options: { width: 400 }
    }
  };

  // Combine steps based on role
  const specificSteps = roleSteps[role] || roleSteps.employee;
  return [...baseSteps, ...specificSteps, ...communicationSteps, finalStep];
};

// Custom tooltip component
const CustomTooltip = ({
  continuous,
  index,
  step,
  backProps,
  closeProps,
  primaryProps,
  tooltipProps,
  isLastStep,
  size
}) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  
  return (
    <div
      {...tooltipProps}
      className={`rounded-xl shadow-2xl border max-w-sm ${
        isDark 
          ? 'bg-zinc-900 border-zinc-700 text-zinc-100' 
          : 'bg-white border-zinc-200 text-zinc-900'
      }`}
    >
      <div className="p-4">
        {step.content}
      </div>
      
      <div className={`flex items-center justify-between px-4 py-3 border-t ${isDark ? 'border-zinc-700' : 'border-zinc-100'}`}>
        <div className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
          {index + 1} of {size}
        </div>
        
        <div className="flex items-center gap-2">
          {index > 0 && (
            <button
              {...backProps}
              className={`px-3 py-1.5 text-sm rounded-lg border ${
                isDark 
                  ? 'border-zinc-600 hover:bg-zinc-800' 
                  : 'border-zinc-200 hover:bg-zinc-50'
              }`}
            >
              <ChevronLeft className="w-4 h-4 inline mr-1" />
              Back
            </button>
          )}
          
          {continuous && (
            <button
              {...primaryProps}
              className="px-4 py-1.5 text-sm bg-orange-500 text-white rounded-lg hover:bg-orange-600 font-medium"
            >
              {isLastStep ? 'Finish' : 'Next'}
              {!isLastStep && <ChevronRight className="w-4 h-4 inline ml-1" />}
            </button>
          )}
        </div>
      </div>
      
      {/* Skip button */}
      <button
        {...closeProps}
        className={`absolute top-2 right-2 p-1 rounded-full ${
          isDark ? 'hover:bg-zinc-800' : 'hover:bg-zinc-100'
        }`}
        title="Skip tour"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

// Welcome dialog for first-time users
const WelcomeDialog = ({ open, onStart, onSkip }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  
  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent className={`${isDark ? 'bg-zinc-900 border-zinc-700' : ''} max-w-md`}>
        <div className="text-center py-4">
          <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-orange-400 to-orange-600 rounded-2xl flex items-center justify-center shadow-lg">
            <Sparkles className="w-10 h-10 text-white" />
          </div>
          
          <DialogHeader>
            <DialogTitle className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : ''}`}>
              Welcome to NETRA!
            </DialogTitle>
          </DialogHeader>
          
          <p className={`mt-3 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            Your complete business management platform. Let us show you around!
          </p>
          
          <div className={`mt-6 p-4 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
            <h4 className={`font-medium mb-2 ${isDark ? 'text-zinc-200' : 'text-zinc-700'}`}>
              What you'll learn:
            </h4>
            <ul className={`text-sm text-left space-y-2 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
              <li className="flex items-center gap-2">
                <Bell className="w-4 h-4 text-orange-500" />
                Real-time notifications & actions
              </li>
              <li className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-purple-500" />
                Email approval shortcuts
              </li>
              <li className="flex items-center gap-2">
                <LayoutDashboard className="w-4 h-4 text-blue-500" />
                Features tailored to your role
              </li>
            </ul>
          </div>
        </div>
        
        <DialogFooter className="flex gap-3 mt-4">
          <Button
            variant="outline"
            onClick={onSkip}
            className={isDark ? 'border-zinc-600' : ''}
          >
            Skip for now
          </Button>
          <Button
            onClick={onStart}
            className="bg-orange-500 hover:bg-orange-600 text-white flex-1"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Start Tour
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// Main OnboardingTour component
const OnboardingTour = () => {
  const { user, token } = useContext(AuthContext);
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  
  const [showWelcome, setShowWelcome] = useState(false);
  const [runTour, setRunTour] = useState(false);
  const [steps, setSteps] = useState([]);
  const [stepIndex, setStepIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  // Check if user needs onboarding
  useEffect(() => {
    const checkOnboarding = async () => {
      if (!user || !token) {
        setLoading(false);
        return;
      }
      
      try {
        const res = await axios.get(`${API}/my/onboarding-status`);
        if (!res.data.has_completed_onboarding) {
          setShowWelcome(true);
        }
      } catch (error) {
        console.error('Failed to check onboarding status:', error);
      } finally {
        setLoading(false);
      }
    };
    
    checkOnboarding();
  }, [user, token]);

  // Set up tour steps based on role
  useEffect(() => {
    if (user?.role) {
      setSteps(getTourSteps(user.role, isDark));
    }
  }, [user?.role, isDark]);

  const handleStartTour = () => {
    setShowWelcome(false);
    setTimeout(() => {
      setRunTour(true);
    }, 300);
  };

  const handleSkipTour = async () => {
    setShowWelcome(false);
    try {
      await axios.post(`${API}/my/complete-onboarding`);
    } catch (error) {
      console.error('Failed to mark onboarding complete:', error);
    }
  };

  const handleJoyrideCallback = useCallback(async (data) => {
    const { action, index, status, type } = data;

    if ([EVENTS.STEP_AFTER, EVENTS.TARGET_NOT_FOUND].includes(type)) {
      setStepIndex(index + (action === ACTIONS.PREV ? -1 : 1));
    }

    if ([STATUS.FINISHED, STATUS.SKIPPED].includes(status)) {
      setRunTour(false);
      setStepIndex(0);
      
      // Mark onboarding as complete
      try {
        await axios.post(`${API}/my/complete-onboarding`);
      } catch (error) {
        console.error('Failed to mark onboarding complete:', error);
      }
    }
  }, []);

  if (loading || !user) return null;

  return (
    <>
      <WelcomeDialog
        open={showWelcome}
        onStart={handleStartTour}
        onSkip={handleSkipTour}
      />
      
      <Joyride
        steps={steps}
        run={runTour}
        stepIndex={stepIndex}
        continuous
        showProgress
        showSkipButton
        scrollToFirstStep
        spotlightClicks
        disableOverlayClose
        tooltipComponent={CustomTooltip}
        callback={handleJoyrideCallback}
        styles={{
          options: {
            zIndex: 10000,
            primaryColor: '#f97316',
            overlayColor: isDark ? 'rgba(0, 0, 0, 0.7)' : 'rgba(0, 0, 0, 0.5)'
          },
          spotlight: {
            borderRadius: 8
          }
        }}
        floaterProps={{
          styles: {
            floater: {
              filter: 'none'
            }
          }
        }}
      />
    </>
  );
};

// Export a function to trigger tour replay
export const useTourReplay = () => {
  const [, setTrigger] = useState(0);
  
  const replayTour = useCallback(async () => {
    try {
      await axios.post(`${API}/my/reset-onboarding`);
      // Force page reload to restart tour
      window.location.reload();
    } catch (error) {
      console.error('Failed to reset onboarding:', error);
    }
  }, []);
  
  return { replayTour };
};

export default OnboardingTour;
