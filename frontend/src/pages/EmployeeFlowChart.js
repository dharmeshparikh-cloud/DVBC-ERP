import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  CheckCircle2, Circle, AlertTriangle, ArrowDown, 
  UserPlus, FileText, Shield, DollarSign, Key, 
  Calendar, Clock, Briefcase, Building, ChevronRight,
  XCircle
} from 'lucide-react';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';

const STEPS = [
  {
    id: 'invite',
    title: 'HR Sends Onboarding Invite',
    actor: 'HR Manager',
    description: 'HR creates candidate record and sends onboarding email with unique link',
    page: '/onboarding',
    icon: UserPlus,
  },
  {
    id: 'candidate_form',
    title: 'Candidate Fills Onboarding Form',
    actor: 'Candidate',
    description: 'Personal details, documents, bank info, emergency contacts, declaration',
    page: null,
    icon: FileText,
  },
  {
    id: 'hr_review',
    title: 'HR Reviews & Completes Onboarding',
    actor: 'HR Manager',
    description: 'Reviews submission, selects system Role, assigns Employee ID, completes onboarding',
    page: '/onboarding',
    icon: Shield,
  },
  {
    id: 'go_live',
    title: 'Go-Live Approval',
    actor: 'Admin / HR',
    description: 'Auto-created Go-Live request appears in Approvals Center. Admin/HR approves to create user account & login credentials',
    page: '/approvals',
    icon: Key,
  },
  {
    id: 'ctc_design',
    title: 'CTC Structure Design',
    actor: 'HR Manager',
    description: 'HR designs salary components (Basic, HRA, Allowances). Goes to Admin for approval',
    page: '/ctc-designer',
    icon: DollarSign,
  },
  {
    id: 'ctc_approve',
    title: 'CTC Approval',
    actor: 'Admin',
    description: 'Admin reviews and approves CTC. Salary gets activated in employee record',
    page: '/approvals',
    icon: DollarSign,
  },
  {
    id: 'permissions',
    title: 'Permission Configuration',
    actor: 'Admin',
    description: 'Assign module access permissions matching the employee role',
    page: '/permissions',
    icon: Shield,
  },
  {
    id: 'leave_balance',
    title: 'Leave Balance Setup',
    actor: 'HR / System',
    description: 'Configure annual leave entitlements (CL, SL, EL, etc.)',
    page: '/leave-management',
    icon: Calendar,
  },
  {
    id: 'first_login',
    title: 'Employee First Login',
    actor: 'Employee',
    description: 'Employee uses credentials from email to log in. Can check in, view details, access assigned modules',
    page: null,
    icon: Clock,
  },
  {
    id: 'daily_work',
    title: 'Employee Starts Working',
    actor: 'Employee',
    description: 'Daily check-in, meetings, MOM recording, expense filing, project work',
    page: '/consulting-meetings',
    icon: Briefcase,
  },
  {
    id: 'payroll',
    title: 'Payroll Processing',
    actor: 'HR / Admin',
    description: 'Monthly payroll run based on CTC, attendance, deductions. Salary slip generation',
    page: '/payroll',
    icon: Building,
  },
];

const EmployeeFlowChart = ({ employeeData }) => {
  const navigate = useNavigate();

  // Determine status of each step based on employee data
  const getStepStatus = (stepId) => {
    if (!employeeData) return 'pending';
    const { employee, user, ctc, permissions, leaveBalance, attendance, payroll, onboarding, goLive } = employeeData;

    switch (stepId) {
      case 'invite':
        return onboarding ? 'done' : 'pending';
      case 'candidate_form':
        return onboarding?.status === 'completed' || onboarding?.status === 'submitted' ? 'done' : (onboarding ? 'in_progress' : 'pending');
      case 'hr_review':
        return employee?.status === 'onboarded' ? 'done' : (onboarding?.status === 'submitted' ? 'in_progress' : 'pending');
      case 'go_live':
        return employee?.go_live_status === 'active' ? 'done' : (goLive?.status === 'pending' ? 'in_progress' : 'pending');
      case 'ctc_design':
        return ctc?.active ? 'done' : (ctc?.pending ? 'in_progress' : 'pending');
      case 'ctc_approve':
        return ctc?.active?.status === 'active' ? 'done' : (ctc?.pending ? 'in_progress' : 'pending');
      case 'permissions':
        return permissions && Object.keys(permissions).length > 0 ? 'done' : 'missing';
      case 'leave_balance':
        return leaveBalance ? 'done' : 'missing';
      case 'first_login':
        return user?.is_active && attendance ? 'done' : (user?.is_active ? 'ready' : 'pending');
      case 'daily_work':
        return attendance ? 'done' : 'pending';
      case 'payroll':
        return payroll ? 'done' : 'pending';
      default:
        return 'pending';
    }
  };

  const STATUS_CONFIG = {
    done: { color: 'bg-emerald-500', textColor: 'text-emerald-700', bgColor: 'bg-emerald-50', borderColor: 'border-emerald-300', label: 'Completed', Icon: CheckCircle2 },
    in_progress: { color: 'bg-blue-500', textColor: 'text-blue-700', bgColor: 'bg-blue-50', borderColor: 'border-blue-300', label: 'In Progress', Icon: Clock },
    ready: { color: 'bg-amber-500', textColor: 'text-amber-700', bgColor: 'bg-amber-50', borderColor: 'border-amber-300', label: 'Ready', Icon: Circle },
    missing: { color: 'bg-red-500', textColor: 'text-red-700', bgColor: 'bg-red-50', borderColor: 'border-red-300', label: 'Action Needed', Icon: AlertTriangle },
    pending: { color: 'bg-zinc-300', textColor: 'text-zinc-500', bgColor: 'bg-zinc-50', borderColor: 'border-zinc-200', label: 'Pending', Icon: Circle },
  };

  return (
    <div className="max-w-3xl mx-auto py-6 px-4" data-testid="employee-flow-chart">
      <h2 className="text-xl font-bold mb-1 text-zinc-900">Employee Lifecycle Flow</h2>
      {employeeData?.employee && (
        <p className="text-sm text-zinc-500 mb-6">
          {employeeData.employee.first_name} {employeeData.employee.last_name} ({employeeData.user?.employee_id})
        </p>
      )}

      <div className="relative">
        {STEPS.map((step, idx) => {
          const status = getStepStatus(step.id);
          const config = STATUS_CONFIG[status];
          const Icon = step.icon;
          const StatusIcon = config.Icon;
          const isLast = idx === STEPS.length - 1;

          return (
            <div key={step.id} className="relative" data-testid={`flow-step-${step.id}`}>
              {/* Connector line */}
              {!isLast && (
                <div className="absolute left-6 top-[72px] w-0.5 h-8 bg-zinc-200 z-0">
                  <ArrowDown className="w-3 h-3 text-zinc-300 absolute -bottom-1 -left-[5px]" />
                </div>
              )}

              <div
                className={`flex items-start gap-4 p-4 rounded-xl border-2 mb-8 transition-all duration-200 ${config.bgColor} ${config.borderColor} ${step.page ? 'cursor-pointer hover:shadow-md' : ''}`}
                onClick={() => step.page && navigate(step.page)}
              >
                {/* Step icon with status ring */}
                <div className="relative shrink-0">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center ${config.color} bg-opacity-15`}>
                    <Icon className={`w-5 h-5 ${config.textColor}`} />
                  </div>
                  <div className={`absolute -bottom-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center ${config.color}`}>
                    <StatusIcon className="w-3 h-3 text-white" />
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-zinc-900 text-sm">{step.title}</h3>
                    <Badge className={`text-[10px] px-1.5 py-0 h-4 ${config.color} text-white`}>
                      {config.label}
                    </Badge>
                    <Badge className="text-[10px] px-1.5 py-0 h-4 bg-zinc-200 text-zinc-600">
                      {step.actor}
                    </Badge>
                  </div>
                  <p className="text-xs text-zinc-600 mt-1">{step.description}</p>
                </div>

                {step.page && (
                  <ChevronRight className="w-4 h-4 text-zinc-400 shrink-0 mt-1" />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default EmployeeFlowChart;
