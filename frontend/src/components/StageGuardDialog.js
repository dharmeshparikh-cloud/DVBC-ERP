import React from 'react';
import { useStageGuard, SALES_STAGES } from '../contexts/StageGuardContext';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { AlertTriangle, CheckCircle2, ArrowRight, X } from 'lucide-react';

/**
 * StageGuardDialog - Shows guided prompts instead of 403 errors
 * 
 * Types:
 * - blocked: User tried to access a stage they can't access yet
 * - complete: User completed a stage, prompt for next action
 * - prompt: General guidance prompt
 */
const StageGuardDialog = () => {
  const { 
    dialogState, 
    closeDialog, 
    goToRequiredStage, 
    proceedToNextStage 
  } = useStageGuard();

  const { isOpen, type, currentStage, targetStage, missingStages, message } = dialogState;

  if (!isOpen) return null;

  // Blocked - User tried to skip stages
  if (type === 'blocked') {
    return (
      <Dialog open={isOpen} onOpenChange={closeDialog}>
        <DialogContent className="sm:max-w-md" data-testid="stage-blocked-dialog">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <DialogTitle className="text-lg">Stage Not Available Yet</DialogTitle>
                <DialogDescription className="text-sm text-zinc-500 mt-1">
                  Complete previous stages first
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          
          <div className="py-4">
            <p className="text-sm text-zinc-700 mb-4">
              To access <span className="font-semibold text-zinc-900">{SALES_STAGES[targetStage]?.name}</span>, you need to complete:
            </p>
            
            {/* Stage Progress Indicator */}
            <div className="bg-zinc-50 rounded-lg p-4 space-y-2">
              {missingStages.map((stage, idx) => (
                <div key={stage} className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center text-xs font-medium text-amber-700">
                    {idx + 1}
                  </div>
                  <span className="text-sm font-medium text-zinc-700">
                    {SALES_STAGES[stage]?.name}
                  </span>
                  {idx < missingStages.length - 1 && (
                    <ArrowRight className="w-4 h-4 text-zinc-400 ml-auto" />
                  )}
                </div>
              ))}
              
              {/* Target Stage */}
              <div className="flex items-center gap-3 pt-2 border-t border-zinc-200 mt-2">
                <div className="w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                </div>
                <span className="text-sm font-medium text-emerald-700">
                  {SALES_STAGES[targetStage]?.name}
                </span>
              </div>
            </div>
          </div>
          
          <DialogFooter className="flex gap-2 sm:gap-2">
            <Button
              variant="outline"
              onClick={closeDialog}
              data-testid="stage-dialog-cancel"
            >
              Cancel
            </Button>
            <Button
              onClick={goToRequiredStage}
              className="bg-amber-600 hover:bg-amber-700"
              data-testid="stage-dialog-go"
            >
              Go to {SALES_STAGES[missingStages[0]]?.name}
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  // Complete - Stage completed, prompt for next
  if (type === 'complete') {
    return (
      <Dialog open={isOpen} onOpenChange={closeDialog}>
        <DialogContent className="sm:max-w-md" data-testid="stage-complete-dialog">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <DialogTitle className="text-lg">
                  {SALES_STAGES[currentStage]?.name} Completed!
                </DialogTitle>
                <DialogDescription className="text-sm text-zinc-500 mt-1">
                  Ready to proceed to the next stage
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          
          <div className="py-4">
            <p className="text-sm text-zinc-700">
              {message}
            </p>
            
            {/* Next Stage Preview */}
            <div className="mt-4 bg-emerald-50 rounded-lg p-4 flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center">
                <ArrowRight className="w-4 h-4 text-white" />
              </div>
              <div>
                <p className="text-sm font-medium text-emerald-900">Next: {SALES_STAGES[targetStage]?.name}</p>
                <p className="text-xs text-emerald-700">Click below to continue</p>
              </div>
            </div>
          </div>
          
          <DialogFooter className="flex gap-2 sm:gap-2">
            <Button
              variant="outline"
              onClick={closeDialog}
              data-testid="stage-dialog-later"
            >
              Maybe Later
            </Button>
            <Button
              onClick={proceedToNextStage}
              className="bg-emerald-600 hover:bg-emerald-700"
              data-testid="stage-dialog-proceed"
            >
              Create {SALES_STAGES[targetStage]?.name} Now
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  // Default prompt
  return (
    <Dialog open={isOpen} onOpenChange={closeDialog}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Guidance</DialogTitle>
          <DialogDescription>{message}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button onClick={closeDialog}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default StageGuardDialog;
