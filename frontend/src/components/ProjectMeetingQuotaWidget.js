import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { 
  Calendar, 
  AlertTriangle, 
  CheckCircle, 
  ArrowRight,
  Building2,
  TrendingUp,
  Plus
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ProjectMeetingQuotaWidget = ({ limit = 5 }) => {
  const navigate = useNavigate();

  // Fetch active projects with meeting status
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects', 'meeting-quota-widget'],
    queryFn: async () => {
      const res = await axios.get(`${API}/projects?status=active`);
      const projectList = res.data || [];
      
      // Fetch meeting status for each project
      const projectsWithStatus = await Promise.all(
        projectList.slice(0, limit).map(async (project) => {
          try {
            const statusRes = await axios.get(`${API}/meeting-schedules/project/${project.id}/meeting-status`);
            return { ...project, meetingStatus: statusRes.data };
          } catch (e) {
            return { 
              ...project, 
              meetingStatus: { 
                total_committed: project.total_meetings_committed || 0,
                total_delivered: project.total_meetings_delivered || 0,
                remaining: (project.total_meetings_committed || 0) - (project.total_meetings_delivered || 0),
                percentage_used: 0,
                can_deliver_meeting: true,
                needs_approval: false
              }
            };
          }
        })
      );
      
      return projectsWithStatus;
    },
    staleTime: 60000, // 1 minute
    refetchInterval: 300000 // 5 minutes
  });

  const getProgressColor = (percentage) => {
    if (percentage >= 100) return 'bg-red-500';
    if (percentage >= 80) return 'bg-amber-500';
    if (percentage >= 50) return 'bg-blue-500';
    return 'bg-green-500';
  };

  const getStatusIndicator = (status) => {
    if (status.needs_approval) {
      return (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <Badge variant="destructive" className="text-xs">
                <AlertTriangle className="w-3 h-3 mr-1" />
                Limit Reached
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              <p>Request additional meetings for approval</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }
    if (status.remaining <= 2 && status.remaining > 0) {
      return (
        <Badge variant="outline" className="text-xs text-amber-600 border-amber-200 bg-amber-50">
          <AlertTriangle className="w-3 h-3 mr-1" />
          {status.remaining} left
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="text-xs text-green-600 border-green-200 bg-green-50">
        <CheckCircle className="w-3 h-3 mr-1" />
        {status.remaining} available
      </Badge>
    );
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Calendar className="w-5 h-5 text-blue-500" />
            Project Meeting Quota
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 bg-zinc-200 rounded w-3/4 mb-2"></div>
                <div className="h-2 bg-zinc-200 rounded w-full"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (projects.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Calendar className="w-5 h-5 text-blue-500" />
            Project Meeting Quota
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-zinc-500 text-center py-4">No active projects</p>
        </CardContent>
      </Card>
    );
  }

  // Calculate summary stats
  const totalCommitted = projects.reduce((sum, p) => sum + (p.meetingStatus?.total_committed || 0), 0);
  const totalDelivered = projects.reduce((sum, p) => sum + (p.meetingStatus?.total_delivered || 0), 0);
  const projectsNeedingApproval = projects.filter(p => p.meetingStatus?.needs_approval).length;

  return (
    <Card data-testid="meeting-quota-widget">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Calendar className="w-5 h-5 text-blue-500" />
            Meeting Quota Status
          </CardTitle>
          <Button 
            variant="ghost" 
            size="sm" 
            className="text-xs"
            onClick={() => navigate('/consulting/additional-meeting-requests')}
          >
            View All
            <ArrowRight className="w-3 h-3 ml-1" />
          </Button>
        </div>
        {/* Summary Stats */}
        <div className="flex items-center gap-4 mt-2 text-xs text-zinc-500">
          <span className="flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            {totalDelivered}/{totalCommitted} delivered
          </span>
          {projectsNeedingApproval > 0 && (
            <Badge variant="destructive" className="text-xs">
              {projectsNeedingApproval} need approval
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {projects.map((project) => {
          const status = project.meetingStatus || {};
          const percentage = status.percentage_used || 0;
          
          return (
            <div key={project.id} className="space-y-2" data-testid={`project-quota-${project.id}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <Building2 className="w-4 h-4 text-zinc-400 flex-shrink-0" />
                  <span className="font-medium text-sm text-zinc-700 truncate">{project.name}</span>
                </div>
                {getStatusIndicator(status)}
              </div>
              
              <div className="flex items-center gap-3">
                <Progress 
                  value={Math.min(percentage, 100)} 
                  className="h-2 flex-1"
                  indicatorClassName={getProgressColor(percentage)}
                />
                <span className="text-xs text-zinc-500 w-16 text-right">
                  {status.total_delivered || 0}/{status.total_committed || 0}
                </span>
              </div>

              {status.needs_approval && (
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="w-full text-xs h-7 mt-1 border-amber-200 text-amber-700 hover:bg-amber-50"
                  onClick={() => navigate('/consulting/additional-meeting-requests')}
                >
                  <Plus className="w-3 h-3 mr-1" />
                  Request Additional Meetings
                </Button>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
};

export default ProjectMeetingQuotaWidget;
