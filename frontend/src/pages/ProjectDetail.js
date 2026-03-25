/**
 * ProjectDetail.js - Project Detail Page with SOW as Primary View
 * 
 * This page serves as the main project view, defaulting to showing:
 * - SOW Delivery (Primary)
 * - Project Tasks
 * - Project Info
 * 
 * The user's request: Clicking project card should open SOW
 */

import React, { useState, useContext } from 'react';
import axios from 'axios';
import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import PageHeader from '../components/ui/page-header';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
  ArrowLeft, Calendar, Clock, Building2, IndianRupee,
  FileText, ListTodo, Users, CheckCircle2, AlertTriangle
} from 'lucide-react';
import { format, differenceInDays } from 'date-fns';
import ProjectSOWDelivery from '../components/ProjectSOWDelivery';

const ProjectDetail = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState('sow'); // Default to SOW

  // Fetch Project
  const { data: project, isLoading, refetch } = useQuery({
    queryKey: ['project', projectId],
    queryFn: async () => {
      const res = await axios.get(`${API}/projects/${projectId}`);
      return res.data;
    },
    staleTime: 3 * 60 * 1000,
  });

  const getStatusBadge = (status) => {
    const statusConfig = {
      active: { bg: 'bg-emerald-50', text: 'text-emerald-700', label: 'Active' },
      at_risk: { bg: 'bg-amber-50', text: 'text-amber-700', label: 'At Risk' },
      delayed: { bg: 'bg-red-50', text: 'text-red-700', label: 'Delayed' },
      completed: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'Completed' },
      on_hold: { bg: 'bg-zinc-100', text: 'text-zinc-600', label: 'On Hold' },
      cancelled: { bg: 'bg-zinc-100', text: 'text-zinc-500', label: 'Cancelled' }
    };
    return statusConfig[status?.toLowerCase()] || { bg: 'bg-zinc-100', text: 'text-zinc-600', label: status || 'Unknown' };
  };

  const getTimelineInfo = () => {
    if (!project?.end_date) return null;
    const endDate = new Date(project.end_date);
    const today = new Date();
    const daysRemaining = differenceInDays(endDate, today);
    return {
      daysRemaining,
      isOverdue: daysRemaining < 0,
      isAtRisk: daysRemaining >= 0 && daysRemaining <= 30
    };
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-zinc-500">Loading project...</div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <p className="text-zinc-500 mb-4">Project not found</p>
        <Button onClick={() => navigate('/projects')} variant="outline">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Projects
        </Button>
      </div>
    );
  }

  const timeline = getTimelineInfo();
  const statusBadge = getStatusBadge(project.status);

  return (
    <div data-testid="project-detail-page" className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Button
            onClick={() => navigate('/projects')}
            variant="ghost"
            className="mb-2 -ml-3 hover:bg-zinc-100 rounded-sm text-zinc-500"
            data-testid="back-btn"
          >
            <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Back to Projects
          </Button>
          <h1 className="text-2xl font-bold text-zinc-950" data-testid="project-title">
            {project.client_name || project.name}
          </h1>
          <p className="text-zinc-500 mt-1">
            {project.name || project.project_name}
          </p>
        </div>
        <Badge className={`${statusBadge.bg} ${statusBadge.text} px-3 py-1`}>
          {statusBadge.label}
        </Badge>
      </div>

      {/* Project Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border-zinc-200 shadow-none">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs text-zinc-500 uppercase tracking-wide mb-1">
              <Calendar className="w-3.5 h-3.5" />
              Start Date
            </div>
            <div className="text-sm font-semibold text-zinc-950">
              {project.start_date ? format(new Date(project.start_date), 'MMM dd, yyyy') : 'Not Set'}
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-zinc-200 shadow-none">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs text-zinc-500 uppercase tracking-wide mb-1">
              <Clock className="w-3.5 h-3.5" />
              End Date
            </div>
            <div className="text-sm font-semibold text-zinc-950">
              {project.end_date ? format(new Date(project.end_date), 'MMM dd, yyyy') : 'Not Set'}
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-zinc-200 shadow-none">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs text-zinc-500 uppercase tracking-wide mb-1">
              <Users className="w-3.5 h-3.5" />
              Meetings
            </div>
            <div className="text-sm font-semibold text-zinc-950">
              {project.total_meetings_delivered || 0} / {project.total_meetings_committed || 0}
            </div>
          </CardContent>
        </Card>
        
        <Card className={`shadow-none ${timeline?.isOverdue ? 'border-red-200 bg-red-50' : timeline?.isAtRisk ? 'border-amber-200 bg-amber-50' : 'border-zinc-200'}`}>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs text-zinc-500 uppercase tracking-wide mb-1">
              {timeline?.isOverdue ? (
                <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
              ) : timeline?.isAtRisk ? (
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5" />
              )}
              Timeline
            </div>
            <div className={`text-sm font-semibold ${timeline?.isOverdue ? 'text-red-700' : timeline?.isAtRisk ? 'text-amber-700' : 'text-zinc-950'}`}>
              {timeline 
                ? timeline.isOverdue 
                  ? `${Math.abs(timeline.daysRemaining)} days overdue`
                  : `${timeline.daysRemaining} days remaining`
                : 'No end date'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-zinc-100 p-1">
          <TabsTrigger value="sow" className="text-sm data-[state=active]:bg-white" data-testid="sow-tab">
            <FileText className="w-4 h-4 mr-2" />
            SOW Delivery
          </TabsTrigger>
          <TabsTrigger value="tasks" className="text-sm data-[state=active]:bg-white" data-testid="tasks-tab">
            <ListTodo className="w-4 h-4 mr-2" />
            Tasks
          </TabsTrigger>
          <TabsTrigger value="info" className="text-sm data-[state=active]:bg-white" data-testid="info-tab">
            <Building2 className="w-4 h-4 mr-2" />
            Project Info
          </TabsTrigger>
        </TabsList>

        {/* SOW Delivery Tab - Default */}
        <TabsContent value="sow" className="mt-0">
          <ProjectSOWDelivery projectId={projectId} />
        </TabsContent>

        {/* Tasks Tab - Link to full Tasks page */}
        <TabsContent value="tasks" className="mt-0">
          <Card className="border-zinc-200 shadow-none">
            <CardContent className="py-12 text-center">
              <ListTodo className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-zinc-700 mb-2">Project Tasks</h3>
              <p className="text-zinc-500 mb-6">View and manage all tasks for this project</p>
              <Button
                onClick={() => navigate(`/projects/${projectId}/tasks`)}
                className="bg-zinc-950 text-white hover:bg-zinc-800"
                data-testid="view-tasks-btn"
              >
                <ListTodo className="w-4 h-4 mr-2" />
                View Full Tasks Page
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Project Info Tab */}
        <TabsContent value="info" className="mt-0">
          <Card className="border-zinc-200 shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Project Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Client Name</label>
                  <p className="text-sm font-medium text-zinc-950">{project.client_name || '-'}</p>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Project Name</label>
                  <p className="text-sm font-medium text-zinc-950">{project.name || project.project_name || '-'}</p>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Project ID</label>
                  <p className="text-sm font-mono text-zinc-600">{project.id}</p>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Status</label>
                  <Badge className={`${statusBadge.bg} ${statusBadge.text} mt-1`}>{statusBadge.label}</Badge>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Tenure</label>
                  <p className="text-sm font-medium text-zinc-950">{project.tenure_months ? `${project.tenure_months} months` : '-'}</p>
                </div>
                <div>
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Budget</label>
                  <p className="text-sm font-medium text-zinc-950">
                    {project.budget ? `₹${project.budget.toLocaleString('en-IN')}` : '-'}
                  </p>
                </div>
              </div>
              
              {project.notes && (
                <div className="pt-4 border-t border-zinc-200">
                  <label className="text-xs text-zinc-500 uppercase tracking-wide">Notes</label>
                  <p className="text-sm text-zinc-700 mt-1">{project.notes}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ProjectDetail;
