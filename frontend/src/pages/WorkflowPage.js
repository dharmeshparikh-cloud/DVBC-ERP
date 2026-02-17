import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  Users, Briefcase, FileText, DollarSign, TrendingUp, Clock,
  MapPin, CreditCard, CheckCircle, ArrowRight, ArrowDown,
  Target, Building2, Calendar, Receipt, PieChart, UserCheck,
  Plane, Wallet, ClipboardList, Award, BarChart3, Play,
  ChevronRight, Info, Zap, GitBranch, CalendarDays, Calculator,
  Shield, RefreshCw, Bell, Upload, Send, FileCheck
} from 'lucide-react';

const WORKFLOWS = {
  sales_to_delivery: {
    id: 'sales_to_delivery',
    title: 'Lead to Delivery',
    subtitle: 'Sales → Consulting Handover',
    color: 'orange',
    icon: TrendingUp,
    steps: [
      { id: 'lead', title: 'Lead Capture', description: 'New lead enters system', icon: Target, link: '/leads', module: 'Sales' },
      { id: 'qualify', title: 'Qualification', description: 'Lead scoring & qualification', icon: CheckCircle, link: '/leads', module: 'Sales' },
      { id: 'proposal', title: 'Proposal', description: 'SOW & pricing shared', icon: FileText, link: '/proposals', module: 'Sales' },
      { id: 'agreement', title: 'Agreement', description: 'Contract signed', icon: ClipboardList, link: '/agreements', module: 'Sales' },
      { id: 'kickoff', title: 'Kickoff Request', description: 'Sales hands over to Consulting', icon: Zap, link: '/kickoff-requests', module: 'Sales' },
      { id: 'kickoff_accept', title: 'Kickoff Accepted', description: 'Consulting accepts project', icon: CheckCircle, link: '/kickoff-requests', module: 'Consulting' },
      { id: 'assign', title: 'Team Assignment', description: 'PM/Admin assigns consultants', icon: Users, link: '/projects', module: 'Consulting' },
      { id: 'delivery', title: 'Meeting Delivery', description: 'Services delivered', icon: Calendar, link: '/meetings', module: 'Consulting' },
      { id: 'closure', title: 'Project Closure', description: 'Project completed', icon: Award, link: '/projects', module: 'Consulting' },
    ]
  },
  attendance_to_payroll: {
    id: 'attendance_to_payroll',
    title: 'Attendance to Payroll',
    subtitle: 'Employee Compensation Flow',
    color: 'blue',
    icon: Clock,
    steps: [
      { id: 'checkin', title: 'Check-In', description: 'Selfie + GPS capture', icon: MapPin, link: '/attendance', module: 'HR' },
      { id: 'work', title: 'Work Location', description: 'Office or Client Site', icon: Building2, link: '/attendance', module: 'HR' },
      { id: 'checkout', title: 'Check-Out', description: 'End of day', icon: Clock, link: '/attendance', module: 'HR' },
      { id: 'travel', title: 'Travel Claim', description: 'Auto-calculated reimbursement', icon: Plane, link: '/travel-reimbursements', module: 'HR' },
      { id: 'expense', title: 'Expense Submit', description: 'Additional expenses', icon: Receipt, link: '/expenses', module: 'HR' },
      { id: 'approval', title: 'HR Approval', description: 'Manager review', icon: UserCheck, link: '/attendance-approvals', module: 'HR' },
      { id: 'payroll', title: 'Payroll Process', description: 'Salary calculation', icon: Wallet, link: '/payroll', module: 'Finance' },
      { id: 'payout', title: 'Payout', description: 'Salary disbursed', icon: CreditCard, link: '/payroll', module: 'Finance' },
    ]
  },
  leave_management: {
    id: 'leave_management',
    title: 'Leave Management',
    subtitle: 'Time-Off Request Flow',
    color: 'teal',
    icon: CalendarDays,
    steps: [
      { id: 'request', title: 'Leave Request', description: 'Employee submits request', icon: FileText, link: '/my-leaves', module: 'HR' },
      { id: 'balance_check', title: 'Balance Check', description: 'Auto-verify leave balance', icon: Calculator, link: '/leave-management', module: 'HR' },
      { id: 'manager_approval', title: 'Manager Approval', description: 'Reporting manager review', icon: UserCheck, link: '/leave-management', module: 'HR' },
      { id: 'hr_approval', title: 'HR Approval', description: 'HR team verification', icon: Shield, link: '/leave-management', module: 'HR' },
      { id: 'balance_update', title: 'Balance Update', description: 'Deduct from quota', icon: RefreshCw, link: '/leave-management', module: 'HR' },
      { id: 'calendar_sync', title: 'Calendar Sync', description: 'Update team calendar', icon: Calendar, link: '/leave-management', module: 'HR' },
      { id: 'notify', title: 'Notification', description: 'Team notified', icon: Bell, link: '/leave-management', module: 'HR' },
    ]
  },
  expense_reimbursement: {
    id: 'expense_reimbursement',
    title: 'Expense Reimbursement',
    subtitle: 'Expense Claim Flow',
    color: 'rose',
    icon: Receipt,
    steps: [
      { id: 'entry', title: 'Expense Entry', description: 'Log expense details', icon: FileText, link: '/my-expenses', module: 'HR' },
      { id: 'receipt', title: 'Receipt Upload', description: 'Attach proof/bills', icon: Upload, link: '/my-expenses', module: 'HR' },
      { id: 'submit', title: 'Submit Claim', description: 'Send for approval', icon: Send, link: '/expenses', module: 'HR' },
      { id: 'manager_review', title: 'Manager Review', description: 'Reporting manager approval', icon: UserCheck, link: '/expenses', module: 'HR' },
      { id: 'finance_approval', title: 'Finance/Admin Approval', description: 'Final verification', icon: Shield, link: '/expenses', module: 'Finance' },
      { id: 'process', title: 'Process Payment', description: 'Add to payroll/direct', icon: Wallet, link: '/payroll', module: 'Finance' },
      { id: 'reimburse', title: 'Reimbursement', description: 'Amount credited', icon: CreditCard, link: '/payroll', module: 'Finance' },
    ]
  },
  invoice_to_collection: {
    id: 'invoice_to_collection',
    title: 'Invoice to Collection',
    subtitle: 'Revenue Collection Flow',
    color: 'amber',
    icon: Receipt,
    steps: [
      { id: 'generate', title: 'Invoice Generated', description: 'Create from agreement', icon: FileText, link: '/invoices', module: 'Finance' },
      { id: 'review', title: 'Review & Approve', description: 'Finance team review', icon: CheckCircle, link: '/invoices', module: 'Finance' },
      { id: 'send', title: 'Send to Client', description: 'Email/share invoice', icon: Send, link: '/invoices', module: 'Finance' },
      { id: 'followup', title: 'Payment Follow-up', description: 'Track & remind', icon: Bell, link: '/invoices', module: 'Finance' },
      { id: 'receive', title: 'Payment Received', description: 'Record payment', icon: CreditCard, link: '/payments', module: 'Finance' },
      { id: 'reconcile', title: 'Reconciliation', description: 'Match with bank', icon: RefreshCw, link: '/payments', module: 'Finance' },
      { id: 'receipt', title: 'Receipt Issued', description: 'Acknowledge payment', icon: FileCheck, link: '/payments', module: 'Finance' },
      { id: 'close', title: 'Invoice Closed', description: 'Mark as paid', icon: CheckCircle, link: '/invoices', module: 'Finance' },
    ]
  },
  hr_operations: {
    id: 'hr_operations',
    title: 'HR Operations',
    subtitle: 'Employee Lifecycle',
    color: 'emerald',
    icon: Users,
    steps: [
      { id: 'onboard', title: 'Onboarding', description: 'New employee setup', icon: UserCheck, link: '/onboarding', module: 'HR' },
      { id: 'profile', title: 'Profile Setup', description: 'Documents & details', icon: FileText, link: '/employees', module: 'HR' },
      { id: 'assign_proj', title: 'Project Assignment', description: 'Assign to projects', icon: Briefcase, link: '/projects', module: 'Consulting' },
      { id: 'attendance', title: 'Daily Attendance', description: 'Track presence', icon: Clock, link: '/attendance', module: 'HR' },
      { id: 'performance', title: 'Performance', description: 'KPI tracking', icon: BarChart3, link: '/performance', module: 'HR' },
      { id: 'leaves', title: 'Leave Management', description: 'Time off requests', icon: Calendar, link: '/leave-management', module: 'HR' },
      { id: 'appraisal', title: 'Appraisal', description: 'Annual review', icon: Award, link: '/performance', module: 'HR' },
      { id: 'payroll_hr', title: 'Compensation', description: 'Salary & benefits', icon: DollarSign, link: '/payroll', module: 'Finance' },
    ]
  },
  finance_flow: {
    id: 'finance_flow',
    title: 'Revenue to Reports',
    subtitle: 'Financial Operations',
    color: 'violet',
    icon: DollarSign,
    steps: [
      { id: 'agreement_fin', title: 'Agreement Value', description: 'Contract amount', icon: FileText, link: '/agreements', module: 'Sales' },
      { id: 'invoice', title: 'Invoice Generation', description: 'Bill creation', icon: Receipt, link: '/invoices', module: 'Finance' },
      { id: 'payment_track', title: 'Payment Tracking', description: 'AR management', icon: CreditCard, link: '/payments', module: 'Finance' },
      { id: 'expense_fin', title: 'Expense Tracking', description: 'Cost management', icon: Wallet, link: '/expenses', module: 'Finance' },
      { id: 'payroll_fin', title: 'Payroll Expense', description: 'Salary costs', icon: Users, link: '/payroll', module: 'Finance' },
      { id: 'pl', title: 'P&L Analysis', description: 'Profit & loss', icon: PieChart, link: '/reports', module: 'Finance' },
      { id: 'reports', title: 'Reports', description: 'Financial reports', icon: BarChart3, link: '/reports', module: 'Finance' },
      { id: 'dashboard', title: 'Dashboard', description: 'Executive view', icon: TrendingUp, link: '/dashboard', module: 'Admin' },
    ]
  }
};

const MODULE_COLORS = {
  Sales: { 
    bg: 'bg-orange-100 dark:bg-orange-900/30', 
    text: 'text-orange-700 dark:text-orange-400', 
    border: 'border-orange-300 dark:border-orange-700' 
  },
  HR: { 
    bg: 'bg-emerald-100 dark:bg-emerald-900/30', 
    text: 'text-emerald-700 dark:text-emerald-400', 
    border: 'border-emerald-300 dark:border-emerald-700' 
  },
  Consulting: { 
    bg: 'bg-blue-100 dark:bg-blue-900/30', 
    text: 'text-blue-700 dark:text-blue-400', 
    border: 'border-blue-300 dark:border-blue-700' 
  },
  Finance: { 
    bg: 'bg-violet-100 dark:bg-violet-900/30', 
    text: 'text-violet-700 dark:text-violet-400', 
    border: 'border-violet-300 dark:border-violet-700' 
  },
  Admin: { 
    bg: 'bg-zinc-100 dark:bg-zinc-800', 
    text: 'text-zinc-700 dark:text-zinc-300', 
    border: 'border-zinc-300 dark:border-zinc-600' 
  },
};

const GRADIENT_COLORS = {
  orange: 'from-orange-500 to-amber-500',
  blue: 'from-blue-500 to-indigo-500',
  emerald: 'from-emerald-500 to-teal-500',
  violet: 'from-violet-500 to-purple-500',
  teal: 'from-teal-500 to-cyan-500',
  rose: 'from-rose-500 to-pink-500',
  amber: 'from-amber-500 to-yellow-500',
};

const WorkflowPage = () => {
  const [activeWorkflow, setActiveWorkflow] = useState('sales_to_delivery');
  const [animatingStep, setAnimatingStep] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  const currentWorkflow = WORKFLOWS[activeWorkflow];

  const startAnimation = () => {
    setIsAnimating(true);
    setAnimatingStep(0);
    
    const interval = setInterval(() => {
      setAnimatingStep(prev => {
        if (prev >= currentWorkflow.steps.length - 1) {
          clearInterval(interval);
          setIsAnimating(false);
          return 0;
        }
        return prev + 1;
      });
    }, 1000);
  };

  return (
    <div className="space-y-6" data-testid="workflow-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-3">
            <GitBranch className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            ERP Workflow
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">Interactive visualization of all business processes</p>
        </div>
        <Badge className="bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 px-4 py-2">
          <Zap className="w-4 h-4 mr-2" />
          All Systems Connected
        </Badge>
      </div>

      {/* Workflow Selector */}
      <div className="grid grid-cols-4 gap-4">
        {Object.values(WORKFLOWS).map((workflow) => {
          const Icon = workflow.icon;
          const isActive = activeWorkflow === workflow.id;
          return (
            <Card
              key={workflow.id}
              className={`cursor-pointer transition-all ${
                isActive 
                  ? `ring-2 ring-${workflow.color}-500 bg-gradient-to-br ${GRADIENT_COLORS[workflow.color]} text-white` 
                  : 'hover:shadow-lg border-zinc-200 dark:border-zinc-700 dark:bg-zinc-900'
              }`}
              onClick={() => setActiveWorkflow(workflow.id)}
              data-testid={`workflow-${workflow.id}`}
            >
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                    isActive ? 'bg-white/20' : `bg-${workflow.color}-100 dark:bg-${workflow.color}-900/30`
                  }`}>
                    <Icon className={`w-6 h-6 ${isActive ? 'text-white' : `text-${workflow.color}-600 dark:text-${workflow.color}-400`}`} />
                  </div>
                  <div>
                    <h3 className={`font-bold ${isActive ? 'text-white' : 'text-zinc-900 dark:text-zinc-100'}`}>{workflow.title}</h3>
                    <p className={`text-sm ${isActive ? 'text-white/70' : 'text-zinc-500 dark:text-zinc-400'}`}>{workflow.subtitle}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Animation Control */}
      <div className="flex items-center justify-between bg-zinc-50 dark:bg-zinc-900 rounded-xl p-4 border border-zinc-200 dark:border-zinc-700">
        <div className="flex items-center gap-4">
          <Info className="w-5 h-5 text-zinc-400" />
          <div>
            <p className="font-medium text-zinc-700 dark:text-zinc-300">Click on any step to navigate to that module</p>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">Or play the animation to see the complete flow</p>
          </div>
        </div>
        <Button 
          onClick={startAnimation}
          disabled={isAnimating}
          className={`bg-gradient-to-r ${GRADIENT_COLORS[currentWorkflow.color]} text-white`}
        >
          <Play className="w-4 h-4 mr-2" />
          {isAnimating ? 'Playing...' : 'Play Animation'}
        </Button>
      </div>

      {/* Workflow Steps */}
      <Card className="border-zinc-200 dark:border-zinc-700 dark:bg-zinc-900">
        <CardHeader className="border-b border-zinc-100 dark:border-zinc-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {React.createElement(currentWorkflow.icon, { 
                className: `w-6 h-6 text-${currentWorkflow.color}-600 dark:text-${currentWorkflow.color}-400` 
              })}
              <div>
                <CardTitle className="text-xl dark:text-zinc-100">{currentWorkflow.title}</CardTitle>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">{currentWorkflow.subtitle}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {['Sales', 'HR', 'Consulting', 'Finance'].map(module => (
                <Badge 
                  key={module} 
                  className={`${MODULE_COLORS[module].bg} ${MODULE_COLORS[module].text} text-xs`}
                >
                  {module}
                </Badge>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-8">
          {/* Horizontal Flow */}
          <div className="flex items-center justify-between overflow-x-auto pb-4">
            {currentWorkflow.steps.map((step, index) => {
              const Icon = step.icon;
              const moduleColor = MODULE_COLORS[step.module];
              const isAnimated = isAnimating && index <= animatingStep;
              const isCurrentAnimating = isAnimating && index === animatingStep;
              
              return (
                <React.Fragment key={step.id}>
                  <Link 
                    to={step.link}
                    className={`flex flex-col items-center text-center min-w-[120px] transition-all duration-300 ${
                      isAnimated ? 'scale-105' : ''
                    } ${isCurrentAnimating ? 'animate-pulse' : ''}`}
                  >
                    <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-3 transition-all border-2 ${
                      isAnimated 
                        ? `bg-gradient-to-br ${GRADIENT_COLORS[currentWorkflow.color]} border-transparent shadow-lg` 
                        : `${moduleColor.bg} ${moduleColor.border}`
                    }`}>
                      <Icon className={`w-7 h-7 ${isAnimated ? 'text-white' : moduleColor.text}`} />
                    </div>
                    <h4 className={`font-semibold text-sm ${isAnimated ? 'text-zinc-900 dark:text-zinc-100' : 'text-zinc-700 dark:text-zinc-300'}`}>
                      {step.title}
                    </h4>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 max-w-[100px]">{step.description}</p>
                    <Badge className={`mt-2 text-[10px] ${moduleColor.bg} ${moduleColor.text}`}>
                      {step.module}
                    </Badge>
                  </Link>
                  
                  {index < currentWorkflow.steps.length - 1 && (
                    <div className="flex-shrink-0 mx-2">
                      <ArrowRight className={`w-6 h-6 transition-all duration-300 ${
                        isAnimating && index < animatingStep 
                          ? `text-${currentWorkflow.color}-500` 
                          : 'text-zinc-300 dark:text-zinc-600'
                      }`} />
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Module Overview Grid */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { 
            module: 'Sales', 
            icon: TrendingUp, 
            stats: [
              { label: 'Active Leads', value: '45', link: '/leads' },
              { label: 'Proposals', value: '12', link: '/proposals' },
              { label: 'Agreements', value: '8', link: '/agreements' },
            ]
          },
          { 
            module: 'HR', 
            icon: Users, 
            stats: [
              { label: 'Employees', value: '86', link: '/employees' },
              { label: 'Pending Approvals', value: '5', link: '/attendance-approvals' },
              { label: 'On Leave', value: '7', link: '/leave-management' },
            ]
          },
          { 
            module: 'Consulting', 
            icon: Briefcase, 
            stats: [
              { label: 'Active Projects', value: '23', link: '/projects' },
              { label: 'This Week Meetings', value: '34', link: '/meetings' },
              { label: 'Consultants', value: '42', link: '/consultants' },
            ]
          },
          { 
            module: 'Finance', 
            icon: DollarSign, 
            stats: [
              { label: 'Revenue YTD', value: '₹4.5Cr', link: '/reports' },
              { label: 'Pending Invoices', value: '15', link: '/invoices' },
              { label: 'This Month Payroll', value: '₹28L', link: '/payroll' },
            ]
          },
        ].map(({ module, icon: Icon, stats }) => {
          const colors = MODULE_COLORS[module];
          return (
            <Card key={module} className={`border ${colors.border} dark:bg-zinc-900`}>
              <CardHeader className={`${colors.bg} py-3`}>
                <div className="flex items-center gap-2">
                  <Icon className={`w-5 h-5 ${colors.text}`} />
                  <CardTitle className={`text-lg ${colors.text}`}>{module} Module</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                {stats.map(stat => (
                  <Link 
                    key={stat.label} 
                    to={stat.link}
                    className="flex items-center justify-between hover:bg-zinc-50 dark:hover:bg-zinc-800 p-2 rounded-lg transition-colors group"
                  >
                    <span className="text-sm text-zinc-600 dark:text-zinc-400">{stat.label}</span>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-zinc-900 dark:text-zinc-100">{stat.value}</span>
                      <ChevronRight className="w-4 h-4 text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </Link>
                ))}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick Links - What's Connected */}
      <Card className="border-zinc-200 dark:border-zinc-700 dark:bg-zinc-900">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 dark:text-zinc-100">
            <Zap className="w-5 h-5 text-amber-500" />
            System Integrations
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            {[
              { 
                from: 'Check-In', 
                to: 'Travel Claim', 
                description: 'Auto-calculates travel reimbursement on check-out from client site',
                icon: MapPin,
                color: 'emerald'
              },
              { 
                from: 'Agreement', 
                to: 'Project Kickoff', 
                description: 'Signed agreements trigger project creation workflow',
                icon: FileText,
                color: 'orange'
              },
              { 
                from: 'Attendance', 
                to: 'Payroll', 
                description: 'Attendance data feeds into payroll calculations',
                icon: Clock,
                color: 'blue'
              },
              { 
                from: 'Lead Conversion', 
                to: 'Revenue', 
                description: 'Won deals update revenue dashboards in real-time',
                icon: TrendingUp,
                color: 'violet'
              },
              { 
                from: 'Project Assignment', 
                to: 'Consultant Workload', 
                description: 'Project assignments update consultant capacity',
                icon: Users,
                color: 'teal'
              },
              { 
                from: 'Expense Submit', 
                to: 'P&L Impact', 
                description: 'Approved expenses reflect in project P&L',
                icon: Receipt,
                color: 'rose'
              },
            ].map((integration, idx) => (
              <div 
                key={idx}
                className={`p-4 rounded-xl bg-${integration.color}-50 dark:bg-${integration.color}-900/20 border border-${integration.color}-200 dark:border-${integration.color}-800`}
              >
                <div className="flex items-center gap-2 mb-2">
                  {React.createElement(integration.icon, { 
                    className: `w-5 h-5 text-${integration.color}-600 dark:text-${integration.color}-400` 
                  })}
                  <span className={`font-semibold text-${integration.color}-700 dark:text-${integration.color}-300`}>
                    {integration.from} → {integration.to}
                  </span>
                </div>
                <p className="text-sm text-zinc-600 dark:text-zinc-400">{integration.description}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default WorkflowPage;
