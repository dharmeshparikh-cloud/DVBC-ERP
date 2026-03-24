import React, { useState, useContext } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { toast } from 'sonner';
import { AuthContext, API } from '../../App';
import { useTheme } from '../../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Switch } from '../../components/ui/switch';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../../components/ui/select';
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger
} from '../../components/ui/tooltip';
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger
} from '../../components/ui/accordion';
import {
  Calendar, Plane, Receipt, Clock, DollarSign, FileText, Settings,
  Plus, Edit2, Trash2, Save, X, ChevronRight, Building2, Users,
  User, Briefcase, AlertCircle, CheckCircle, Eye, Search, Filter,
  Loader2, Copy, ToggleLeft, Info, IndianRupee, Calculator,
  BookOpen, HelpCircle, Lightbulb, Target, ShieldCheck, ArrowRight,
  CheckSquare, ExternalLink, Zap
} from 'lucide-react';
import { isAdmin as checkIsAdmin, isHR as checkIsHR } from '../../utils/roles';

// ==================== DROPDOWN OPTIONS FOR RULE FORM ====================

// Applies To (Scope) - Who does this rule apply to?
const APPLIES_TO_OPTIONS = {
  scope_type: [
    { value: 'all_employees', label: 'All Employees', description: 'Rule applies to everyone in the organization' },
    { value: 'by_department', label: 'By Department', description: 'Rule applies to specific departments' },
    { value: 'by_role', label: 'By Role', description: 'Rule applies to specific roles' },
    { value: 'by_grade', label: 'By Grade/Level', description: 'Rule applies to specific employee grades' },
    { value: 'by_employment_type', label: 'By Employment Type', description: 'Rule applies to specific employment types' },
    { value: 'by_location', label: 'By Location', description: 'Rule applies to specific work locations' },
    { value: 'by_experience', label: 'By Experience', description: 'Rule applies based on years of experience' },
    { value: 'by_ctc_range', label: 'By CTC Range', description: 'Rule applies to specific salary bands' },
    { value: 'custom_group', label: 'Custom Employee Group', description: 'Rule applies to a custom defined group' }
  ],
  departments: [
    { value: 'HR', label: 'Human Resources' },
    { value: 'Finance', label: 'Finance & Accounts' },
    { value: 'Sales', label: 'Sales' },
    { value: 'Marketing', label: 'Marketing' },
    { value: 'Engineering', label: 'Engineering' },
    { value: 'Operations', label: 'Operations' },
    { value: 'Consulting', label: 'Consulting' },
    { value: 'IT', label: 'Information Technology' },
    { value: 'Legal', label: 'Legal & Compliance' },
    { value: 'Admin', label: 'Administration' },
    { value: 'Support', label: 'Customer Support' },
    { value: 'R&D', label: 'Research & Development' }
  ],
  roles: [
    { value: 'admin', label: 'Administrator' },
    { value: 'hr_manager', label: 'HR Manager' },
    { value: 'manager', label: 'Manager' },
    { value: 'team_lead', label: 'Team Lead' },
    { value: 'senior', label: 'Senior Employee' },
    { value: 'employee', label: 'Employee' },
    { value: 'consultant', label: 'Consultant' },
    { value: 'contractor', label: 'Contractor' },
    { value: 'intern', label: 'Intern' },
    { value: 'trainee', label: 'Trainee' }
  ],
  grades: [
    { value: 'L1', label: 'L1 - Entry Level / Fresher' },
    { value: 'L2', label: 'L2 - Junior' },
    { value: 'L3', label: 'L3 - Mid-Level' },
    { value: 'L4', label: 'L4 - Senior' },
    { value: 'L5', label: 'L5 - Lead / Principal' },
    { value: 'L6', label: 'L6 - Manager' },
    { value: 'L7', label: 'L7 - Senior Manager / Director' },
    { value: 'L8', label: 'L8 - VP / Head' },
    { value: 'L9', label: 'L9 - CXO / Executive' }
  ],
  employment_types: [
    { value: 'full_time', label: 'Full-Time Permanent' },
    { value: 'part_time', label: 'Part-Time' },
    { value: 'contract', label: 'Contract / Fixed-Term' },
    { value: 'consultant', label: 'Consultant' },
    { value: 'intern', label: 'Intern / Trainee' },
    { value: 'probation', label: 'On Probation' },
    { value: 'confirmed', label: 'Confirmed Employee' },
    { value: 'notice_period', label: 'In Notice Period' }
  ],
  locations: [
    { value: 'metro', label: 'Metro Cities (Tier 1)' },
    { value: 'non_metro', label: 'Non-Metro Cities (Tier 2/3)' },
    { value: 'mumbai', label: 'Mumbai' },
    { value: 'delhi', label: 'Delhi NCR' },
    { value: 'bangalore', label: 'Bangalore' },
    { value: 'chennai', label: 'Chennai' },
    { value: 'hyderabad', label: 'Hyderabad' },
    { value: 'kolkata', label: 'Kolkata' },
    { value: 'pune', label: 'Pune' },
    { value: 'ahmedabad', label: 'Ahmedabad' },
    { value: 'remote', label: 'Remote / WFH' },
    { value: 'client_site', label: 'Client Site' }
  ],
  experience_ranges: [
    { value: '0-1', label: '0-1 years (Fresher)' },
    { value: '1-3', label: '1-3 years' },
    { value: '3-5', label: '3-5 years' },
    { value: '5-8', label: '5-8 years' },
    { value: '8-12', label: '8-12 years' },
    { value: '12+', label: '12+ years (Senior)' }
  ],
  ctc_ranges: [
    { value: '0-5L', label: 'Up to ₹5 LPA' },
    { value: '5-10L', label: '₹5-10 LPA' },
    { value: '10-20L', label: '₹10-20 LPA' },
    { value: '20-35L', label: '₹20-35 LPA' },
    { value: '35-50L', label: '₹35-50 LPA' },
    { value: '50L+', label: '₹50 LPA and above' }
  ]
};

// Category options by policy type
const CATEGORY_OPTIONS = {
  leave: [
    { value: 'quota', label: 'Leave Quota', description: 'Annual/monthly leave entitlements' },
    { value: 'accrual', label: 'Accrual Rules', description: 'How leaves are credited over time' },
    { value: 'carry_forward', label: 'Carry Forward', description: 'Rules for carrying unused leaves' },
    { value: 'encashment', label: 'Encashment', description: 'Rules for leave encashment at exit/year-end' },
    { value: 'special_leave', label: 'Special Leave', description: 'Maternity, Paternity, Bereavement, etc.' },
    { value: 'sandwich', label: 'Sandwich Policy', description: 'Rules for leaves between holidays' },
    { value: 'approval', label: 'Approval Rules', description: 'Leave approval workflow rules' },
    { value: 'restriction', label: 'Restrictions', description: 'Leave blackout periods, minimums, etc.' }
  ],
  travel: [
    { value: 'daily_allowance', label: 'Daily Allowance (DA)', description: 'Per diem for food and incidentals' },
    { value: 'accommodation', label: 'Accommodation', description: 'Hotel and lodging limits' },
    { value: 'transport_flight', label: 'Flight / Air Travel', description: 'Flight class and booking rules' },
    { value: 'transport_train', label: 'Train Travel', description: 'Train class and booking rules' },
    { value: 'transport_cab', label: 'Cab / Taxi', description: 'Local cab and taxi limits' },
    { value: 'transport_own', label: 'Own Vehicle', description: 'Mileage reimbursement rules' },
    { value: 'advance', label: 'Travel Advance', description: 'Pre-trip advance rules' },
    { value: 'settlement', label: 'Settlement', description: 'Post-trip claim settlement rules' },
    { value: 'international', label: 'International Travel', description: 'Rules specific to international trips' },
    { value: 'client_billable', label: 'Client Billable', description: 'Rules for client-reimbursable travel' }
  ],
  expense: [
    { value: 'approval_limits', label: 'Approval Limits', description: 'Auto-approval thresholds' },
    { value: 'documentation', label: 'Documentation', description: 'Receipt and invoice requirements' },
    { value: 'meal_entertainment', label: 'Meals & Entertainment', description: 'Limits for food and entertainment' },
    { value: 'office_supplies', label: 'Office Supplies', description: 'Stationery and supplies limits' },
    { value: 'communication', label: 'Communication', description: 'Phone, internet reimbursement' },
    { value: 'professional_dev', label: 'Professional Development', description: 'Training, certifications, books' },
    { value: 'compliance', label: 'Compliance', description: 'Audit and compliance rules' },
    { value: 'cutoff', label: 'Processing Cutoff', description: 'Submission and processing deadlines' }
  ],
  attendance: [
    { value: 'work_hours', label: 'Work Hours', description: 'Standard working hours and timing' },
    { value: 'core_hours', label: 'Core Hours', description: 'Mandatory presence timing' },
    { value: 'flexibility', label: 'Flexibility', description: 'Flexi-time and grace periods' },
    { value: 'wfh', label: 'Work From Home', description: 'Remote working policies' },
    { value: 'overtime', label: 'Overtime', description: 'OT calculation and limits' },
    { value: 'compoff', label: 'Compensatory Off', description: 'Comp-off accrual and usage' },
    { value: 'late_penalty', label: 'Late Penalty', description: 'Late arrival penalty rules' },
    { value: 'absent_penalty', label: 'Absent Penalty', description: 'Unauthorized absence rules' },
    { value: 'shift', label: 'Shift Rules', description: 'Night shift, rotational shift rules' }
  ],
  payroll: [
    { value: 'processing_date', label: 'Processing Date', description: 'Payroll run schedule' },
    { value: 'statutory_pf', label: 'PF (Provident Fund)', description: 'PF contribution rules' },
    { value: 'statutory_esi', label: 'ESI', description: 'ESI contribution rules' },
    { value: 'statutory_pt', label: 'Professional Tax', description: 'PT deduction rules' },
    { value: 'statutory_tds', label: 'TDS', description: 'Tax deduction rules' },
    { value: 'deduction_lop', label: 'LOP Deduction', description: 'Loss of Pay calculation' },
    { value: 'bonus', label: 'Bonus', description: 'Bonus calculation rules' },
    { value: 'reimbursement', label: 'Reimbursement', description: 'Expense reimbursement processing' },
    { value: 'disbursement', label: 'Disbursement', description: 'Salary credit rules' }
  ],
  general: [
    { value: 'probation', label: 'Probation', description: 'Probation period rules' },
    { value: 'notice_period', label: 'Notice Period', description: 'Resignation notice rules' },
    { value: 'termination', label: 'Termination', description: 'Employment termination rules' },
    { value: 'increment', label: 'Increment', description: 'Annual increment rules' },
    { value: 'promotion', label: 'Promotion', description: 'Promotion eligibility rules' },
    { value: 'confirmation', label: 'Confirmation', description: 'Employment confirmation rules' },
    { value: 'retirement', label: 'Retirement', description: 'Retirement age and rules' },
    { value: 'workplace', label: 'Workplace', description: 'Dress code, conduct, etc.' }
  ]
};

// Unit options based on rule type and category
const UNIT_OPTIONS = [
  { value: 'days/year', label: 'Days per Year' },
  { value: 'days/month', label: 'Days per Month' },
  { value: 'days', label: 'Days' },
  { value: 'hours', label: 'Hours' },
  { value: 'hours/day', label: 'Hours per Day' },
  { value: 'hours/week', label: 'Hours per Week' },
  { value: 'hours/month', label: 'Hours per Month' },
  { value: 'minutes', label: 'Minutes' },
  { value: 'INR', label: 'INR (₹)' },
  { value: 'INR/day', label: 'INR per Day' },
  { value: 'INR/month', label: 'INR per Month' },
  { value: 'INR/km', label: 'INR per Kilometer' },
  { value: 'INR/trip', label: 'INR per Trip' },
  { value: 'percent', label: 'Percentage (%)' },
  { value: 'percent_of_basic', label: '% of Basic Salary' },
  { value: 'percent_of_ctc', label: '% of CTC' },
  { value: 'count', label: 'Count / Number' },
  { value: 'incidents', label: 'Incidents' },
  { value: 'times', label: 'Times / Occurrences' },
  { value: 'months', label: 'Months' },
  { value: 'weeks', label: 'Weeks' },
  { value: 'years', label: 'Years' },
  { value: 'day_of_month', label: 'Day of Month' },
  { value: 'AM', label: 'Time (AM)' },
  { value: 'PM', label: 'Time (PM)' }
];

// String Value templates based on rule type
const STRING_VALUE_TEMPLATES = {
  limit: [
    { value: 'not_applicable', label: '-- Not Applicable --' },
    { value: 'max_per_claim', label: 'Maximum per single claim' },
    { value: 'max_per_day', label: 'Maximum per day' },
    { value: 'max_per_month', label: 'Maximum per month' },
    { value: 'max_per_year', label: 'Maximum per year' },
    { value: 'min_required', label: 'Minimum required' },
    { value: 'cap_ceiling', label: 'Absolute cap/ceiling' }
  ],
  threshold: [
    { value: 'not_applicable', label: '-- Not Applicable --' },
    { value: 'trigger_above', label: 'Trigger when above value' },
    { value: 'trigger_below', label: 'Trigger when below value' },
    { value: 'require_approval_above', label: 'Require approval above value' },
    { value: 'auto_approve_below', label: 'Auto-approve below value' },
    { value: 'penalty_after', label: 'Apply penalty after threshold' },
    { value: 'bonus_eligible_above', label: 'Bonus eligible above value' }
  ],
  condition: [
    { value: 'select_condition', label: '-- Select Condition Type --' },
    { value: 'if_then', label: 'IF-THEN Condition' },
    { value: 'and_condition', label: 'AND Condition (all must be true)' },
    { value: 'or_condition', label: 'OR Condition (any one true)' },
    { value: 'when_equals', label: 'WHEN equals specific value' },
    { value: 'when_greater', label: 'WHEN greater than value' },
    { value: 'when_less', label: 'WHEN less than value' },
    { value: 'when_between', label: 'WHEN between range' },
    { value: 'except_when', label: 'EXCEPT WHEN condition' },
    { value: 'mandatory', label: 'Mandatory / Required' },
    { value: 'optional', label: 'Optional' },
    { value: 'prohibited', label: 'Prohibited / Not Allowed' }
  ],
  formula: [
    { value: 'select_formula', label: '-- Select Formula Type --' },
    { value: 'basic_salary * 0.12', label: 'Basic × 12% (PF Standard)' },
    { value: 'basic_salary * 0.0325', label: 'Basic × 3.25% (ESI Employer)' },
    { value: 'basic_salary * 0.0075', label: 'Basic × 0.75% (ESI Employee)' },
    { value: '(gross_ctc / 30) * lop_days', label: 'Gross CTC/30 × LOP Days' },
    { value: '(basic_salary / working_days) * present_days', label: 'Pro-rata Basic' },
    { value: 'gross_salary * tax_rate', label: 'Gross × Tax Rate (TDS)' },
    { value: 'basic_per_day', label: 'Basic Per Day Calculation' },
    { value: 'percentage_of_basic', label: 'Percentage of Basic Salary' },
    { value: 'slab_based', label: 'Slab-based Calculation' },
    { value: 'custom_formula', label: 'Custom Formula (enter in description)' }
  ],
  approval: [
    { value: 'select_approval', label: '-- Select Approval Type --' },
    { value: 'auto_approve', label: 'Auto-Approve' },
    { value: 'manager_approval', label: 'Reporting Manager Approval' },
    { value: 'hr_approval', label: 'HR Approval Required' },
    { value: 'finance_approval', label: 'Finance Approval Required' },
    { value: 'admin_approval', label: 'Admin Approval Required' },
    { value: 'two_level_approval', label: 'Two-Level Approval (Manager + HR)' },
    { value: 'skip_level_approval', label: 'Skip-Level Manager Approval' },
    { value: 'no_self_approval', label: 'Self-Approval Prohibited' },
    { value: 'delegation_allowed', label: 'Delegation to Substitute Allowed' },
    { value: 'escalate_after_days', label: 'Auto-Escalate After Days' }
  ]
};

// Conditions builder options
const CONDITION_FIELD_OPTIONS = [
  { value: 'department', label: 'Department' },
  { value: 'role', label: 'Role' },
  { value: 'grade', label: 'Grade/Level' },
  { value: 'employment_type', label: 'Employment Type' },
  { value: 'location', label: 'Location' },
  { value: 'experience_years', label: 'Years of Experience' },
  { value: 'basic_salary', label: 'Basic Salary' },
  { value: 'gross_salary', label: 'Gross Salary' },
  { value: 'ctc', label: 'CTC' },
  { value: 'travel_hours', label: 'Travel Duration (hours)' },
  { value: 'claim_amount', label: 'Claim Amount' },
  { value: 'leave_balance', label: 'Leave Balance' },
  { value: 'late_count', label: 'Late Count' },
  { value: 'is_manager', label: 'Is Manager' },
  { value: 'is_client_facing', label: 'Is Client Facing' },
  { value: 'is_on_probation', label: 'Is On Probation' },
  { value: 'tenure_months', label: 'Tenure (months)' }
];

const CONDITION_OPERATORS = [
  { value: '==', label: 'equals' },
  { value: '!=', label: 'not equals' },
  { value: '>', label: 'greater than' },
  { value: '>=', label: 'greater than or equal' },
  { value: '<', label: 'less than' },
  { value: '<=', label: 'less than or equal' },
  { value: 'in', label: 'is one of' },
  { value: 'not_in', label: 'is not one of' },
  { value: 'contains', label: 'contains' },
  { value: 'starts_with', label: 'starts with' }
];

const POLICY_TYPE_ICONS = {
  leave: Calendar,
  travel: Plane,
  expense: Receipt,
  attendance: Clock,
  payroll: DollarSign,
  general: FileText
};

const POLICY_TYPE_COLORS = {
  leave: 'bg-blue-100 text-blue-700 border-blue-200',
  travel: 'bg-purple-100 text-purple-700 border-purple-200',
  expense: 'bg-amber-100 text-amber-700 border-amber-200',
  attendance: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  payroll: 'bg-rose-100 text-rose-700 border-rose-200',
  general: 'bg-zinc-100 text-zinc-700 border-zinc-200'
};

const SCOPE_ICONS = {
  company: Building2,
  department: Users,
  role: Briefcase,
  employee: User
};

// SOP (Standard Operating Procedures) and Impact Analysis Data
// Each policy has 200+ word comprehensive documentation
const POLICY_SOP_DATA = {
  leave: {
    title: 'Leave Policy Management',
    summary: 'Governs employee leave entitlements, accruals, and encashment. Changes here affect leave balances and payroll.',
    icon: Calendar,
    quickTips: [
      'Leave quotas are credited yearly or accrued monthly',
      'Sandwich policy: Leave between holidays counts as leave',
      'Encashment rules affect Full & Final settlement'
    ],
    impacts: [
      { area: 'Leave Balances', impact: 'Direct', description: 'Changing quotas immediately affects employee leave dashboards' },
      { area: 'Payroll', impact: 'Direct', description: 'LOP deductions and encashment affect monthly salary calculation' },
      { area: 'F&F Settlement', impact: 'Direct', description: 'Encashable leaves are paid out during exit process' }
    ],
    payrollLinkage: {
      affects: ['LOP Deduction (PY008)', 'Leave Encashment (LV011)', 'F&F Calculation'],
      disbursement: 'Monthly Payroll & Exit Settlement',
      ctcComponents: ['Basic Salary (for per-day calculation)']
    },
    detailedSOP: `
## Leave Policy Configuration - Standard Operating Procedure

### Overview
The Leave Policy defines how employees accrue, utilize, and encash their leave entitlements. This policy directly integrates with the Payroll module for Loss of Pay (LOP) deductions and the F&F Settlement module for leave encashment during exit.

### Rule Categories

**Quota Rules (LV001-LV006):** Define annual entitlements for each leave type including Casual Leave, Sick Leave, Earned Leave, Maternity/Paternity Leave. These quotas are pro-rated for employees joining mid-year based on their Date of Joining.

**Accrual Rules (LV007-LV008):** Control how leaves are credited - either lump sum at year start or monthly accrual. Monthly accrual at 1.25 days/month for Earned Leave is recommended for better cash flow management.

**Carry Forward Rules (LV009-LV010):** Determine if unused leaves can be carried to next year. Maximum carry forward limits prevent excessive accumulation while providing flexibility to employees.

**Encashment Rules (LV011-LV012):** Specify which leave types can be encashed and the calculation formula (basic_per_day). Encashment directly affects F&F settlement amount during resignation.

### Configuration Process

1. **Identify Requirement:** Determine which rule needs modification based on HR policy review or management directive.

2. **Impact Assessment:** Use the Payroll Simulator to test how changes affect sample employee salaries. Check both current month impact and potential F&F impact.

3. **Approval:** Obtain necessary approvals from HR Head and Finance before making changes to encashment or LOP-related rules.

4. **Implementation:** Update the rule value, toggle enabled/disabled status, and save. Changes take effect immediately for new leave applications.

5. **Communication:** Notify all employees about policy changes through official channels. Update the employee handbook.

6. **Monitoring:** Track leave application patterns for 30 days post-change to identify any anomalies or concerns.

### Payroll Integration Points

- **LOP Calculation:** When an employee takes unpaid leave, the deduction formula is: (Basic Salary / Working Days) × LOP Days
- **Encashment Payout:** Calculated as: (Basic Salary / 30) × Encashable Leave Balance
- **F&F Settlement:** All encashable leaves are automatically included in the final settlement calculation

### Best Practices

- Review leave utilization quarterly to identify patterns
- Align policy changes with financial year start (April)
- Maintain minimum sick leave quota for employee welfare
- Consider pro-rata impact on mid-year joiners before changing quotas
    `,
    sop: {
      title: 'Leave Policy Configuration SOP',
      sections: [
        {
          heading: 'Critical Rules (Payroll Linked)',
          checklist: [
            'LV001-LV006: Leave quotas directly affect LOP calculation',
            'LV007: Accrual rate impacts monthly leave credit',
            'LV011: Encashment formula affects F&F settlement',
            'LV012: Carry forward limits affect year-end balance'
          ]
        },
        {
          heading: 'Before Making Changes',
          checklist: [
            'Review current leave utilization reports from Dashboard',
            'Check if change affects mid-year employees (pro-rata impact)',
            'Notify Finance if encashment rules are changing',
            'Document reason for policy change in change log',
            'Get HR Head approval for quota changes'
          ]
        },
        {
          heading: 'Configuration Steps',
          checklist: [
            'Click on specific leave rule (LV001-LV012) to expand',
            'Click Edit button to modify values',
            'Update numeric value (days) and unit (days/year or percent)',
            'Toggle rule enabled/disabled using switch',
            'Add/update description for audit trail',
            'Click Save Changes - takes effect immediately'
          ]
        },
        {
          heading: 'Testing & Verification',
          checklist: [
            'Open Payroll Simulator from top-right button',
            'Enter sample employee CTC and leave days',
            'Verify LOP deduction calculation is correct',
            'Check encashment amount in F&F preview',
            'Confirm changes reflect in Leave Dashboard'
          ]
        },
        {
          heading: 'Post-Change Actions',
          checklist: [
            'Announce policy update via company email',
            'Update employee handbook document',
            'Monitor leave applications for 30 days',
            'Review any grievances or escalations',
            'Document changes in HR policy log'
          ]
        }
      ],
      warnings: [
        '⚠️ Reducing leave quota mid-year may cause negative balances for employees who already utilized more',
        '⚠️ Disabling encashment immediately affects employees planning resignation',
        '⚠️ Sandwich policy changes can surprise employees on approved long leaves',
        '⚠️ Accrual rate changes affect leave credit from next month onwards'
      ],
      bestPractices: [
        '✓ Change policies effective from next financial year (April)',
        '✓ Allow 30-day grace period for existing approved applications',
        '✓ Keep minimum 6 sick leaves for employee health emergencies',
        '✓ Align earned leave accrual with industry standard (15-18 days/year)',
        '✓ Enable carry forward with reasonable limits (max 30 days)'
      ]
    }
  },
  travel: {
    title: 'Travel Policy Management',
    summary: 'Controls travel allowances, hotel limits, and expense claims for business travel. Directly impacts expense reimbursements.',
    icon: Plane,
    quickTips: [
      'Daily allowances are tier-based (Metro/Non-Metro)',
      'Flight class is determined by travel distance and role',
      'Advance request must be submitted 7 days before travel'
    ],
    impacts: [
      { area: 'Expense Claims', impact: 'Direct', description: 'Limits determine max claimable amounts' },
      { area: 'Payroll', impact: 'Direct', description: 'Approved travel expenses are reimbursed via payroll' },
      { area: 'Budget', impact: 'High', description: 'Higher limits increase travel cost budgets' }
    ],
    payrollLinkage: {
      affects: ['Travel Reimbursement', 'Expense Settlement', 'Advance Adjustment'],
      disbursement: 'Monthly Payroll (with salary) or Separate Disbursement',
      ctcComponents: ['Not linked to CTC - Reimbursement based']
    },
    detailedSOP: `
## Travel Policy Configuration - Standard Operating Procedure

### Overview
The Travel Policy governs all business travel expenses including daily allowances, accommodation, flights, and local conveyance. This policy integrates with the Expense Management module and ultimately flows to Payroll for reimbursement disbursement.

### Rule Categories

**Daily Allowance Rules (TR001-TR003):** Define per-day food and incidental allowances. Metro cities (Mumbai, Delhi, Bangalore, Chennai, Hyderabad, Kolkata) typically have 20-30% higher limits due to higher cost of living.

**Accommodation Rules (TR004-TR005):** Set hotel tariff limits by city tier and employee grade. Senior management may have higher limits. Pre-booking through company portal is recommended for compliance.

**Transport Rules (TR006-TR008):** Cover flight class eligibility (Economy/Business), train class (AC 2-tier/3-tier), and local conveyance (cab/auto limits). Flight class may upgrade for journeys exceeding 4 hours.

**Advance & Settlement (TR009-TR010):** Define travel advance policy (typically 70-80% of estimated expenses) and settlement timeline (within 7 days of return). Unsettled advances are adjusted against salary.

### Payroll Integration

- **Reimbursement Processing:** Approved travel claims are included in the monthly payroll cycle for disbursement
- **Advance Adjustment:** Any travel advances are automatically adjusted against the final claim amount
- **Budget Tracking:** All travel expenses are tracked against departmental travel budgets

### Metro City List
For higher allowance eligibility: Mumbai, Delhi NCR, Bangalore, Chennai, Hyderabad, Kolkata, Pune, Ahmedabad

### Configuration Guidelines

1. Review industry benchmarks annually for allowance revision
2. Consider inflation impact on accommodation limits
3. Allow role-based exceptions for client-facing senior staff
4. Ensure settlement timelines align with payroll cutoff dates
    `,
    sop: {
      title: 'Travel Policy Configuration SOP',
      sections: [
        {
          heading: 'Payroll-Linked Rules',
          checklist: [
            'TR001-TR003: Daily allowances reimbursed via payroll',
            'TR004-TR005: Hotel limits affect claim approval',
            'TR009: Advance policy - unsettled advances adjust salary',
            'TR010: Settlement deadline affects payroll cutoff'
          ]
        },
        {
          heading: 'Rule Configuration Guide',
          checklist: [
            'TR001-TR003: Set daily allowance by city tier (Metro/Non-Metro)',
            'TR004-TR005: Set hotel limits by employee grade',
            'TR006-TR007: Define flight/train class eligibility',
            'TR008: Set local conveyance limits',
            'TR009-TR010: Configure advance and settlement rules'
          ]
        },
        {
          heading: 'Before Making Changes',
          checklist: [
            'Review current travel expense reports',
            'Compare with industry standards and inflation',
            'Check pending travel requests that may be affected',
            'Inform Sales/Consulting teams about upcoming changes',
            'Get Finance approval for budget impact'
          ]
        },
        {
          heading: 'Configuration Steps',
          checklist: [
            'Select travel rule to modify (TR001-TR010)',
            'Update limit values (daily/per-trip/per-km)',
            'Review conditions (metro vs non-metro, grade-based)',
            'Save - applies to NEW travel requests only',
            'Test with sample travel claim submission'
          ]
        }
      ],
      warnings: [
        '⚠️ Lowering limits may cause employees to pay out-of-pocket',
        '⚠️ Strict limits can affect client meeting quality',
        '⚠️ Settlement deadline changes need 15-day advance notice',
        '⚠️ Advance policy changes affect employees on ongoing travel'
      ],
      bestPractices: [
        '✓ Review travel limits annually against inflation',
        '✓ Allow exceptions approval process for special cases',
        '✓ Metro cities: Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad',
        '✓ Align settlement deadline with payroll cutoff (15th of month)',
        '✓ Provide adequate advance (70-80%) to avoid employee burden'
      ]
    }
  },
  expense: {
    title: 'Expense Policy Management',
    summary: 'Defines expense claim rules, approval thresholds, and receipt requirements. Ensures compliance and fraud prevention.',
    icon: Receipt,
    quickTips: [
      'Self-approval prevention (EX001) is mandatory for compliance',
      'Receipt required for claims above threshold (typically Rs.500)',
      'Cutoff date (15th) determines which payroll cycle includes reimbursement'
    ],
    impacts: [
      { area: 'Expense Approvals', impact: 'Direct', description: 'Threshold changes affect approval routing' },
      { area: 'Payroll', impact: 'Direct', description: 'Approved expenses go to designated payroll period' },
      { area: 'Audit Compliance', impact: 'Critical', description: 'Receipt rules ensure audit readiness' }
    ],
    payrollLinkage: {
      affects: ['Expense Reimbursement', 'Payroll Cutoff Processing'],
      disbursement: 'Monthly Payroll (Reimbursement Component)',
      ctcComponents: ['Reimbursements section of pay slip']
    },
    detailedSOP: `
## Expense Policy Configuration - Standard Operating Procedure

### Overview
The Expense Policy controls how employees submit, get approval for, and receive reimbursement for business expenses. This policy is critical for compliance, audit readiness, and accurate payroll processing.

### Rule Categories

**Compliance Rules (EX001-EX003):** These are CRITICAL rules that should NEVER be disabled:
- EX001: Self-Approval Prevention - Ensures no one can approve their own expenses
- EX002: Receipt Threshold - Defines minimum amount requiring receipt (Rs.500 standard)
- EX003: Cutoff Date - Determines which payroll cycle includes the expense

**Limit Rules (EX004-EX006):** Define maximum expense amounts:
- EX004: Maximum Single Expense - Per-claim limit requiring additional approval
- EX005: Monthly Ceiling - Total monthly expense limit per employee
- EX006: Meal/Entertainment - Specific category limits

### Payroll Integration

Expenses flow to payroll based on the following process:
1. Employee submits expense claim with receipts
2. Manager approves (self-approval blocked by EX001)
3. Finance verifies compliance (receipts checked per EX002)
4. If submitted before cutoff (EX003), included in current month payroll
5. If after cutoff, rolls to next month payroll
6. Reimbursement appears in payslip under "Reimbursements"

### Audit Requirements

All expense claims are subject to internal and statutory audits. The expense policy must ensure:
- Complete receipt documentation for amounts above threshold
- Proper approval hierarchy (no self-approval)
- Clear cutoff dates for financial period closing
- Category-wise limits to prevent misuse

### Configuration Best Practices

1. Never disable EX001 (Self-Approval Prevention) - Audit failure risk
2. Keep receipt threshold at Rs.500 or lower for good documentation
3. Align cutoff date (15th) with payroll processing schedule
4. Review expense patterns quarterly for fraud detection
    `,
    sop: {
      title: 'Expense Policy Configuration SOP',
      sections: [
        {
          heading: 'Critical Rules (DO NOT DISABLE)',
          checklist: [
            'EX001: Self-approval prevention - MANDATORY for audit compliance',
            'EX002: Receipt threshold (Rs.500) - Required for documentation',
            'EX003: Cutoff date (15th) - Affects payroll accuracy'
          ]
        },
        {
          heading: 'Configurable Limit Rules',
          checklist: [
            'EX004: Maximum single expense limit (typically Rs.50,000)',
            'EX005: Monthly expense ceiling per employee',
            'EX006: Meal/Entertainment limits per claim'
          ]
        },
        {
          heading: 'Payroll Impact Flow',
          checklist: [
            'Claim submitted → Manager approves → Finance verifies',
            'Before cutoff (15th) → Current month payroll',
            'After cutoff → Next month payroll',
            'Reimbursement in payslip → Disbursed with salary'
          ]
        },
        {
          heading: 'Configuration Steps',
          checklist: [
            'Select expense rule (EX001-EX006)',
            'Update limit values (INR amount)',
            'Review approval conditions if applicable',
            'Save changes - applies to new claims only',
            'Test by submitting a sample expense claim'
          ]
        }
      ],
      warnings: [
        '🚫 NEVER disable EX001 (Self-Approval) - Causes audit failure',
        '⚠️ Raising limits significantly may enable fraud/misuse',
        '⚠️ Removing receipt requirements risks audit findings',
        '⚠️ Changing cutoff date affects month-end close process'
      ],
      bestPractices: [
        '✓ Keep receipt threshold at Rs.500 or lower',
        '✓ Cutoff on 15th aligns with standard payroll cycles',
        '✓ Review expense patterns quarterly for anomalies',
        '✓ Maintain clear category definitions for claims',
        '✓ Enable email notifications for approval reminders'
      ]
    }
  },
  attendance: {
    title: 'Attendance Policy Management',
    summary: 'Governs work hours, WFH policies, late penalties, and overtime rules. Directly affects payroll calculations.',
    icon: Clock,
    quickTips: [
      'Core hours (10AM-5PM) define mandatory office presence',
      'Late threshold (3 incidents) triggers salary penalty',
      'Overtime must be pre-approved by manager for payment'
    ],
    impacts: [
      { area: 'Salary Calculation', impact: 'Direct', description: 'Late penalties and LOP deductions affect net pay' },
      { area: 'Employee Flexibility', impact: 'High', description: 'WFH and flexi-time rules affect work-life balance' },
      { area: 'Compliance', impact: 'Critical', description: 'Overtime rules must comply with labor laws (max 48hrs/month)' }
    ],
    payrollLinkage: {
      affects: ['Late Deductions', 'Overtime Payment', 'LOP Calculation', 'Attendance Bonus'],
      disbursement: 'Monthly Payroll - Attendance processed before salary generation',
      ctcComponents: ['Basic Salary (for LOP)', 'Overtime Allowance']
    },
    detailedSOP: `
## Attendance Policy Configuration - Standard Operating Procedure

### Overview
The Attendance Policy defines work hours, flexibility options, penalty rules, and overtime payment criteria. This policy directly integrates with Payroll for calculating attendance-based deductions and overtime payments.

### Rule Categories

**Work Hours Rules (AT001-AT003):**
- AT001: Standard work hours (9 hours including lunch break)
- AT002: Core hours start time (10:00 AM - mandatory presence begins)
- AT003: Core hours end time (5:00 PM - mandatory presence ends)

**Flexibility Rules (AT004-AT006):**
- AT004: Grace period for late arrival (typically 15 minutes)
- AT005: Work From Home days allowed per week/month
- AT006: Comp-off accrual rules for weekend/holiday work

**Penalty Rules (AT007-AT008):**
- AT007: Late arrival threshold (3 incidents = half-day deduction)
- AT008: Unauthorized absence treatment (full day = 1.5x LOP)

### Payroll Integration

Attendance data flows to payroll as follows:
1. Daily attendance captured (biometric/manual/geo-tagged)
2. Month-end: Late arrivals counted against threshold
3. Penalties calculated: Late penalties + LOP deductions
4. Overtime calculated: Pre-approved OT hours × rate
5. Net attendance impact reflected in payslip

### Calculation Formulas

**LOP Deduction:** (Basic Salary / Working Days in Month) × LOP Days
**Late Penalty:** After 3 late arrivals, each additional = 0.5 day LOP
**Overtime Payment:** (Basic Salary / 30 / 8) × OT Hours × 1.5

### Compliance Requirements

Per Shops & Establishment Act:
- Maximum 48 hours overtime per month
- Overtime must be compensated at 1.5x or 2x rate
- Rest day (Sunday) work requires prior approval
- Night shift allowances for 10PM-6AM work
    `,
    sop: {
      title: 'Attendance Policy Configuration SOP',
      sections: [
        {
          heading: 'Payroll-Linked Rules',
          checklist: [
            'AT001: Work hours affect full-day/half-day calculation',
            'AT002-AT003: Core hours determine late marking window',
            'AT007: Late penalty directly deducts from salary',
            'AT008: Unauthorized absence = 1.5x LOP deduction'
          ]
        },
        {
          heading: 'Work Hours Configuration',
          checklist: [
            'AT001: Standard work hours (9 hours with lunch)',
            'AT002: Core hours start - 10:00 AM',
            'AT003: Core hours end - 5:00 PM (17:00)',
            'AT004: Grace period - 15 minutes buffer'
          ]
        },
        {
          heading: 'Flexibility & WFH Rules',
          checklist: [
            'AT005: WFH days allowed per week (typically 2)',
            'AT006: Comp-off for weekend/holiday work',
            'Define WFH eligibility by role/department',
            'Set approval process for ad-hoc WFH requests'
          ]
        },
        {
          heading: 'Penalty Configuration',
          checklist: [
            'AT007: Late threshold (3 incidents) before penalty',
            'AT008: Penalty rate (0.5 day per excess late)',
            'Define reset period (monthly/quarterly)',
            'Configure unauthorized absence multiplier (1.5x)'
          ]
        },
        {
          heading: 'Overtime Rules',
          checklist: [
            'OT requires manager pre-approval',
            'Maximum 48 hours/month (legal limit)',
            'OT rate: 1.5x for weekdays, 2x for weekends',
            'Track against departmental OT budget'
          ]
        }
      ],
      warnings: [
        '⚠️ Strict late penalties may affect employee morale',
        '⚠️ Overtime rules must comply with Shops & Establishment Act',
        '⚠️ WFH restrictions should consider role requirements',
        '⚠️ Penalty changes apply from next attendance cycle'
      ],
      bestPractices: [
        '✓ Allow 15-minute grace period for late arrivals',
        '✓ Cap overtime at 48 hours/month (legal compliance)',
        '✓ Hybrid WFH (2-3 days) balances productivity & flexibility',
        '✓ Monthly attendance review before payroll processing',
        '✓ Communicate penalty rules clearly in employee handbook'
      ]
    }
  },
  payroll: {
    title: 'Payroll Rules Management',
    summary: 'CRITICAL: Defines statutory compliance (PF, ESI, PT) reference thresholds and salary processing rules. CTC Designer handles actual calculations.',
    icon: DollarSign,
    quickTips: [
      'PF/ESI thresholds are statutory - actual calculation in CTC Designer',
      'Processing dates (28th) affect when employees receive salary',
      'Tax calculation uses government-mandated slabs'
    ],
    impacts: [
      { area: 'Salary Processing', impact: 'Critical', description: 'Processing date determines pay day' },
      { area: 'Statutory Compliance', impact: 'Critical', description: 'PF/ESI rules are government mandated - view only here' },
      { area: 'Tax Filing', impact: 'High', description: 'TDS calculation affects Form 16 accuracy' }
    ],
    payrollLinkage: {
      affects: ['Salary Disbursement Date', 'Payslip Generation', 'Bank File Creation'],
      disbursement: 'Monthly - Based on PY001 Processing Date',
      ctcComponents: ['All CTC components calculated in CTC Designer, NOT here']
    },
    detailedSOP: `
## Payroll Rules Configuration - Standard Operating Procedure

### IMPORTANT ARCHITECTURE NOTE

⚠️ **Single Source of Truth (SSOT) Principle:**

This Business Rules page shows REFERENCE information for payroll-related thresholds. However, **all actual salary calculations** happen in the **CTC Designer** module. This separation ensures:

1. Compliance accuracy - CTC Designer uses certified statutory formulas
2. No conflicting calculations - Single source for all PF/ESI/PT math
3. Audit trail - All changes in CTC Designer are logged

### Rule Categories

**Processing Rules (PY001-PY003):** These ARE configurable here:
- PY001: Payroll processing date (typically 28th of month)
- PY002: Payslip generation date (within 5 days of salary credit)
- PY003: Input cutoff date (attendance/expense cutoff for current month)

**Reference Rules (PY004-PY010):** View-only for awareness:
- PY004-PY006: PF thresholds (EPF ceiling Rs.15,000 basic)
- PY007: Professional Tax slab reference
- PY008: LOP calculation formula reference
- PY009-PY010: Bonus and incentive thresholds

### Payroll Processing Flow

1. **Input Collection (by PY003 cutoff):**
   - Attendance data finalized
   - Expense claims approved
   - Leave applications processed

2. **Calculation (automatic):**
   - CTC Designer calculates all components
   - Statutory deductions auto-applied
   - Reimbursements included

3. **Generation (PY001 date):**
   - Payroll file generated
   - Bank file created for disbursement
   - Payslips prepared

4. **Disbursement:**
   - Bank transfer initiated
   - Payslips emailed to employees

### Configuration Restrictions

The following CANNOT be changed here (use CTC Designer):
- PF contribution percentages (12% employee, 12% employer)
- ESI contribution rates (0.75% employee, 3.25% employer)
- Professional Tax slab amounts
- TDS calculation method

These CAN be changed here:
- Processing and generation dates
- Cutoff dates for inputs
- Notification settings
    `,
    sop: {
      title: 'Payroll Rules Configuration SOP',
      sections: [
        {
          heading: '⚠️ CRITICAL: CTC Designer vs Business Rules',
          checklist: [
            'Business Rules: Processing dates & reference thresholds ONLY',
            'CTC Designer: ALL actual salary component calculations',
            'NEVER use Business Rules to override statutory compliance',
            'PF/ESI/PT formulas are LOCKED in CTC Designer'
          ]
        },
        {
          heading: 'Safe to Configure (PY001-PY003)',
          checklist: [
            'PY001: Payroll processing date (28th recommended)',
            'PY002: Payslip generation date (within 5 days)',
            'PY003: Input cutoff date (20th-25th of month)'
          ]
        },
        {
          heading: 'View Only - Reference (PY004-PY010)',
          checklist: [
            'PY004-PY006: PF thresholds (Rs.15,000 basic ceiling)',
            'PY007: PT slabs (state-wise, Karnataka shown)',
            'PY008: LOP formula reference',
            'PY009-PY010: Bonus/Incentive thresholds'
          ]
        },
        {
          heading: 'Processing Date Guidelines',
          checklist: [
            'Process by 28th for end-of-month salary credit',
            'Allow 2-3 days for bank processing',
            'Generate payslips before salary hits accounts',
            'Send payslip emails on salary credit day'
          ]
        }
      ],
      warnings: [
        '🚫 DO NOT modify PF/ESI percentage rules - they are statutory',
        '⚠️ Payroll date changes affect employee financial planning',
        '⚠️ Tax rules are government-mandated - not configurable',
        '⚠️ Late processing affects employee trust and compliance'
      ],
      bestPractices: [
        '✓ Process payroll by 28th for end-of-month credit',
        '✓ Generate payslips within 5 days of salary credit',
        '✓ Use Payroll Simulator to verify calculations',
        '✓ Maintain payroll calendar shared with all teams',
        '✓ Review statutory rates quarterly for updates'
      ]
    }
  },
  general: {
    title: 'General HR Policies',
    summary: 'Covers probation, notice periods, increment cycles, and general employment terms that affect payroll and exit processes.',
    icon: FileText,
    quickTips: [
      'Probation period (6 months) affects benefits eligibility',
      'Notice period (30-90 days) enforced during resignation',
      'Increment month (April) sets annual appraisal cycle'
    ],
    impacts: [
      { area: 'Onboarding', impact: 'High', description: 'Probation rules affect new employee benefits and confirmation' },
      { area: 'Exit Process', impact: 'Critical', description: 'Notice period determines last working day and F&F' },
      { area: 'Compensation', impact: 'Direct', description: 'Increment month affects salary revision timing' }
    ],
    payrollLinkage: {
      affects: ['Probation Completion Bonus', 'Notice Period Recovery', 'Increment Processing'],
      disbursement: 'Various - Confirmation bonus, Annual increment, F&F settlement',
      ctcComponents: ['Salary revision effective from HR005 month']
    },
    detailedSOP: `
## General HR Policy Configuration - Standard Operating Procedure

### Overview
General HR Policies define the employment lifecycle rules from joining to exit. These policies have significant payroll and compliance implications.

### Rule Categories

**Probation Rules (HR001-HR002):**
- HR001: Probation period duration (typically 6 months)
- HR002: Probation extension rules (max 3 months extension)

During probation:
- No earned leave accrual
- Limited insurance coverage
- Shorter notice period (15 days vs 30-90)
- Performance review at 3 months and 6 months

**Notice Period Rules (HR003-HR004):**
- HR003: Notice period for employee resignation
- HR004: Notice period for company termination

Notice period enforcement:
- Shortfall days = salary recovery
- Notice buyout option (company discretion)
- Serving notice vs notice pay calculation

**Compensation Cycle (HR005-HR006):**
- HR005: Annual increment month (typically April)
- HR006: Performance review frequency (annual/bi-annual)

### Payroll Implications

**Probation Completion:**
- Benefits activated (full insurance, PF contribution)
- Earned leave starts accruing
- Confirmation letter generated
- Optional: Confirmation bonus processed

**Notice Period:**
- F&F calculation triggered
- Notice recovery if not served
- Leave encashment processed
- Gratuity (if eligible) calculated

**Annual Increment:**
- Revised CTC effective from increment month
- Arrears calculated if late processing
- Updated tax projection for remaining year
    `,
    sop: {
      title: 'General HR Policy Configuration SOP',
      sections: [
        {
          heading: 'Payroll-Linked Rules',
          checklist: [
            'HR001: Probation affects benefits & leave accrual',
            'HR003-HR004: Notice period affects F&F calculation',
            'HR005: Increment month sets salary revision date',
            'HR006: Review frequency affects bonus timing'
          ]
        },
        {
          heading: 'Probation Configuration',
          checklist: [
            'HR001: Standard period (6 months recommended)',
            'HR002: Extension rules (max 3 months)',
            'Define probation benefits (limited vs full)',
            'Set review milestones (3-month, 5-month)'
          ]
        },
        {
          heading: 'Notice Period Configuration',
          checklist: [
            'HR003: Employee resignation notice (30-90 days)',
            'HR004: Company termination notice',
            'Define notice buyout policy',
            'Set notice recovery calculation method'
          ]
        },
        {
          heading: 'Compensation Cycle',
          checklist: [
            'HR005: Increment month - April (FY start)',
            'HR006: Review frequency - Annual',
            'Define increment eligibility criteria',
            'Set bell curve/rating distribution'
          ]
        },
        {
          heading: 'Other Employment Terms',
          checklist: [
            'HR007: Retirement age (58-60 years)',
            'HR008: Re-employment rules',
            'Dress code policy reference',
            'Code of conduct reference'
          ]
        }
      ],
      warnings: [
        '⚠️ Changing notice period affects current employees',
        '⚠️ Probation extension needs proper documentation',
        '⚠️ Increment month change affects annual planning',
        '⚠️ Notice recovery must comply with labor laws'
      ],
      bestPractices: [
        '✓ 90 days notice for senior roles, 30 days for others',
        '✓ 6-month probation provides adequate evaluation time',
        '✓ April increment aligns with financial year',
        '✓ Bi-annual reviews for junior staff, annual for seniors',
        '✓ Document all policy exceptions with HR approval'
      ]
    }
  }
};

// SOP Detail Modal Component
const SOPDetailModal = ({ isOpen, onClose, policyType, isDark }) => {
  const sopData = POLICY_SOP_DATA[policyType];
  if (!sopData) return null;
  
  const Icon = sopData.icon;
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className={`max-w-4xl max-h-[90vh] overflow-y-auto ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${POLICY_TYPE_COLORS[policyType]?.split(' ')[0]}`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <span>{sopData.sop.title}</span>
              <p className={`text-sm font-normal mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                Standard Operating Procedure & Impact Analysis (200+ words)
              </p>
            </div>
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6 py-4">
          {/* Impact Analysis Section */}
          <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900 border border-zinc-700' : 'bg-zinc-50 border border-zinc-200'}`}>
            <h4 className="font-semibold flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-blue-500" />
              Impact Analysis
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {(sopData?.impacts || []).map((item, idx) => (
                <div key={idx} className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-white'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm">{item.area}</span>
                    <Badge className={`text-xs ${
                      item.impact === 'Critical' ? 'bg-red-100 text-red-700' :
                      item.impact === 'High' ? 'bg-amber-100 text-amber-700' :
                      item.impact === 'Direct' ? 'bg-blue-100 text-blue-700' :
                      'bg-zinc-100 text-zinc-700'
                    }`}>
                      {item.impact}
                    </Badge>
                  </div>
                  <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>{item.description}</p>
                </div>
              ))}
            </div>
          </div>
          
          {/* Payroll Linkage Section */}
          {sopData.payrollLinkage && (
            <div className={`p-4 rounded-lg ${isDark ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
              <h4 className="font-semibold flex items-center gap-2 mb-3 text-blue-600">
                <DollarSign className="w-4 h-4" />
                Payroll & Disbursement Linkage
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <p className={`text-xs font-medium ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>Affects:</p>
                  <ul className="mt-1 space-y-1">
                    {(sopData?.payrollLinkage?.affects || []).map((item, idx) => (
                      <li key={idx} className={`text-xs flex items-center gap-1 ${isDark ? 'text-blue-200' : 'text-blue-600'}`}>
                        <ArrowRight className="w-3 h-3" /> {item}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className={`text-xs font-medium ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>Disbursement:</p>
                  <p className={`text-xs mt-1 ${isDark ? 'text-blue-200' : 'text-blue-600'}`}>
                    {sopData.payrollLinkage.disbursement}
                  </p>
                </div>
                <div>
                  <p className={`text-xs font-medium ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>CTC Components:</p>
                  <ul className="mt-1 space-y-1">
                    {(sopData?.payrollLinkage?.ctcComponents || []).map((item, idx) => (
                      <li key={idx} className={`text-xs flex items-center gap-1 ${isDark ? 'text-blue-200' : 'text-blue-600'}`}>
                        <ArrowRight className="w-3 h-3" /> {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
          
          {/* SOP Sections with Checklists */}
          <Accordion type="multiple" className="w-full" defaultValue={['section-0', 'section-1']}>
            {(sopData?.sop?.sections || []).map((section, idx) => (
              <AccordionItem key={idx} value={`section-${idx}`} className={isDark ? 'border-zinc-700' : ''}>
                <AccordionTrigger className="hover:no-underline">
                  <div className="flex items-center gap-2">
                    <CheckSquare className="w-4 h-4 text-emerald-500" />
                    <span>{section.heading}</span>
                    <Badge variant="outline" className="ml-2 text-xs">{section.checklist.length} items</Badge>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-2 pl-6">
                    {(section?.checklist || []).map((item, itemIdx) => (
                      <div key={itemIdx} className={`flex items-start gap-2 p-2 rounded ${isDark ? 'bg-zinc-800/50' : 'bg-zinc-50'}`}>
                        <ArrowRight className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                        <span className="text-sm">{item}</span>
                      </div>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
          
          {/* Detailed SOP Document */}
          {sopData.detailedSOP && (
            <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900 border border-zinc-700' : 'bg-white border border-zinc-200'}`}>
              <h4 className="font-semibold flex items-center gap-2 mb-3">
                <BookOpen className="w-4 h-4 text-purple-500" />
                Detailed SOP Documentation
              </h4>
              <div className={`prose prose-sm max-w-none ${isDark ? 'prose-invert' : ''}`}>
                <pre className={`whitespace-pre-wrap text-xs leading-relaxed font-sans ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                  {sopData.detailedSOP.trim()}
                </pre>
              </div>
            </div>
          )}
          
          {/* Warnings */}
          <div className={`p-4 rounded-lg ${isDark ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'}`}>
            <h4 className="font-semibold flex items-center gap-2 mb-3 text-red-600">
              <AlertCircle className="w-4 h-4" />
              Warnings & Cautions
            </h4>
            <ul className="space-y-2">
              {(sopData?.sop?.warnings || []).map((warning, idx) => (
                <li key={idx} className={`text-sm flex items-start gap-2 ${isDark ? 'text-red-300' : 'text-red-700'}`}>
                  <span className="text-red-500">•</span>
                  {warning}
                </li>
              ))}
            </ul>
          </div>
          
          {/* Best Practices */}
          <div className={`p-4 rounded-lg ${isDark ? 'bg-emerald-900/20 border border-emerald-800' : 'bg-emerald-50 border border-emerald-200'}`}>
            <h4 className="font-semibold flex items-center gap-2 mb-3 text-emerald-600">
              <Lightbulb className="w-4 h-4" />
              Best Practices
            </h4>
            <ul className="space-y-2">
              {(sopData?.sop?.bestPractices || []).map((practice, idx) => (
                <li key={idx} className={`text-sm flex items-start gap-2 ${isDark ? 'text-emerald-300' : 'text-emerald-700'}`}>
                  <CheckCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                  {practice}
                </li>
              ))}
            </ul>
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={() => onClose(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// Quick Tips Tooltip Component
const QuickTipsTooltip = ({ policyType, children, isDark }) => {
  const sopData = POLICY_SOP_DATA[policyType];
  if (!sopData) return children;
  
  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger asChild>
          {children}
        </TooltipTrigger>
        <TooltipContent side="right" className={`max-w-xs p-3 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <div className="space-y-2">
            <p className="font-semibold text-sm">{sopData.title}</p>
            <ul className="space-y-1">
              {(sopData?.quickTips || []).map((tip, idx) => (
                <li key={idx} className="text-xs flex items-start gap-1.5">
                  <Zap className="w-3 h-3 text-amber-500 mt-0.5 flex-shrink-0" />
                  {tip}
                </li>
              ))}
            </ul>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

const BusinessRules = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const queryClient = useQueryClient();
  const isDark = theme === 'dark';
  
  const isAdmin = checkIsAdmin(user);
  const isHR = checkIsHR(user);
  const canEdit = isAdmin || isHR;
  
  // State
  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [editingRule, setEditingRule] = useState(null);
  const [showPolicyDialog, setShowPolicyDialog] = useState(false);
  const [showRuleDialog, setShowRuleDialog] = useState(false);
  const [showSimulator, setShowSimulator] = useState(false);
  const [simulatorData, setSimulatorData] = useState({
    annual_ctc: 600000,
    basic_percentage: 40,
    hra_percentage: 50,
    working_days: 26,
    present_days: 26,
    lop_days: 0,
    expense_reimbursement: 0
  });
  const [simulationResult, setSimulationResult] = useState(null);
  const [simulating, setSimulating] = useState(false);
  const [showSOPModal, setShowSOPModal] = useState(false);
  const [selectedSOPType, setSelectedSOPType] = useState(null);
  const [showTestMyRule, setShowTestMyRule] = useState(false);
  const [testRuleData, setTestRuleData] = useState({
    employee_name: '',
    employee_ctc: 800000,
    basic_salary: 320000,
    department: 'Engineering',
    role: 'employee',
    grade: 'L3',
    location: 'bangalore',
    scenario_value: 0,  // The value being tested (expense amount, leave days, etc.)
    scenario_type: ''   // What we're testing
  });
  const [testResult, setTestResult] = useState(null);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('');
  
  // Attendance Configuration State
  const [attendanceConfig, setAttendanceConfig] = useState(null);
  const [attendanceOverrides, setAttendanceOverrides] = useState({ role_overrides: [], employee_overrides: [] });
  const [showAttendanceConfig, setShowAttendanceConfig] = useState(true);
  const [savingAttendanceConfig, setSavingAttendanceConfig] = useState(false);
  const [showAddOverrideDialog, setShowAddOverrideDialog] = useState(false);
  const [newOverride, setNewOverride] = useState({
    scope: 'role',
    scope_value: '',
    name: '',
    working_days: [],
    core_hours_start: '10:00',
    core_hours_end: '19:00',
    grace_period_minutes: 30,
    wfh_days_per_week: 2,
    reason: ''
  });
  
  // Fetch all employees for dropdown
  const { data: employeesList = [] } = useQuery({
    queryKey: ['employees-for-test'],
    queryFn: async () => {
      const res = await axios.get(`${API}/employees/all`);
      return res.data || [];
    },
    staleTime: 5 * 60 * 1000
  });
  
  // Fetch all policies
  const { data: policies = [], isLoading: loading, refetch } = useQuery({
    queryKey: ['business-policies'],
    queryFn: async () => {
      const res = await axios.get(`${API}/business-rules`);
      return res.data || [];
    },
    staleTime: 3 * 60 * 1000
  });
  
  // Fetch policy types
  const { data: policyTypes } = useQuery({
    queryKey: ['policy-types'],
    queryFn: async () => {
      const res = await axios.get(`${API}/business-rules/types`);
      return res.data;
    },
    staleTime: 30 * 60 * 1000
  });
  
  // Fetch attendance configuration when attendance tab is active
  const { data: fetchedAttendanceConfig, refetch: refetchAttendanceConfig } = useQuery({
    queryKey: ['attendance-config'],
    queryFn: async () => {
      const res = await axios.get(`${API}/business-rules/attendance/config`);
      return res.data;
    },
    enabled: activeTab === 'attendance',
    staleTime: 2 * 60 * 1000,
    onSuccess: (data) => {
      setAttendanceConfig(data);
    }
  });
  
  // Fetch attendance overrides
  const { data: fetchedOverrides, refetch: refetchOverrides } = useQuery({
    queryKey: ['attendance-overrides'],
    queryFn: async () => {
      const res = await axios.get(`${API}/business-rules/attendance/overrides`);
      return res.data;
    },
    enabled: activeTab === 'attendance' && canEdit,
    staleTime: 2 * 60 * 1000,
    onSuccess: (data) => {
      setAttendanceOverrides(data);
    }
  });
  
  // Update attendance config when fetched data changes
  React.useEffect(() => {
    if (fetchedAttendanceConfig) {
      setAttendanceConfig(fetchedAttendanceConfig);
    }
  }, [fetchedAttendanceConfig]);
  
  React.useEffect(() => {
    if (fetchedOverrides) {
      setAttendanceOverrides(fetchedOverrides);
    }
  }, [fetchedOverrides]);
  
  // Update rule mutation
  const updateRuleMutation = useMutation({
    mutationFn: async ({ policyId, ruleId, ruleData }) => {
      return axios.put(`${API}/business-rules/${policyId}/rule/${ruleId}`, ruleData);
    },
    onSuccess: () => {
      toast.success('Rule updated successfully');
      queryClient.invalidateQueries(['business-policies']);
      setShowRuleDialog(false);
      setEditingRule(null);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to update rule')
  });
  
  // Update policy mutation
  const updatePolicyMutation = useMutation({
    mutationFn: async ({ policyId, policyData }) => {
      return axios.put(`${API}/business-rules/${policyId}`, policyData);
    },
    onSuccess: () => {
      toast.success('Policy updated successfully');
      queryClient.invalidateQueries(['business-policies']);
      setShowPolicyDialog(false);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to update policy')
  });
  
  // Add new rule mutation
  const addRuleMutation = useMutation({
    mutationFn: async ({ policyId, ruleData }) => {
      return axios.post(`${API}/business-rules/${policyId}/rule`, ruleData);
    },
    onSuccess: (data) => {
      toast.success(`Rule ${data.data.rule_id} added successfully`);
      queryClient.invalidateQueries(['business-policies']);
      setShowRuleDialog(false);
      setEditingRule(null);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to add rule')
  });
  
  // Delete rule mutation
  const deleteRuleMutation = useMutation({
    mutationFn: async ({ policyId, ruleId }) => {
      return axios.delete(`${API}/business-rules/${policyId}/rule/${ruleId}`);
    },
    onSuccess: () => {
      toast.success('Rule deleted successfully');
      queryClient.invalidateQueries(['business-policies']);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to delete rule')
  });
  
  // Save attendance configuration
  const handleSaveAttendanceConfig = async () => {
    if (!attendanceConfig) return;
    
    setSavingAttendanceConfig(true);
    try {
      await axios.put(`${API}/business-rules/attendance/config`, {
        working_days: attendanceConfig.working_days,
        core_hours_start: attendanceConfig.core_hours_start,
        core_hours_end: attendanceConfig.core_hours_end,
        grace_period_minutes: attendanceConfig.grace_period_minutes,
        grace_days_per_month: attendanceConfig.grace_days_per_month,
        late_penalty_amount: attendanceConfig.late_penalty_amount,
        wfh_days_per_week: attendanceConfig.wfh_days_per_week
      });
      toast.success('Attendance configuration saved successfully');
      refetchAttendanceConfig();
      queryClient.invalidateQueries(['business-policies']);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save attendance configuration');
    } finally {
      setSavingAttendanceConfig(false);
    }
  };
  
  // Create attendance override
  const handleCreateOverride = async () => {
    if (!newOverride.scope_value) {
      toast.error(`Please select a ${newOverride.scope}`);
      return;
    }
    
    try {
      await axios.post(`${API}/business-rules/attendance/override`, {
        ...newOverride,
        working_days: newOverride.working_days.length > 0 ? newOverride.working_days : attendanceConfig?.working_days
      });
      toast.success('Override created successfully');
      setShowAddOverrideDialog(false);
      setNewOverride({
        scope: 'role',
        scope_value: '',
        name: '',
        working_days: [],
        core_hours_start: '10:00',
        core_hours_end: '19:00',
        grace_period_minutes: 30,
        wfh_days_per_week: 2,
        reason: ''
      });
      refetchOverrides();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create override');
    }
  };
  
  // Delete attendance override
  const handleDeleteOverride = async (policyId) => {
    if (!window.confirm('Delete this override? The affected employees will use company defaults.')) return;
    
    try {
      await axios.delete(`${API}/business-rules/attendance/override/${policyId}`);
      toast.success('Override deleted');
      refetchOverrides();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete override');
    }
  };
  
  // Toggle working day in attendance config
  const toggleWorkingDay = (day) => {
    if (!attendanceConfig) return;
    
    const currentDays = attendanceConfig.working_days || [];
    const newDays = currentDays.includes(day)
      ? (currentDays || []).filter(d => d !== day)
      : [...currentDays, day];
    
    // Maintain day order
    const orderedDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const sortedDays = newDays.sort((a, b) => orderedDays.indexOf(a) - orderedDays.indexOf(b));
    
    setAttendanceConfig({ ...attendanceConfig, working_days: sortedDays });
  };
  
  // Toggle working day in new override
  const toggleOverrideWorkingDay = (day) => {
    const currentDays = newOverride.working_days || [];
    const newDays = currentDays.includes(day)
      ? (currentDays || []).filter(d => d !== day)
      : [...currentDays, day];
    
    const orderedDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const sortedDays = newDays.sort((a, b) => orderedDays.indexOf(a) - orderedDays.indexOf(b));
    
    setNewOverride({ ...newOverride, working_days: sortedDays });
  };
  
  // Filter policies
  const filteredPolicies = (policies || []).filter(p => {
    if (activeTab !== 'all' && p.policy_type !== activeTab) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return p.name?.toLowerCase().includes(query) || 
             p.description?.toLowerCase().includes(query) ||
             p.rules?.some(r => r.rule_name?.toLowerCase().includes(query));
    }
    return true;
  });
  
  // Group policies by type
  const policiesByType = (policies || []).reduce((acc, p) => {
    if (!acc[p.policy_type]) acc[p.policy_type] = [];
    acc[p.policy_type].push(p);
    return acc;
  }, {});
  
  const handleEditRule = (policy, rule) => {
    setSelectedPolicy(policy);
    setEditingRule({ ...rule, _isNew: false });
    setShowRuleDialog(true);
  };
  
  const handleAddNewRule = (policy) => {
    setSelectedPolicy(policy);
    // Create a blank new rule template
    const policyPrefix = policy.policy_type.substring(0, 2).toUpperCase();
    const nextNum = (policy.rules?.length || 0) + 1;
    setEditingRule({
      rule_id: `${policyPrefix}${String(nextNum).zfill ? nextNum.toString().padStart(3, '0') : String(nextNum).padStart(3, '0')}`,
      rule_name: '',
      rule_type: 'limit',
      category: '',
      numeric_value: null,
      unit: '',
      value: '',
      description: '',
      is_enabled: true,
      _isNew: true
    });
    setShowRuleDialog(true);
  };
  
  const handleSaveRule = () => {
    if (!selectedPolicy || !editingRule) return;
    
    // Validate required fields
    if (!editingRule.rule_name) {
      toast.error('Rule name is required');
      return;
    }
    
    if (editingRule._isNew) {
      // Add new rule
      addRuleMutation.mutate({
        policyId: selectedPolicy.id,
        ruleData: {
          ...editingRule,
          _isNew: undefined  // Remove internal flag
        }
      });
    } else {
      // Update existing rule
      updateRuleMutation.mutate({
        policyId: selectedPolicy.id,
        ruleId: editingRule.rule_id,
        ruleData: editingRule
      });
    }
  };
  
  const handleDeleteRule = (policy, rule) => {
    if (!window.confirm(`Are you sure you want to delete rule "${rule.rule_name}" (${rule.rule_id})?`)) {
      return;
    }
    deleteRuleMutation.mutate({
      policyId: policy.id,
      ruleId: rule.rule_id
    });
  };
  
  const handleToggleRule = async (policy, rule) => {
    if (!canEdit) {
      toast.error('You do not have permission to modify rules');
      return;
    }
    
    try {
      await axios.put(`${API}/business-rules/${policy.id}/rule/${rule.rule_id}`, {
        ...rule,
        is_enabled: !rule.is_enabled
      });
      toast.success(`Rule ${rule.is_enabled ? 'disabled' : 'enabled'}`);
      queryClient.invalidateQueries(['business-policies']);
    } catch (err) {
      toast.error('Failed to toggle rule');
    }
  };
  
  const getRuleTypeColor = (type) => {
    const colors = {
      limit: 'bg-red-100 text-red-700',
      threshold: 'bg-blue-100 text-blue-700',
      condition: 'bg-purple-100 text-purple-700',
      formula: 'bg-emerald-100 text-emerald-700',
      approval: 'bg-amber-100 text-amber-700'
    };
    return colors[type] || 'bg-zinc-100 text-zinc-700';
  };
  
  const formatRuleValue = (rule) => {
    // For FORMULA types, prioritize showing the formula
    if (rule.rule_type === 'formula') {
      if (rule.conditions?.formula) {
        return rule.conditions.formula;
      }
      if (rule.value && (rule.value.includes('*') || rule.value.includes('/'))) {
        return rule.value;
      }
    }
    
    if (rule.numeric_value !== undefined && rule.numeric_value !== null) {
      const formatted = new Intl.NumberFormat('en-IN').format(rule.numeric_value);
      const unit = rule.unit || '';
      // For time-based rules, show better format
      if (rule.value && (rule.value.includes(':') || rule.category === 'timing')) {
        return `${rule.value} (${formatted}${unit ? ' ' + unit : ''})`;
      }
      return `${formatted} ${unit}`.trim();
    }
    if (rule.value) return rule.value;
    return '-';
  };
  
  // Format conditions for display in a human-readable way
  const formatConditions = (conditions, rule) => {
    if (!conditions) return null;
    
    // If it's a simple key-value object, format nicely
    if (typeof conditions === 'object') {
      const entries = Object.entries(conditions || {});
      if (entries.length === 0) return null;
      
      // Check for slab-based conditions (like Professional Tax)
      if ((entries || []).some(([k]) => k.startsWith('slab'))) {
        return (entries || []).filter(([k]) => k.startsWith('slab')).map(([key, val]) => {
          if (typeof val === 'object' && val.min !== undefined) {
            return `WHEN ₹${val.min?.toLocaleString('en-IN') || 0} - ₹${val.max?.toLocaleString('en-IN') || '∞'} THEN ₹${val.tax || 0}`;
          }
          return `${key}: ${JSON.stringify(val)}`;
        }).join(' | ');
      }
      
      // Check for formula conditions - show prominently for FORMULA type
      if (conditions.formula) {
        const otherConditions = (entries || []).filter(([k]) => k !== 'formula');
        let result = `FORMULA: ${conditions.formula}`;
        if (otherConditions.length > 0) {
          result += ' | ' + (otherConditions || []).map(([k, v]) => `${k}=${v}`).join(', ');
        }
        return result;
      }
      
      // Format as key=value pairs with AND
      return (entries || []).map(([key, val]) => {
        if (typeof val === 'boolean') {
          return val ? key : `NOT ${key}`;
        }
        if (typeof val === 'object') {
          // For nested objects like {applies_to: "manager_and_above"}
          return `${key.replace(/_/g, ' ')}: ${typeof val === 'object' ? JSON.stringify(val) : val}`;
        }
        return `${key.replace(/_/g, ' ')} = ${val}`;
      }).join(' AND ');
    }
    
    return String(conditions);
  };
  
  const renderRuleCard = (policy, rule, index) => {
    const Icon = rule.is_enabled ? CheckCircle : AlertCircle;
    
    return (
      <div
        key={rule.rule_id || index}
        className={`p-4 rounded-lg border transition-all ${
          rule.is_enabled 
            ? isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'
            : isDark ? 'bg-zinc-900/50 border-zinc-800' : 'bg-zinc-50 border-zinc-200 opacity-60'
        }`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Badge className={`text-xs ${getRuleTypeColor(rule.rule_type)}`}>
                {rule.rule_type?.toUpperCase()}
              </Badge>
              <span className="text-xs text-zinc-500">{rule.rule_id}</span>
              {rule.category && (
                <span className={`text-xs px-2 py-0.5 rounded ${isDark ? 'bg-zinc-700' : 'bg-zinc-100'}`}>
                  {rule.category}
                </span>
              )}
            </div>
            <h4 className="font-medium">{rule.rule_name}</h4>
            <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
              {rule.description}
            </p>
            
            {/* Rule Value Display */}
            <div className={`mt-3 p-2 rounded ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
              <div className="flex flex-col gap-2 text-sm">
                <div className="flex items-center gap-4">
                  <div>
                    <span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>Value: </span>
                    <span className="font-mono font-medium">{formatRuleValue(rule)}</span>
                  </div>
                </div>
                {rule.conditions && (
                  <div className={`text-xs p-2 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                    <div className="flex items-center gap-1 mb-1">
                      <Info className="w-3 h-3 text-blue-500" />
                      <span className={`font-medium ${isDark ? 'text-zinc-300' : 'text-zinc-600'}`}>
                        {rule.rule_type === 'formula' ? 'Formula:' : 'Conditions:'}
                      </span>
                    </div>
                    <code className={`font-mono text-xs ${isDark ? 'text-amber-400' : 'text-amber-600'}`}>
                      {formatConditions(rule.conditions, rule)}
                    </code>
                  </div>
                )}
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {canEdit && (
              <>
                <Switch
                  checked={rule.is_enabled}
                  onCheckedChange={() => handleToggleRule(policy, rule)}
                  data-testid={`toggle-${rule.rule_id}`}
                />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleEditRule(policy, rule)}
                  data-testid={`edit-${rule.rule_id}`}
                >
                  <Edit2 className="w-4 h-4" />
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  };
  
  const renderPolicyCard = (policy) => {
    const TypeIcon = POLICY_TYPE_ICONS[policy.policy_type] || FileText;
    const ScopeIcon = SCOPE_ICONS[policy.scope] || Building2;
    const enabledRules = policy.rules?.filter(r => r.is_enabled)?.length || 0;
    const totalRules = policy.rules?.length || 0;
    
    return (
      <Card 
        key={policy.id} 
        className={`${isDark ? 'bg-zinc-800 border-zinc-700' : ''} hover:shadow-lg transition-shadow cursor-pointer`}
        onClick={() => setSelectedPolicy(selectedPolicy?.id === policy.id ? null : policy)}
        data-testid={`policy-${policy.policy_type}`}
      >
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${POLICY_TYPE_COLORS[policy.policy_type]?.split(' ')[0]} ${isDark ? 'opacity-80' : ''}`}>
                <TypeIcon className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  {policy.name}
                  {policy.is_active ? (
                    <Badge className="bg-emerald-100 text-emerald-700">Active</Badge>
                  ) : (
                    <Badge className="bg-zinc-100 text-zinc-500">Inactive</Badge>
                  )}
                </CardTitle>
                <CardDescription className="flex items-center gap-2 mt-1">
                  <ScopeIcon className="w-3 h-3" />
                  {policy.scope === 'company' ? 'All Employees' : policy.scope_value || policy.scope}
                </CardDescription>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium">{enabledRules}/{totalRules} rules</p>
              <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                Effective: {new Date(policy.effective_from).toLocaleDateString()}
              </p>
            </div>
          </div>
        </CardHeader>
        
        {selectedPolicy?.id === policy.id && (
          <CardContent className="pt-4 border-t border-zinc-200 dark:border-zinc-700">
            <p className={`text-sm mb-4 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
              {policy.description}
            </p>
            
            {/* Rules List */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-medium flex items-center gap-2">
                  <Settings className="w-4 h-4" />
                  Policy Rules ({totalRules})
                </h4>
                {canEdit && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAddNewRule(policy);
                    }}
                    className="flex items-center gap-1"
                    data-testid={`add-rule-${policy.policy_type}`}
                  >
                    <Plus className="w-4 h-4" />
                    Add New Rule
                  </Button>
                )}
              </div>
              {policy.rules?.map((rule, idx) => renderRuleCard(policy, rule, idx))}
            </div>
            
            {/* Payroll Integration Info */}
            {policy.payroll_integration && Object.keys(policy.payroll_integration || {}).length > 0 && (
              <div className={`mt-4 p-3 rounded-lg ${isDark ? 'bg-emerald-900/20 border border-emerald-800' : 'bg-emerald-50 border border-emerald-200'}`}>
                <h5 className="font-medium text-emerald-700 dark:text-emerald-400 flex items-center gap-2 mb-2">
                  <IndianRupee className="w-4 h-4" />
                  Payroll Integration
                </h5>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(policy.payroll_integration || {}).map(([key, value]) => (
                    <div key={key}>
                      <span className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
                        {key.replace(/_/g, ' ')}: 
                      </span>
                      <span className="font-medium ml-1">
                        {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* CTC Linkage Info */}
            {policy.ctc_linkage && Object.keys(policy.ctc_linkage || {}).length > 0 && (
              <div className={`mt-4 p-3 rounded-lg ${isDark ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                <h5 className="font-medium text-blue-700 dark:text-blue-400 flex items-center gap-2 mb-2">
                  <Calculator className="w-4 h-4" />
                  CTC Component Linkage
                </h5>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(policy.ctc_linkage || {}).map(([key, value]) => (
                    <div key={key}>
                      <span className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
                        {key.replace(/_/g, ' ')}: 
                      </span>
                      <span className="font-medium ml-1">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        )}
      </Card>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div data-testid="business-rules-page" className={`space-y-6 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FileText className="w-6 h-6 text-emerald-600" />
            Business Rules & Policies
          </h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            {canEdit ? 'View and manage all company policies and rules' : 'View company policies and rules'}
          </p>
        </div>
        
        {/* Search */}
        <div className="flex items-center gap-3">
          {canEdit && (
            <Button
              onClick={() => setShowSimulator(true)}
              className="bg-emerald-600 hover:bg-emerald-700"
              data-testid="open-simulator-btn"
            >
              <Calculator className="w-4 h-4 mr-2" />
              Payroll Simulator
            </Button>
          )}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <Input
              type="text"
              placeholder="Search rules..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={`pl-10 w-64 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
              data-testid="search-rules"
            />
          </div>
        </div>
      </div>
      
      {/* Permission Notice */}
      {!canEdit && (
        <div className={`p-4 rounded-lg flex items-center gap-3 ${isDark ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
          <Info className="w-5 h-5 text-blue-500" />
          <p className={`text-sm ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>
            You have view-only access to company policies. Contact HR for any policy-related queries.
          </p>
        </div>
      )}
      
      {/* SOP Quick Reference Card - Shows when a specific tab is selected */}
      {activeTab !== 'all' && POLICY_SOP_DATA[activeTab] && (
        <div className={`p-4 rounded-lg border ${isDark ? 'bg-zinc-800/50 border-zinc-700' : 'bg-gradient-to-r from-white to-zinc-50 border-zinc-200'}`}>
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-lg ${POLICY_TYPE_COLORS[activeTab]?.split(' ')[0]} ${isDark ? 'opacity-80' : ''}`}>
                <BookOpen className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold flex items-center gap-2">
                  {POLICY_SOP_DATA[activeTab].title}
                  <Badge variant="outline" className="text-xs">SOP Available</Badge>
                </h3>
                <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                  {POLICY_SOP_DATA[activeTab].summary}
                </p>
                
                {/* Quick Tips - Visible Summary */}
                <div className="mt-3 flex flex-wrap gap-2">
                  {(POLICY_SOP_DATA[activeTab]?.quickTips || []).map((tip, idx) => (
                    <div key={idx} className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 ${isDark ? 'bg-zinc-700 text-zinc-300' : 'bg-zinc-100 text-zinc-600'}`}>
                      <Lightbulb className="w-3 h-3 text-amber-500" />
                      {tip}
                    </div>
                  ))}
                </div>
                
                {/* Impact Badges */}
                <div className="mt-3 flex items-center gap-3">
                  <span className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Impacts:</span>
                  {(POLICY_SOP_DATA[activeTab]?.impacts || []).map((impact, idx) => (
                    <Badge key={idx} variant="outline" className={`text-xs ${
                      impact.impact === 'Critical' ? 'border-red-300 text-red-600' :
                      impact.impact === 'High' ? 'border-amber-300 text-amber-600' :
                      impact.impact === 'Direct' ? 'border-blue-300 text-blue-600' :
                      'border-zinc-300 text-zinc-600'
                    }`}>
                      {impact.area}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSelectedSOPType(activeTab);
                setShowSOPModal(true);
              }}
              className="flex items-center gap-2"
              data-testid="view-sop-btn"
            >
              <BookOpen className="w-4 h-4" />
              View Full SOP
            </Button>
          </div>
        </div>
      )}
      
      {/* Policy Type Tabs */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setActiveTab('all')}
          className={`px-4 py-2 rounded-lg font-medium text-sm flex items-center gap-2 transition-colors ${
            activeTab === 'all'
              ? 'bg-emerald-600 text-white'
              : isDark ? 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
          }`}
          data-testid="tab-all"
        >
          All Policies
          <Badge className={activeTab === 'all' ? 'bg-white/20 text-white' : ''}>{policies.length}</Badge>
        </button>
        
        {policyTypes?.policy_types?.map(pt => {
          const Icon = POLICY_TYPE_ICONS[pt.id] || FileText;
          const count = policiesByType[pt.id]?.length || 0;
          
          return (
            <button
              key={pt.id}
              onClick={() => setActiveTab(pt.id)}
              className={`px-4 py-2 rounded-lg font-medium text-sm flex items-center gap-2 transition-colors ${
                activeTab === pt.id
                  ? `${POLICY_TYPE_COLORS[pt.id]?.split(' ').slice(0, 2).join(' ')} border`
                  : isDark ? 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
              }`}
              data-testid={`tab-${pt.id}`}
            >
              <Icon className="w-4 h-4" />
              {pt.name}
              {count > 0 && (
                <Badge className={activeTab === pt.id ? 'bg-white/30' : ''}>{count}</Badge>
              )}
            </button>
          );
        })}
      </div>
      
      {/* Stats Summary */}
      <div className="grid grid-cols-6 gap-4">
        {policyTypes?.policy_types?.map(pt => {
          const Icon = POLICY_TYPE_ICONS[pt.id] || FileText;
          const policyList = policiesByType[pt.id] || [];
          const totalRules = (policyList || []).reduce((sum, p) => sum + (p.rules?.length || 0), 0);
          const sopData = POLICY_SOP_DATA[pt.id];
          
          return (
            <QuickTipsTooltip key={pt.id} policyType={pt.id} isDark={isDark}>
              <div
                className={`p-4 rounded-lg border cursor-pointer transition-all ${
                  activeTab === pt.id ? 'ring-2 ring-emerald-500' : ''
                } ${isDark ? 'bg-zinc-800 border-zinc-700 hover:bg-zinc-700' : 'bg-white border-zinc-200 hover:bg-zinc-50'}`}
                onClick={() => setActiveTab(pt.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Icon className={`w-4 h-4 ${POLICY_TYPE_COLORS[pt.id]?.split(' ')[1]}`} />
                    <span className="text-xs font-medium">{pt.name.replace(' Policies', '').replace(' Rules', '')}</span>
                  </div>
                  {sopData && (
                    <HelpCircle className={`w-3 h-3 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`} />
                  )}
                </div>
                <p className="text-2xl font-bold">{totalRules}</p>
                <div className="flex items-center justify-between">
                  <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>rules</p>
                  {sopData && (
                    <Badge variant="outline" className="text-[10px] py-0 px-1">SOP</Badge>
                  )}
                </div>
              </div>
            </QuickTipsTooltip>
          );
        })}
      </div>
      
      {/* ==================== ATTENDANCE CONFIGURATION PANEL ==================== */}
      {activeTab === 'attendance' && attendanceConfig && canEdit && (
        <Card className={`${isDark ? 'bg-gradient-to-br from-emerald-900/20 to-zinc-800 border-emerald-700' : 'bg-gradient-to-br from-emerald-50 to-white border-emerald-200'}`}>
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/50">
                  <Clock className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    Attendance Policy Configuration
                    <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-400">
                      Company-Wide
                    </Badge>
                  </CardTitle>
                  <CardDescription>
                    Configure working days, core hours, and penalty rules for all employees
                  </CardDescription>
                </div>
              </div>
              <Button
                onClick={() => setShowAttendanceConfig(!showAttendanceConfig)}
                variant="ghost"
                size="sm"
              >
                {showAttendanceConfig ? 'Collapse' : 'Expand'}
                <ChevronRight className={`w-4 h-4 ml-1 transition-transform ${showAttendanceConfig ? 'rotate-90' : ''}`} />
              </Button>
            </div>
          </CardHeader>
          
          {showAttendanceConfig && (
            <CardContent className="space-y-6">
              {/* Working Days Configuration */}
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900/50 border border-zinc-700' : 'bg-white border border-zinc-200'}`}>
                <h4 className="font-semibold flex items-center gap-2 mb-4">
                  <Calendar className="w-4 h-4 text-blue-500" />
                  Working Days Schedule
                  <Badge variant="outline" className="text-xs">AT009</Badge>
                </h4>
                
                <div className="flex flex-wrap gap-2">
                  {(attendanceConfig.all_weekdays || ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']).map(day => {
                    const isSelected = attendanceConfig.working_days?.includes(day);
                    const shortDay = day.slice(0, 3);
                    
                    return (
                      <button
                        key={day}
                        onClick={() => toggleWorkingDay(day)}
                        className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                          isSelected
                            ? 'bg-emerald-600 text-white shadow-md'
                            : isDark 
                              ? 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700 border border-zinc-700' 
                              : 'bg-zinc-100 text-zinc-500 hover:bg-zinc-200 border border-zinc-200'
                        }`}
                        data-testid={`working-day-${shortDay.toLowerCase()}`}
                      >
                        {shortDay}
                        {isSelected && <CheckCircle className="w-3 h-3 ml-1 inline" />}
                      </button>
                    );
                  })}
                </div>
                
                <p className={`text-xs mt-3 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                  Selected: {attendanceConfig.working_days?.length || 0} working days per week
                  ({attendanceConfig.working_days?.map(d => d.slice(0, 3)).join(', ') || 'None'})
                </p>
              </div>
              
              {/* Core Hours Configuration */}
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900/50 border border-zinc-700' : 'bg-white border border-zinc-200'}`}>
                <h4 className="font-semibold flex items-center gap-2 mb-4">
                  <Clock className="w-4 h-4 text-purple-500" />
                  Core Hours (Mandatory Presence)
                  <Badge variant="outline" className="text-xs">AT002 & AT003</Badge>
                </h4>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <Label className="text-xs mb-1 block">Start Time</Label>
                    <Select
                      value={attendanceConfig.core_hours_start || '10:00'}
                      onValueChange={(val) => setAttendanceConfig({ ...attendanceConfig, core_hours_start: val })}
                    >
                      <SelectTrigger className={isDark ? 'bg-zinc-800 border-zinc-700' : ''} data-testid="core-hours-start">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {['08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '12:00'].map(time => (
                          <SelectItem key={time} value={time}>{time}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label className="text-xs mb-1 block">End Time</Label>
                    <Select
                      value={attendanceConfig.core_hours_end || '19:00'}
                      onValueChange={(val) => setAttendanceConfig({ ...attendanceConfig, core_hours_end: val })}
                    >
                      <SelectTrigger className={isDark ? 'bg-zinc-800 border-zinc-700' : ''} data-testid="core-hours-end">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {['16:00', '16:30', '17:00', '17:30', '18:00', '18:30', '19:00', '19:30', '20:00', '20:30', '21:00'].map(time => (
                          <SelectItem key={time} value={time}>{time}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label className="text-xs mb-1 block">Grace Period (mins)</Label>
                    <Input
                      type="number"
                      value={attendanceConfig.grace_period_minutes || 30}
                      onChange={(e) => setAttendanceConfig({ ...attendanceConfig, grace_period_minutes: parseInt(e.target.value) || 0 })}
                      className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
                      min={0}
                      max={60}
                      data-testid="grace-period-minutes"
                    />
                  </div>
                  
                  <div>
                    <Label className="text-xs mb-1 block">WFH Days/Week</Label>
                    <Input
                      type="number"
                      value={attendanceConfig.wfh_days_per_week || 2}
                      onChange={(e) => setAttendanceConfig({ ...attendanceConfig, wfh_days_per_week: parseInt(e.target.value) || 0 })}
                      className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
                      min={0}
                      max={7}
                      data-testid="wfh-days"
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
                  <div>
                    <Label className="text-xs mb-1 block">Grace Days/Month</Label>
                    <Input
                      type="number"
                      value={attendanceConfig.grace_days_per_month || 3}
                      onChange={(e) => setAttendanceConfig({ ...attendanceConfig, grace_days_per_month: parseInt(e.target.value) || 0 })}
                      className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
                      min={0}
                      max={10}
                      data-testid="grace-days-month"
                    />
                  </div>
                  
                  <div>
                    <Label className="text-xs mb-1 block">Late Penalty (₹/day)</Label>
                    <Input
                      type="number"
                      value={attendanceConfig.late_penalty_amount || 100}
                      onChange={(e) => setAttendanceConfig({ ...attendanceConfig, late_penalty_amount: parseInt(e.target.value) || 0 })}
                      className={isDark ? 'bg-zinc-800 border-zinc-700' : ''}
                      min={0}
                      data-testid="late-penalty-amount"
                    />
                  </div>
                  
                  <div className="flex items-end">
                    <Button
                      onClick={handleSaveAttendanceConfig}
                      disabled={savingAttendanceConfig}
                      className="bg-emerald-600 hover:bg-emerald-700 w-full"
                      data-testid="save-attendance-config"
                    >
                      {savingAttendanceConfig ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Save className="w-4 h-4 mr-2" />
                      )}
                      Save Configuration
                    </Button>
                  </div>
                </div>
                
                <div className={`mt-4 p-3 rounded-lg ${isDark ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                  <p className={`text-xs ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>
                    <strong>Summary:</strong> Employees work {attendanceConfig.working_days?.length || 0} days/week, 
                    core hours {attendanceConfig.core_hours_start || '10:00'} - {attendanceConfig.core_hours_end || '19:00'}, 
                    with {attendanceConfig.grace_period_minutes || 30} mins grace period, 
                    {attendanceConfig.grace_days_per_month || 3} grace days/month, 
                    and ₹{attendanceConfig.late_penalty_amount || 100}/day penalty for violations.
                  </p>
                </div>
              </div>
              
              {/* Role-wise & Employee-wise Overrides */}
              <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900/50 border border-zinc-700' : 'bg-white border border-zinc-200'}`}>
                <div className="flex items-center justify-between mb-4">
                  <h4 className="font-semibold flex items-center gap-2">
                    <Users className="w-4 h-4 text-amber-500" />
                    Policy Overrides
                    <Badge variant="outline" className="text-xs">
                      {(attendanceOverrides.total_role_overrides || 0) + (attendanceOverrides.total_employee_overrides || 0)} active
                    </Badge>
                  </h4>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowAddOverrideDialog(true)}
                    className="flex items-center gap-1"
                    data-testid="add-override-btn"
                  >
                    <Plus className="w-4 h-4" />
                    Add Override
                  </Button>
                </div>
                
                {/* Role Overrides */}
                {attendanceOverrides.role_overrides?.length > 0 && (
                  <div className="mb-4">
                    <p className={`text-xs font-medium mb-2 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                      <Briefcase className="w-3 h-3 inline mr-1" />
                      Role-wise Overrides ({attendanceOverrides.total_role_overrides})
                    </p>
                    <div className="space-y-2">
                      {(attendanceOverrides?.role_overrides || []).map(override => {
                        const rules = override.rules?.reduce((acc, r) => ({ ...acc, [r.rule_id]: r }), {}) || {};
                        return (
                          <div 
                            key={override.id} 
                            className={`p-3 rounded-lg flex items-center justify-between ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}
                          >
                            <div>
                              <p className="font-medium text-sm">{override.scope_value}</p>
                              <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                                {rules.AT002?.value || '10:00'} - {rules.AT003?.value || '19:00'} | 
                                {rules.AT009?.list_value?.length || 6} days/week
                              </p>
                            </div>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleDeleteOverride(override.id)}
                              className="text-red-500 hover:text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                
                {/* Employee Overrides */}
                {attendanceOverrides.employee_overrides?.length > 0 && (
                  <div>
                    <p className={`text-xs font-medium mb-2 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                      <User className="w-3 h-3 inline mr-1" />
                      Employee-wise Overrides ({attendanceOverrides.total_employee_overrides})
                    </p>
                    <div className="space-y-2">
                      {(attendanceOverrides?.employee_overrides || []).map(override => {
                        const rules = override.rules?.reduce((acc, r) => ({ ...acc, [r.rule_id]: r }), {}) || {};
                        return (
                          <div 
                            key={override.id} 
                            className={`p-3 rounded-lg flex items-center justify-between ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}
                          >
                            <div>
                              <p className="font-medium text-sm">
                                {override.employee_name || override.scope_value}
                                <span className={`text-xs ml-2 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                                  ({override.employee_code || '-'})
                                </span>
                              </p>
                              <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                                {rules.AT002?.value || '10:00'} - {rules.AT003?.value || '19:00'} | 
                                {rules.AT009?.list_value?.length || 6} days/week
                                {override.description && ` | ${override.description}`}
                              </p>
                            </div>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleDeleteOverride(override.id)}
                              className="text-red-500 hover:text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                
                {/* No overrides message */}
                {(!attendanceOverrides.role_overrides?.length && !attendanceOverrides.employee_overrides?.length) && (
                  <p className={`text-sm text-center py-4 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                    No overrides configured. All employees use company-wide settings.
                  </p>
                )}
              </div>
            </CardContent>
          )}
        </Card>
      )}
      
      {/* Policies Grid */}
      <div className="space-y-4">
        {filteredPolicies.length === 0 ? (
          <div className={`text-center py-12 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
            <FileText className="w-12 h-12 mx-auto mb-4 text-zinc-400" />
            <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
              {searchQuery ? `No policies found matching "${searchQuery}"` : 'No policies found'}
            </p>
          </div>
        ) : (
          (filteredPolicies || []).map(policy => renderPolicyCard(policy))
        )}
      </div>
      
      {/* Edit/Add Rule Dialog - Enhanced with Dropdowns */}
      <Dialog open={showRuleDialog} onOpenChange={setShowRuleDialog}>
        <DialogContent className={`max-w-2xl max-h-[90vh] overflow-y-auto ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {editingRule?._isNew ? <Plus className="w-5 h-5" /> : <Edit2 className="w-5 h-5" />}
              {editingRule?._isNew ? 'Add New Rule' : `Edit Rule: ${editingRule?.rule_name}`}
            </DialogTitle>
            <DialogDescription>
              {editingRule?._isNew 
                ? 'Configure the new rule with all applicable settings. Fields marked with * are required.'
                : 'Modify the rule configuration. Changes will take effect immediately.'
              }
            </DialogDescription>
          </DialogHeader>
          
          {editingRule && (
            <div className="space-y-4 py-4">
              {/* Row 1: Rule ID and Rule Type */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Rule ID {editingRule._isNew && '(auto-generated if empty)'}</Label>
                  <Input
                    value={editingRule.rule_id || ''}
                    onChange={(e) => setEditingRule({...editingRule, rule_id: e.target.value.toUpperCase()})}
                    placeholder="e.g., LV013"
                    disabled={!editingRule._isNew}
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
                <div>
                  <Label>Rule Type *</Label>
                  <Select
                    value={editingRule.rule_type || 'limit'}
                    onValueChange={(val) => setEditingRule({...editingRule, rule_type: val, value: ''})}
                  >
                    <SelectTrigger className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="limit">LIMIT (max values, quotas)</SelectItem>
                      <SelectItem value="threshold">THRESHOLD (trigger points)</SelectItem>
                      <SelectItem value="condition">CONDITION (if/then logic)</SelectItem>
                      <SelectItem value="formula">FORMULA (calculations)</SelectItem>
                      <SelectItem value="approval">APPROVAL (workflow rules)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {/* Row 2: Rule Name */}
              <div>
                <Label>Rule Name *</Label>
                <Input
                  value={editingRule.rule_name || ''}
                  onChange={(e) => setEditingRule({...editingRule, rule_name: e.target.value})}
                  placeholder="e.g., Maximum Single Expense Claim"
                  className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                />
              </div>
              
              {/* Row 3: Description */}
              <div>
                <Label>Description</Label>
                <Input
                  value={editingRule.description || ''}
                  onChange={(e) => setEditingRule({...editingRule, description: e.target.value})}
                  placeholder="Brief description of what this rule governs"
                  className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                />
              </div>
              
              {/* Row 4: Category Dropdown */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Category *</Label>
                  <Select
                    value={editingRule.category || ''}
                    onValueChange={(val) => setEditingRule({...editingRule, category: val})}
                  >
                    <SelectTrigger className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}>
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent className="max-h-60">
                      {(CATEGORY_OPTIONS[selectedPolicy?.policy_type] || CATEGORY_OPTIONS.general).map(cat => (
                        <SelectItem key={cat.value} value={cat.value}>
                          <div className="flex flex-col">
                            <span>{cat.label}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Applies To - Scope Type */}
                <div>
                  <Label>Applies To *</Label>
                  <Select
                    value={editingRule.applies_to?.scope_type || 'all_employees'}
                    onValueChange={(val) => setEditingRule({
                      ...editingRule, 
                      applies_to: { ...editingRule.applies_to, scope_type: val, scope_value: '' }
                    })}
                  >
                    <SelectTrigger className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}>
                      <SelectValue placeholder="Who does this apply to?" />
                    </SelectTrigger>
                    <SelectContent className="max-h-60">
                      {(APPLIES_TO_OPTIONS?.scope_type || []).map(opt => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {/* Row 5: Scope Value Dropdown (conditional based on scope_type) */}
              {editingRule.applies_to?.scope_type && editingRule.applies_to.scope_type !== 'all_employees' && (
                <div>
                  <Label>
                    {editingRule.applies_to.scope_type === 'by_department' && 'Select Department'}
                    {editingRule.applies_to.scope_type === 'by_role' && 'Select Role'}
                    {editingRule.applies_to.scope_type === 'by_grade' && 'Select Grade'}
                    {editingRule.applies_to.scope_type === 'by_employment_type' && 'Select Employment Type'}
                    {editingRule.applies_to.scope_type === 'by_location' && 'Select Location'}
                    {editingRule.applies_to.scope_type === 'by_experience' && 'Select Experience Range'}
                    {editingRule.applies_to.scope_type === 'by_ctc_range' && 'Select CTC Range'}
                    {editingRule.applies_to.scope_type === 'custom_group' && 'Custom Group Name'}
                  </Label>
                  {editingRule.applies_to.scope_type === 'custom_group' ? (
                    <Input
                      value={editingRule.applies_to?.scope_value || ''}
                      onChange={(e) => setEditingRule({
                        ...editingRule,
                        applies_to: { ...editingRule.applies_to, scope_value: e.target.value }
                      })}
                      placeholder="Enter custom group name"
                      className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                    />
                  ) : (
                    <Select
                      value={editingRule.applies_to?.scope_value || ''}
                      onValueChange={(val) => setEditingRule({
                        ...editingRule,
                        applies_to: { ...editingRule.applies_to, scope_value: val }
                      })}
                    >
                      <SelectTrigger className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}>
                        <SelectValue placeholder="Select specific value" />
                      </SelectTrigger>
                      <SelectContent className="max-h-60">
                        {editingRule.applies_to.scope_type === 'by_department' && 
                          (APPLIES_TO_OPTIONS?.departments || []).map(opt => (
                            <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                          ))
                        }
                        {editingRule.applies_to.scope_type === 'by_role' && 
                          (APPLIES_TO_OPTIONS?.roles || []).map(opt => (
                            <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                          ))
                        }
                        {editingRule.applies_to.scope_type === 'by_grade' && 
                          (APPLIES_TO_OPTIONS?.grades || []).map(opt => (
                            <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                          ))
                        }
                        {editingRule.applies_to.scope_type === 'by_employment_type' && 
                          (APPLIES_TO_OPTIONS?.employment_types || []).map(opt => (
                            <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                          ))
                        }
                        {editingRule.applies_to.scope_type === 'by_location' && 
                          (APPLIES_TO_OPTIONS?.locations || []).map(opt => (
                            <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                          ))
                        }
                        {editingRule.applies_to.scope_type === 'by_experience' && 
                          (APPLIES_TO_OPTIONS?.experience_ranges || []).map(opt => (
                            <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                          ))
                        }
                        {editingRule.applies_to.scope_type === 'by_ctc_range' && 
                          (APPLIES_TO_OPTIONS?.ctc_ranges || []).map(opt => (
                            <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                          ))
                        }
                      </SelectContent>
                    </Select>
                  )}
                </div>
              )}
              
              {/* Divider */}
              <div className={`border-t ${isDark ? 'border-zinc-700' : 'border-zinc-200'} my-2`} />
              
              {/* Row 6: Numeric Value and Unit */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Numeric Value</Label>
                  <Input
                    type="number"
                    value={editingRule.numeric_value ?? ''}
                    onChange={(e) => setEditingRule({...editingRule, numeric_value: e.target.value ? parseFloat(e.target.value) : null})}
                    placeholder="e.g., 50000, 12, 15"
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
                <div>
                  <Label>Unit *</Label>
                  <Select
                    value={editingRule.unit || ''}
                    onValueChange={(val) => setEditingRule({...editingRule, unit: val})}
                  >
                    <SelectTrigger className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}>
                      <SelectValue placeholder="Select unit" />
                    </SelectTrigger>
                    <SelectContent className="max-h-60">
                      {UNIT_OPTIONS.map(opt => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {/* Row 7: String Value / Formula - with templates based on rule type */}
              <div>
                <Label>
                  {editingRule.rule_type === 'formula' ? 'Formula / Calculation' :
                   editingRule.rule_type === 'condition' ? 'Condition Logic' :
                   editingRule.rule_type === 'approval' ? 'Approval Type' :
                   'Value Type / Behavior'}
                </Label>
                <Select
                  value={editingRule.value || ''}
                  onValueChange={(val) => setEditingRule({...editingRule, value: val})}
                >
                  <SelectTrigger className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}>
                    <SelectValue placeholder="Select or enter value" />
                  </SelectTrigger>
                  <SelectContent className="max-h-60">
                    {(STRING_VALUE_TEMPLATES[editingRule.rule_type] || STRING_VALUE_TEMPLATES.limit).map(opt => (
                      <SelectItem key={opt.value || 'empty'} value={opt.value}>{opt.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {/* Custom value input if they want to override */}
                <Input
                  value={editingRule.value || ''}
                  onChange={(e) => setEditingRule({...editingRule, value: e.target.value})}
                  placeholder="Or type a custom value/formula..."
                  className={`mt-2 ${isDark ? 'bg-zinc-900 border-zinc-700' : ''}`}
                />
              </div>
              
              {/* Row 8: Condition Builder (only for CONDITION type) */}
              {editingRule.rule_type === 'condition' && (
                <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-900 border border-zinc-700' : 'bg-zinc-50 border border-zinc-200'}`}>
                  <Label className="flex items-center gap-2 mb-2">
                    <Settings className="w-4 h-4" />
                    Condition Builder (Optional)
                  </Label>
                  <div className="grid grid-cols-3 gap-2">
                    <Select
                      value={editingRule.conditions?.field || ''}
                      onValueChange={(val) => setEditingRule({
                        ...editingRule,
                        conditions: { ...editingRule.conditions, field: val }
                      })}
                    >
                      <SelectTrigger className={isDark ? 'bg-zinc-800 border-zinc-600' : ''}>
                        <SelectValue placeholder="Field" />
                      </SelectTrigger>
                      <SelectContent className="max-h-48">
                        {CONDITION_FIELD_OPTIONS.map(opt => (
                          <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Select
                      value={editingRule.conditions?.operator || ''}
                      onValueChange={(val) => setEditingRule({
                        ...editingRule,
                        conditions: { ...editingRule.conditions, operator: val }
                      })}
                    >
                      <SelectTrigger className={isDark ? 'bg-zinc-800 border-zinc-600' : ''}>
                        <SelectValue placeholder="Operator" />
                      </SelectTrigger>
                      <SelectContent>
                        {CONDITION_OPERATORS.map(opt => (
                          <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Input
                      value={editingRule.conditions?.compare_value || ''}
                      onChange={(e) => setEditingRule({
                        ...editingRule,
                        conditions: { ...editingRule.conditions, compare_value: e.target.value }
                      })}
                      placeholder="Value"
                      className={isDark ? 'bg-zinc-800 border-zinc-600' : ''}
                    />
                  </div>
                  <p className={`text-xs mt-2 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                    Example: department == Sales → Rule applies only to Sales dept
                  </p>
                </div>
              )}
              
              {/* Divider */}
              <div className={`border-t ${isDark ? 'border-zinc-700' : 'border-zinc-200'} my-2`} />
              
              {/* Row 9: Rule Enabled */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Switch
                    checked={editingRule.is_enabled}
                    onCheckedChange={(checked) => setEditingRule({...editingRule, is_enabled: checked})}
                  />
                  <Label>Rule Enabled</Label>
                </div>
                <Badge className={editingRule.is_enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-zinc-100 text-zinc-500'}>
                  {editingRule.is_enabled ? 'Active' : 'Inactive'}
                </Badge>
              </div>
              
              {/* Summary Preview */}
              <div className={`p-3 rounded-lg ${isDark ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                <p className={`text-xs font-medium ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>Rule Preview:</p>
                <p className={`text-sm mt-1 ${isDark ? 'text-blue-200' : 'text-blue-600'}`}>
                  {editingRule.rule_name || 'Unnamed Rule'} 
                  {editingRule.numeric_value !== null && editingRule.numeric_value !== undefined && 
                    ` = ${editingRule.numeric_value} ${editingRule.unit || ''}`}
                  {editingRule.applies_to?.scope_type && editingRule.applies_to.scope_type !== 'all_employees' &&
                    ` (for ${editingRule.applies_to.scope_value || editingRule.applies_to.scope_type})`}
                </p>
              </div>
              
              {/* RULE IMPACT SIMULATION - Shows what happens when rule is applied */}
              <div className={`p-4 rounded-lg ${isDark ? 'bg-gradient-to-br from-purple-900/30 to-zinc-900 border border-purple-700' : 'bg-gradient-to-br from-purple-50 to-white border border-purple-200'}`}>
                <h4 className={`font-semibold flex items-center gap-2 mb-3 ${isDark ? 'text-purple-300' : 'text-purple-700'}`}>
                  <Calculator className="w-4 h-4" />
                  Impact Simulation - What Will Happen?
                </h4>
                
                {/* LIMIT Rule Examples */}
                {editingRule.rule_type === 'limit' && (
                  <div className="space-y-3">
                    <p className={`text-xs ${isDark ? 'text-purple-300' : 'text-purple-600'}`}>
                      <strong>LIMIT Rule:</strong> Sets maximum allowable values. Exceeding this limit triggers rejection or requires special approval.
                    </p>
                    <div className={`p-3 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                      <p className="text-xs font-medium text-emerald-600 mb-2">✅ Example 1 - Within Limit:</p>
                      <div className="text-sm space-y-1">
                        <p>Employee CTC: <strong>₹8,00,000/year</strong> (Basic: ₹3,20,000)</p>
                        <p>Rule: {editingRule.rule_name || 'Max Leave'} = <strong>{editingRule.numeric_value || 12} {editingRule.unit || 'days/year'}</strong></p>
                        <p>Employee requests: <strong>{Math.floor((editingRule.numeric_value || 12) * 0.8)} {editingRule.unit?.replace('/year', '').replace('/month', '') || 'days'}</strong></p>
                        <p className="text-emerald-600">→ <strong>APPROVED</strong> (within limit)</p>
                      </div>
                    </div>
                    <div className={`p-3 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                      <p className="text-xs font-medium text-red-600 mb-2">❌ Example 2 - Exceeds Limit:</p>
                      <div className="text-sm space-y-1">
                        <p>Employee CTC: <strong>₹12,00,000/year</strong> (Basic: ₹4,80,000)</p>
                        <p>Rule: {editingRule.rule_name || 'Max Expense'} = <strong>{editingRule.numeric_value || 50000} {editingRule.unit || 'INR'}</strong></p>
                        <p>Employee claims: <strong>₹{((editingRule.numeric_value || 50000) * 1.5).toLocaleString('en-IN')}</strong></p>
                        <p className="text-red-600">→ <strong>REJECTED</strong> (exceeds limit by ₹{((editingRule.numeric_value || 50000) * 0.5).toLocaleString('en-IN')})</p>
                        <p className="text-xs text-zinc-500">CTC Impact: None (claim not processed)</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* THRESHOLD Rule Examples */}
                {editingRule.rule_type === 'threshold' && (
                  <div className="space-y-3">
                    <p className={`text-xs ${isDark ? 'text-purple-300' : 'text-purple-600'}`}>
                      <strong>THRESHOLD Rule:</strong> Triggers actions when values cross defined thresholds (auto-approve, penalties, escalations).
                    </p>
                    <div className={`p-3 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                      <p className="text-xs font-medium text-emerald-600 mb-2">✅ Example 1 - Below Threshold (Auto-Approved):</p>
                      <div className="text-sm space-y-1">
                        <p>Employee CTC: <strong>₹6,00,000/year</strong> (Monthly: ₹50,000)</p>
                        <p>Threshold: Auto-approve expenses below <strong>₹{(editingRule.numeric_value || 500).toLocaleString('en-IN')}</strong></p>
                        <p>Employee expense claim: <strong>₹{Math.floor((editingRule.numeric_value || 500) * 0.6).toLocaleString('en-IN')}</strong></p>
                        <p className="text-emerald-600">→ <strong>AUTO-APPROVED</strong> (no manager approval needed)</p>
                        <p className="text-xs text-zinc-500">Payroll Impact: ₹{Math.floor((editingRule.numeric_value || 500) * 0.6).toLocaleString('en-IN')} added to reimbursements in next payroll</p>
                      </div>
                    </div>
                    <div className={`p-3 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                      <p className="text-xs font-medium text-amber-600 mb-2">⚠️ Example 2 - Above Threshold (Penalty Applied):</p>
                      <div className="text-sm space-y-1">
                        <p>Employee CTC: <strong>₹10,00,000/year</strong> (Basic: ₹4,00,000, Daily: ₹1,333)</p>
                        <p>Threshold: Late penalty after <strong>{editingRule.numeric_value || 3} incidents</strong></p>
                        <p>Employee late arrivals this month: <strong>{(editingRule.numeric_value || 3) + 2}</strong></p>
                        <p className="text-amber-600">→ <strong>PENALTY TRIGGERED</strong> ({(editingRule.numeric_value || 3) + 2 - (editingRule.numeric_value || 3)} excess = 0.5 day LOP each)</p>
                        <p className="text-xs text-red-500">CTC Impact: ₹{Math.floor(1333 * 0.5 * 2).toLocaleString('en-IN')} deducted from salary (1 day LOP)</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* FORMULA Rule Examples */}
                {editingRule.rule_type === 'formula' && (
                  <div className="space-y-3">
                    <p className={`text-xs ${isDark ? 'text-purple-300' : 'text-purple-600'}`}>
                      <strong>FORMULA Rule:</strong> Calculates values dynamically based on CTC components (Basic, Gross, etc.).
                    </p>
                    <div className={`p-3 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                      <p className="text-xs font-medium text-blue-600 mb-2">📊 Example 1 - PF Calculation:</p>
                      <div className="text-sm space-y-1">
                        <p>Employee CTC: <strong>₹10,00,000/year</strong></p>
                        <p>Basic Salary: <strong>₹4,00,000/year</strong> (₹33,333/month)</p>
                        <p>Formula: <code className="bg-zinc-100 px-1 rounded text-xs">{editingRule.value || 'basic_salary * 0.12'}</code></p>
                        <p className="text-blue-600">→ PF Contribution: <strong>₹33,333 × 12% = ₹4,000/month</strong></p>
                        <p className="text-xs text-zinc-500">CTC Impact: Employee: -₹4,000 | Employer: +₹4,000 (total ₹8,000 to PF account)</p>
                      </div>
                    </div>
                    <div className={`p-3 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                      <p className="text-xs font-medium text-red-600 mb-2">📊 Example 2 - LOP Deduction:</p>
                      <div className="text-sm space-y-1">
                        <p>Employee Gross CTC: <strong>₹12,00,000/year</strong> (₹1,00,000/month)</p>
                        <p>Monthly Gross: <strong>₹1,00,000</strong> (Daily: ₹3,333)</p>
                        <p>LOP Days: <strong>3 days</strong></p>
                        <p>Formula: <code className="bg-zinc-100 px-1 rounded text-xs">(gross_ctc / 30) × lop_days</code></p>
                        <p className="text-red-600">→ LOP Deduction: <strong>₹3,333 × 3 = ₹10,000</strong></p>
                        <p className="text-xs text-zinc-500">Payslip Impact: Gross ₹1,00,000 - LOP ₹10,000 = Net before tax ₹90,000</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* CONDITION Rule Examples */}
                {editingRule.rule_type === 'condition' && (
                  <div className="space-y-3">
                    <p className={`text-xs ${isDark ? 'text-purple-300' : 'text-purple-600'}`}>
                      <strong>CONDITION Rule:</strong> Applies different rules based on employee attributes (department, role, CTC, etc.).
                    </p>
                    <div className={`p-3 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                      <p className="text-xs font-medium text-emerald-600 mb-2">✅ Example 1 - Condition Met:</p>
                      <div className="text-sm space-y-1">
                        <p>Rule: Flight Class = Business <strong>WHEN</strong> travel_hours &gt; 4 hours <strong>AND</strong> role = manager</p>
                        <p>Employee: <strong>Sales Manager</strong>, Travel: Mumbai → Delhi (5 hours)</p>
                        <p>CTC: <strong>₹20,00,000/year</strong></p>
                        <p className="text-emerald-600">→ <strong>CONDITION MET</strong> - Business class allowed</p>
                        <p className="text-xs text-zinc-500">Expense Impact: ₹25,000 flight claim approved (vs ₹8,000 economy)</p>
                      </div>
                    </div>
                    <div className={`p-3 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                      <p className="text-xs font-medium text-amber-600 mb-2">⚠️ Example 2 - Condition NOT Met:</p>
                      <div className="text-sm space-y-1">
                        <p>Rule: Flight Class = Business <strong>WHEN</strong> travel_hours &gt; 4 hours <strong>AND</strong> role = manager</p>
                        <p>Employee: <strong>Senior Developer</strong>, Travel: Mumbai → Delhi (5 hours)</p>
                        <p>CTC: <strong>₹15,00,000/year</strong></p>
                        <p className="text-amber-600">→ <strong>CONDITION NOT MET</strong> (not a manager) - Economy class only</p>
                        <p className="text-xs text-zinc-500">Expense Impact: Max ₹8,000 flight claim allowed</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* APPROVAL Rule Examples */}
                {editingRule.rule_type === 'approval' && (
                  <div className="space-y-3">
                    <p className={`text-xs ${isDark ? 'text-purple-300' : 'text-purple-600'}`}>
                      <strong>APPROVAL Rule:</strong> Defines who can approve what, prevents self-approval, sets escalation paths.
                    </p>
                    <div className={`p-3 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                      <p className="text-xs font-medium text-emerald-600 mb-2">✅ Example 1 - Proper Approval Flow:</p>
                      <div className="text-sm space-y-1">
                        <p>Rule: {editingRule.rule_name || 'Self-Approval Prevention'} = <strong>{editingRule.value?.replace(/_/g, ' ') || 'No Self Approval'}</strong></p>
                        <p>Employee CTC: <strong>₹8,00,000/year</strong></p>
                        <p>Expense claim: <strong>₹15,000</strong> for client dinner</p>
                        <p>Submitted by: Employee → Approved by: <strong>Reporting Manager</strong></p>
                        <p className="text-emerald-600">→ <strong>APPROVED</strong> - Correct workflow followed</p>
                        <p className="text-xs text-zinc-500">Payroll Impact: ₹15,000 added to next month reimbursements</p>
                      </div>
                    </div>
                    <div className={`p-3 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                      <p className="text-xs font-medium text-red-600 mb-2">❌ Example 2 - Self-Approval Blocked:</p>
                      <div className="text-sm space-y-1">
                        <p>Rule: {editingRule.rule_name || 'Self-Approval Prevention'} = <strong>Prohibited</strong></p>
                        <p>Manager CTC: <strong>₹25,00,000/year</strong></p>
                        <p>Manager's expense claim: <strong>₹50,000</strong> for conference</p>
                        <p>Manager tries to approve own claim</p>
                        <p className="text-red-600">→ <strong>BLOCKED</strong> - Self-approval not allowed</p>
                        <p className="text-xs text-zinc-500">System redirects to: Skip-level manager or HR for approval</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* CTC Components Affected */}
                <div className={`mt-4 p-3 rounded ${isDark ? 'bg-zinc-800/50' : 'bg-zinc-50'} border ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                  <p className="text-xs font-medium mb-2 flex items-center gap-2">
                    <IndianRupee className="w-3 h-3" />
                    CTC Components This Rule May Affect:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {editingRule.rule_type === 'formula' && (
                      <>
                        <Badge variant="outline" className="text-xs">Basic Salary</Badge>
                        <Badge variant="outline" className="text-xs">PF Contribution</Badge>
                        <Badge variant="outline" className="text-xs">ESI Deduction</Badge>
                        <Badge variant="outline" className="text-xs">Gross Salary</Badge>
                      </>
                    )}
                    {editingRule.rule_type === 'limit' && (
                      <>
                        <Badge variant="outline" className="text-xs">Reimbursements</Badge>
                        <Badge variant="outline" className="text-xs">Leave Encashment</Badge>
                        <Badge variant="outline" className="text-xs">Travel Claims</Badge>
                      </>
                    )}
                    {editingRule.rule_type === 'threshold' && (
                      <>
                        <Badge variant="outline" className="text-xs">LOP Deductions</Badge>
                        <Badge variant="outline" className="text-xs">Attendance Bonus</Badge>
                        <Badge variant="outline" className="text-xs">Overtime Pay</Badge>
                      </>
                    )}
                    {editingRule.rule_type === 'condition' && (
                      <>
                        <Badge variant="outline" className="text-xs">Allowances</Badge>
                        <Badge variant="outline" className="text-xs">Grade-based Benefits</Badge>
                        <Badge variant="outline" className="text-xs">Location Allowance</Badge>
                      </>
                    )}
                    {editingRule.rule_type === 'approval' && (
                      <>
                        <Badge variant="outline" className="text-xs">Expense Reimbursements</Badge>
                        <Badge variant="outline" className="text-xs">Leave Balance</Badge>
                        <Badge variant="outline" className="text-xs">Advance Settlements</Badge>
                      </>
                    )}
                  </div>
                </div>
                
                {/* TEST MY RULE - Interactive Testing */}
                <div className={`mt-4 p-4 rounded-lg ${isDark ? 'bg-amber-900/20 border border-amber-700' : 'bg-amber-50 border border-amber-200'}`}>
                  <div 
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => setShowTestMyRule(!showTestMyRule)}
                  >
                    <h4 className={`font-semibold flex items-center gap-2 ${isDark ? 'text-amber-300' : 'text-amber-700'}`}>
                      <User className="w-4 h-4" />
                      Test My Rule - Try with Real Data
                    </h4>
                    <ChevronRight className={`w-5 h-5 transition-transform ${showTestMyRule ? 'rotate-90' : ''} ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
                  </div>
                  
                  {showTestMyRule && (
                    <div className="mt-4 space-y-4">
                      <p className={`text-xs ${isDark ? 'text-amber-300' : 'text-amber-600'}`}>
                        Select an employee to auto-fill their data, or enter details manually to see rule impact.
                      </p>
                      
                      {/* Employee Selection Dropdown */}
                      <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800 border border-zinc-700' : 'bg-white border border-amber-200'}`}>
                        <Label className="text-xs font-medium flex items-center gap-2">
                          <Users className="w-4 h-4" />
                          Quick Select Employee (Auto-fills data)
                        </Label>
                        <Select
                          value={selectedEmployeeId}
                          onValueChange={(empId) => {
                            setSelectedEmployeeId(empId);
                            if (empId && empId !== 'manual') {
                              const emp = (employeesList || []).find(e => e.id === empId || e.employee_id === empId);
                              if (emp) {
                                // Calculate annual CTC from monthly gross salary (multiply by 12)
                                const annualCTC = (emp.gross_salary || emp.salary || 0) * 12;
                                const annualBasic = Math.round(annualCTC * 0.4);  // 40% of CTC is basic
                                
                                // Map employee department to dropdown value
                                const deptMap = {
                                  'HR': 'HR', 'Human Resources': 'HR',
                                  'Finance': 'Finance', 'Finance & Accounts': 'Finance',
                                  'Sales': 'Sales', 'Marketing': 'Marketing',
                                  'Engineering': 'Engineering', 'Operations': 'Operations',
                                  'Consulting': 'Consulting', 'IT': 'IT',
                                  'Legal': 'Legal', 'Admin': 'Admin', 'Administration': 'Admin',
                                  'Support': 'Support', 'R&D': 'R&D'
                                };
                                
                                // Map role
                                const roleMap = {
                                  'admin': 'admin', 'hr_manager': 'hr_manager', 
                                  'manager': 'manager', 'team_lead': 'team_lead',
                                  'senior': 'senior', 'employee': 'employee',
                                  'consultant': 'consultant', 'contractor': 'contractor',
                                  'intern': 'intern', 'trainee': 'trainee'
                                };
                                
                                // Map level/grade
                                const gradeMap = {
                                  'fresher': 'L1', 'junior': 'L2', 'mid': 'L3', 'mid-level': 'L3',
                                  'senior': 'L4', 'lead': 'L5', 'principal': 'L5',
                                  'manager': 'L6', 'senior_manager': 'L7', 'director': 'L7',
                                  'vp': 'L8', 'head': 'L8', 'cxo': 'L9', 'executive': 'L3'
                                };
                                
                                // Map city to location
                                const locationMap = {
                                  'Mumbai': 'mumbai', 'Delhi': 'delhi', 'Delhi NCR': 'delhi',
                                  'Bangalore': 'bangalore', 'Bengaluru': 'bangalore',
                                  'Chennai': 'chennai', 'Hyderabad': 'hyderabad',
                                  'Kolkata': 'kolkata', 'Pune': 'pune', 'Ahmedabad': 'ahmedabad'
                                };
                                
                                setTestRuleData({
                                  ...testRuleData,
                                  employee_name: `${emp.first_name || ''} ${emp.last_name || ''}`.trim() || emp.email?.split('@')[0] || 'Employee',
                                  employee_ctc: annualCTC,
                                  basic_salary: annualBasic,
                                  department: deptMap[emp.department] || emp.department || 'Engineering',
                                  role: roleMap[emp.role] || emp.role || 'employee',
                                  grade: gradeMap[emp.level] || 'L3',
                                  location: locationMap[emp.city] || 'bangalore'
                                });
                                setTestResult(null);
                              }
                            }
                          }}
                        >
                          <SelectTrigger className={`h-9 mt-2 ${isDark ? 'bg-zinc-900 border-zinc-600' : ''}`}>
                            <SelectValue placeholder="Select employee to auto-fill..." />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="manual">✏️ Enter manually</SelectItem>
                            {(employeesList || []).map(emp => (
                              <SelectItem key={emp.id || emp.employee_id} value={emp.id || emp.employee_id}>
                                {emp.employee_id} - {emp.first_name} {emp.last_name} ({emp.department}, ₹{((emp.gross_salary || emp.salary || 0) * 12).toLocaleString('en-IN')}/yr)
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      
                      {/* Employee Details - Now with inherited values */}
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <Label className="text-xs">Employee Name</Label>
                          <Input
                            value={testRuleData.employee_name}
                            onChange={(e) => setTestRuleData({...testRuleData, employee_name: e.target.value})}
                            placeholder="e.g., Rahul Sharma"
                            className={`h-8 text-sm ${isDark ? 'bg-zinc-800 border-zinc-600' : ''}`}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Annual Gross CTC (₹)</Label>
                          <Input
                            type="number"
                            value={testRuleData.employee_ctc}
                            onChange={(e) => {
                              const ctc = parseFloat(e.target.value) || 0;
                              setTestRuleData({
                                ...testRuleData, 
                                employee_ctc: ctc,
                                basic_salary: Math.round(ctc * 0.4)  // Auto-calculate basic as 40%
                              });
                            }}
                            className={`h-8 text-sm ${isDark ? 'bg-zinc-800 border-zinc-600' : ''}`}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Basic Salary (₹/year)</Label>
                          <Input
                            type="number"
                            value={testRuleData.basic_salary}
                            onChange={(e) => setTestRuleData({...testRuleData, basic_salary: parseFloat(e.target.value) || 0})}
                            className={`h-8 text-sm ${isDark ? 'bg-zinc-800 border-zinc-600' : ''}`}
                          />
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-4 gap-3">
                        <div>
                          <Label className="text-xs">Department</Label>
                          <Select
                            value={testRuleData.department}
                            onValueChange={(val) => setTestRuleData({...testRuleData, department: val})}
                          >
                            <SelectTrigger className={`h-8 text-sm ${isDark ? 'bg-zinc-800 border-zinc-600' : ''}`}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {(APPLIES_TO_OPTIONS?.departments || []).map(d => (
                                <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs">Role</Label>
                          <Select
                            value={testRuleData.role}
                            onValueChange={(val) => setTestRuleData({...testRuleData, role: val})}
                          >
                            <SelectTrigger className={`h-8 text-sm ${isDark ? 'bg-zinc-800 border-zinc-600' : ''}`}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {(APPLIES_TO_OPTIONS?.roles || []).map(r => (
                                <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs">Grade</Label>
                          <Select
                            value={testRuleData.grade}
                            onValueChange={(val) => setTestRuleData({...testRuleData, grade: val})}
                          >
                            <SelectTrigger className={`h-8 text-sm ${isDark ? 'bg-zinc-800 border-zinc-600' : ''}`}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {(APPLIES_TO_OPTIONS?.grades || []).map(g => (
                                <SelectItem key={g.value} value={g.value}>{g.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs">Location</Label>
                          <Select
                            value={testRuleData.location}
                            onValueChange={(val) => setTestRuleData({...testRuleData, location: val})}
                          >
                            <SelectTrigger className={`h-8 text-sm ${isDark ? 'bg-zinc-800 border-zinc-600' : ''}`}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {(APPLIES_TO_OPTIONS?.locations || []).map(l => (
                                <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      
                      {/* Scenario Input */}
                      <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-800 border border-zinc-700' : 'bg-white border border-zinc-200'}`}>
                        <Label className="text-xs font-medium">Test Scenario</Label>
                        <div className="grid grid-cols-2 gap-3 mt-2">
                          <div>
                            <Label className="text-xs text-zinc-500">
                              {editingRule.rule_type === 'limit' && 'Amount/Value to Test'}
                              {editingRule.rule_type === 'threshold' && 'Value to Check Against Threshold'}
                              {editingRule.rule_type === 'formula' && 'Days/Value for Calculation'}
                              {editingRule.rule_type === 'condition' && 'Scenario Value'}
                              {editingRule.rule_type === 'approval' && 'Claim Amount'}
                            </Label>
                            <Input
                              type="number"
                              value={testRuleData.scenario_value}
                              onChange={(e) => setTestRuleData({...testRuleData, scenario_value: parseFloat(e.target.value) || 0})}
                              placeholder={
                                editingRule.rule_type === 'limit' ? 'e.g., 15000 (expense amount)' :
                                editingRule.rule_type === 'threshold' ? 'e.g., 4 (late arrivals)' :
                                editingRule.rule_type === 'formula' ? 'e.g., 3 (LOP days)' :
                                'Enter value'
                              }
                              className={`h-8 text-sm ${isDark ? 'bg-zinc-900 border-zinc-600' : ''}`}
                            />
                          </div>
                          <div className="flex items-end">
                            <Button
                              onClick={() => {
                                // Calculate test result based on rule type
                                const basicMonthly = testRuleData.basic_salary / 12;
                                const basicDaily = testRuleData.basic_salary / 365;
                                // LOP uses Gross CTC, not Basic
                                const grossMonthly = testRuleData.employee_ctc / 12;
                                const grossDaily = grossMonthly / 30;  // 30 days in a month for LOP
                                const ruleValue = editingRule.numeric_value || 0;
                                const testValue = testRuleData.scenario_value;
                                
                                let result = {
                                  passed: false,
                                  message: '',
                                  impact: '',
                                  calculation: ''
                                };
                                
                                if (editingRule.rule_type === 'limit') {
                                  result.passed = testValue <= ruleValue;
                                  result.message = result.passed 
                                    ? `✅ APPROVED - ₹${testValue.toLocaleString('en-IN')} is within limit of ₹${ruleValue.toLocaleString('en-IN')}`
                                    : `❌ REJECTED - ₹${testValue.toLocaleString('en-IN')} exceeds limit of ₹${ruleValue.toLocaleString('en-IN')} by ₹${(testValue - ruleValue).toLocaleString('en-IN')}`;
                                  result.impact = result.passed 
                                    ? `₹${testValue.toLocaleString('en-IN')} will be added to reimbursements`
                                    : 'No payroll impact - claim rejected';
                                }
                                else if (editingRule.rule_type === 'threshold') {
                                  result.passed = testValue <= ruleValue;
                                  const excessCount = Math.max(0, testValue - ruleValue);
                                  const penalty = Math.round(grossDaily * 0.5 * excessCount);
                                  result.message = result.passed
                                    ? `✅ WITHIN THRESHOLD - ${testValue} is within allowed ${ruleValue}`
                                    : `⚠️ THRESHOLD EXCEEDED - ${testValue} exceeds ${ruleValue} by ${excessCount}`;
                                  result.impact = result.passed
                                    ? 'No penalty applied'
                                    : `Penalty: ₹${penalty.toLocaleString('en-IN')} (${excessCount} × 0.5 day LOP × ₹${Math.round(grossDaily).toLocaleString('en-IN')}/day)`;
                                }
                                else if (editingRule.rule_type === 'formula') {
                                  const pfAmount = Math.round(basicMonthly * 0.12);
                                  // LOP = Gross CTC / 30 days * LOP days
                                  const lopDeduction = Math.round(grossDaily * testValue);
                                  result.passed = true;
                                  result.message = `📊 FORMULA CALCULATED`;
                                  result.calculation = editingRule.value?.includes('lop') || editingRule.value?.includes('LOP') || editingRule.value?.includes('gross')
                                    ? `(₹${Math.round(grossMonthly).toLocaleString('en-IN')} / 30) × ${testValue} days = ₹${lopDeduction.toLocaleString('en-IN')}`
                                    : `₹${Math.round(basicMonthly).toLocaleString('en-IN')} × 12% = ₹${pfAmount.toLocaleString('en-IN')}/month`;
                                  result.impact = editingRule.value?.includes('lop') || editingRule.value?.includes('gross')
                                    ? `LOP Deduction: ₹${lopDeduction.toLocaleString('en-IN')} from gross salary`
                                    : `PF: Employee -₹${pfAmount.toLocaleString('en-IN')} | Employer +₹${pfAmount.toLocaleString('en-IN')}`;
                                }
                                else if (editingRule.rule_type === 'condition') {
                                  // Check if employee matches condition
                                  const matchesDept = !editingRule.applies_to?.scope_value || editingRule.applies_to.scope_value === testRuleData.department;
                                  const matchesRole = !editingRule.applies_to?.scope_value || editingRule.applies_to.scope_value === testRuleData.role;
                                  result.passed = matchesDept && matchesRole;
                                  result.message = result.passed
                                    ? `✅ CONDITION MET - Rule applies to this employee`
                                    : `⚠️ CONDITION NOT MET - Rule does not apply`;
                                  result.impact = result.passed
                                    ? 'Employee is eligible for this rule/benefit'
                                    : 'Standard policy applies instead';
                                }
                                else if (editingRule.rule_type === 'approval') {
                                  result.passed = true;
                                  result.message = `🔄 APPROVAL REQUIRED`;
                                  result.impact = editingRule.value?.includes('self') || editingRule.value?.includes('no_self')
                                    ? `${testRuleData.employee_name || 'Employee'} cannot self-approve. Routed to: Manager/HR`
                                    : `Claim of ₹${testValue.toLocaleString('en-IN')} requires ${editingRule.value?.replace(/_/g, ' ') || 'manager'} approval`;
                                }
                                
                                setTestResult(result);
                              }}
                              className="bg-amber-600 hover:bg-amber-700 text-white h-8"
                              size="sm"
                            >
                              <Calculator className="w-4 h-4 mr-1" />
                              Calculate Impact
                            </Button>
                          </div>
                        </div>
                      </div>
                      
                      {/* Test Result */}
                      {testResult && (
                        <div className={`p-4 rounded-lg ${
                          testResult.passed 
                            ? isDark ? 'bg-emerald-900/30 border border-emerald-700' : 'bg-emerald-50 border border-emerald-200'
                            : isDark ? 'bg-red-900/30 border border-red-700' : 'bg-red-50 border border-red-200'
                        }`}>
                          <div className="space-y-2">
                            <p className={`font-semibold ${testResult.passed ? 'text-emerald-600' : 'text-red-600'}`}>
                              {testResult.message}
                            </p>
                            {testResult.calculation && (
                              <p className={`text-sm font-mono ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                                Calculation: {testResult.calculation}
                              </p>
                            )}
                            <div className={`p-2 rounded ${isDark ? 'bg-zinc-800' : 'bg-white'}`}>
                              <p className="text-xs font-medium">Payroll Impact:</p>
                              <p className={`text-sm ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>{testResult.impact}</p>
                            </div>
                            <div className="flex items-center gap-2 pt-2 border-t border-zinc-200 dark:border-zinc-700">
                              <User className="w-4 h-4 text-zinc-400" />
                              <span className="text-xs text-zinc-500">
                                Testing for: <strong>{testRuleData.employee_name || 'Employee'}</strong> | 
                                CTC: ₹{testRuleData.employee_ctc.toLocaleString('en-IN')} | 
                                {testRuleData.department} | {testRuleData.role} | {testRuleData.grade}
                              </span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                
                {/* Apply Rule Button - Prominent after simulation */}
                <div className={`mt-4 p-4 rounded-lg ${isDark ? 'bg-emerald-900/30 border border-emerald-700' : 'bg-emerald-50 border border-emerald-200'}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className={`text-sm font-medium ${isDark ? 'text-emerald-300' : 'text-emerald-700'}`}>
                        Ready to apply this rule?
                      </p>
                      <p className={`text-xs ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>
                        The rule will be saved and applied immediately to {editingRule.applies_to?.scope_type === 'all_employees' ? 'all employees' : (editingRule.applies_to?.scope_value || 'selected scope')}.
                      </p>
                    </div>
                    <Button
                      onClick={handleSaveRule}
                      disabled={updateRuleMutation.isPending || addRuleMutation.isPending || !editingRule.rule_name}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white"
                      size="lg"
                    >
                      {(updateRuleMutation.isPending || addRuleMutation.isPending) ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <CheckCircle className="w-4 h-4 mr-2" />
                      )}
                      Apply Rule & Close
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <DialogFooter className="border-t pt-4">
            <Button variant="outline" onClick={() => setShowRuleDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveRule}
              disabled={updateRuleMutation.isPending || addRuleMutation.isPending || !editingRule?.rule_name}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              {(updateRuleMutation.isPending || addRuleMutation.isPending) ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              {editingRule?._isNew ? 'Add Rule' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Payroll Simulator Dialog */}
      <Dialog open={showSimulator} onOpenChange={setShowSimulator}>
        <DialogContent className={`max-w-4xl max-h-[90vh] overflow-y-auto ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Calculator className="w-5 h-5 text-emerald-500" />
              Payroll Simulator - Rule Engine
            </DialogTitle>
            <DialogDescription>
              Test payroll calculations with live rule evaluation. All business rules are applied automatically.
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid grid-cols-2 gap-6 py-4">
            {/* Input Section */}
            <div className="space-y-4">
              <h4 className="font-medium flex items-center gap-2">
                <Edit2 className="w-4 h-4" />
                Input Parameters
              </h4>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Annual CTC (₹)</Label>
                  <Input
                    type="number"
                    value={simulatorData.annual_ctc}
                    onChange={(e) => setSimulatorData({...simulatorData, annual_ctc: parseFloat(e.target.value) || 0})}
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
                <div>
                  <Label className="text-xs">Basic %</Label>
                  <Input
                    type="number"
                    value={simulatorData.basic_percentage}
                    onChange={(e) => setSimulatorData({...simulatorData, basic_percentage: parseFloat(e.target.value) || 40})}
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
                <div>
                  <Label className="text-xs">HRA %</Label>
                  <Input
                    type="number"
                    value={simulatorData.hra_percentage}
                    onChange={(e) => setSimulatorData({...simulatorData, hra_percentage: parseFloat(e.target.value) || 50})}
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
                <div>
                  <Label className="text-xs">Working Days</Label>
                  <Input
                    type="number"
                    value={simulatorData.working_days}
                    onChange={(e) => setSimulatorData({...simulatorData, working_days: parseInt(e.target.value) || 26})}
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
                <div>
                  <Label className="text-xs">Present Days</Label>
                  <Input
                    type="number"
                    value={simulatorData.present_days}
                    onChange={(e) => setSimulatorData({...simulatorData, present_days: parseInt(e.target.value) || 26})}
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
                <div>
                  <Label className="text-xs">LOP Days</Label>
                  <Input
                    type="number"
                    value={simulatorData.lop_days}
                    onChange={(e) => setSimulatorData({...simulatorData, lop_days: parseInt(e.target.value) || 0})}
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
                <div className="col-span-2">
                  <Label className="text-xs">Expense Reimbursement (₹)</Label>
                  <Input
                    type="number"
                    value={simulatorData.expense_reimbursement}
                    onChange={(e) => setSimulatorData({...simulatorData, expense_reimbursement: parseFloat(e.target.value) || 0})}
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
              </div>
              
              <Button
                onClick={async () => {
                  setSimulating(true);
                  try {
                    const res = await axios.post(`${API}/business-rules/engine/simulate-payroll`, simulatorData);
                    setSimulationResult(res.data);
                  } catch (err) {
                    toast.error(err.response?.data?.detail || 'Simulation failed');
                  } finally {
                    setSimulating(false);
                  }
                }}
                disabled={simulating}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
                data-testid="run-simulation-btn"
              >
                {simulating ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Calculator className="w-4 h-4 mr-2" />
                )}
                Run Simulation
              </Button>
            </div>
            
            {/* Results Section */}
            <div className="space-y-4">
              <h4 className="font-medium flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Calculation Results
              </h4>
              
              {simulationResult ? (
                <div className="space-y-3">
                  {/* Earnings */}
                  <div className={`p-3 rounded-lg ${isDark ? 'bg-emerald-900/20 border border-emerald-800' : 'bg-emerald-50 border border-emerald-200'}`}>
                    <h5 className="text-xs font-medium text-emerald-600 mb-2">EARNINGS</h5>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span>Basic Salary</span>
                        <span className="font-mono">₹{simulationResult.earnings?.basic_salary?.toLocaleString('en-IN')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>HRA</span>
                        <span className="font-mono">₹{simulationResult.earnings?.hra?.toLocaleString('en-IN')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Special Allowance</span>
                        <span className="font-mono">₹{simulationResult.earnings?.special_allowance?.toLocaleString('en-IN')}</span>
                      </div>
                      {simulationResult.earnings?.expense_reimbursement > 0 && (
                        <div className="flex justify-between">
                          <span>Expense Reimbursement</span>
                          <span className="font-mono">₹{simulationResult.earnings?.expense_reimbursement?.toLocaleString('en-IN')}</span>
                        </div>
                      )}
                      <div className="flex justify-between font-medium pt-1 border-t border-emerald-300">
                        <span>Total Earnings</span>
                        <span className="font-mono">₹{simulationResult.earnings?.total_earnings?.toLocaleString('en-IN')}</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Deductions */}
                  <div className={`p-3 rounded-lg ${isDark ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'}`}>
                    <h5 className="text-xs font-medium text-red-600 mb-2">DEDUCTIONS</h5>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span>PF (Employee)</span>
                        <span className="font-mono">₹{simulationResult.deductions?.pf_employee?.toLocaleString('en-IN')}</span>
                      </div>
                      {simulationResult.deductions?.esi_employee > 0 && (
                        <div className="flex justify-between">
                          <span>ESI (Employee)</span>
                          <span className="font-mono">₹{simulationResult.deductions?.esi_employee?.toLocaleString('en-IN')}</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span>Professional Tax</span>
                        <span className="font-mono">₹{simulationResult.deductions?.professional_tax?.toLocaleString('en-IN')}</span>
                      </div>
                      {simulationResult.deductions?.lop_deduction > 0 && (
                        <div className="flex justify-between text-red-600">
                          <span>LOP Deduction</span>
                          <span className="font-mono">₹{simulationResult.deductions?.lop_deduction?.toLocaleString('en-IN')}</span>
                        </div>
                      )}
                      <div className="flex justify-between font-medium pt-1 border-t border-red-300">
                        <span>Total Deductions</span>
                        <span className="font-mono">₹{simulationResult.deductions?.total_deductions?.toLocaleString('en-IN')}</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Employer Contributions */}
                  <div className={`p-3 rounded-lg ${isDark ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                    <h5 className="text-xs font-medium text-blue-600 mb-2">EMPLOYER CONTRIBUTIONS</h5>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span>PF (Employer)</span>
                        <span className="font-mono">₹{simulationResult.employer_contributions?.pf_employer?.toLocaleString('en-IN')}</span>
                      </div>
                      {simulationResult.employer_contributions?.esi_employer > 0 && (
                        <div className="flex justify-between">
                          <span>ESI (Employer)</span>
                          <span className="font-mono">₹{simulationResult.employer_contributions?.esi_employer?.toLocaleString('en-IN')}</span>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Summary */}
                  <div className={`p-4 rounded-lg ${isDark ? 'bg-zinc-900 border border-zinc-700' : 'bg-zinc-100 border border-zinc-200'}`}>
                    <div className="space-y-2">
                      <div className="flex justify-between text-lg font-bold">
                        <span>Net Salary</span>
                        <span className="text-emerald-600 font-mono">₹{simulationResult.summary?.net_salary?.toLocaleString('en-IN')}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>CTC (Monthly)</span>
                        <span className="font-mono">₹{simulationResult.summary?.cost_to_company_monthly?.toLocaleString('en-IN')}</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Rules Applied */}
                  {simulationResult.rules_applied?.length > 0 && (
                    <div className={`p-3 rounded-lg ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                      <h5 className="text-xs font-medium mb-2">Rules Applied</h5>
                      <div className="flex flex-wrap gap-1">
                        {(simulationResult?.rules_applied || []).map(rule => (
                          <Badge key={rule} variant="outline" className="text-xs">
                            {rule}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className={`p-8 rounded-lg text-center ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
                  <Calculator className="w-12 h-12 mx-auto mb-3 text-zinc-400" />
                  <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
                    Enter parameters and click "Run Simulation" to see calculated payroll
                  </p>
                </div>
              )}
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSimulator(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Override Dialog */}
      <Dialog open={showAddOverrideDialog} onOpenChange={setShowAddOverrideDialog}>
        <DialogContent className={`max-w-lg ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5 text-emerald-500" />
              Create Attendance Override
            </DialogTitle>
            <DialogDescription>
              Create custom attendance rules for specific roles or employees
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Override Type */}
            <div>
              <Label className="mb-2 block">Override Type</Label>
              <div className="flex gap-2">
                <Button
                  variant={newOverride.scope === 'role' ? 'default' : 'outline'}
                  onClick={() => setNewOverride({ ...newOverride, scope: 'role', scope_value: '' })}
                  className={newOverride.scope === 'role' ? 'bg-emerald-600' : ''}
                  data-testid="override-type-role"
                >
                  <Briefcase className="w-4 h-4 mr-2" />
                  Role-wise
                </Button>
                <Button
                  variant={newOverride.scope === 'employee' ? 'default' : 'outline'}
                  onClick={() => setNewOverride({ ...newOverride, scope: 'employee', scope_value: '' })}
                  className={newOverride.scope === 'employee' ? 'bg-emerald-600' : ''}
                  data-testid="override-type-employee"
                >
                  <User className="w-4 h-4 mr-2" />
                  Employee-wise
                </Button>
              </div>
            </div>
            
            {/* Select Role or Employee */}
            {newOverride.scope === 'role' ? (
              <div>
                <Label className="mb-2 block">Select Role</Label>
                <Select
                  value={newOverride.scope_value}
                  onValueChange={(val) => setNewOverride({ ...newOverride, scope_value: val })}
                >
                  <SelectTrigger className={isDark ? 'bg-zinc-900 border-zinc-700' : ''} data-testid="override-role-select">
                    <SelectValue placeholder="Select a role..." />
                  </SelectTrigger>
                  <SelectContent>
                    {(APPLIES_TO_OPTIONS?.roles || []).map(role => (
                      <SelectItem key={role.value} value={role.value}>{role.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : (
              <div>
                <Label className="mb-2 block">Select Employee</Label>
                <Select
                  value={newOverride.scope_value}
                  onValueChange={(val) => setNewOverride({ ...newOverride, scope_value: val })}
                >
                  <SelectTrigger className={isDark ? 'bg-zinc-900 border-zinc-700' : ''} data-testid="override-employee-select">
                    <SelectValue placeholder="Select an employee..." />
                  </SelectTrigger>
                  <SelectContent className="max-h-60">
                    {(employeesList || []).map(emp => (
                      <SelectItem key={emp.id} value={emp.id}>
                        {emp.employee_id} - {emp.first_name} {emp.last_name} ({emp.department || '-'})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            
            {/* Working Days */}
            <div>
              <Label className="mb-2 block">Working Days (leave empty to inherit)</Label>
              <div className="flex flex-wrap gap-2">
                {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map(day => {
                  const isSelected = newOverride.working_days?.includes(day);
                  return (
                    <button
                      key={day}
                      type="button"
                      onClick={() => toggleOverrideWorkingDay(day)}
                      className={`px-3 py-1 rounded text-sm transition-all ${
                        isSelected
                          ? 'bg-emerald-600 text-white'
                          : isDark 
                            ? 'bg-zinc-700 text-zinc-400 hover:bg-zinc-600' 
                            : 'bg-zinc-100 text-zinc-500 hover:bg-zinc-200'
                      }`}
                    >
                      {day.slice(0, 3)}
                    </button>
                  );
                })}
              </div>
            </div>
            
            {/* Core Hours */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-2 block">Core Hours Start</Label>
                <Select
                  value={newOverride.core_hours_start}
                  onValueChange={(val) => setNewOverride({ ...newOverride, core_hours_start: val })}
                >
                  <SelectTrigger className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {['08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '12:00'].map(time => (
                      <SelectItem key={time} value={time}>{time}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label className="mb-2 block">Core Hours End</Label>
                <Select
                  value={newOverride.core_hours_end}
                  onValueChange={(val) => setNewOverride({ ...newOverride, core_hours_end: val })}
                >
                  <SelectTrigger className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {['16:00', '16:30', '17:00', '17:30', '18:00', '18:30', '19:00', '19:30', '20:00', '20:30', '21:00'].map(time => (
                      <SelectItem key={time} value={time}>{time}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            {/* Grace & WFH */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="mb-2 block">Grace Period (mins)</Label>
                <Input
                  type="number"
                  value={newOverride.grace_period_minutes}
                  onChange={(e) => setNewOverride({ ...newOverride, grace_period_minutes: parseInt(e.target.value) || 0 })}
                  className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  min={0}
                  max={60}
                />
              </div>
              
              <div>
                <Label className="mb-2 block">WFH Days/Week</Label>
                <Input
                  type="number"
                  value={newOverride.wfh_days_per_week}
                  onChange={(e) => setNewOverride({ ...newOverride, wfh_days_per_week: parseInt(e.target.value) || 0 })}
                  className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  min={0}
                  max={7}
                />
              </div>
            </div>
            
            {/* Reason */}
            <div>
              <Label className="mb-2 block">Reason for Override</Label>
              <Input
                value={newOverride.reason}
                onChange={(e) => setNewOverride({ ...newOverride, reason: e.target.value })}
                placeholder="e.g., Consulting role with flexible schedule"
                className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddOverrideDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleCreateOverride}
              className="bg-emerald-600 hover:bg-emerald-700"
              data-testid="create-override-btn"
            >
              Create Override
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* SOP Detail Modal */}
      <SOPDetailModal 
        isOpen={showSOPModal}
        onClose={setShowSOPModal}
        policyType={selectedSOPType}
        isDark={isDark}
      />
    </div>
  );
};

export default BusinessRules;
