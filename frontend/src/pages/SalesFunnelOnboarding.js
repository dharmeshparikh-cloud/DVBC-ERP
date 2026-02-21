import React, { useState, useEffect, useContext } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { 
  User, Calendar, DollarSign, FileText, Receipt, 
  FileCheck, CreditCard, Rocket, CheckCircle, 
  ChevronRight, ArrowLeft, Building2, Phone, Mail,
  Clock, AlertCircle, ExternalLink, Lock
} from 'lucide-react';
import { toast } from 'sonner';

// Complete 9-Step Sales Funnel
const FUNNEL_STEPS = [
  { 
    id: 'lead', 
    title: 'Lead Capture', 
    icon: User, 
    description: 'Review lead details and contact information',
    route: null, // Inline step
    checkField: 'id' // Lead exists
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
    route: null, // Inline or part of client-onboarding
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

  useEffect(() => {
    if (leadId) {
      fetchFunnelData();
    }
  }, [leadId]);

  const fetchFunnelData = async () => {
    setLoading(true);
    try {
      // Fetch lead
      const leadRes = await axios.get(`${API}/leads/${leadId}`);
      setLead(leadRes.data);

      // Fetch funnel progress
      const progressRes = await axios.get(`${API}/leads/${leadId}/funnel-progress`);
      setFunnelStatus(progressRes.data);
      
      // Determine current step based on progress
      const completedSteps = progressRes.data.completed_steps || [];
      const lastCompleted = completedSteps.length > 0 ? 
        FUNNEL_STEPS.findIndex(s => s.id === completedSteps[completedSteps.length - 1]) : -1;
      setCurrentStep(Math.min(lastCompleted + 1, FUNNEL_STEPS.length - 1));
      
    } catch (error) {
      console.error('Error fetching funnel data:', error);
      toast.error('Failed to load onboarding data');
    } finally {
      setLoading(false);
    }
  };

  const isStepCompleted = (stepId) => {
    return funnelStatus.completed_steps?.includes(stepId) || false;
  };

  const isStepAccessible = (index) => {
    // Step is accessible if all previous steps are completed
    if (index === 0) return true;
    for (let i = 0; i < index; i++) {
      if (!isStepCompleted(FUNNEL_STEPS[i].id)) {
        return false;
      }
    }
    return true;
  };

  const handleStepClick = (index) => {
    if (!isStepAccessible(index)) {
      toast.error('Please complete previous steps first');
      return;
    }
    setCurrentStep(index);
  };

  const handleContinue = () => {
    const step = FUNNEL_STEPS[currentStep];
    
    if (step.route) {
      // Navigate to the existing page with leadId
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
      // Inline steps - handle here or navigate to client-onboarding
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
    <div className="max-w-6xl mx-auto p-6" data-testid="sales-funnel-onboarding">
      {/* Header */}
      <div className="mb-8">
        <Button
          onClick={() => navigate('/leads')}
          variant="ghost"
          className="hover:bg-zinc-100 rounded-sm mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Leads
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-zinc-950 mb-2">
              Sales Funnel
            </h1>
            <p className="text-zinc-500">
              Complete all steps to onboard <span className="font-medium text-zinc-700">{lead.company || lead.first_name}</span>
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-zinc-500">Progress</p>
            <p className="text-2xl font-semibold text-emerald-600">{completedCount} of {FUNNEL_STEPS.length}</p>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-8">
        <Progress value={progress} className="h-3" />
      </div>

      {/* Steps Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Steps List */}
        <div className="lg:col-span-1 space-y-2">
          {FUNNEL_STEPS.map((step, index) => {
            const StepIcon = step.icon;
            const isCompleted = isStepCompleted(step.id);
            const isCurrent = index === currentStep;
            const isAccessible = isStepAccessible(index);
            
            return (
              <div
                key={step.id}
                onClick={() => handleStepClick(index)}
                className={`p-4 rounded-lg border cursor-pointer transition-all ${
                  isCurrent 
                    ? 'border-blue-500 bg-blue-50' 
                    : isCompleted 
                      ? 'border-emerald-200 bg-emerald-50 hover:bg-emerald-100' 
                      : isAccessible
                        ? 'border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50'
                        : 'border-zinc-100 bg-zinc-50 opacity-50 cursor-not-allowed'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    isCompleted 
                      ? 'bg-emerald-500 text-white' 
                      : isCurrent 
                        ? 'bg-blue-500 text-white' 
                        : 'bg-zinc-200 text-zinc-500'
                  }`}>
                    {isCompleted ? (
                      <CheckCircle className="w-5 h-5" />
                    ) : !isAccessible ? (
                      <Lock className="w-4 h-4" />
                    ) : (
                      <StepIcon className="w-5 h-5" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`font-medium truncate ${
                      isCurrent ? 'text-blue-700' : isCompleted ? 'text-emerald-700' : 'text-zinc-700'
                    }`}>
                      {index + 1}. {step.title}
                    </p>
                    <p className="text-xs text-zinc-500 truncate">{step.description}</p>
                  </div>
                  {isCurrent && (
                    <ChevronRight className="w-5 h-5 text-blue-500" />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Current Step Content */}
        <div className="lg:col-span-2">
          <Card className="border-zinc-200 shadow-none">
            <CardHeader className="border-b border-zinc-100">
              <div className="flex items-center gap-3">
                {React.createElement(FUNNEL_STEPS[currentStep].icon, {
                  className: `w-8 h-8 ${
                    isStepCompleted(FUNNEL_STEPS[currentStep].id) 
                      ? 'text-emerald-500' 
                      : 'text-blue-500'
                  }`
                })}
                <div>
                  <CardTitle className="text-xl">
                    Step {currentStep + 1}: {FUNNEL_STEPS[currentStep].title}
                  </CardTitle>
                  <CardDescription>{FUNNEL_STEPS[currentStep].description}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              {/* Step Status */}
              {isStepCompleted(FUNNEL_STEPS[currentStep].id) ? (
                <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                  <div className="flex items-center gap-2 text-emerald-700 mb-2">
                    <CheckCircle className="w-5 h-5" />
                    <span className="font-medium">Step Completed</span>
                  </div>
                  {(() => {
                    const details = getStepDetails(FUNNEL_STEPS[currentStep]);
                    return details ? (
                      <div className="text-sm text-emerald-600">
                        <p className="font-medium">{details.title}</p>
                        {details.subtitle && <p>{details.subtitle}</p>}
                      </div>
                    ) : null;
                  })()}
                </div>
              ) : (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center gap-2 text-blue-700">
                    <Clock className="w-5 h-5" />
                    <span className="font-medium">Pending - Action Required</span>
                  </div>
                </div>
              )}

              {/* Lead Details (Step 1) */}
              {currentStep === 0 && lead && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-zinc-50 rounded-lg">
                      <p className="text-xs text-zinc-500 uppercase">Name</p>
                      <p className="font-semibold">{lead.first_name} {lead.last_name}</p>
                    </div>
                    <div className="p-4 bg-zinc-50 rounded-lg">
                      <p className="text-xs text-zinc-500 uppercase">Company</p>
                      <p className="font-semibold">{lead.company || 'N/A'}</p>
                    </div>
                    <div className="p-4 bg-zinc-50 rounded-lg">
                      <p className="text-xs text-zinc-500 uppercase">Email</p>
                      <p className="font-semibold">{lead.email}</p>
                    </div>
                    <div className="p-4 bg-zinc-50 rounded-lg">
                      <p className="text-xs text-zinc-500 uppercase">Phone</p>
                      <p className="font-semibold">{lead.phone || 'N/A'}</p>
                    </div>
                    <div className="p-4 bg-zinc-50 rounded-lg">
                      <p className="text-xs text-zinc-500 uppercase">Lead Score</p>
                      <p className="font-semibold">{lead.score || 0}</p>
                    </div>
                    <div className="p-4 bg-zinc-50 rounded-lg">
                      <p className="text-xs text-zinc-500 uppercase">Status</p>
                      <p className="font-semibold capitalize">{lead.status || 'New'}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Project Complete (Step 9) */}
              {currentStep === 8 && (
                <div className="text-center py-8">
                  {funnelStatus.project_id ? (
                    <>
                      <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
                        <CheckCircle className="w-10 h-10 text-emerald-600" />
                      </div>
                      <h2 className="text-2xl font-semibold text-zinc-800 mb-2">
                        Onboarding Complete!
                      </h2>
                      <p className="text-zinc-500 mb-6">
                        {lead.company || lead.first_name} has been successfully onboarded.
                        <br />Project has been created and PM has been notified.
                      </p>
                      <Button
                        onClick={() => navigate(`/projects/${funnelStatus.project_id}`)}
                        className="bg-emerald-600 hover:bg-emerald-700"
                      >
                        <ExternalLink className="w-4 h-4 mr-2" />
                        View Project
                      </Button>
                    </>
                  ) : (
                    <>
                      <Clock className="w-16 h-16 text-amber-500 mx-auto mb-4" />
                      <h2 className="text-xl font-semibold mb-2">Awaiting Kickoff Approval</h2>
                      <p className="text-zinc-500">
                        Project will be created once Sr. Manager / Principal Consultant approves the kickoff request.
                      </p>
                    </>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex justify-between mt-8 pt-6 border-t">
                <Button
                  variant="outline"
                  onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                  disabled={currentStep === 0}
                >
                  Previous Step
                </Button>
                
                {currentStep < 8 && (
                  <Button
                    onClick={handleContinue}
                    className={isStepCompleted(FUNNEL_STEPS[currentStep].id) 
                      ? 'bg-emerald-600 hover:bg-emerald-700' 
                      : 'bg-blue-600 hover:bg-blue-700'
                    }
                  >
                    {isStepCompleted(FUNNEL_STEPS[currentStep].id) ? (
                      <>
                        Next Step
                        <ChevronRight className="w-4 h-4 ml-2" />
                      </>
                    ) : (
                      <>
                        {FUNNEL_STEPS[currentStep].route ? 'Open ' : 'Complete '} 
                        {FUNNEL_STEPS[currentStep].title}
                        <ExternalLink className="w-4 h-4 ml-2" />
                      </>
                    )}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default SalesFunnelOnboarding;
