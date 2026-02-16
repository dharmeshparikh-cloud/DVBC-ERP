import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Toaster } from './components/ui/sonner';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import Dashboard from './pages/Dashboard';
import Leads from './pages/Leads';
import Projects from './pages/Projects';
import SalesMeetings from './pages/SalesMeetings';
import ConsultingMeetings from './pages/ConsultingMeetings';
import OrgChart from './pages/OrgChart';
import LeaveManagement from './pages/LeaveManagement';
import Attendance from './pages/Attendance';
import Payroll from './pages/Payroll';
import MyAttendance from './pages/MyAttendance';
import MyLeaves from './pages/MyLeaves';
import MySalarySlips from './pages/MySalarySlips';
import MyExpenses from './pages/MyExpenses';
import ProjectRoadmap from './pages/ProjectRoadmap';
import ConsultantPerformance from './pages/ConsultantPerformance';
import EmailTemplates from './pages/EmailTemplates';
import PricingPlanBuilder from './pages/sales-funnel/PricingPlanBuilder';
import SOWBuilder from './pages/sales-funnel/SOWBuilder';
import SalesScopeSelection from './pages/sales-funnel/SalesScopeSelection';
import ConsultingScopeView from './pages/sales-funnel/ConsultingScopeView';
import SalesSOWList from './pages/sales-funnel/SalesSOWList';
import ProformaInvoice from './pages/sales-funnel/ProformaInvoice';
import Agreements from './pages/sales-funnel/Agreements';
import AgreementView from './pages/sales-funnel/AgreementView';
import ManagerApprovals from './pages/sales-funnel/ManagerApprovals';
import ConsultingSOWList from './pages/consulting/ConsultingSOWList';
import ConsultingProjectTasks from './pages/consulting/ConsultingProjectTasks';
import MyProjects from './pages/consulting/MyProjects';
import AssignTeam from './pages/consulting/AssignTeam';
import Consultants from './pages/Consultants';
import ConsultantDashboard from './pages/ConsultantDashboard';
import ProjectTasks from './pages/ProjectTasks';
import HandoverAlerts from './pages/HandoverAlerts';
import KickoffMeeting from './pages/KickoffMeeting';
import KickoffRequests from './pages/KickoffRequests';
import UserProfile from './pages/UserProfile';
import UserManagement from './pages/UserManagement';
import Employees from './pages/Employees';
import ApprovalsCenter from './pages/ApprovalsCenter';
import Clients from './pages/Clients';
import Expenses from './pages/Expenses';
import Reports from './pages/Reports';
import SecurityAuditLog from './pages/SecurityAuditLog';
import GanttChart from './pages/GanttChart';
import Downloads from './pages/Downloads';
import SalesDashboard from './pages/SalesDashboard';
import ConsultingDashboard from './pages/ConsultingDashboard';
import HRDashboard from './pages/HRDashboard';
import AdminMasters from './pages/AdminMasters';
import Layout from './components/Layout';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const AuthContext = React.createContext(null);

function AppRouter({ user, login, logout, loading }) {
  const location = useLocation();

  // Check URL fragment for session_id synchronously during render (prevents race conditions)
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback onLogin={login} />;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  const getDefaultDashboard = () => {
    if (user?.role === 'consultant') {
      return <ConsultantDashboard />;
    }
    return <Dashboard />;
  };

  return (
    <Routes>
      <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />
      <Route
        path="/"
        element={user ? <Layout /> : <Navigate to="/login" />}
      >
        <Route index element={getDefaultDashboard()} />
        <Route path="leads" element={<Leads />} />
        <Route path="projects" element={<Projects />} />
        <Route path="sales-meetings" element={<SalesMeetings />} />
        <Route path="consulting-meetings" element={<ConsultingMeetings />} />
        <Route path="org-chart" element={<OrgChart />} />
        <Route path="leave-management" element={<LeaveManagement />} />
        <Route path="attendance" element={<Attendance />} />
        <Route path="payroll" element={<Payroll />} />
        <Route path="my-attendance" element={<MyAttendance />} />
        <Route path="my-leaves" element={<MyLeaves />} />
        <Route path="my-salary-slips" element={<MySalarySlips />} />
        <Route path="my-expenses" element={<MyExpenses />} />
        <Route path="project-roadmap" element={<ProjectRoadmap />} />
        <Route path="consultant-performance" element={<ConsultantPerformance />} />
        <Route path="email-templates" element={<EmailTemplates />} />
        <Route path="sales-funnel/pricing-plans" element={<PricingPlanBuilder />} />
        <Route path="sales-funnel/sow/:pricingPlanId" element={<SOWBuilder />} />
        <Route path="sales-funnel/scope-selection/:pricingPlanId" element={<SalesScopeSelection />} />
        <Route path="sales-funnel/sow-review/:pricingPlanId" element={<ConsultingScopeView />} />
        <Route path="sales-funnel/sow-list" element={<SalesSOWList />} />
        <Route path="sales-funnel/quotations" element={<ProformaInvoice />} />
        <Route path="sales-funnel/proforma-invoice" element={<ProformaInvoice />} />
        <Route path="sales-funnel/agreements" element={<Agreements />} />
        <Route path="sales-funnel/agreement/:agreementId" element={<AgreementView />} />
        <Route path="sales-funnel/agreement" element={<AgreementView />} />
        <Route path="sales-funnel/approvals" element={<ManagerApprovals />} />
        <Route path="consulting/projects" element={<ConsultingSOWList />} />
        <Route path="consulting/my-projects" element={<MyProjects />} />
        <Route path="consulting/project-tasks/:sowId" element={<ConsultingProjectTasks />} />
        <Route path="consultants" element={<Consultants />} />
        <Route path="consultant-dashboard" element={<ConsultantDashboard />} />
        <Route path="projects/:projectId/tasks" element={<ProjectTasks />} />
        <Route path="projects/:projectId/kickoff" element={<KickoffMeeting />} />
        <Route path="handover-alerts" element={<HandoverAlerts />} />
        <Route path="kickoff-requests" element={<KickoffRequests />} />
        <Route path="profile" element={<UserProfile />} />
        <Route path="user-management" element={<UserManagement />} />
        <Route path="employees" element={<Employees />} />
        <Route path="approvals" element={<ApprovalsCenter />} />
        <Route path="clients" element={<Clients />} />
        <Route path="expenses" element={<Expenses />} />
        <Route path="reports" element={<Reports />} />
        <Route path="security-audit" element={<SecurityAuditLog />} />
        <Route path="gantt-chart" element={<GanttChart />} />
        <Route path="downloads" element={<Downloads />} />
        <Route path="sales-dashboard" element={<SalesDashboard />} />
        <Route path="consulting-dashboard" element={<ConsultingDashboard />} />
        <Route path="hr-dashboard" element={<HRDashboard />} />
        <Route path="admin-masters" element={<AdminMasters />} />
      </Route>
    </Routes>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];
    } finally {
      setLoading(false);
    }
  };

  const login = (token, userData) => {
    localStorage.setItem('token', token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      <Toaster position="top-right" />
      <BrowserRouter>
        <AppRouter user={user} login={login} logout={logout} loading={loading} />
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

export default App;
