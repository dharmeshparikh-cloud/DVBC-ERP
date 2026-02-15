import React from 'react';
import { Check, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const SalesFunnelProgress = ({ 
  currentStep, 
  pricingPlanId, 
  leadId,
  quotationId,
  sowCompleted = false,
  proformaCompleted = false,
  agreementCompleted = false 
}) => {
  const navigate = useNavigate();

  const steps = [
    {
      id: 1,
      name: 'Pricing Plan',
      shortName: 'Pricing',
      description: 'Define investment & team',
      href: '/sales-funnel/pricing-plans',
      completed: !!pricingPlanId,
      enabled: true
    },
    {
      id: 2,
      name: 'Scope Selection',
      shortName: 'SOW',
      description: 'Select scope of work',
      href: pricingPlanId ? `/sales-funnel/scope-selection/${pricingPlanId}` : null,
      completed: sowCompleted,
      enabled: !!pricingPlanId
    },
    {
      id: 3,
      name: 'Proforma Invoice',
      shortName: 'Invoice',
      description: 'Generate invoice',
      href: pricingPlanId ? `/sales-funnel/proforma-invoice?pricing_plan_id=${pricingPlanId}` : '/sales-funnel/proforma-invoice',
      completed: proformaCompleted,
      enabled: sowCompleted || proformaCompleted
    },
    {
      id: 4,
      name: 'Agreement',
      shortName: 'Agreement',
      description: 'Finalize contract',
      href: quotationId ? `/sales-funnel/agreements?quotationId=${quotationId}&leadId=${leadId}` : '/sales-funnel/agreements',
      completed: agreementCompleted,
      enabled: proformaCompleted
    }
  ];

  const handleStepClick = (step) => {
    if (step.enabled && step.href) {
      navigate(step.href);
    }
  };

  const getStepStatus = (step, index) => {
    if (step.completed) return 'completed';
    if (currentStep === step.id) return 'current';
    if (step.enabled) return 'upcoming';
    return 'disabled';
  };

  return (
    <div className="mb-8">
      {/* Progress Bar */}
      <div className="relative">
        {/* Background line */}
        <div className="absolute top-5 left-0 right-0 h-0.5 bg-zinc-200" />
        
        {/* Progress line */}
        <div 
          className="absolute top-5 left-0 h-0.5 bg-emerald-500 transition-all duration-500"
          style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
        />

        {/* Steps */}
        <div className="relative flex justify-between">
          {steps.map((step, index) => {
            const status = getStepStatus(step, index);
            
            return (
              <div
                key={step.id}
                className={`flex flex-col items-center ${step.enabled ? 'cursor-pointer' : 'cursor-not-allowed'}`}
                onClick={() => handleStepClick(step)}
              >
                {/* Step Circle */}
                <div
                  className={`
                    w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold
                    transition-all duration-300 border-2
                    ${status === 'completed' 
                      ? 'bg-emerald-500 border-emerald-500 text-white' 
                      : status === 'current'
                        ? 'bg-white border-emerald-500 text-emerald-600 ring-4 ring-emerald-100'
                        : status === 'upcoming'
                          ? 'bg-white border-zinc-300 text-zinc-500 hover:border-zinc-400'
                          : 'bg-zinc-100 border-zinc-200 text-zinc-400'
                    }
                  `}
                >
                  {status === 'completed' ? (
                    <Check className="w-5 h-5" strokeWidth={2.5} />
                  ) : (
                    step.id
                  )}
                </div>

                {/* Step Info */}
                <div className="mt-3 text-center">
                  <p
                    className={`text-sm font-medium ${
                      status === 'current' 
                        ? 'text-emerald-600' 
                        : status === 'completed'
                          ? 'text-zinc-700'
                          : status === 'upcoming'
                            ? 'text-zinc-600'
                            : 'text-zinc-400'
                    }`}
                  >
                    {step.shortName}
                  </p>
                  <p className="text-xs text-zinc-400 mt-0.5 hidden sm:block">
                    {step.description}
                  </p>
                </div>

                {/* Status Badge */}
                {status === 'current' && (
                  <span className="mt-2 px-2 py-0.5 text-xs font-medium bg-emerald-100 text-emerald-700 rounded-full">
                    Current
                  </span>
                )}
                {status === 'completed' && (
                  <span className="mt-2 px-2 py-0.5 text-xs font-medium bg-zinc-100 text-zinc-600 rounded-full">
                    Done
                  </span>
                )}
                {status === 'disabled' && !step.completed && (
                  <span className="mt-2 px-2 py-0.5 text-xs font-medium bg-zinc-100 text-zinc-400 rounded-full">
                    Pending
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Flow Info Card */}
      <div className="mt-6 p-4 bg-zinc-50 rounded-sm border border-zinc-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 text-xs text-zinc-500">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>Completed</span>
            </div>
            <div className="flex items-center gap-1 text-xs text-zinc-500">
              <span className="w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-emerald-200"></span>
              <span>In Progress</span>
            </div>
            <div className="flex items-center gap-1 text-xs text-zinc-500">
              <span className="w-2 h-2 rounded-full bg-zinc-300"></span>
              <span>Upcoming</span>
            </div>
          </div>
          <div className="text-xs text-zinc-500">
            Step {currentStep} of {steps.length}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SalesFunnelProgress;
