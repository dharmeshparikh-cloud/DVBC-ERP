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
      { area: 'Payroll', impact: 'Indirect', description: 'LOP deductions and encashment affect monthly salary' },
      { area: 'F&F Settlement', impact: 'Direct', description: 'Encashable leaves are paid out during exit' }
    ],
    sop: {
      title: 'Leave Policy Configuration SOP',
      sections: [
        {
          heading: 'Before Making Changes',
          checklist: [
            'Review current leave utilization reports',
            'Check if change affects mid-year employees (pro-rata impact)',
            'Notify Finance if encashment rules are changing',
            'Document reason for policy change'
          ]
        },
        {
          heading: 'Configuration Steps',
          checklist: [
            'Select the specific leave type rule (LV001-LV012)',
            'Update the numeric value (days/percentage)',
            'Toggle rule enabled/disabled as needed',
            'Save changes - takes effect immediately'
          ]
        },
        {
          heading: 'After Changes',
          checklist: [
            'Verify in Payroll Simulator with sample employee',
            'Announce policy update via company communication',
            'Update employee handbook if applicable',
            'Monitor leave applications for next 30 days'
          ]
        }
      ],
      warnings: [
        'Reducing leave quota mid-year may cause negative balances',
        'Disabling encashment affects employees planning resignation',
        'Sandwich policy changes can surprise employees on long leaves'
      ],
      bestPractices: [
        'Change policies effective from next financial year',
        'Allow 30-day grace period for existing applications',
        'Keep minimum 6 sick leaves for employee welfare'
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
      { area: 'Budget', impact: 'Indirect', description: 'Higher limits increase travel cost budgets' }
    ],
    sop: {
      title: 'Travel Policy Configuration SOP',
      sections: [
        {
          heading: 'Understanding Travel Rules',
          checklist: [
            'TR001-TR003: Daily allowances (food, incidentals)',
            'TR004-TR005: Hotel and flight class rules',
            'TR006-TR007: Advance and settlement processes',
            'TR008-TR010: Conveyance and local travel'
          ]
        },
        {
          heading: 'Before Making Changes',
          checklist: [
            'Review current travel expense reports',
            'Compare with industry standards',
            'Check pending travel requests that may be affected',
            'Inform Sales/Consulting teams about upcoming changes'
          ]
        },
        {
          heading: 'Configuration Steps',
          checklist: [
            'Select travel rule to modify',
            'Update limit values (daily/per-trip)',
            'Review conditions (metro vs non-metro)',
            'Save - applies to NEW travel requests only'
          ]
        }
      ],
      warnings: [
        'Lowering limits may cause employees to pay out-of-pocket',
        'Strict limits can affect client meeting quality',
        'Settlement deadline changes need advance notice'
      ],
      bestPractices: [
        'Review travel limits annually against inflation',
        'Allow exceptions for client-facing roles',
        'Metro cities: Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad'
      ]
    }
  },
  expense: {
    title: 'Expense Policy Management',
    summary: 'Defines expense claim rules, approval thresholds, and receipt requirements. Ensures compliance and fraud prevention.',
    icon: Receipt,
    quickTips: [
      'Self-approval prevention (Code I52) is mandatory',
      'Receipt required for claims above threshold',
      'Cutoff date affects which payroll cycle includes reimbursement'
    ],
    impacts: [
      { area: 'Expense Approvals', impact: 'Direct', description: 'Threshold changes affect approval routing' },
      { area: 'Payroll', impact: 'Direct', description: 'Approved expenses go to designated payroll period' },
      { area: 'Audit Compliance', impact: 'Critical', description: 'Receipt rules ensure audit readiness' }
    ],
    sop: {
      title: 'Expense Policy Configuration SOP',
      sections: [
        {
          heading: 'Critical Rules (Do Not Disable)',
          checklist: [
            'EX001: Self-approval prevention - MANDATORY for compliance',
            'EX002: Receipt threshold - Required for audit',
            'EX003: Cutoff dates - Affects payroll accuracy'
          ]
        },
        {
          heading: 'Configurable Rules',
          checklist: [
            'EX004: Maximum single expense limit',
            'EX005: Monthly expense ceiling per employee',
            'EX006: Meal/Entertainment limits'
          ]
        },
        {
          heading: 'Impact on Finance',
          checklist: [
            'Cutoff date (15th) - expenses after this go to next month',
            'Receipt threshold affects documentation workload',
            'Limits affect cash flow forecasting'
          ]
        }
      ],
      warnings: [
        'NEVER disable self-approval prevention (audit failure risk)',
        'Raising limits significantly may enable fraud',
        'Removing receipt requirements risks audit findings'
      ],
      bestPractices: [
        'Review expense patterns quarterly',
        'Keep receipt threshold at Rs.500 or lower',
        'Cutoff on 15th aligns with standard payroll cycles'
      ]
    }
  },
  attendance: {
    title: 'Attendance Policy Management',
    summary: 'Governs work hours, WFH policies, late penalties, and overtime rules. Affects payroll calculations.',
    icon: Clock,
    quickTips: [
      'Core hours define mandatory office presence',
      'Late threshold triggers penalty after 3 incidents',
      'Overtime must be pre-approved by manager'
    ],
    impacts: [
      { area: 'Salary Calculation', impact: 'Direct', description: 'Late penalties and LOP deductions affect net pay' },
      { area: 'Employee Flexibility', impact: 'High', description: 'WFH and flexi-time rules affect work-life balance' },
      { area: 'Compliance', impact: 'Moderate', description: 'Overtime rules must comply with labor laws' }
    ],
    sop: {
      title: 'Attendance Policy Configuration SOP',
      sections: [
        {
          heading: 'Work Hours Configuration',
          checklist: [
            'AT001: Standard work hours (typically 8-9 hours)',
            'AT002: Core hours window (e.g., 10AM-4PM)',
            'AT003: Break duration allowance',
            'AT004: Overtime calculation method'
          ]
        },
        {
          heading: 'Flexibility Rules',
          checklist: [
            'AT005: WFH days per week/month',
            'AT006: Flexi-time grace period',
            'AT007: Comp-off accrual rules',
            'AT008: Half-day definitions'
          ]
        },
        {
          heading: 'Penalty Configuration',
          checklist: [
            'Late arrival threshold (minutes)',
            'Number of incidents before penalty',
            'Penalty amount or leave deduction',
            'Reset period (monthly/quarterly)'
          ]
        }
      ],
      warnings: [
        'Strict late penalties may affect morale',
        'Overtime rules must comply with Shops & Establishment Act',
        'WFH restrictions should consider role requirements'
      ],
      bestPractices: [
        'Allow 15-minute grace period for late arrivals',
        'Cap overtime at 48 hours/month (legal limit)',
        'Hybrid WFH (2-3 days) balances productivity & flexibility'
      ]
    }
  },
  payroll: {
    title: 'Payroll Rules Management',
    summary: 'CRITICAL: Defines statutory compliance (PF, ESI, PT) and salary processing rules. CTC Designer handles actual calculations.',
    icon: DollarSign,
    quickTips: [
      'PF/ESI thresholds are statutory - consult CTC Designer for changes',
      'Processing dates affect when employees receive salary',
      'Tax calculation uses government-mandated slabs'
    ],
    impacts: [
      { area: 'Salary Processing', impact: 'Critical', description: 'Processing dates determine pay day' },
      { area: 'Statutory Compliance', impact: 'Critical', description: 'PF/ESI rules are government mandated' },
      { area: 'Tax Filing', impact: 'High', description: 'TDS calculation affects Form 16 accuracy' }
    ],
    sop: {
      title: 'Payroll Rules Configuration SOP',
      sections: [
        {
          heading: 'IMPORTANT: CTC Designer vs Business Rules',
          checklist: [
            'Business Rules: Display reference thresholds only',
            'CTC Designer: ACTUAL salary component calculations',
            'Never use Business Rules to override statutory compliance',
            'All PF/ESI calculations are in CTC Designer'
          ]
        },
        {
          heading: 'Safe to Configure Here',
          checklist: [
            'PY001: Payroll processing date (typically 25th-30th)',
            'PY002: Pay slip generation date',
            'PY003: Reimbursement inclusion cutoff'
          ]
        },
        {
          heading: 'View Only (Reference)',
          checklist: [
            'PY004-PY010: PF/ESI thresholds for reference',
            'These are statutory and auto-calculated',
            'Use CTC Designer to see actual deductions'
          ]
        }
      ],
      warnings: [
        'DO NOT modify PF/ESI rules - they are statutory',
        'Payroll date changes affect employee financial planning',
        'Tax rules are set by government - not configurable'
      ],
      bestPractices: [
        'Process payroll by 28th to allow bank processing time',
        'Generate pay slips within 5 days of salary credit',
        'Use Payroll Simulator to verify calculations'
      ]
    }
  },
  general: {
    title: 'General HR Policies',
    summary: 'Covers probation, notice periods, increment cycles, and general employment terms.',
    icon: FileText,
    quickTips: [
      'Probation period affects confirmation and benefits eligibility',
      'Notice period is enforced during resignation',
      'Increment month sets annual appraisal cycle'
    ],
    impacts: [
      { area: 'Onboarding', impact: 'High', description: 'Probation rules affect new employee benefits' },
      { area: 'Exit Process', impact: 'High', description: 'Notice period determines last working day' },
      { area: 'Compensation', impact: 'Moderate', description: 'Increment month affects salary revision timing' }
    ],
    sop: {
      title: 'General HR Policy Configuration SOP',
      sections: [
        {
          heading: 'Employment Terms',
          checklist: [
            'GH001: Standard probation period (typically 3-6 months)',
            'GH002: Notice period for resignation',
            'GH003: Notice period for termination',
            'GH004: Retirement age'
          ]
        },
        {
          heading: 'Performance & Compensation',
          checklist: [
            'GH005: Annual increment month (typically April)',
            'GH006: Performance review frequency',
            'GH007: Confirmation criteria',
            'GH008: Extension rules for probation'
          ]
        },
        {
          heading: 'Workplace Policies',
          checklist: [
            'Dress code guidelines',
            'Code of conduct reference',
            'Reporting structure rules',
            'Communication protocols'
          ]
        }
      ],
      warnings: [
        'Changing notice period affects current employees',
        'Probation extension needs proper documentation',
        'Retirement age must comply with company policy'
      ],
      bestPractices: [
        '90 days notice for senior roles, 30 days for others',
        '6-month probation provides adequate evaluation time',
        'April increment aligns with financial year'
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
      <DialogContent className={`max-w-3xl max-h-[85vh] overflow-y-auto ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${POLICY_TYPE_COLORS[policyType]?.split(' ')[0]}`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <span>{sopData.sop.title}</span>
              <p className={`text-sm font-normal mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                Standard Operating Procedure & Impact Analysis
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
              {sopData.impacts.map((item, idx) => (
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
          
          {/* SOP Sections with Checklists */}
          <Accordion type="multiple" className="w-full" defaultValue={['section-0']}>
            {sopData.sop.sections.map((section, idx) => (
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
                    {section.checklist.map((item, itemIdx) => (
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
          
          {/* Warnings */}
          <div className={`p-4 rounded-lg ${isDark ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'}`}>
            <h4 className="font-semibold flex items-center gap-2 mb-3 text-red-600">
              <AlertCircle className="w-4 h-4" />
              Warnings & Cautions
            </h4>
            <ul className="space-y-2">
              {sopData.sop.warnings.map((warning, idx) => (
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
              {sopData.sop.bestPractices.map((practice, idx) => (
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
              {sopData.quickTips.map((tip, idx) => (
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
  
  // Filter policies
  const filteredPolicies = policies.filter(p => {
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
  const policiesByType = policies.reduce((acc, p) => {
    if (!acc[p.policy_type]) acc[p.policy_type] = [];
    acc[p.policy_type].push(p);
    return acc;
  }, {});
  
  const handleEditRule = (policy, rule) => {
    setSelectedPolicy(policy);
    setEditingRule({ ...rule });
    setShowRuleDialog(true);
  };
  
  const handleSaveRule = () => {
    if (!selectedPolicy || !editingRule) return;
    updateRuleMutation.mutate({
      policyId: selectedPolicy.id,
      ruleId: editingRule.rule_id,
      ruleData: editingRule
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
      const entries = Object.entries(conditions);
      if (entries.length === 0) return null;
      
      // Check for slab-based conditions (like Professional Tax)
      if (entries.some(([k]) => k.startsWith('slab'))) {
        return entries.filter(([k]) => k.startsWith('slab')).map(([key, val]) => {
          if (typeof val === 'object' && val.min !== undefined) {
            return `WHEN ₹${val.min?.toLocaleString('en-IN') || 0} - ₹${val.max?.toLocaleString('en-IN') || '∞'} THEN ₹${val.tax || 0}`;
          }
          return `${key}: ${JSON.stringify(val)}`;
        }).join(' | ');
      }
      
      // Check for formula conditions - show prominently for FORMULA type
      if (conditions.formula) {
        const otherConditions = entries.filter(([k]) => k !== 'formula');
        let result = `FORMULA: ${conditions.formula}`;
        if (otherConditions.length > 0) {
          result += ' | ' + otherConditions.map(([k, v]) => `${k}=${v}`).join(', ');
        }
        return result;
      }
      
      // Format as key=value pairs with AND
      return entries.map(([key, val]) => {
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
              <h4 className="font-medium flex items-center gap-2">
                <Settings className="w-4 h-4" />
                Policy Rules ({totalRules})
              </h4>
              {policy.rules?.map((rule, idx) => renderRuleCard(policy, rule, idx))}
            </div>
            
            {/* Payroll Integration Info */}
            {policy.payroll_integration && Object.keys(policy.payroll_integration).length > 0 && (
              <div className={`mt-4 p-3 rounded-lg ${isDark ? 'bg-emerald-900/20 border border-emerald-800' : 'bg-emerald-50 border border-emerald-200'}`}>
                <h5 className="font-medium text-emerald-700 dark:text-emerald-400 flex items-center gap-2 mb-2">
                  <IndianRupee className="w-4 h-4" />
                  Payroll Integration
                </h5>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(policy.payroll_integration).map(([key, value]) => (
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
            {policy.ctc_linkage && Object.keys(policy.ctc_linkage).length > 0 && (
              <div className={`mt-4 p-3 rounded-lg ${isDark ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                <h5 className="font-medium text-blue-700 dark:text-blue-400 flex items-center gap-2 mb-2">
                  <Calculator className="w-4 h-4" />
                  CTC Component Linkage
                </h5>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(policy.ctc_linkage).map(([key, value]) => (
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
                  {POLICY_SOP_DATA[activeTab].quickTips.map((tip, idx) => (
                    <div key={idx} className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 ${isDark ? 'bg-zinc-700 text-zinc-300' : 'bg-zinc-100 text-zinc-600'}`}>
                      <Lightbulb className="w-3 h-3 text-amber-500" />
                      {tip}
                    </div>
                  ))}
                </div>
                
                {/* Impact Badges */}
                <div className="mt-3 flex items-center gap-3">
                  <span className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>Impacts:</span>
                  {POLICY_SOP_DATA[activeTab].impacts.map((impact, idx) => (
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
          const totalRules = policyList.reduce((sum, p) => sum + (p.rules?.length || 0), 0);
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
          filteredPolicies.map(policy => renderPolicyCard(policy))
        )}
      </div>
      
      {/* Edit Rule Dialog */}
      <Dialog open={showRuleDialog} onOpenChange={setShowRuleDialog}>
        <DialogContent className={`max-w-lg ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit2 className="w-5 h-5" />
              Edit Rule: {editingRule?.rule_name}
            </DialogTitle>
            <DialogDescription>
              Modify the rule configuration. Changes will take effect immediately.
            </DialogDescription>
          </DialogHeader>
          
          {editingRule && (
            <div className="space-y-4 py-4">
              <div>
                <Label>Rule Name</Label>
                <Input
                  value={editingRule.rule_name || ''}
                  onChange={(e) => setEditingRule({...editingRule, rule_name: e.target.value})}
                  className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                />
              </div>
              
              <div>
                <Label>Description</Label>
                <Input
                  value={editingRule.description || ''}
                  onChange={(e) => setEditingRule({...editingRule, description: e.target.value})}
                  className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Numeric Value</Label>
                  <Input
                    type="number"
                    value={editingRule.numeric_value || ''}
                    onChange={(e) => setEditingRule({...editingRule, numeric_value: parseFloat(e.target.value) || null})}
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
                <div>
                  <Label>Unit</Label>
                  <Input
                    value={editingRule.unit || ''}
                    onChange={(e) => setEditingRule({...editingRule, unit: e.target.value})}
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
              </div>
              
              <div>
                <Label>String Value</Label>
                <Input
                  value={editingRule.value || ''}
                  onChange={(e) => setEditingRule({...editingRule, value: e.target.value})}
                  className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                />
              </div>
              
              <div className="flex items-center gap-2">
                <Switch
                  checked={editingRule.is_enabled}
                  onCheckedChange={(checked) => setEditingRule({...editingRule, is_enabled: checked})}
                />
                <Label>Rule Enabled</Label>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRuleDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveRule}
              disabled={updateRuleMutation.isPending}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              {updateRuleMutation.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              Save Changes
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
                        {simulationResult.rules_applied.map(rule => (
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
