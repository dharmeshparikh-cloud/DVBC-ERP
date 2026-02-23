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
  Download, Eye, Users, TrendingUp, ClipboardList,
  Home, Settings, Bell, Search, Menu, X, KeyRound
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const LOGO_URL = "https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png";

const ClientPortal = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [clientData, setClientData] = useState(null);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectDetails, setProjectDetails] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    const data = localStorage.getItem('client_data');
    const token = localStorage.getItem('client_token');
    
    if (!token || !data) {
      navigate('/client-login');
      return;
    }
    
    const parsed = JSON.parse(data);
    
    if (parsed.must_change_password) {
      navigate('/client-portal/change-password');
      return;
    }
    
    setClientData(parsed);
    fetchProjects(token);
  }, [navigate]);

  const fetchProjects = async (token) => {
    try {
      const response = await axios.get(`${API}/api/client-auth/my-projects`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setProjects(response.data.projects || []);
      
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
      const response = await axios.get(`${API}/api/client-auth/project/${projectId}`, {
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
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  const getStatusColor = (status) => {
    const colors = {
      active: 'bg-emerald-100 text-emerald-700 border-emerald-200',
      completed: 'bg-blue-100 text-blue-700 border-blue-200',
      on_hold: 'bg-amber-100 text-amber-700 border-amber-200',
      pending: 'bg-zinc-100 text-zinc-700 border-zinc-200'
    };
    return colors[status] || 'bg-zinc-100 text-zinc-700 border-zinc-200';
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
    <div className="min-h-screen bg-zinc-50">
      {/* Header - Matching Main ERP */}
      <header className="bg-white border-b border-zinc-200 sticky top-0 z-50">
        <div className="flex items-center justify-between h-16 px-4 lg:px-6">
          {/* Left - Logo & Title */}
          <div className="flex items-center gap-4">
            <button 
              className="lg:hidden p-2 hover:bg-zinc-100 rounded-lg"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              <Menu className="w-5 h-5 text-zinc-600" />
            </button>
            <img src={LOGO_URL} alt="D&V" className="h-8" />
            <div className="hidden sm:block">
              <h1 className="text-base font-semibold text-zinc-800">DVBC - NETRA</h1>
              <p className="text-xs text-zinc-500">Client Portal</p>
            </div>
          </div>
          
          {/* Right - User Info */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:block text-right">
              <p className="text-sm font-medium text-zinc-800">{clientData?.full_name}</p>
              <p className="text-xs text-zinc-500">Client ID: {clientData?.client_id}</p>
            </div>
            <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
              <User className="w-5 h-5 text-amber-600" />
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-zinc-600 hover:text-zinc-800 hover:bg-zinc-100"
              data-testid="client-logout-btn"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar - Projects List */}
        <aside className={`
          fixed lg:static inset-y-0 left-0 z-40 w-72 bg-white border-r border-zinc-200 
          transform transition-transform duration-200 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          pt-16 lg:pt-0
        `}>
          {/* Mobile Close Button */}
          <button 
            className="lg:hidden absolute top-4 right-4 p-2 hover:bg-zinc-100 rounded-lg"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-5 h-5 text-zinc-600" />
          </button>

          <div className="p-4">
            <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-3">
              My Projects
            </h2>
            <div className="space-y-2">
              {projects.length === 0 ? (
                <div className="text-center py-8 text-zinc-500">
                  <Building2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No projects found</p>
                </div>
              ) : (
                projects.map((project) => (
                  <button
                    key={project.id}
                    onClick={() => {
                      setSelectedProject(project.id);
                      fetchProjectDetails(project.id);
                      setSidebarOpen(false);
                    }}
                    className={`w-full text-left p-3 rounded-lg transition-all ${
                      selectedProject === project.id
                        ? 'bg-amber-50 border-2 border-amber-500'
                        : 'bg-zinc-50 border border-zinc-200 hover:border-zinc-300 hover:bg-zinc-100'
                    }`}
                    data-testid={`project-${project.id}`}
                  >
                    <p className="font-medium text-zinc-800 text-sm truncate">
                      {project.name}
                    </p>
                    <p className="text-xs text-zinc-500 mt-1 font-mono">{project.id}</p>
                    <Badge className={`mt-2 text-xs ${getStatusColor(project.status)}`}>
                      {project.status?.replace('_', ' ').toUpperCase()}
                    </Badge>
                  </button>
                ))
              )}
            </div>
          </div>
        </aside>

        {/* Mobile Overlay */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/20 z-30 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main Content */}
        <main className="flex-1 p-4 lg:p-6 min-h-[calc(100vh-64px)]">
          {projectDetails ? (
            <div className="max-w-6xl mx-auto space-y-6">
              {/* Project Header Card */}
              <Card className="border-zinc-200">
                <CardContent className="p-6">
                  <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <Badge className={getStatusColor(projectDetails.status)}>
                          {projectDetails.status?.replace('_', ' ').toUpperCase()}
                        </Badge>
                        <span className="text-xs text-zinc-500 font-mono">{projectDetails.id}</span>
                      </div>
                      <h1 className="text-xl font-bold text-zinc-800">{projectDetails.name}</h1>
                      <p className="text-sm text-zinc-500 mt-1">{projectDetails.client_name}</p>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <div className="bg-zinc-50 px-4 py-2 rounded-lg border border-zinc-200">
                        <p className="text-xs text-zinc-500">Contract Value</p>
                        <p className="text-lg font-bold text-emerald-600">
                          ₹{(projectDetails.project_value || 0).toLocaleString()}
                        </p>
                      </div>
                      <div className="bg-zinc-50 px-4 py-2 rounded-lg border border-zinc-200">
                        <p className="text-xs text-zinc-500">Duration</p>
                        <p className="text-lg font-bold text-zinc-800">
                          {projectDetails.tenure_months || 12} months
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="mt-6">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-zinc-600">Project Progress</span>
                      <span className="font-medium text-zinc-800">{Math.round(calculateProgress(projectDetails))}%</span>
                    </div>
                    <Progress value={calculateProgress(projectDetails)} className="h-2" />
                    <div className="flex justify-between text-xs text-zinc-500 mt-2">
                      <span>{projectDetails.start_date?.split('T')[0] || 'TBD'}</span>
                      <span>{projectDetails.end_date?.split('T')[0] || 'TBD'}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="border-zinc-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                        <Users className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="text-xs text-zinc-500">Consultants</p>
                        <p className="text-xl font-bold text-zinc-800">
                          {projectDetails.active_consultants?.length || 0}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-zinc-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                        <ClipboardList className="w-5 h-5 text-purple-600" />
                      </div>
                      <div>
                        <p className="text-xs text-zinc-500">Meetings</p>
                        <p className="text-xl font-bold text-zinc-800">
                          {projectDetails.meetings?.length || 0}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-zinc-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
                        <CreditCard className="w-5 h-5 text-emerald-600" />
                      </div>
                      <div>
                        <p className="text-xs text-zinc-500">Payments</p>
                        <p className="text-xl font-bold text-zinc-800">
                          {projectDetails.payments?.length || 0}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-zinc-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
                        <FileText className="w-5 h-5 text-orange-600" />
                      </div>
                      <div>
                        <p className="text-xs text-zinc-500">Documents</p>
                        <p className="text-xl font-bold text-zinc-800">
                          {(projectDetails.documents?.length || 0) + (projectDetails.agreement ? 1 : 0)}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Two Column Layout */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Assigned Consultant */}
                <Card className="border-zinc-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2 text-zinc-800">
                      <Users className="w-5 h-5 text-amber-600" />
                      Assigned Consultant
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {projectDetails.active_consultants?.length > 0 ? (
                      <div className="space-y-3">
                        {projectDetails.active_consultants.map((assignment, idx) => (
                          <div key={idx} className="flex items-center gap-3 p-3 bg-zinc-50 rounded-lg border border-zinc-100">
                            <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                              <User className="w-5 h-5 text-amber-600" />
                            </div>
                            <div className="flex-1">
                              <p className="font-medium text-zinc-800">
                                {assignment.consultant_details?.full_name || assignment.consultant_name}
                              </p>
                              <p className="text-xs text-zinc-500">
                                {assignment.consultant_role?.replace('_', ' ').toUpperCase()}
                              </p>
                            </div>
                          </div>
                        ))}
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full mt-2 border-amber-300 text-amber-700 hover:bg-amber-50"
                          onClick={handleConsultantChangeRequest}
                          data-testid="change-consultant-btn"
                        >
                          <RefreshCw className="w-4 h-4 mr-2" />
                          Request Consultant Change
                        </Button>
                      </div>
                    ) : (
                      <div className="text-center py-6 text-zinc-500">
                        <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">Consultant will be assigned soon</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Reporting Manager */}
                <Card className="border-zinc-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2 text-zinc-800">
                      <Building2 className="w-5 h-5 text-blue-600" />
                      Reporting Manager
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {projectDetails.reporting_manager ? (
                      <div className="flex items-center gap-3 p-3 bg-zinc-50 rounded-lg border border-zinc-100">
                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                          <User className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <p className="font-medium text-zinc-800">
                            {projectDetails.reporting_manager.full_name}
                          </p>
                          <p className="text-xs text-zinc-500">
                            {projectDetails.reporting_manager.role?.replace('_', ' ').toUpperCase()}
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
                      <div className="text-center py-6 text-zinc-500">
                        <Building2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">Manager details not available</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Meetings / MOM */}
              <Card className="border-zinc-200">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2 text-zinc-800">
                    <ClipboardList className="w-5 h-5 text-purple-600" />
                    Meeting Notes (MOM)
                  </CardTitle>
                  <CardDescription>
                    Minutes of meetings recorded by your consultant
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {projectDetails.meetings?.length > 0 ? (
                    <div className="space-y-3 max-h-80 overflow-y-auto">
                      {projectDetails.meetings.map((meeting, idx) => (
                        <div key={idx} className="p-4 bg-zinc-50 rounded-lg border border-zinc-100">
                          <div className="flex items-start justify-between">
                            <div>
                              <p className="font-medium text-zinc-800">
                                {meeting.title || meeting.meeting_type || 'Meeting'}
                              </p>
                              <p className="text-xs text-zinc-500 flex items-center gap-1 mt-1">
                                <Calendar className="w-3 h-3" />
                                {meeting.date?.split('T')[0]}
                              </p>
                            </div>
                            <Badge variant="outline" className="text-xs border-zinc-300">
                              {meeting.status || 'completed'}
                            </Badge>
                          </div>
                          {meeting.mom && (
                            <div className="mt-3 p-3 bg-white rounded border border-zinc-200">
                              <p className="text-xs font-medium text-zinc-500 mb-1">Meeting Notes:</p>
                              <p className="text-sm text-zinc-700 whitespace-pre-wrap">
                                {meeting.mom.length > 300 ? `${meeting.mom.substring(0, 300)}...` : meeting.mom}
                              </p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-zinc-500">
                      <ClipboardList className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No meetings recorded yet</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Documents & Payments Row */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Documents */}
                <Card className="border-zinc-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2 text-zinc-800">
                      <FileText className="w-5 h-5 text-orange-600" />
                      Documents
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {projectDetails.documents?.length > 0 || projectDetails.agreement ? (
                      <div className="space-y-2">
                        {projectDetails.agreement && (
                          <div className="flex items-center justify-between p-3 bg-zinc-50 rounded-lg border border-zinc-100">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded bg-orange-100 flex items-center justify-center">
                                <FileText className="w-4 h-4 text-orange-600" />
                              </div>
                              <div>
                                <p className="text-sm font-medium text-zinc-800">Service Agreement</p>
                                <p className="text-xs text-zinc-500">{projectDetails.agreement.agreement_number}</p>
                              </div>
                            </div>
                            <Button variant="ghost" size="sm" className="text-zinc-500 hover:text-zinc-800">
                              <Eye className="w-4 h-4" />
                            </Button>
                          </div>
                        )}
                        {projectDetails.documents?.map((doc, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-zinc-50 rounded-lg border border-zinc-100">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded bg-orange-100 flex items-center justify-center">
                                <FileText className="w-4 h-4 text-orange-600" />
                              </div>
                              <span className="text-sm font-medium text-zinc-800">{doc.name}</span>
                            </div>
                            <Button variant="ghost" size="sm" className="text-zinc-500 hover:text-zinc-800">
                              <Download className="w-4 h-4" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-6 text-zinc-500">
                        <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No documents available</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Payments */}
                <Card className="border-zinc-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2 text-zinc-800">
                      <CreditCard className="w-5 h-5 text-emerald-600" />
                      Payments
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {projectDetails.payments?.length > 0 && (
                      <div className="mb-4">
                        <p className="text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wide">Payment History</p>
                        <div className="space-y-2">
                          {projectDetails.payments.slice(0, 3).map((payment, idx) => (
                            <div key={idx} className="flex items-center justify-between p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                              <div>
                                <p className="text-sm font-medium text-zinc-800">
                                  ₹{(payment.amount || 0).toLocaleString()}
                                </p>
                                <p className="text-xs text-zinc-500">
                                  {payment.created_at?.split('T')[0]}
                                </p>
                              </div>
                              <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">Paid</Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {projectDetails.upcoming_payments?.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-zinc-500 mb-2 uppercase tracking-wide">Upcoming</p>
                        <div className="space-y-2">
                          {projectDetails.upcoming_payments.map((payment, idx) => (
                            <div key={idx} className="flex items-center justify-between p-3 bg-amber-50 rounded-lg border border-amber-100">
                              <div>
                                <p className="text-sm font-medium text-zinc-800">
                                  ₹{(payment.amount || 0).toLocaleString()}
                                </p>
                                <p className="text-xs text-zinc-500">
                                  Due: {payment.due_date?.split('T')[0]}
                                </p>
                              </div>
                              <Badge className="bg-amber-100 text-amber-700 border-amber-200">Pending</Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {!projectDetails.payments?.length && !projectDetails.upcoming_payments?.length && (
                      <div className="text-center py-6 text-zinc-500">
                        <CreditCard className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No payment records</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[60vh]">
              <Card className="p-8 text-center border-zinc-200">
                <Building2 className="w-12 h-12 mx-auto mb-4 text-zinc-300" />
                <p className="text-zinc-500">Select a project to view details</p>
              </Card>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default ClientPortal;
