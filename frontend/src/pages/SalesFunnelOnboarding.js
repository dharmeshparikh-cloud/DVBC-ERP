import React, { useState, useEffect, useContext } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { Badge } from '../components/ui/badge';
import { 
  User, Calendar, DollarSign, FileText, Receipt, 
  FileCheck, CreditCard, Rocket, CheckCircle, 
  ChevronRight, ArrowLeft, Building2, Phone, Mail,
  Clock, AlertCircle, ExternalLink, Lock, Lightbulb,
  Circle, CheckCircle2, Info, AlertTriangle
} from 'lucide-react';
import { toast } from 'sonner';

// Complete 9-Step Sales Funnel
const FUNNEL_STEPS = [
  { 
    id: 'lead', 
    title: 'Lead Capture', 
    icon: User, 
    description: 'Review lead details and contact information',
    route: null,
    checkField: 'id'
  },
  { 
    id: 'meeting', 
    title: 'Record Meeting', 
    icon: Calendar, 
    description: 'Log meeting with client - date, attendees, MOM',
    route: '/sales-funnel/meeting/record',
    checkCollection: 'meeting_records'
  },
  { 
    id: 'pricing', 
    title: 'Pricing Plan', 
    icon: DollarSign, 
    description: 'Create investment plan with services and team',
    route: '/sales-funnel/pricing-plans',
    checkCollection: 'pricing_plans'
  },
  { 
    id: 'sow', 
    title: 'Scope of Work', 
    icon: FileText, 
    description: 'Define deliverables, milestones and scope items',
    route: '/sales-funnel/sow',
    checkCollection: 'enhanced_sow'
  },
  { 
    id: 'quotation', 
    title: 'Quotation', 
    icon: Receipt, 
    description: 'Generate proforma invoice with payment terms',
    route: '/sales-funnel/quotation',
    checkCollection: 'quotations'
  },
  { 
    id: 'agreement', 
    title: 'Agreement', 
    icon: FileCheck, 
    description: 'Create and sign consulting services contract',
    route: '/sales-funnel/agreement',
    checkCollection: 'agreements',
    checkStatus: 'signed'
  },
  { 
    id: 'payment', 
    title: 'Record Payment', 
    icon: CreditCard, 
    description: 'Log payment received - Cheque/NEFT/UPI',
    route: null,
    checkCollection: 'agreement_payments'
  },
  { 
    id: 'kickoff', 
    title: 'Kickoff Request', 
    icon: Rocket, 
    description: 'Submit for approval - assign PM, set start date',
    route: null,
    checkCollection: 'kickoff_requests'
  },
  { 
    id: 'complete', 
    title: 'Project Created', 
    icon: CheckCircle, 
    description: 'Kickoff approved - project and team assigned',
    route: null,
    checkCollection: 'projects'
  },
];

const SalesFunnelOnboarding = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');

  const [loading, setLoading] = useState(true);
  const [lead, setLead] = useState(null);
  const [funnelStatus, setFunnelStatus] = useState({});
  const [currentStep, setCurrentStep] = useState(0);
  const [checklist, setChecklist] = useState(null);
  const [showTips, setShowTips] = useState(false);

  useEffect(() => {
    if (leadId) {
      fetchFunnelData();
    }
  }, [leadId]);

  const fetchFunnelData = async () => {
    setLoading(true);
    try {
      const [leadRes, progressRes, checklistRes] = await Promise.all([
        axios.get(`${API}/leads/${leadId}`),
        axios.get(`${API}/leads/${leadId}/funnel-progress`),
        axios.get(`${API}/leads/${leadId}/funnel-checklist`)
      ]);
      
      setLead(leadRes.data);
      setFunnelStatus(progressRes.data);
      setChecklist(checklistRes.data);
      
      const completedSteps = progressRes.data.completed_steps || [];
      const lastCompleted = completedSteps.length > 0 ? 
        FUNNEL_STEPS.findIndex(s => s.id === completedSteps[completedSteps.length - 1]) : -1;
      setCurrentStep(Math.min(lastCompleted + 1, FUNNEL_STEPS.length - 1));
      
      // Save funnel draft position
      saveFunnelDraft(Math.min(lastCompleted + 1, FUNNEL_STEPS.length - 1));
      
    } catch (error) {
      console.error('Error fetching funnel data:', error);
      toast.error('Failed to load onboarding data');
    } finally {
      setLoading(false);
    }
  };

  // Save funnel position as draft
  const saveFunnelDraft = async (step) => {
    try {
      await axios.post(`${API}/leads/${leadId}/funnel-draft`, {
        current_step: FUNNEL_STEPS[step]?.id || 'lead_capture'
      });
    } catch (error) {
      console.error('Failed to save funnel draft:', error);
    }
  };

  // Get step checklist key mapping
  const getChecklistKey = (stepId) => {
    const mapping = {
      'lead': 'lead_capture',
      'meeting': 'record_meeting',
      'pricing': 'pricing_plan',
      'sow': 'scope_of_work',
      'quotation': 'quotation',
      'agreement': 'agreement',
      'payment': 'record_payment',
      'kickoff': 'kickoff_request',
      'complete': 'project_created'
    };
    return mapping[stepId] || stepId;
  };

  const isStepCompleted = (stepId) => {
    return funnelStatus.completed_steps?.includes(stepId) || false;
  };

  // Check if a step is blocked due to agreement status
  const isStepBlockedByAgreement = (stepId) => {
    // Steps that should be blocked if agreement is pending/rejected
    const blockedSteps = ['payment', 'kickoff', 'complete'];
    if (!blockedSteps.includes(stepId)) return false;
    return funnelStatus.is_blocked === true;
  };

  const isStepAccessible = (index) => {
    if (index === 0) return true;
    
    const stepId = FUNNEL_STEPS[index]?.id;
    
    // Check if step is blocked by agreement status
    if (isStepBlockedByAgreement(stepId)) {
      return false;
    }
    
    for (let i = 0; i < index; i++) {
      if (!isStepCompleted(FUNNEL_STEPS[i].id)) {
        return false;
      }
    }
    return true;
  };

  const handleStepClick = (index) => {
    const stepId = FUNNEL_STEPS[index]?.id;
    
    // Show specific message if blocked by agreement
    if (isStepBlockedByAgreement(stepId)) {
      toast.error(funnelStatus.blocked_reason || 'Agreement must be approved before proceeding');
      return;
    }
    
    if (!isStepAccessible(index)) {
      toast.error('Please complete previous steps first');
      return;
    }
    setCurrentStep(index);
  };

  const handleContinue = () => {
    const step = FUNNEL_STEPS[currentStep];
    
    // Check if trying to proceed past a blocked step
    if (funnelStatus.is_blocked && ['agreement', 'payment', 'kickoff'].includes(step.id)) {
      if (step.id === 'agreement') {
        // Allow viewing/editing agreement, but warn about status
        if (funnelStatus.agreement_status?.toLowerCase() === 'rejected') {
          toast.warning('Agreement was rejected. Please revise and resubmit.');
        } else if (['pending', 'draft', 'review'].includes(funnelStatus.agreement_status?.toLowerCase())) {
          toast.info('Agreement is pending approval. Continue to view/edit.');
        }
      } else {
        // Block navigation to payment/kickoff
        toast.error(funnelStatus.blocked_reason || 'Agreement must be approved first');
        return;
      }
    }
    
    
    if (step.route) {
      let route = step.route;
      if (step.id === 'meeting') {
        route = `${step.route}?leadId=${leadId}`;
      } else if (step.id === 'pricing') {
        route = `${step.route}?leadId=${leadId}`;
      } else if (step.id === 'sow' && funnelStatus.pricing_plan_id) {
        route = `${step.route}/${funnelStatus.pricing_plan_id}`;
      } else if (step.id === 'quotation' && funnelStatus.pricing_plan_id) {
        route = `/sales-funnel/quotation?pricingPlanId=${funnelStatus.pricing_plan_id}`;
      } else if (step.id === 'agreement' && funnelStatus.quotation_id) {
        route = `/sales-funnel/agreement?quotationId=${funnelStatus.quotation_id}`;
      }
      navigate(route);
    } else {
      if (step.id === 'payment' || step.id === 'kickoff') {
        if (funnelStatus.agreement_id) {
          navigate(`/client-onboarding?agreementId=${funnelStatus.agreement_id}&leadId=${leadId}`);
        } else {
          toast.error('Please complete Agreement step first');
        }
      } else if (step.id === 'complete') {
        if (funnelStatus.project_id) {
          navigate(`/projects/${funnelStatus.project_id}`);
        } else {
          toast.info('Project will be created after kickoff approval');
        }
      }
    }
  };

  const getStepDetails = (step) => {
    switch (step.id) {
      case 'lead':
        return lead ? {
          title: `${lead.first_name} ${lead.last_name}`,
          subtitle: lead.company,
          details: [
            { icon: Mail, value: lead.email },
            { icon: Phone, value: lead.phone },
            { icon: Building2, value: lead.company }
          ]
        } : null;
      case 'meeting':
        return funnelStatus.meeting_count > 0 ? {
          title: `${funnelStatus.meeting_count} Meeting(s) Recorded`,
          subtitle: `Last: ${funnelStatus.last_meeting_date || 'N/A'}`
        } : null;
      case 'pricing':
        return funnelStatus.pricing_plan_id ? {
          title: 'Pricing Plan Created',
          subtitle: `Total: ${formatCurrency(funnelStatus.pricing_plan_total)}`
        } : null;
      case 'sow':
        return funnelStatus.sow_id ? {
          title: 'SOW Created',
          subtitle: `${funnelStatus.sow_items_count || 0} scope items`
        } : null;
      case 'quotation':
        return funnelStatus.quotation_id ? {
          title: 'Quotation Generated',
          subtitle: `#${funnelStatus.quotation_number || 'N/A'}`
        } : null;
      case 'agreement':
        return funnelStatus.agreement_id ? {
          title: `Agreement ${funnelStatus.agreement_status || 'Draft'}`,
          subtitle: `#${funnelStatus.agreement_number || 'N/A'}`
        } : null;
      case 'payment':
        return funnelStatus.total_paid > 0 ? {
          title: `${formatCurrency(funnelStatus.total_paid)} Received`,
          subtitle: `${funnelStatus.payment_count || 0} payment(s)`
        } : null;
      case 'kickoff':
        return funnelStatus.kickoff_status ? {
          title: `Kickoff ${funnelStatus.kickoff_status}`,
          subtitle: funnelStatus.kickoff_status === 'accepted' ? 'Approved!' : 'Pending approval'
        } : null;
      case 'complete':
        return funnelStatus.project_id ? {
          title: 'Project Created',
          subtitle: funnelStatus.project_name || 'View Project'
        } : null;
      default:
        return null;
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount || 0);
  };

  const completedCount = funnelStatus.completed_steps?.length || 0;
  const progress = (completedCount / FUNNEL_STEPS.length) * 100;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-zinc-500">Loading onboarding data...</div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center">
        <AlertCircle className="w-16 h-16 text-amber-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">Lead Not Found</h2>
        <p className="text-zinc-500 mb-6">The lead could not be loaded.</p>
        <Button onClick={() => navigate('/leads')}>
          Go to Leads
        </Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950" data-testid="sales-funnel-onboarding">
      {/* Header */}
      <div className="bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Button
            onClick={() => navigate('/leads')}
            variant="ghost"
            size="sm"
            className="mb-3 -ml-2 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
            data-testid="back-to-leads-btn"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Leads
          </Button>
          
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
                Sales Funnel
              </h1>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                Complete all steps to onboard <span className="font-medium text-zinc-700 dark:text-zinc-300">{lead.company || `${lead.first_name} ${lead.last_name}`}</span>
              </p>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">Progress</p>
                <p className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                  {completedCount} of {FUNNEL_STEPS.length}
                </p>
              </div>
              <div className="w-32">
                <Progress value={progress} className="h-2" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - Two Column Layout */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex gap-6">
          {/* Left Sidebar - Steps List */}
          <div className="w-80 flex-shrink-0">
            <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden">
              <div className="p-4 border-b border-zinc-100 dark:border-zinc-800">
                <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wide">
                  Onboarding Steps
                </h3>
              </div>
              
              <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                {FUNNEL_STEPS.map((step, index) => {
                  const StepIcon = step.icon;
                  const isCompleted = isStepCompleted(step.id);
                  const isCurrent = index === currentStep;
                  const isAccessible = isStepAccessible(index);
                  
                  return (
                    <div
                      key={step.id}
                      onClick={() => handleStepClick(index)}
                      data-testid={`step-${step.id}`}
                      className={`p-4 cursor-pointer transition-all duration-200 ${
                        isCurrent 
                          ? 'bg-blue-50 dark:bg-blue-950/30 border-l-4 border-l-blue-500' 
                          : isCompleted 
                            ? 'bg-emerald-50/50 dark:bg-emerald-950/20 hover:bg-emerald-50 dark:hover:bg-emerald-950/30' 
                            : isAccessible
                              ? 'hover:bg-zinc-50 dark:hover:bg-zinc-800/50'
                              : 'opacity-50 cursor-not-allowed bg-zinc-50/50 dark:bg-zinc-800/30'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {/* Step Icon/Status */}
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                          isCompleted 
                            ? 'bg-emerald-500 text-white' 
                            : isCurrent 
                              ? 'bg-blue-500 text-white ring-4 ring-blue-100 dark:ring-blue-900' 
                              : isAccessible
                                ? 'bg-zinc-100 dark:bg-zinc-700 text-zinc-400 dark:text-zinc-500'
                                : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-300 dark:text-zinc-600'
                        }`}>
                          {isCompleted ? (
                            <CheckCircle className="w-4 h-4" />
                          ) : !isAccessible ? (
                            <Lock className="w-3.5 h-3.5" />
                          ) : (
                            <span className="text-xs font-semibold">{index + 1}</span>
                          )}
                        </div>
                        
                        {/* Step Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <StepIcon className={`w-4 h-4 flex-shrink-0 ${
                              isCurrent ? 'text-blue-600 dark:text-blue-400' : 
                              isCompleted ? 'text-emerald-600 dark:text-emerald-400' : 
                              'text-zinc-400 dark:text-zinc-500'
                            }`} />
                            <p className={`text-sm font-medium truncate ${
                              isCurrent ? 'text-blue-700 dark:text-blue-300' : 
                              isCompleted ? 'text-emerald-700 dark:text-emerald-300' : 
                              'text-zinc-700 dark:text-zinc-300'
                            }`}>
                              {step.title}
                            </p>
                          </div>
                          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 truncate">
                            {step.description}
                          </p>
                          
                          {/* Step Details if Completed */}
                          {isCompleted && (() => {
                            const details = getStepDetails(step);
                            return details ? (
                              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1 font-medium">
                                {details.title}
                              </p>
                            ) : null;
                          })()}
                        </div>
                        
                        {/* Arrow indicator for current step */}
                        {isCurrent && (
                          <ChevronRight className="w-4 h-4 text-blue-500 flex-shrink-0" />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Content Area */}
          <div className="flex-1">
            <Card className="border-zinc-200 dark:border-zinc-800 shadow-sm">
              <CardHeader className="border-b border-zinc-100 dark:border-zinc-800 bg-white dark:bg-zinc-900">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                    isStepCompleted(FUNNEL_STEPS[currentStep].id)
                      ? 'bg-emerald-100 dark:bg-emerald-900/30'
                      : 'bg-blue-100 dark:bg-blue-900/30'
                  }`}>
                    {React.createElement(FUNNEL_STEPS[currentStep].icon, {
                      className: `w-6 h-6 ${
                        isStepCompleted(FUNNEL_STEPS[currentStep].id) 
                          ? 'text-emerald-600 dark:text-emerald-400' 
                          : 'text-blue-600 dark:text-blue-400'
                      }`
                    })}
                  </div>
                  <div>
                    <CardTitle className="text-xl text-zinc-900 dark:text-zinc-100">
                      Step {currentStep + 1}: {FUNNEL_STEPS[currentStep].title}
                    </CardTitle>
                    <CardDescription className="text-zinc-500 dark:text-zinc-400">
                      {FUNNEL_STEPS[currentStep].description}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              
              <CardContent className="p-6 bg-white dark:bg-zinc-900">
                {/* Step Status Banner */}
                {isStepCompleted(FUNNEL_STEPS[currentStep].id) ? (
                  <div className="mb-6 p-4 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                    <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300 mb-1">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-semibold">Step Completed</span>
                    </div>
                    {(() => {
                      const details = getStepDetails(FUNNEL_STEPS[currentStep]);
                      return details ? (
                        <div className="text-sm text-emerald-600 dark:text-emerald-400 ml-7">
                          <p className="font-medium">{details.title}</p>
                          {details.subtitle && <p className="text-emerald-500">{details.subtitle}</p>}
                        </div>
                      ) : null;
                    })()}
                  </div>
                ) : (
                  <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg">
                    <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                      <Clock className="w-5 h-5" />
                      <span className="font-semibold">Pending - Action Required</span>
                    </div>
                  </div>
                )}

                {/* Agreement Blocking Banner */}
                {funnelStatus.is_blocked && (
                  <div className="mb-6 p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <div className="flex items-center gap-2 text-red-700 dark:text-red-300 mb-1">
                          <span className="font-semibold">Progress Blocked</span>
                          <Badge variant="destructive" className="text-xs">
                            Agreement {funnelStatus.agreement_status?.toUpperCase() || 'PENDING'}
                          </Badge>
                        </div>
                        <p className="text-sm text-red-600 dark:text-red-400">
                          {funnelStatus.blocked_reason}
                        </p>
                        {funnelStatus.agreement_id && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="mt-3 border-red-300 text-red-700 hover:bg-red-100 dark:border-red-700 dark:text-red-300 dark:hover:bg-red-900/30"
                            onClick={() => navigate(`/sales-funnel/agreement?id=${funnelStatus.agreement_id}`)}
                            data-testid="review-agreement-btn"
                          >
                            <FileCheck className="w-4 h-4 mr-2" />
                            Review Agreement
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Progress Checklist for Current Step */}
                {checklist && (
                  <div className="mb-6">
                    {(() => {
                      const stepKey = getChecklistKey(FUNNEL_STEPS[currentStep].id);
                      const stepChecklist = checklist[stepKey];
                      if (!stepChecklist) return null;
                      
                      const requirements = stepChecklist.requirements || [];
                      const tips = stepChecklist.tips || [];
                      const completedReqs = requirements.filter(r => r.completed).length;
                      const totalReqs = requirements.length;
                      const reqProgress = totalReqs > 0 ? (completedReqs / totalReqs) * 100 : 0;
                      
                      return (
                        <div className="bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <CheckCircle2 className="w-5 h-5 text-blue-500" />
                              <h4 className="font-semibold text-zinc-800 dark:text-zinc-200">
                                Completion Checklist
                              </h4>
                            </div>
                            <Badge 
                              variant={completedReqs === totalReqs ? "default" : "secondary"}
                              className={completedReqs === totalReqs ? "bg-emerald-500" : ""}
                            >
                              {completedReqs}/{totalReqs} Done
                            </Badge>
                          </div>
                          
                          {/* Progress Bar */}
                          <div className="mb-4">
                            <Progress value={reqProgress} className="h-2" />
                          </div>
                          
                          {/* Requirements List */}
                          <div className="space-y-2 mb-4">
                            {requirements.map((req, idx) => (
                              <div 
                                key={idx}
                                className={`flex items-center gap-2 text-sm ${
                                  req.completed 
                                    ? 'text-emerald-600 dark:text-emerald-400' 
                                    : 'text-zinc-600 dark:text-zinc-400'
                                }`}
                              >
                                {req.completed ? (
                                  <CheckCircle className="w-4 h-4 flex-shrink-0" />
                                ) : (
                                  <Circle className="w-4 h-4 flex-shrink-0" />
                                )}
                                <span className={req.completed ? 'line-through opacity-70' : ''}>
                                  {req.item}
                                </span>
                                {req.required && !req.completed && (
                                  <Badge variant="destructive" className="text-xs px-1.5 py-0">Required</Badge>
                                )}
                              </div>
                            ))}
                          </div>
                          
                          {/* Tips Section */}
                          {tips.length > 0 && (
                            <div className="border-t border-zinc-200 dark:border-zinc-600 pt-3">
                              <button
                                onClick={() => setShowTips(!showTips)}
                                className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300"
                              >
                                <Lightbulb className="w-4 h-4" />
                                <span className="font-medium">Tips for New Salespeople</span>
                                <ChevronRight className={`w-4 h-4 transition-transform ${showTips ? 'rotate-90' : ''}`} />
                              </button>
                              
                              {showTips && (
                                <ul className="mt-2 ml-6 space-y-1">
                                  {tips.map((tip, idx) => (
                                    <li key={idx} className="text-xs text-zinc-500 dark:text-zinc-400 flex items-start gap-2">
                                      <Info className="w-3 h-3 mt-0.5 flex-shrink-0 text-amber-500" />
                                      {tip}
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                )}

                {/* Lead Details (Step 1) */}
                {currentStep === 0 && lead && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border border-zinc-100 dark:border-zinc-700">
                        <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wide mb-1">Name</p>
                        <p className="font-semibold text-zinc-900 dark:text-zinc-100">{lead.first_name} {lead.last_name}</p>
                      </div>
                      <div className="p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border border-zinc-100 dark:border-zinc-700">
                        <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wide mb-1">Company</p>
                        <p className="font-semibold text-zinc-900 dark:text-zinc-100">{lead.company || 'N/A'}</p>
                      </div>
                      <div className="p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border border-zinc-100 dark:border-zinc-700">
                        <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wide mb-1">Email</p>
                        <p className="font-semibold text-zinc-900 dark:text-zinc-100">{lead.email}</p>
                      </div>
                      <div className="p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border border-zinc-100 dark:border-zinc-700">
                        <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wide mb-1">Phone</p>
                        <p className="font-semibold text-zinc-900 dark:text-zinc-100">{lead.phone || 'N/A'}</p>
                      </div>
                      <div className="p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border border-zinc-100 dark:border-zinc-700">
                        <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wide mb-1">Lead Score</p>
                        <p className="font-semibold text-zinc-900 dark:text-zinc-100">{lead.score || 0}</p>
                      </div>
                      <div className="p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border border-zinc-100 dark:border-zinc-700">
                        <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wide mb-1">Status</p>
                        <p className="font-semibold text-zinc-900 dark:text-zinc-100 capitalize">{lead.status || 'New'}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Project Complete (Step 9) */}
                {currentStep === 8 && (
                  <div className="text-center py-8">
                    {funnelStatus.project_id ? (
                      <>
                        <div className="w-20 h-20 bg-emerald-100 dark:bg-emerald-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
                          <CheckCircle className="w-10 h-10 text-emerald-600 dark:text-emerald-400" />
                        </div>
                        <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
                          Onboarding Complete!
                        </h2>
                        <p className="text-zinc-500 dark:text-zinc-400 mb-6">
                          {lead.company || lead.first_name} has been successfully onboarded.
                          <br />Project has been created and PM has been notified.
                        </p>
                        <Button
                          onClick={() => navigate(`/projects/${funnelStatus.project_id}`)}
                          className="bg-emerald-600 hover:bg-emerald-700"
                          data-testid="view-project-btn"
                        >
                          <ExternalLink className="w-4 h-4 mr-2" />
                          View Project
                        </Button>
                      </>
                    ) : (
                      <>
                        <Clock className="w-16 h-16 text-amber-500 mx-auto mb-4" />
                        <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
                          Awaiting Kickoff Approval
                        </h2>
                        <p className="text-zinc-500 dark:text-zinc-400">
                          Project will be created once Sr. Manager / Principal Consultant approves the kickoff request.
                        </p>
                      </>
                    )}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex justify-between mt-8 pt-6 border-t border-zinc-100 dark:border-zinc-800">
                  <Button
                    variant="outline"
                    onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                    disabled={currentStep === 0}
                    data-testid="prev-step-btn"
                    className="border-zinc-200 dark:border-zinc-700"
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Previous Step
                  </Button>
                  
                  {currentStep < 8 && (() => {
                    const nextStepId = FUNNEL_STEPS[currentStep + 1]?.id;
                    const isNextStepBlocked = isStepBlockedByAgreement(nextStepId);
                    const isCurrentCompleted = isStepCompleted(FUNNEL_STEPS[currentStep].id);
                    
                    // If navigating to next step would be blocked
                    if (isCurrentCompleted && isNextStepBlocked) {
                      return (
                        <Button
                          disabled
                          data-testid="continue-btn-blocked"
                          className="bg-zinc-400 cursor-not-allowed"
                        >
                          <Lock className="w-4 h-4 mr-2" />
                          Agreement Approval Required
                        </Button>
                      );
                    }
                    
                    return (
                      <Button
                        onClick={handleContinue}
                        data-testid="continue-btn"
                        className={isCurrentCompleted 
                          ? 'bg-emerald-600 hover:bg-emerald-700' 
                          : 'bg-blue-600 hover:bg-blue-700'
                        }
                      >
                        {isCurrentCompleted ? (
                          <>
                            Next Step
                            <ChevronRight className="w-4 h-4 ml-2" />
                          </>
                        ) : (
                          <>
                            Open {FUNNEL_STEPS[currentStep].title}
                            <ExternalLink className="w-4 h-4 ml-2" />
                          </>
                        )}
                      </Button>
                    );
                  })()}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SalesFunnelOnboarding;
