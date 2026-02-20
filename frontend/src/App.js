import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Toaster } from './components/ui/sonner';
import { ThemeProvider } from './contexts/ThemeContext';
import { ApprovalProvider } from './contexts/ApprovalContext';
import { PermissionProvider } from './contexts/PermissionContext';
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
import CTCDesigner from './pages/CTCDesigner';
import DocumentCenter from './pages/DocumentCenter';
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
import PaymentVerification from './pages/sales-funnel/PaymentVerification';
import ManagerApprovals from './pages/sales-funnel/ManagerApprovals';
import ConsultingSOWList from './pages/consulting/ConsultingSOWList';
import ConsultingProjectTasks from './pages/consulting/ConsultingProjectTasks';
import MyProjects from './pages/consulting/MyProjects';
import AssignTeam from './pages/consulting/AssignTeam';
import SOWChangeRequests from './pages/consulting/SOWChangeRequests';
import PaymentReminders from './pages/consulting/PaymentReminders';
import Consultants from './pages/Consultants';
import ConsultantDashboard from './pages/ConsultantDashboard';
import ProjectTasks from './pages/ProjectTasks';
import Timesheets from './pages/Timesheets';
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
import SalesDashboardEnhanced from './pages/SalesDashboardEnhanced';
import SalesTeamPerformance from './pages/SalesTeamPerformance';
import ConsultingDashboard from './pages/ConsultingDashboard';
import HRDashboard from './pages/HRDashboard';
import AdminMasters from './pages/AdminMasters';
import PermissionManager from './pages/PermissionManager';
import PermissionDashboard from './pages/PermissionDashboard';
import EmployeePermissions from './pages/EmployeePermissions';
import DepartmentAccessManager from './pages/DepartmentAccessManager';
import ExpenseApprovals from './pages/ExpenseApprovals';
import EmployeeScorecard from './pages/EmployeeScorecard';
import RoleManagement from './pages/RoleManagement';
// DocumentCenter replaces both LetterManagement and DocumentBuilder
import LetterheadSettings from './pages/LetterheadSettings';
import AcceptOfferPage from './pages/AcceptOfferPage';
import AdminDashboardMockups from './pages/admin/AdminDashboardMockups';
import FlowDiagram from './pages/FlowDiagram';
import ProjectPayments from './pages/ProjectPayments';
import ProjectPaymentDetails from './pages/ProjectPaymentDetails';
import Layout from './components/Layout';
import SalesLayout from './components/SalesLayout';
import HRLayout from './components/HRLayout';
import SalesLogin from './pages/SalesLogin';
import HRLogin from './pages/HRLogin';
import HRPortalDashboard from './pages/HRPortalDashboard';
import HRTeamWorkload from './pages/HRTeamWorkload';
import HRStaffingRequests from './pages/HRStaffingRequests';
import HROnboarding from './pages/HROnboarding';
import AdminDashboard from './pages/AdminDashboard';
import PerformanceDashboard from './pages/PerformanceDashboard';
import EmployeeMobileApp from './pages/EmployeeMobileApp';
import HRAttendanceApprovals from './pages/hr/HRAttendanceApprovals';
import OfficeLocationsSettings from './pages/OfficeLocationsSettings';
import MobileAppDownload from './pages/MobileAppDownload';
import TravelReimbursement from './pages/TravelReimbursement';
import WorkflowPage from './pages/WorkflowPage';
import OnboardingTutorial from './pages/OnboardingTutorial';
import BankDetailsChangeRequest from './pages/BankDetailsChangeRequest';
import PasswordManagement from './pages/PasswordManagement';
import GoLiveDashboard from './pages/GoLiveDashboard';
import Notifications from './pages/Notifications';
import PWAInstallPrompt from './components/PWAInstallPrompt';
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

  // Sales roles check for portal access
  const SALES_ROLES = ['executive', 'account_manager', 'manager'];
  const isSalesUser = user && SALES_ROLES.includes(user.role);

  const getDefaultDashboard = () => {
    if (user?.role === 'consultant') {
      return <ConsultantDashboard />;
    }
    // Sales users get the enhanced sales dashboard
    if (isSalesUser) {
      return <SalesDashboardEnhanced />;
    }
    // Admin gets the unified admin dashboard
    if (user?.role === 'admin') {
      return <AdminDashboard />;
    }
    // Others get the general dashboard
    return <Dashboard />;
  };

  return (
    <Routes>
      <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />
      
      {/* Public Letter Acceptance Routes - No auth required */}
      <Route path="/accept-offer/:token" element={<AcceptOfferPage />} />
      
      {/* Mobile Employee App - dedicated mobile view */}
      <Route path="/mobile" element={user ? <EmployeeMobileApp /> : <Navigate to="/login" />} />
      
      {/* Sales Portal Routes - restricted to sales roles */}
      <Route path="/sales/login" element={<SalesLogin />} />
      <Route
        path="/sales"
        element={
          user 
            ? (isSalesUser ? <SalesLayout /> : <Navigate to="/" />) 
            : <Navigate to="/sales/login" />
        }
      >
        <Route index element={<SalesDashboardEnhanced />} />
        <Route path="leads" element={<Leads />} />
        <Route path="pricing-plans" element={<PricingPlanBuilder />} />
        <Route path="sow/:pricingPlanId" element={<SOWBuilder />} />
        <Route path="scope-selection/:pricingPlanId" element={<SalesScopeSelection />} />
        <Route path="sow-review/:pricingPlanId" element={<ConsultingScopeView />} />
        <Route path="sow-list" element={<SalesSOWList />} />
        <Route path="quotations" element={<ProformaInvoice />} />
        <Route path="agreements" element={<Agreements />} />
        <Route path="agreement/:agreementId" element={<AgreementView />} />
        <Route path="payment-verification" element={<PaymentVerification />} />
        <Route path="kickoff-requests" element={<KickoffRequests />} />
        <Route path="clients" element={<Clients />} />
        <Route path="meetings" element={<SalesMeetings />} />
        <Route path="reports" element={<Reports />} />
        <Route path="team-performance" element={<SalesTeamPerformance />} />
        {/* Employee Workspace */}
        <Route path="my-attendance" element={<MyAttendance />} />
        <Route path="my-leaves" element={<MyLeaves />} />
        <Route path="my-salary" element={<MySalarySlips />} />
        <Route path="my-expenses" element={<MyExpenses />} />
        <Route path="my-bank-details" element={<BankDetailsChangeRequest />} />
      </Route>
      
      {/* HR Portal Routes - restricted to HR roles */}
      <Route path="/hr/login" element={<HRLogin />} />
      <Route
        path="/hr"
        element={
          user 
            ? (['hr_manager', 'hr_executive'].includes(user.role) ? <HRLayout /> : <Navigate to="/" />) 
            : <Navigate to="/hr/login" />
        }
      >
        <Route index element={<HRPortalDashboard />} />
        <Route path="employees" element={<Employees />} />
        <Route path="onboarding" element={<HROnboarding />} />
        <Route path="password-management" element={<PasswordManagement />} />
        <Route path="go-live" element={<GoLiveDashboard />} />
        <Route path="org-chart" element={<OrgChart />} />
        <Route path="leave-management" element={<LeaveManagement />} />
        <Route path="attendance" element={<Attendance />} />
        <Route path="payroll" element={<Payroll />} />
        <Route path="ctc-designer" element={<CTCDesigner />} />
        <Route path="document-center" element={<DocumentCenter />} />
        <Route path="document-builder" element={<DocumentCenter />} />
        <Route path="expenses" element={<Expenses />} />
        <Route path="travel-reimbursement" element={<TravelReimbursement />} />
        <Route path="approvals" element={<ApprovalsCenter />} />
        {/* HR Manager Only - Team View */}
        <Route path="department-access" element={<DepartmentAccessManager />} />
        <Route path="expense-approvals" element={<ExpenseApprovals />} />
        <Route path="team-workload" element={<HRTeamWorkload />} />
        <Route path="staffing-requests" element={<HRStaffingRequests />} />
        <Route path="performance-dashboard" element={<PerformanceDashboard />} />
        <Route path="attendance-approvals" element={<HRAttendanceApprovals />} />
        {/* Self Service */}
        <Route path="my-attendance" element={<MyAttendance />} />
        <Route path="my-leaves" element={<MyLeaves />} />
        <Route path="my-salary" element={<MySalarySlips />} />
        <Route path="my-expenses" element={<MyExpenses />} />
        <Route path="my-bank-details" element={<BankDetailsChangeRequest />} />
        {/* Reports */}
        <Route path="reports" element={<Reports />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="employee-permissions" element={<EmployeePermissions />} />
      </Route>
      
      {/* Main App Routes */}
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
        <Route path="ctc-designer" element={<CTCDesigner />} />
        <Route path="document-center" element={<DocumentCenter />} />
        <Route path="document-builder" element={<DocumentCenter />} />
        <Route path="my-attendance" element={<MyAttendance />} />
        <Route path="my-leaves" element={<MyLeaves />} />
        <Route path="my-salary-slips" element={<MySalarySlips />} />
        <Route path="my-expenses" element={<MyExpenses />} />
        <Route path="my-bank-details" element={<BankDetailsChangeRequest />} />
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
        <Route path="sales-funnel/payment-verification" element={<PaymentVerification />} />
        <Route path="sales-funnel/approvals" element={<ManagerApprovals />} />
        <Route path="consulting/projects" element={<ConsultingSOWList />} />
        <Route path="consulting/my-projects" element={<MyProjects />} />
        <Route path="consulting/assign-team/:projectId" element={<AssignTeam />} />
        <Route path="consulting/project-tasks/:sowId" element={<ConsultingProjectTasks />} />
        <Route path="consulting/sow-changes" element={<SOWChangeRequests />} />
        <Route path="consulting/payments" element={<PaymentReminders />} />
        <Route path="consultants" element={<Consultants />} />
        <Route path="consultant-dashboard" element={<ConsultantDashboard />} />
        <Route path="projects/:projectId/tasks" element={<ProjectTasks />} />
        <Route path="projects/:projectId/kickoff" element={<KickoffMeeting />} />
        <Route path="projects/:projectId/payments" element={<ProjectPaymentDetails />} />
        <Route path="payments" element={<ProjectPayments />} />
        <Route path="timesheets" element={<Timesheets />} />
        <Route path="handover-alerts" element={<HandoverAlerts />} />
        <Route path="kickoff-requests" element={<KickoffRequests />} />
        <Route path="profile" element={<UserProfile />} />
        <Route path="user-management" element={<UserManagement />} />
        <Route path="employees" element={<Employees />} />
        <Route path="password-management" element={<PasswordManagement />} />
        <Route path="approvals" element={<ApprovalsCenter />} />
        <Route path="clients" element={<Clients />} />
        <Route path="expenses" element={<Expenses />} />
        <Route path="travel-reimbursement" element={<TravelReimbursement />} />
        <Route path="reports" element={<Reports />} />
        <Route path="security-audit" element={<SecurityAuditLog />} />
        <Route path="gantt-chart" element={<GanttChart />} />
        <Route path="downloads" element={<Downloads />} />
        <Route path="sales-dashboard" element={<SalesDashboardEnhanced />} />
        <Route path="consulting-dashboard" element={<ConsultingDashboard />} />
        <Route path="hr-dashboard" element={<HRDashboard />} />
        <Route path="admin-masters" element={<AdminMasters />} />
        <Route path="permission-manager" element={<PermissionManager />} />
        <Route path="permission-dashboard" element={<PermissionDashboard />} />
        <Route path="employee-permissions" element={<EmployeePermissions />} />
        <Route path="department-access" element={<DepartmentAccessManager />} />
        <Route path="employee-scorecard" element={<EmployeeScorecard />} />
        <Route path="role-management" element={<RoleManagement />} />
        <Route path="document-center" element={<DocumentCenter />} />
        <Route path="letter-management" element={<DocumentCenter />} />
        <Route path="document-builder" element={<DocumentCenter />} />
        <Route path="letterhead-settings" element={<LetterheadSettings />} />
        <Route path="admin-dashboard-mockups" element={<AdminDashboardMockups />} />
        <Route path="admin-dashboard" element={<AdminDashboard />} />
        <Route path="office-locations" element={<OfficeLocationsSettings />} />
        <Route path="flow-diagram" element={<FlowDiagram />} />
        <Route path="workflow" element={<WorkflowPage />} />
        <Route path="tutorials" element={<OnboardingTutorial />} />
        {/* HR Features accessible to Admin in Main ERP */}
        <Route path="team-workload" element={<HRTeamWorkload />} />
        <Route path="staffing-requests" element={<HRStaffingRequests />} />
        <Route path="performance-dashboard" element={<PerformanceDashboard />} />
        <Route path="onboarding" element={<HROnboarding />} />
        <Route path="attendance-approvals" element={<HRAttendanceApprovals />} />
        <Route path="mobile-app" element={<MobileAppDownload />} />
        <Route path="go-live" element={<GoLiveDashboard />} />
        <Route path="notifications" element={<Notifications />} />
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
    <ThemeProvider>
      <AuthContext.Provider value={{ user, login, logout }}>
        <PermissionProvider>
          <ApprovalProvider>
            <Toaster position="top-right" />
            <PWAInstallPrompt />
            <BrowserRouter>
              <AppRouter user={user} login={login} logout={logout} loading={loading} />
            </BrowserRouter>
          </ApprovalProvider>
        </PermissionProvider>
      </AuthContext.Provider>
    </ThemeProvider>
  );
}

export default App;
