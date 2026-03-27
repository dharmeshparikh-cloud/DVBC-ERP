import React from 'react';
import { Check, ChevronRight, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { API } from '../App';
import { Button } from './ui/button';

const STEPS = [
  { id: 'lead_capture', label: 'Lead', guide: 'Capture lead details and contact information.' },
  { id: 'record_meeting', label: 'Meeting', guide: 'Schedule and record a meeting with MoM.' },
  { id: 'pricing_plan', label: 'Pricing', guide: 'Create a pricing plan with team allocation.' },
  { id: 'scope_of_work', label: 'SOW', guide: 'Define the scope of work and deliverables.' },
  { id: 'quotation', label: 'Proforma', guide: 'Generate a proforma invoice for the client.' },
  { id: 'agreement', label: 'Agreement', guide: 'Create and get the agreement signed.' },
  { id: 'record_payment', label: 'Payment', guide: 'Record and verify payment from the client.' },
  { id: 'kickoff_request', label: 'Kickoff', guide: 'Submit the project kickoff request.' },
  { id: 'project_created', label: 'Project', guide: 'Project created — client onboarded.' },
];

function getStepRoute(stepId, progress) {
  const lid = progress?.lead_id;
  const ppId = progress?.pricing_plan_id;
  const qId = progress?.quotation_id;
  switch (stepId) {
    case 'lead_capture': return lid ? `/sales-funnel-onboarding?leadId=${lid}` : '/leads';
    case 'record_meeting': return `/sales-funnel/meeting/record?leadId=${lid}`;
    case 'pricing_plan': return `/sales-funnel/pricing-plans?leadId=${lid}`;
    case 'scope_of_work': return ppId ? `/sales-funnel/sow/${ppId}?leadId=${lid}` : null;
    case 'quotation': return `/sales-funnel/proforma-invoices?leadId=${lid}&pricingPlanId=${ppId}`;
    case 'agreement': return `/sales-funnel/agreements?leadId=${lid}${qId ? `&quotationId=${qId}` : ''}`;
    case 'record_payment': return `/sales-funnel/payment-verification?leadId=${lid}`;
    case 'kickoff_request': return `/kickoff-requests?leadId=${lid}`;
    case 'project_created': return lid ? `/sales-funnel-onboarding?leadId=${lid}` : null;
    default: return null;
  }
}

const FunnelStepperHeader = ({ leadId, currentStepId }) => {
  const navigate = useNavigate();

  const { data: progress } = useQuery({
    queryKey: ['funnel-progress', leadId],
    queryFn: async () => {
      const { data } = await axios.get(`${API}/leads/${leadId}/funnel-progress`);
      return data;
    },
    enabled: !!leadId,
    staleTime: 30 * 1000,
  });

  if (!leadId || !progress) return null;

  const completedSteps = progress.completed_steps || [];
  const currentIdx = STEPS.findIndex(s => s.id === (currentStepId || progress.current_step));
  const nextStep = STEPS.find(s => !completedSteps.includes(s.id));

  return (
    <div className="mb-6" data-testid="funnel-stepper-header">
      {/* Company name + progress */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-zinc-950">{progress.company}</span>
          <span className="text-xs text-zinc-400">{progress.completed_count}/{progress.total_steps} steps</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="text-xs text-zinc-500 h-7"
          onClick={() => navigate(`/sales-funnel-onboarding?leadId=${leadId}`)}
        >
          Full Funnel View
          <ChevronRight className="w-3 h-3 ml-1" />
        </Button>
      </div>

      {/* 9-step stepper bar */}
      <div className="relative">
        {/* Background line */}
        <div className="absolute top-4 left-[2%] right-[2%] h-[2px] bg-zinc-200" />
        {/* Completed line */}
        {currentIdx >= 0 && (
          <div
            className="absolute top-4 left-[2%] h-[2px] bg-emerald-500 transition-all duration-500"
            style={{ width: `${Math.min((currentIdx / (STEPS.length - 1)) * 96, 96)}%` }}
          />
        )}

        <div className="relative flex justify-between">
          {STEPS.map((step, idx) => {
            const done = completedSteps.includes(step.id);
            const isCurrent = step.id === (currentStepId || progress.current_step);
            const isClickable = done || isCurrent || (idx <= currentIdx + 1);
            const route = getStepRoute(step.id, progress);

            return (
              <div
                key={step.id}
                className={`flex flex-col items-center w-[11%] ${isClickable && route ? 'cursor-pointer group' : 'cursor-default'}`}
                onClick={() => isClickable && route && navigate(route)}
                data-testid={`stepper-step-${step.id}`}
              >
                <div className={`
                  w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold
                  transition-all duration-200 border-2
                  ${done
                    ? 'bg-emerald-500 border-emerald-500 text-white'
                    : isCurrent
                      ? 'bg-white border-emerald-500 text-emerald-600 ring-2 ring-emerald-100'
                      : 'bg-white border-zinc-200 text-zinc-400'
                  }
                  ${isClickable && route ? 'group-hover:scale-110' : ''}
                `}>
                  {done ? <Check className="w-3.5 h-3.5" strokeWidth={3} /> : idx + 1}
                </div>
                <span className={`mt-1.5 text-[10px] font-medium text-center leading-tight ${
                  isCurrent ? 'text-emerald-600' : done ? 'text-zinc-700' : 'text-zinc-400'
                }`}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Next action guide */}
      {nextStep && (
        <div className="mt-4 flex items-center gap-3 px-3 py-2 bg-zinc-50 border border-zinc-200 rounded-sm" data-testid="funnel-next-guide">
          <div className="flex-1 min-w-0">
            <p className="text-xs text-zinc-500">
              <span className="font-medium text-zinc-700">Next: {nextStep.label}</span>
              {' — '}{nextStep.guide}
            </p>
          </div>
          {getStepRoute(nextStep.id, progress) && currentStepId !== nextStep.id && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs rounded-sm border-zinc-300 flex-shrink-0"
              onClick={() => navigate(getStepRoute(nextStep.id, progress))}
            >
              Go <ArrowRight className="w-3 h-3 ml-1" />
            </Button>
          )}
        </div>
      )}
      {!nextStep && (
        <div className="mt-4 flex items-center gap-2 px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-sm" data-testid="funnel-complete-guide">
          <Check className="w-4 h-4 text-emerald-600" />
          <p className="text-xs font-medium text-emerald-700">All steps complete — client onboarded!</p>
        </div>
      )}
    </div>
  );
};

export default FunnelStepperHeader;
