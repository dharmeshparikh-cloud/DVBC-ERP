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
        `${API}/api/client-auth/change-consultant-request?project_id=${selectedProject}&reason=${encodeURIComponent(reason)}`,
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
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-black border-t-transparent rounded-full"></div>
      </div>
    );
  }

  const getStatusColor = (status) => {
    const colors = {
      active: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      completed: 'bg-blue-50 text-blue-700 border-blue-200',
      on_hold: 'bg-amber-50 text-amber-700 border-amber-200',
      pending: 'bg-black/5 text-black/70 border-black/10'
    };
    return colors[status] || 'bg-black/5 text-black/70 border-black/10';
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
    <div className="min-h-screen bg-white" data-testid="client-portal-page">
      {/* Header - Matching Main ERP */}
      <header className="bg-white border-b border-black/10 sticky top-0 z-50">
        <div className="flex items-center justify-between h-16 px-4 lg:px-6">
          {/* Left - Logo & Title */}
          <div className="flex items-center gap-4">
            <button 
              className="lg:hidden p-2 hover:bg-black/5 rounded-lg"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              <Menu className="w-5 h-5 text-black/60" />
            </button>
            <img src={LOGO_URL} alt="D&V" className="h-8" />
            <div className="hidden sm:block">
              <h1 className="text-base font-semibold text-black">DVBC - NETRA</h1>
              <p className="text-xs text-black/50">Client Portal</p>
            </div>
          </div>
          
          {/* Right - User Info */}
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/client-portal/change-password')}
              className="text-black/60 hover:text-black hover:bg-black/5"
              data-testid="change-password-nav-btn"
            >
              <KeyRound className="w-4 h-4" />
            </Button>
            <div className="hidden sm:block text-right">
              <p className="text-sm font-medium text-black">{clientData?.full_name}</p>
              <p className="text-xs text-black/50">Client ID: {clientData?.client_id}</p>
            </div>
            <div className="w-10 h-10 rounded-full bg-black/5 flex items-center justify-center border border-black/10">
              <User className="w-5 h-5 text-black/60" />
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-black/60 hover:text-black hover:bg-black/5"
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
          fixed lg:static inset-y-0 left-0 z-40 w-72 bg-white border-r border-black/10 
          transform transition-transform duration-200 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          pt-16 lg:pt-0
        `}>
          {/* Mobile Close Button */}
          <button 
            className="lg:hidden absolute top-4 right-4 p-2 hover:bg-black/5 rounded-lg"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-5 h-5 text-black/60" />
          </button>

          <div className="p-4">
            <h2 className="text-xs font-semibold text-black/50 uppercase tracking-wide mb-3">
              My Projects
            </h2>
            <div className="space-y-2">
              {projects.length === 0 ? (
                <div className="text-center py-8 text-black/50">
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
                        ? 'bg-black text-white'
                        : 'bg-black/5 border border-black/10 hover:border-black/20 hover:bg-black/10 text-black'
                    }`}
                    data-testid={`project-${project.id}`}
                  >
                    <p className={`font-medium text-sm truncate ${selectedProject === project.id ? 'text-white' : 'text-black'}`}>
                      {project.name}
                    </p>
                    <p className={`text-xs mt-1 font-mono ${selectedProject === project.id ? 'text-white/70' : 'text-black/50'}`}>
                      {project.id}
                    </p>
                    <Badge className={`mt-2 text-xs ${selectedProject === project.id ? 'bg-white/20 text-white border-white/30' : getStatusColor(project.status)}`}>
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
        <main className="flex-1 p-4 lg:p-6 min-h-[calc(100vh-64px)] bg-black/[0.02]">
          {projectDetails ? (
            <div className="max-w-6xl mx-auto space-y-6">
              {/* Project Header Card */}
              <Card className="border-black/10 bg-white shadow-sm">
                <CardContent className="p-6">
                  <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <Badge className={getStatusColor(projectDetails.status)}>
                          {projectDetails.status?.replace('_', ' ').toUpperCase()}
                        </Badge>
                        <span className="text-xs text-black/50 font-mono">{projectDetails.id}</span>
                      </div>
                      <h1 className="text-xl font-bold text-black">{projectDetails.name}</h1>
                      <p className="text-sm text-black/50 mt-1">{projectDetails.client_name}</p>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <div className="bg-black/5 px-4 py-2 rounded-lg border border-black/10">
                        <p className="text-xs text-black/50">Contract Value</p>
                        <p className="text-lg font-bold text-emerald-600">
                          ₹{(projectDetails.project_value || 0).toLocaleString()}
                        </p>
                      </div>
                      <div className="bg-black/5 px-4 py-2 rounded-lg border border-black/10">
                        <p className="text-xs text-black/50">Duration</p>
                        <p className="text-lg font-bold text-black">
                          {projectDetails.tenure_months || 12} months
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="mt-6">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-black/60">Project Progress</span>
                      <span className="font-medium text-black">{Math.round(calculateProgress(projectDetails))}%</span>
                    </div>
                    <Progress value={calculateProgress(projectDetails)} className="h-2" />
                    <div className="flex justify-between text-xs text-black/50 mt-2">
                      <span>{projectDetails.start_date?.split('T')[0] || 'TBD'}</span>
                      <span>{projectDetails.end_date?.split('T')[0] || 'TBD'}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="border-black/10 bg-white shadow-sm">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
                        <Users className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="text-xs text-black/50">Consultants</p>
                        <p className="text-xl font-bold text-black">
                          {projectDetails.active_consultants?.length || 0}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-black/10 bg-white shadow-sm">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center">
                        <ClipboardList className="w-5 h-5 text-purple-600" />
                      </div>
                      <div>
                        <p className="text-xs text-black/50">Meetings</p>
                        <p className="text-xl font-bold text-black">
                          {projectDetails.meetings?.length || 0}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-black/10 bg-white shadow-sm">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center">
                        <CreditCard className="w-5 h-5 text-emerald-600" />
                      </div>
                      <div>
                        <p className="text-xs text-black/50">Payments</p>
                        <p className="text-xl font-bold text-black">
                          {projectDetails.payments?.length || 0}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-black/10 bg-white shadow-sm">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-orange-50 flex items-center justify-center">
                        <FileText className="w-5 h-5 text-orange-600" />
                      </div>
                      <div>
                        <p className="text-xs text-black/50">Documents</p>
                        <p className="text-xl font-bold text-black">
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
                <Card className="border-black/10 bg-white shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2 text-black">
                      <Users className="w-5 h-5 text-black/60" />
                      Assigned Consultant
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {projectDetails.active_consultants?.length > 0 ? (
                      <div className="space-y-3">
                        {projectDetails.active_consultants.map((assignment, idx) => (
                          <div key={idx} className="flex items-center gap-3 p-3 bg-black/5 rounded-lg border border-black/5">
                            <div className="w-10 h-10 rounded-full bg-black/10 flex items-center justify-center">
                              <User className="w-5 h-5 text-black/60" />
                            </div>
                            <div className="flex-1">
                              <p className="font-medium text-black">
                                {assignment.consultant_details?.full_name || assignment.consultant_name}
                              </p>
                              <p className="text-xs text-black/50">
                                {assignment.consultant_role?.replace('_', ' ').toUpperCase()}
                              </p>
                            </div>
                          </div>
                        ))}
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full mt-2 border-black/20 text-black/70 hover:bg-black/5"
                          onClick={handleConsultantChangeRequest}
                          data-testid="change-consultant-btn"
                        >
                          <RefreshCw className="w-4 h-4 mr-2" />
                          Request Consultant Change
                        </Button>
                      </div>
                    ) : (
                      <div className="text-center py-6 text-black/50">
                        <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">Consultant will be assigned soon</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Reporting Manager */}
                <Card className="border-black/10 bg-white shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2 text-black">
                      <Building2 className="w-5 h-5 text-black/60" />
                      Reporting Manager
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {projectDetails.reporting_manager ? (
                      <div className="flex items-center gap-3 p-3 bg-black/5 rounded-lg border border-black/5">
                        <div className="w-10 h-10 rounded-full bg-black/10 flex items-center justify-center">
                          <User className="w-5 h-5 text-black/60" />
                        </div>
                        <div>
                          <p className="font-medium text-black">
                            {projectDetails.reporting_manager.full_name}
                          </p>
                          <p className="text-xs text-black/50">
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
                      <div className="text-center py-6 text-black/50">
                        <Building2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">Manager details not available</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Meetings / MOM */}
              <Card className="border-black/10 bg-white shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2 text-black">
                    <ClipboardList className="w-5 h-5 text-black/60" />
                    Meeting Notes (MOM)
                  </CardTitle>
                  <CardDescription className="text-black/50">
                    Minutes of meetings recorded by your consultant
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {projectDetails.meetings?.length > 0 ? (
                    <div className="space-y-3 max-h-80 overflow-y-auto">
                      {projectDetails.meetings.map((meeting, idx) => (
                        <div key={idx} className="p-4 bg-black/5 rounded-lg border border-black/5">
                          <div className="flex items-start justify-between">
                            <div>
                              <p className="font-medium text-black">
                                {meeting.title || meeting.meeting_type || 'Meeting'}
                              </p>
                              <p className="text-xs text-black/50 flex items-center gap-1 mt-1">
                                <Calendar className="w-3 h-3" />
                                {meeting.date?.split('T')[0]}
                              </p>
                            </div>
                            <Badge variant="outline" className="text-xs border-black/20">
                              {meeting.status || 'completed'}
                            </Badge>
                          </div>
                          {meeting.mom && (
                            <div className="mt-3 p-3 bg-white rounded border border-black/10">
                              <p className="text-xs font-medium text-black/50 mb-1">Meeting Notes:</p>
                              <p className="text-sm text-black/70 whitespace-pre-wrap">
                                {meeting.mom.length > 300 ? `${meeting.mom.substring(0, 300)}...` : meeting.mom}
                              </p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-black/50">
                      <ClipboardList className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No meetings recorded yet</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Documents & Payments Row */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Documents */}
                <Card className="border-black/10 bg-white shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2 text-black">
                      <FileText className="w-5 h-5 text-black/60" />
                      Documents
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {projectDetails.documents?.length > 0 || projectDetails.agreement ? (
                      <div className="space-y-2">
                        {projectDetails.agreement && (
                          <div className="flex items-center justify-between p-3 bg-black/5 rounded-lg border border-black/5">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded bg-orange-50 flex items-center justify-center">
                                <FileText className="w-4 h-4 text-orange-600" />
                              </div>
                              <div>
                                <p className="text-sm font-medium text-black">Service Agreement</p>
                                <p className="text-xs text-black/50">{projectDetails.agreement.agreement_number}</p>
                              </div>
                            </div>
                            <Button variant="ghost" size="sm" className="text-black/50 hover:text-black">
                              <Eye className="w-4 h-4" />
                            </Button>
                          </div>
                        )}
                        {projectDetails.documents?.map((doc, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-black/5 rounded-lg border border-black/5">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded bg-orange-50 flex items-center justify-center">
                                <FileText className="w-4 h-4 text-orange-600" />
                              </div>
                              <span className="text-sm font-medium text-black">{doc.name}</span>
                            </div>
                            <Button variant="ghost" size="sm" className="text-black/50 hover:text-black">
                              <Download className="w-4 h-4" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-6 text-black/50">
                        <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No documents available</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Payments */}
                <Card className="border-black/10 bg-white shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2 text-black">
                      <CreditCard className="w-5 h-5 text-black/60" />
                      Payments
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {projectDetails.payments?.length > 0 && (
                      <div className="mb-4">
                        <p className="text-xs font-medium text-black/50 mb-2 uppercase tracking-wide">Payment History</p>
                        <div className="space-y-2">
                          {projectDetails.payments.slice(0, 3).map((payment, idx) => (
                            <div key={idx} className="flex items-center justify-between p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                              <div>
                                <p className="text-sm font-medium text-black">
                                  ₹{(payment.amount || 0).toLocaleString()}
                                </p>
                                <p className="text-xs text-black/50">
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
                        <p className="text-xs font-medium text-black/50 mb-2 uppercase tracking-wide">Upcoming</p>
                        <div className="space-y-2">
                          {projectDetails.upcoming_payments.map((payment, idx) => (
                            <div key={idx} className="flex items-center justify-between p-3 bg-amber-50 rounded-lg border border-amber-100">
                              <div>
                                <p className="text-sm font-medium text-black">
                                  ₹{(payment.amount || 0).toLocaleString()}
                                </p>
                                <p className="text-xs text-black/50">
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
                      <div className="text-center py-6 text-black/50">
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
              <Card className="p-8 text-center border-black/10 bg-white">
                <Building2 className="w-12 h-12 mx-auto mb-4 text-black/30" />
                <p className="text-black/50">Select a project to view details</p>
              </Card>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default ClientPortal;
