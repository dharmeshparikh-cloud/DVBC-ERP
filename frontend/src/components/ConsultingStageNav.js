import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, ChevronLeft, CheckCircle, Circle, Loader2, Lock, Eye } from 'lucide-react';
import { Button } from './ui/button';
import { isProjectReadOnly } from '../utils/projectActions';

/**
 * ConsultingStageNav - Navigation component showing the consulting workflow stages
 * 
 * Props:
 * - currentStage: number (1-7) - The current stage in the workflow
 * - projectId: string - The project ID for building navigation paths
 * - projectName: string - Optional project name for display
 * - projectStatus: string - Project status (active, completed, etc.)
 * - onBack: function - Optional custom back handler
 */

const STAGES = [
  { id: 1, name: 'Kickoff', shortName: 'Kickoff', basePath: '/kickoff-requests', actionStage: true },
  { id: 2, name: 'Team Assignment', shortName: 'Team', basePath: '/consulting/assign-team', actionStage: true },
  { id: 3, name: 'My Projects', shortName: 'Projects', basePath: '/consulting/my-projects', actionStage: false },
  { id: 4, name: 'SOW Management', shortName: 'SOW', basePath: '/consulting/sow', actionStage: true },
  { id: 5, name: 'Roadmap', shortName: 'Roadmap', basePath: '/consulting/roadmap', actionStage: false },
  { id: 6, name: 'Payments', shortName: 'Payments', basePath: '/consulting/payments', actionStage: false },
  { id: 7, name: 'Performance', shortName: 'Review', basePath: '/consulting/monthly-review', actionStage: false },
];

const ConsultingStageNav = ({ 
  currentStage = 1, 
  projectId = null, 
  projectName = null,
  projectStatus = 'active',
  completedStages = [],
  onBack = null,
  showFullNav = true 
}) => {
  const navigate = useNavigate();
  const isReadOnly = isProjectReadOnly(projectStatus);

  const getPath = (stage) => {
    if (stage.id === 1 || stage.id === 3 || stage.id === 6) {
      return stage.basePath;
    }
    return projectId ? `${stage.basePath}/${projectId}` : stage.basePath;
  };

  const handleStageClick = (stage) => {
    if (stage.id <= currentStage || completedStages.includes(stage.id)) {
      navigate(getPath(stage));
    }
  };

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else if (currentStage > 1) {
      const prevStage = STAGES.find(s => s.id === currentStage - 1);
      if (prevStage) {
        navigate(getPath(prevStage));
      }
    }
  };

  const currentStageData = STAGES.find(s => s.id === currentStage);

  return (
    <div className="mb-6" data-testid="consulting-stage-nav">
      {/* Read-only Banner */}
      {isReadOnly && (
        <div className="mb-3 p-2 bg-amber-50 border border-amber-200 rounded-sm flex items-center justify-center gap-2">
          <Lock className="w-4 h-4 text-amber-600" />
          <span className="text-sm text-amber-700 font-medium">
            Project {projectStatus} — Navigation is view-only
          </span>
          <Eye className="w-4 h-4 text-amber-600" />
        </div>
      )}
      {/* Back Button + Current Stage Title */}
      <div className="flex items-center gap-3 mb-4">
        {currentStage > 1 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            className="text-zinc-600 hover:text-zinc-900 -ml-2"
            data-testid="stage-back-btn"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Back
          </Button>
        )}
        {projectName && (
          <div className="text-sm text-zinc-500">
            <span className="font-medium text-zinc-700">{projectName}</span>
            {currentStageData && (
              <span className="ml-2">• Stage {currentStage}: {currentStageData.name}</span>
            )}
          </div>
        )}
      </div>

      {/* Stage Progress Bar */}
      {showFullNav && (
        <div className="flex items-center gap-1 p-2 bg-zinc-50 rounded-sm border border-zinc-200 overflow-x-auto">
          {STAGES.map((stage, index) => {
            const isCompleted = stage.id < currentStage || completedStages.includes(stage.id);
            const isCurrent = stage.id === currentStage;
            const isClickable = isCompleted || isCurrent;
            // For completed projects, action stages show view-only indicator
            const isViewOnly = isReadOnly && stage.actionStage;

            return (
              <React.Fragment key={stage.id}>
                <button
                  onClick={() => handleStageClick(stage)}
                  disabled={!isClickable}
                  title={isViewOnly ? `${stage.name} (View Only)` : stage.name}
                  className={`
                    flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-medium
                    transition-colors whitespace-nowrap relative
                    ${isCurrent 
                      ? 'bg-zinc-900 text-white' 
                      : isCompleted 
                        ? isViewOnly
                          ? 'bg-amber-100 text-amber-700 hover:bg-amber-200 cursor-pointer'
                          : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200 cursor-pointer' 
                        : 'bg-zinc-100 text-zinc-400 cursor-not-allowed'
                    }
                  `}
                  data-testid={`stage-${stage.id}`}
                >
                  {isViewOnly && isCompleted ? (
                    <Eye className="w-3.5 h-3.5" />
                  ) : isCompleted ? (
                    <CheckCircle className="w-3.5 h-3.5" />
                  ) : isCurrent ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Circle className="w-3.5 h-3.5" />
                  )}
                  <span className="hidden sm:inline">{stage.name}</span>
                  <span className="sm:hidden">{stage.shortName}</span>
                  {isViewOnly && <Lock className="w-3 h-3 ml-0.5 opacity-60" />}
                </button>
                {index < STAGES.length - 1 && (
                  <ChevronRight className="w-4 h-4 text-zinc-300 flex-shrink-0" />
                )}
              </React.Fragment>
            );
          })}
        </div>
      )}

      {/* Minimal Progress Indicator */}
      {!showFullNav && (
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {STAGES.map((stage) => (
              <div
                key={stage.id}
                className={`w-2 h-2 rounded-full ${
                  stage.id < currentStage 
                    ? 'bg-emerald-500' 
                    : stage.id === currentStage 
                      ? 'bg-zinc-900' 
                      : 'bg-zinc-200'
                }`}
              />
            ))}
          </div>
          <span className="text-xs text-zinc-500">
            Step {currentStage} of {STAGES.length}
          </span>
        </div>
      )}
    </div>
  );
};

export default ConsultingStageNav;
export { STAGES };
