import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import {
  Building2, User, Calendar, FileText, CreditCard, 
  MessageSquare, Clock, CheckCircle, AlertCircle,
  LogOut, ChevronRight, Phone, Mail, RefreshCw,
  Download, Eye, Users, TrendingUp, ClipboardList
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const ClientPortal = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [clientData, setClientData] = useState(null);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectDetails, setProjectDetails] = useState(null);

  useEffect(() => {
    const data = localStorage.getItem('client_data');
    const token = localStorage.getItem('client_token');
    
    if (!token || !data) {
      navigate('/client-login');
      return;
    }
    
    const parsed = JSON.parse(data);
    
    // Check if password change is required
    if (parsed.must_change_password) {
      navigate('/client-portal/change-password');
      return;
    }
    
    setClientData(parsed);
    fetchProjects(token);
  }, [navigate]);

  const fetchProjects = async (token) => {
    try {
      const response = await axios.get(`${API}/client-auth/my-projects`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setProjects(response.data.projects || []);
      
      // Auto-select first project
      if (response.data.projects?.length > 0) {
        setSelectedProject(response.data.projects[0].id);
        fetchProjectDetails(response.data.projects[0].id, token);
      }
    } catch (error) {
      console.error('Error fetching projects:', error);
      if (error.response?.status === 401) {
        handleLogout();
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchProjectDetails = async (projectId, token) => {
    try {
      const authToken = token || localStorage.getItem('client_token');
      const response = await axios.get(`${API}/client-auth/project/${projectId}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      setProjectDetails(response.data);
    } catch (error) {
      console.error('Error fetching project details:', error);
      toast.error('Failed to load project details');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('client_token');
    localStorage.removeItem('client_data');
    navigate('/client-login');
  };

  const handleConsultantChangeRequest = async () => {
    const reason = prompt('Please describe why you want to change the consultant:');
    if (!reason) return;

    try {
      const token = localStorage.getItem('client_token');
      await axios.post(
        `${API}/client-auth/change-consultant-request?project_id=${selectedProject}&reason=${encodeURIComponent(reason)}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Consultant change request submitted successfully');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit request');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  const getStatusColor = (status) => {
    const colors = {
      active: 'bg-emerald-100 text-emerald-700',
      completed: 'bg-blue-100 text-blue-700',
      on_hold: 'bg-amber-100 text-amber-700',
      pending: 'bg-slate-100 text-slate-700'
    };
    return colors[status] || 'bg-slate-100 text-slate-700';
  };

  const calculateProgress = (project) => {
    if (!project?.start_date || !project?.end_date) return 0;
    const start = new Date(project.start_date).getTime();
    const end = new Date(project.end_date).getTime();
    const now = Date.now();
    const progress = ((now - start) / (end - start)) * 100;
    return Math.min(Math.max(progress, 0), 100);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <img 
                src="https://dvconsulting.co.in/wp-content/uploads/2020/02/logov4-min.png" 
                alt="D&V" 
                className="h-10"
              />
              <div className="hidden sm:block">
                <h1 className="text-lg font-semibold text-slate-800">Client Portal</h1>
                <p className="text-xs text-slate-500">NETRA ERP</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium text-slate-800">{clientData?.full_name}</p>
                <p className="text-xs text-slate-500">ID: {clientData?.client_id}</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleLogout}
                className="text-slate-600"
                data-testid="client-logout-btn"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Banner */}
        <div className="bg-gradient-to-r from-emerald-600 to-teal-600 rounded-xl p-6 mb-8 text-white">
          <h2 className="text-2xl font-bold mb-2">Welcome, {clientData?.full_name}!</h2>
          <p className="text-emerald-100">
            Track your project progress, view documents, and communicate with your consultant.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Projects Sidebar */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wide">
                  My Projects
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {projects.length === 0 ? (
                  <p className="text-sm text-slate-500 text-center py-4">No projects found</p>
                ) : (
                  projects.map((project) => (
                    <button
                      key={project.id}
                      onClick={() => {
                        setSelectedProject(project.id);
                        fetchProjectDetails(project.id);
                      }}
                      className={`w-full text-left p-3 rounded-lg transition-all ${
                        selectedProject === project.id
                          ? 'bg-emerald-50 border-2 border-emerald-500'
                          : 'bg-slate-50 border border-slate-200 hover:border-slate-300'
                      }`}
                      data-testid={`project-${project.id}`}
                    >
                      <p className="font-medium text-slate-800 text-sm truncate">
                        {project.name}
                      </p>
                      <p className="text-xs text-slate-500 mt-1">{project.id}</p>
                      <Badge className={`mt-2 ${getStatusColor(project.status)}`}>
                        {project.status?.replace('_', ' ')}
                      </Badge>
                    </button>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3 space-y-6">
            {projectDetails ? (
              <>
                {/* Project Overview */}
                <Card>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle className="text-xl">{projectDetails.name}</CardTitle>
                        <CardDescription className="mt-1">
                          Project ID: {projectDetails.id}
                        </CardDescription>
                      </div>
                      <Badge className={getStatusColor(projectDetails.status)}>
                        {projectDetails.status?.replace('_', ' ').toUpperCase()}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {/* Progress Bar */}
                      <div>
                        <div className="flex items-center justify-between text-sm mb-2">
                          <span className="text-slate-600">Project Progress</span>
                          <span className="font-medium">{Math.round(calculateProgress(projectDetails))}%</span>
                        </div>
                        <Progress value={calculateProgress(projectDetails)} className="h-2" />
                      </div>

                      {/* Key Details Grid */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
                        <div className="bg-slate-50 p-3 rounded-lg">
                          <p className="text-xs text-slate-500">Start Date</p>
                          <p className="font-medium text-slate-800">
                            {projectDetails.start_date?.split('T')[0] || 'TBD'}
                          </p>
                        </div>
                        <div className="bg-slate-50 p-3 rounded-lg">
                          <p className="text-xs text-slate-500">End Date</p>
                          <p className="font-medium text-slate-800">
                            {projectDetails.end_date?.split('T')[0] || 'TBD'}
                          </p>
                        </div>
                        <div className="bg-slate-50 p-3 rounded-lg">
                          <p className="text-xs text-slate-500">Duration</p>
                          <p className="font-medium text-slate-800">
                            {projectDetails.tenure_months || 12} months
                          </p>
                        </div>
                        <div className="bg-slate-50 p-3 rounded-lg">
                          <p className="text-xs text-slate-500">Contract Value</p>
                          <p className="font-medium text-emerald-600">
                            ₹{(projectDetails.project_value || 0).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Two Column Layout */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Assigned Consultant */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Users className="w-5 h-5 text-emerald-600" />
                        Assigned Consultant
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {projectDetails.active_consultants?.length > 0 ? (
                        <div className="space-y-3">
                          {projectDetails.active_consultants.map((assignment, idx) => (
                            <div key={idx} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                                <User className="w-5 h-5 text-emerald-600" />
                              </div>
                              <div className="flex-1">
                                <p className="font-medium text-slate-800">
                                  {assignment.consultant_details?.full_name || assignment.consultant_name}
                                </p>
                                <p className="text-xs text-slate-500">
                                  {assignment.consultant_role?.replace('_', ' ')}
                                </p>
                              </div>
                            </div>
                          ))}
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full mt-2 text-amber-600 border-amber-300 hover:bg-amber-50"
                            onClick={handleConsultantChangeRequest}
                            data-testid="change-consultant-btn"
                          >
                            <RefreshCw className="w-4 h-4 mr-2" />
                            Request Consultant Change
                          </Button>
                        </div>
                      ) : (
                        <div className="text-center py-6 text-slate-500">
                          <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
                          <p className="text-sm">Consultant will be assigned soon</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Reporting Manager */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Building2 className="w-5 h-5 text-blue-600" />
                        Reporting Manager
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {projectDetails.reporting_manager ? (
                        <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                          <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                            <User className="w-5 h-5 text-blue-600" />
                          </div>
                          <div>
                            <p className="font-medium text-slate-800">
                              {projectDetails.reporting_manager.full_name}
                            </p>
                            <p className="text-xs text-slate-500">
                              {projectDetails.reporting_manager.role?.replace('_', ' ')}
                            </p>
                            {projectDetails.reporting_manager.email && (
                              <a 
                                href={`mailto:${projectDetails.reporting_manager.email}`}
                                className="text-xs text-blue-600 hover:underline flex items-center gap-1 mt-1"
                              >
                                <Mail className="w-3 h-3" />
                                {projectDetails.reporting_manager.email}
                              </a>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="text-center py-6 text-slate-500">
                          <Building2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                          <p className="text-sm">Manager details not available</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Meetings / MOM */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <ClipboardList className="w-5 h-5 text-purple-600" />
                      Meeting Notes (MOM)
                    </CardTitle>
                    <CardDescription>
                      Minutes of meetings recorded by your consultant
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {projectDetails.meetings?.length > 0 ? (
                      <div className="space-y-3 max-h-64 overflow-y-auto">
                        {projectDetails.meetings.map((meeting, idx) => (
                          <div key={idx} className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                            <div className="flex items-start justify-between">
                              <div>
                                <p className="font-medium text-slate-800">
                                  {meeting.title || meeting.meeting_type || 'Meeting'}
                                </p>
                                <p className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                                  <Calendar className="w-3 h-3" />
                                  {meeting.date?.split('T')[0]}
                                </p>
                              </div>
                              <Badge variant="outline" className="text-xs">
                                {meeting.status || 'completed'}
                              </Badge>
                            </div>
                            {meeting.mom && (
                              <div className="mt-2 p-2 bg-white rounded border border-slate-200">
                                <p className="text-xs text-slate-600 whitespace-pre-wrap">
                                  {meeting.mom.length > 200 ? `${meeting.mom.substring(0, 200)}...` : meeting.mom}
                                </p>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-slate-500">
                        <ClipboardList className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No meetings recorded yet</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Documents & Payments Row */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Documents */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <FileText className="w-5 h-5 text-orange-600" />
                        Documents
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {projectDetails.documents?.length > 0 || projectDetails.agreement ? (
                        <div className="space-y-2">
                          {/* Agreement */}
                          {projectDetails.agreement && (
                            <div className="flex items-center justify-between p-2 bg-slate-50 rounded-lg">
                              <div className="flex items-center gap-2">
                                <FileText className="w-4 h-4 text-slate-500" />
                                <span className="text-sm text-slate-700">Service Agreement</span>
                              </div>
                              <Button variant="ghost" size="sm">
                                <Eye className="w-4 h-4" />
                              </Button>
                            </div>
                          )}
                          {/* Other Documents */}
                          {projectDetails.documents?.map((doc, idx) => (
                            <div key={idx} className="flex items-center justify-between p-2 bg-slate-50 rounded-lg">
                              <div className="flex items-center gap-2">
                                <FileText className="w-4 h-4 text-slate-500" />
                                <span className="text-sm text-slate-700">{doc.name}</span>
                              </div>
                              <Button variant="ghost" size="sm">
                                <Download className="w-4 h-4" />
                              </Button>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-center py-6 text-slate-500">
                          <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                          <p className="text-sm">No documents available</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Payments */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <CreditCard className="w-5 h-5 text-green-600" />
                        Payments
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {/* Payment History */}
                      {projectDetails.payments?.length > 0 && (
                        <div className="mb-4">
                          <p className="text-xs font-medium text-slate-500 mb-2">PAYMENT HISTORY</p>
                          <div className="space-y-2">
                            {projectDetails.payments.slice(0, 3).map((payment, idx) => (
                              <div key={idx} className="flex items-center justify-between p-2 bg-green-50 rounded-lg">
                                <div>
                                  <p className="text-sm font-medium text-slate-700">
                                    ₹{(payment.amount || 0).toLocaleString()}
                                  </p>
                                  <p className="text-xs text-slate-500">
                                    {payment.created_at?.split('T')[0]}
                                  </p>
                                </div>
                                <Badge className="bg-green-100 text-green-700">Paid</Badge>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Upcoming Payments */}
                      {projectDetails.upcoming_payments?.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-slate-500 mb-2">UPCOMING</p>
                          <div className="space-y-2">
                            {projectDetails.upcoming_payments.map((payment, idx) => (
                              <div key={idx} className="flex items-center justify-between p-2 bg-amber-50 rounded-lg">
                                <div>
                                  <p className="text-sm font-medium text-slate-700">
                                    ₹{(payment.amount || 0).toLocaleString()}
                                  </p>
                                  <p className="text-xs text-slate-500">
                                    Due: {payment.due_date?.split('T')[0]}
                                  </p>
                                </div>
                                <Badge className="bg-amber-100 text-amber-700">Pending</Badge>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {!projectDetails.payments?.length && !projectDetails.upcoming_payments?.length && (
                        <div className="text-center py-6 text-slate-500">
                          <CreditCard className="w-8 h-8 mx-auto mb-2 opacity-50" />
                          <p className="text-sm">No payment records</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </>
            ) : (
              <Card className="p-8 text-center">
                <div className="text-slate-500">
                  <Building2 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Select a project to view details</p>
                </div>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default ClientPortal;
