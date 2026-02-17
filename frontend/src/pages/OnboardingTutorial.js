import React, { useState } from 'react';
import { 
  BookOpen, Users, UserPlus, Key, CheckCircle, ArrowRight, 
  Play, ChevronDown, ChevronUp, Building2, Briefcase, 
  ClipboardList, Calendar, DollarSign, FileText, Shield,
  Clock, MapPin, Smartphone, Mail, Lock, Eye, UserCheck
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';

const OnboardingTutorial = () => {
  const [expandedTutorial, setExpandedTutorial] = useState('add-employee');
  const [completedSteps, setCompletedSteps] = useState([]);

  const markStepComplete = (stepId) => {
    if (!completedSteps.includes(stepId)) {
      setCompletedSteps([...completedSteps, stepId]);
    }
  };

  const tutorials = [
    {
      id: 'add-employee',
      title: 'Add New Employee',
      description: 'Create employee records in the HR system',
      icon: UserPlus,
      color: 'emerald',
      duration: '2 min',
      steps: [
        {
          id: 'step1',
          title: 'Navigate to Employees',
          description: 'Go to HR section in the sidebar and click on "Employees"',
          action: 'Click on "Employees" in the left sidebar under HR section',
          tip: 'You can also use keyboard shortcut Ctrl+E',
        },
        {
          id: 'step2',
          title: 'Click Add Employee',
          description: 'Open the new employee form',
          action: 'Click the "+ Add Employee" button in the top right corner',
          tip: 'The button is highlighted in blue',
        },
        {
          id: 'step3',
          title: 'Fill Basic Information',
          description: 'Enter employee details',
          action: 'Fill in: Employee ID, First Name, Last Name, Work Email, Phone',
          tip: 'Work Email will be used as their login email',
          fields: ['Employee ID (e.g., EMP001)', 'First Name', 'Last Name', 'Work Email', 'Phone Number']
        },
        {
          id: 'step4',
          title: 'Add Work Information',
          description: 'Set department and role details',
          action: 'Select Department, Designation, Reporting Manager, and Joining Date',
          tip: 'Department helps organize employees and filter reports',
          fields: ['Department', 'Designation', 'Reporting Manager', 'Joining Date']
        },
        {
          id: 'step5',
          title: 'Save Employee',
          description: 'Create the employee record',
          action: 'Scroll down and click "Create Employee" button',
          tip: 'You can add more details like bank info later',
        },
      ]
    },
    {
      id: 'grant-access',
      title: 'Grant System Access',
      description: 'Create login credentials for employees',
      icon: Key,
      color: 'blue',
      duration: '1 min',
      steps: [
        {
          id: 'access1',
          title: 'Find the Employee',
          description: 'Locate the employee in the list',
          action: 'Go to Employees page and find the employee who needs system access',
          tip: 'Use the search bar to quickly find employees',
        },
        {
          id: 'access2',
          title: 'Click Grant Access',
          description: 'Open the access dialog',
          action: 'Click the green "Grant Access" button next to the employee',
          tip: 'The button shows a person with checkmark icon',
        },
        {
          id: 'access3',
          title: 'Select Role',
          description: 'Choose the appropriate system role',
          action: 'Select a role from the dropdown (Consultant, HR Manager, Admin, etc.)',
          tip: 'Role determines what features the employee can access',
          roles: [
            { name: 'Consultant', access: 'View own attendance, leaves, salary' },
            { name: 'Project Manager', access: 'Manage projects, assign team' },
            { name: 'HR Manager', access: 'Full HR module access' },
            { name: 'Admin', access: 'Full system access' },
          ]
        },
        {
          id: 'access4',
          title: 'Set Password',
          description: 'Create temporary login password',
          action: 'Enter a temporary password (default: Welcome@123)',
          tip: 'Employee should change this after first login',
        },
        {
          id: 'access5',
          title: 'Grant Access',
          description: 'Complete the process',
          action: 'Click "Grant Access" button to create login credentials',
          tip: 'A success message will show the email and password',
        },
      ]
    },
    {
      id: 'attendance',
      title: 'Mark Attendance',
      description: 'How employees check-in and check-out',
      icon: Clock,
      color: 'orange',
      duration: '1 min',
      steps: [
        {
          id: 'att1',
          title: 'Quick Attendance Widget',
          description: 'Use the dashboard widget',
          action: 'On the dashboard, find the "Quick Attendance" card and click "Check In"',
          tip: 'This is the fastest way to mark attendance',
        },
        {
          id: 'att2',
          title: 'Select Work Location',
          description: 'Choose where you are working from',
          action: 'Select "Work From Home", "Office", or "On-Site"',
          tip: 'On-Site will ask you to select a client project',
        },
        {
          id: 'att3',
          title: 'Capture Photo (Optional)',
          description: 'Take attendance selfie if required',
          action: 'Click "Capture" to take a photo, or skip if not required',
          tip: 'Some organizations require photo verification',
        },
        {
          id: 'att4',
          title: 'Check Out',
          description: 'End your work day',
          action: 'Click "Check Out" when done working',
          tip: 'For On-Site work, you may be prompted to submit travel reimbursement',
        },
      ]
    },
    {
      id: 'leave-request',
      title: 'Apply for Leave',
      description: 'Request time off from work',
      icon: Calendar,
      color: 'purple',
      duration: '2 min',
      steps: [
        {
          id: 'leave1',
          title: 'Go to Leave Management',
          description: 'Access the leave section',
          action: 'Click "My Leaves" in the sidebar under My Workspace',
          tip: 'You can see your leave balance here',
        },
        {
          id: 'leave2',
          title: 'Apply New Leave',
          description: 'Start a leave request',
          action: 'Click "Apply Leave" button',
          tip: 'Check your balance before applying',
        },
        {
          id: 'leave3',
          title: 'Fill Leave Details',
          description: 'Enter leave information',
          action: 'Select leave type, start date, end date, and reason',
          tip: 'Attach documents for medical leave',
          fields: ['Leave Type', 'Start Date', 'End Date', 'Reason']
        },
        {
          id: 'leave4',
          title: 'Submit Request',
          description: 'Send for approval',
          action: 'Click "Submit" to send to your reporting manager',
          tip: 'You will receive email notification when approved',
        },
      ]
    },
  ];

  const quickLinks = [
    { title: 'Add Employee', path: '/employees', icon: UserPlus, color: 'emerald' },
    { title: 'Mark Attendance', path: '/my-attendance', icon: Clock, color: 'blue' },
    { title: 'Apply Leave', path: '/my-leaves', icon: Calendar, color: 'purple' },
    { title: 'View Payroll', path: '/payroll', icon: DollarSign, color: 'amber' },
    { title: 'Team Workload', path: '/team-workload', icon: Users, color: 'rose' },
  ];

  return (
    <div className="space-y-6" data-testid="onboarding-tutorial-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-3">
            <BookOpen className="w-8 h-8 text-blue-600" />
            Onboarding Tutorials
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">
            Step-by-step guides to help you get started with the ERP system
          </p>
        </div>
        <Badge className="bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 px-4 py-2">
          {completedSteps.length} steps completed
        </Badge>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-5 gap-4">
        {quickLinks.map((link) => {
          const Icon = link.icon;
          return (
            <a
              key={link.title}
              href={link.path}
              className={`p-4 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 hover:shadow-lg transition-all group`}
            >
              <div className={`w-10 h-10 rounded-lg bg-${link.color}-100 dark:bg-${link.color}-900/30 flex items-center justify-center mb-3`}>
                <Icon className={`w-5 h-5 text-${link.color}-600 dark:text-${link.color}-400`} />
              </div>
              <h3 className="font-medium text-zinc-900 dark:text-zinc-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                {link.title}
              </h3>
            </a>
          );
        })}
      </div>

      {/* Tutorial Cards */}
      <div className="space-y-4">
        {tutorials.map((tutorial) => {
          const Icon = tutorial.icon;
          const isExpanded = expandedTutorial === tutorial.id;
          const completedCount = tutorial.steps.filter(s => completedSteps.includes(s.id)).length;
          const progress = (completedCount / tutorial.steps.length) * 100;

          return (
            <Card 
              key={tutorial.id} 
              className={`border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 overflow-hidden transition-all ${isExpanded ? 'ring-2 ring-blue-500' : ''}`}
            >
              <CardHeader 
                className="cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
                onClick={() => setExpandedTutorial(isExpanded ? null : tutorial.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-xl bg-${tutorial.color}-100 dark:bg-${tutorial.color}-900/30 flex items-center justify-center`}>
                      <Icon className={`w-6 h-6 text-${tutorial.color}-600 dark:text-${tutorial.color}-400`} />
                    </div>
                    <div>
                      <CardTitle className="text-lg font-bold text-zinc-900 dark:text-zinc-100">{tutorial.title}</CardTitle>
                      <p className="text-sm text-zinc-500 dark:text-zinc-400">{tutorial.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm font-medium text-zinc-600 dark:text-zinc-300">{completedCount}/{tutorial.steps.length} steps</p>
                      <p className="text-xs text-zinc-400">{tutorial.duration}</p>
                    </div>
                    <div className="w-20 h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full bg-${tutorial.color}-500 transition-all`}
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-zinc-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-zinc-400" />
                    )}
                  </div>
                </div>
              </CardHeader>

              {isExpanded && (
                <CardContent className="border-t border-zinc-100 dark:border-zinc-800 pt-6">
                  <div className="space-y-4">
                    {tutorial.steps.map((step, index) => {
                      const isComplete = completedSteps.includes(step.id);
                      return (
                        <div 
                          key={step.id}
                          className={`p-4 rounded-xl border-2 transition-all ${
                            isComplete 
                              ? 'border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20' 
                              : 'border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/50'
                          }`}
                        >
                          <div className="flex items-start gap-4">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                              isComplete 
                                ? 'bg-emerald-500 text-white' 
                                : 'bg-zinc-200 dark:bg-zinc-700 text-zinc-600 dark:text-zinc-300'
                            }`}>
                              {isComplete ? (
                                <CheckCircle className="w-5 h-5" />
                              ) : (
                                <span className="font-bold text-sm">{index + 1}</span>
                              )}
                            </div>
                            <div className="flex-1">
                              <h4 className="font-semibold text-zinc-900 dark:text-zinc-100">{step.title}</h4>
                              <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">{step.description}</p>
                              
                              <div className="mt-3 p-3 bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-700">
                                <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-2">
                                  <ArrowRight className="w-4 h-4 text-blue-500" />
                                  {step.action}
                                </p>
                              </div>

                              {step.fields && (
                                <div className="mt-3 flex flex-wrap gap-2">
                                  {step.fields.map(field => (
                                    <Badge key={field} variant="outline" className="text-xs">
                                      {field}
                                    </Badge>
                                  ))}
                                </div>
                              )}

                              {step.roles && (
                                <div className="mt-3 grid grid-cols-2 gap-2">
                                  {step.roles.map(role => (
                                    <div key={role.name} className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                      <p className="font-medium text-sm text-blue-700 dark:text-blue-400">{role.name}</p>
                                      <p className="text-xs text-blue-600 dark:text-blue-500">{role.access}</p>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {step.tip && (
                                <p className="mt-2 text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                                  <span className="font-semibold">Tip:</span> {step.tip}
                                </p>
                              )}
                            </div>
                            <Button
                              size="sm"
                              variant={isComplete ? "outline" : "default"}
                              onClick={() => markStepComplete(step.id)}
                              className={isComplete ? "text-emerald-600" : ""}
                            >
                              {isComplete ? "Done" : "Mark Done"}
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {completedCount === tutorial.steps.length && (
                    <div className="mt-6 p-4 bg-emerald-100 dark:bg-emerald-900/30 rounded-xl text-center">
                      <CheckCircle className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
                      <p className="font-semibold text-emerald-700 dark:text-emerald-400">
                        Tutorial Complete! You've learned how to {tutorial.title.toLowerCase()}.
                      </p>
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>

      {/* Help Section */}
      <Card className="border-zinc-200 dark:border-zinc-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
                <Mail className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="font-bold text-zinc-900 dark:text-zinc-100">Need More Help?</h3>
                <p className="text-sm text-zinc-600 dark:text-zinc-400">Contact your HR administrator or system admin for assistance</p>
              </div>
            </div>
            <Button className="bg-blue-600 hover:bg-blue-700 text-white">
              Contact Support
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default OnboardingTutorial;
