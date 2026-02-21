import React, { useState, useEffect, useContext, useCallback } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { 
  Sparkles, X, ChevronRight, ChevronLeft, 
  Bell, Wifi, MousePointerClick, Mail, 
  LayoutDashboard, Users, Briefcase, FileText,
  Calendar, MessageSquare, Bot
} from 'lucide-react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';

// Role-specific tour configurations
const getTourSteps = (role) => {
  const baseSteps = [
    {
      id: 'notification-bell',
      title: 'Real-time Notifications',
      description: 'Stay updated with instant notifications for approvals, mentions, and important updates. The badge shows unread count.',
      icon: Bell,
      iconColor: 'text-orange-500',
      position: 'bottom'
    },
    {
      id: 'ws-status',
      title: 'Live Connection Status',
      description: 'Green dot means updates arrive instantly. Gray means reconnecting.',
      icon: Wifi,
      iconColor: 'text-emerald-500',
      position: 'bottom'
    },
    {
      id: 'notification-panel',
      title: 'One-Click Actions',
      description: 'Many notifications have quick action buttons - approve requests or jump to relevant pages directly from here!',
      icon: MousePointerClick,
      iconColor: 'text-blue-500',
      position: 'left'
    },
    {
      id: 'email-info',
      title: 'Email Action Links',
      description: 'For approval requests, you\'ll receive emails with secure one-click approve/reject links that work without logging in. Links expire after 24 hours.',
      icon: Mail,
      iconColor: 'text-purple-500',
      position: 'center'
    }
  ];

  // Role-specific steps
  const roleSteps = {
    admin: [
      {
        id: 'hr-section',
        title: 'HR Management',
        description: 'Full access to employee management, onboarding, CTC structures, and Go-Live approvals.',
        icon: Users,
        iconColor: 'text-indigo-500',
        position: 'right'
      },
      {
        id: 'approvals-link',
        title: 'Approvals Center',
        description: 'Review and approve CTC structures, Go-Live requests, permissions, and more. Now with bulk approve!',
        icon: FileText,
        iconColor: 'text-orange-500',
        position: 'right'
      }
    ],
    hr_manager: [
      {
        id: 'hr-section',
        title: 'HR Management',
        description: 'Manage employees, track attendance, process leaves, and create CTC structures.',
        icon: Users,
        iconColor: 'text-indigo-500',
        position: 'right'
      }
    ],
    manager: [
      {
        id: 'sales-section',
        title: 'Sales & CRM',
        description: 'Manage leads, create quotations, track agreements, and monitor your sales pipeline.',
        icon: Briefcase,
        iconColor: 'text-blue-500',
        position: 'right'
      },
      {
        id: 'approvals-link',
        title: 'Team Approvals',
        description: 'Review and approve leave requests from your team members.',
        icon: FileText,
        iconColor: 'text-orange-500',
        position: 'right'
      }
    ],
    project_manager: [
      {
        id: 'projects-link',
        title: 'Project Management',
        description: 'Manage assigned projects, track milestones, and handle kickoff requests.',
        icon: Calendar,
        iconColor: 'text-purple-500',
        position: 'right'
      }
    ],
    employee: [
      {
        id: 'my-workspace',
        title: 'My Workspace',
        description: 'Access attendance, leaves, salary slips, expenses, and personal information.',
        icon: LayoutDashboard,
        iconColor: 'text-blue-500',
        position: 'right'
      }
    ]
  };

  // Communication tools (for everyone)
  const communicationSteps = [
    {
      id: 'chat-link',
      title: 'Team Chat',
      description: 'Real-time messaging with colleagues. Send direct messages or create group channels.',
      icon: MessageSquare,
      iconColor: 'text-blue-500',
      position: 'right'
    },
    {
      id: 'ai-assistant-link',
      title: 'AI Assistant',
      description: 'Ask questions about your ERP data - attendance trends, leave balances, project status. The AI respects your role permissions.',
      icon: Bot,
      iconColor: 'text-purple-500',
      position: 'right'
    }
  ];

  const specificSteps = roleSteps[role] || roleSteps.employee;
  return [...baseSteps, ...specificSteps, ...communicationSteps];
};

// Welcome dialog for first-time users
const WelcomeDialog = ({ open, onStart, onSkip, isDark }) => {
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

// Tour tooltip component
const TourTooltip = ({ step, stepIndex, totalSteps, onNext, onPrev, onClose, isDark }) => {
  const Icon = step.icon;
  
  return (
    <div className="fixed inset-0 z-[9999] pointer-events-none">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/50 pointer-events-auto" onClick={onClose} />
      
      {/* Tooltip */}
      <div className={`
        absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2
        w-[90%] max-w-md p-6 rounded-xl shadow-2xl pointer-events-auto
        ${isDark ? 'bg-zinc-900 border border-zinc-700' : 'bg-white border border-zinc-200'}
        animate-in fade-in zoom-in-95 duration-300
      `}>
        {/* Close button */}
        <button
          onClick={onClose}
          className={`absolute top-3 right-3 p-1 rounded-full ${isDark ? 'hover:bg-zinc-800' : 'hover:bg-zinc-100'}`}
        >
          <X className="w-5 h-5" />
        </button>
        
        {/* Content */}
        <div className="text-center">
          <div className={`w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center ${isDark ? 'bg-zinc-800' : 'bg-zinc-100'}`}>
            <Icon className={`w-8 h-8 ${step.iconColor}`} />
          </div>
          
          <h3 className={`text-xl font-semibold mb-2 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            {step.title}
          </h3>
          
          <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            {step.description}
          </p>
        </div>
        
        {/* Footer */}
        <div className={`flex items-center justify-between mt-6 pt-4 border-t ${isDark ? 'border-zinc-700' : 'border-zinc-100'}`}>
          <span className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
            {stepIndex + 1} of {totalSteps}
          </span>
          
          <div className="flex items-center gap-2">
            {stepIndex > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={onPrev}
                className={isDark ? 'border-zinc-600' : ''}
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Back
              </Button>
            )}
            
            <Button
              size="sm"
              onClick={onNext}
              className="bg-orange-500 hover:bg-orange-600 text-white"
            >
              {stepIndex === totalSteps - 1 ? 'Finish' : 'Next'}
              {stepIndex < totalSteps - 1 && <ChevronRight className="w-4 h-4 ml-1" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Completion dialog
const CompletionDialog = ({ open, onClose, isDark }) => {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className={`${isDark ? 'bg-zinc-900 border-zinc-700' : ''} max-w-md`}>
        <div className="text-center py-6">
          <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-full flex items-center justify-center shadow-lg">
            <Sparkles className="w-10 h-10 text-white" />
          </div>
          
          <h2 className={`text-2xl font-bold mb-2 ${isDark ? 'text-zinc-100' : ''}`}>
            You're All Set!
          </h2>
          
          <p className={`${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            You've completed the tour. Explore the app and reach out if you need any help.
          </p>
          
          <div className={`mt-6 p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-100'}`}>
            <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
              <strong>Pro Tip:</strong> You can replay this tour anytime from your Profile settings.
            </p>
          </div>
        </div>
        
        <DialogFooter>
          <Button
            onClick={onClose}
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            Get Started
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
  const [showTour, setShowTour] = useState(false);
  const [showCompletion, setShowCompletion] = useState(false);
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
    
    // Small delay to let the page render first
    const timer = setTimeout(checkOnboarding, 1000);
    return () => clearTimeout(timer);
  }, [user, token]);

  // Set up tour steps based on role
  useEffect(() => {
    if (user?.role) {
      setSteps(getTourSteps(user.role));
    }
  }, [user?.role]);

  const handleStartTour = () => {
    setShowWelcome(false);
    setTimeout(() => {
      setShowTour(true);
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

  const handleNext = async () => {
    if (stepIndex < steps.length - 1) {
      setStepIndex(prev => prev + 1);
    } else {
      // Tour complete
      setShowTour(false);
      setShowCompletion(true);
      try {
        await axios.post(`${API}/my/complete-onboarding`);
      } catch (error) {
        console.error('Failed to mark onboarding complete:', error);
      }
    }
  };

  const handlePrev = () => {
    if (stepIndex > 0) {
      setStepIndex(prev => prev - 1);
    }
  };

  const handleClose = async () => {
    setShowTour(false);
    try {
      await axios.post(`${API}/my/complete-onboarding`);
    } catch (error) {
      console.error('Failed to mark onboarding complete:', error);
    }
  };

  const handleCompletionClose = () => {
    setShowCompletion(false);
  };

  if (loading || !user) return null;

  return (
    <>
      <WelcomeDialog
        open={showWelcome}
        onStart={handleStartTour}
        onSkip={handleSkipTour}
        isDark={isDark}
      />
      
      {showTour && steps[stepIndex] && (
        <TourTooltip
          step={steps[stepIndex]}
          stepIndex={stepIndex}
          totalSteps={steps.length}
          onNext={handleNext}
          onPrev={handlePrev}
          onClose={handleClose}
          isDark={isDark}
        />
      )}
      
      <CompletionDialog
        open={showCompletion}
        onClose={handleCompletionClose}
        isDark={isDark}
      />
    </>
  );
};

export default OnboardingTour;
