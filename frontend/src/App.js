import React, { useState, useEffect, Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Toaster } from './components/ui/sonner';
import { ThemeProvider } from './contexts/ThemeContext';
import { ApprovalProvider } from './contexts/ApprovalContext';
import { PermissionProvider } from './contexts/PermissionContext';
import { GuidanceProvider } from './contexts/GuidanceContext';
import { StageGuardProvider } from './contexts/StageGuardContext';
import StageGuardDialog from './components/StageGuardDialog';

// Critical paths - keep as regular imports for fast initial load
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import Dashboard from './pages/Dashboard';

// Lazy load non-critical pages for better performance
const Leads = lazy(() => import('./pages/Leads'));
const Projects = lazy(() => import('./pages/Projects'));
const SalesMeetings = lazy(() => import('./pages/SalesMeetings'));
const ConsultingMeetings = lazy(() => import('./pages/ConsultingMeetings'));
const OrgChart = lazy(() => import('./pages/OrgChart'));
const LeaveManagement = lazy(() => import('./pages/LeaveManagement'));
const Attendance = lazy(() => import('./pages/Attendance'));
const Payroll = lazy(() => import('./pages/Payroll'));
const CTCDesigner = lazy(() => import('./pages/CTCDesigner'));
const DocumentCenter = lazy(() => import('./pages/DocumentCenter'));
const MyAttendance = lazy(() => import('./pages/MyAttendance'));
const MyLeaves = lazy(() => import('./pages/MyLeaves'));
const MySalarySlips = lazy(() => import('./pages/MySalarySlips'));
const MyExpenses = lazy(() => import('./pages/MyExpenses'));
const MyDetails = lazy(() => import('./pages/MyDetails'));
const MyDrafts = lazy(() => import('./pages/MyDrafts'));
const ProjectRoadmap = lazy(() => import('./pages/ProjectRoadmap'));
const ConsultantPerformance = lazy(() => import('./pages/ConsultantPerformance'));
const EmailTemplates = lazy(() => import('./pages/EmailTemplates'));
const PricingPlanBuilder = lazy(() => import('./pages/sales-funnel/PricingPlanBuilder'));
const MeetingRecord = lazy(() => import('./pages/sales-funnel/MeetingRecord'));
const SOWBuilder = lazy(() => import('./pages/sales-funnel/SOWBuilder'));
const SalesScopeSelection = lazy(() => import('./pages/sales-funnel/SalesScopeSelection'));
const ConsultingScopeView = lazy(() => import('./pages/sales-funnel/ConsultingScopeView'));
const SalesSOWList = lazy(() => import('./pages/sales-funnel/SalesSOWList'));
const ProformaInvoice = lazy(() => import('./pages/sales-funnel/ProformaInvoice'));
const Agreements = lazy(() => import('./pages/sales-funnel/Agreements'));
const AgreementView = lazy(() => import('./pages/sales-funnel/AgreementView'));
const PaymentVerification = lazy(() => import('./pages/sales-funnel/PaymentVerification'));
const ManagerApprovals = lazy(() => import('./pages/sales-funnel/ManagerApprovals'));
const ClientOnboarding = lazy(() => import('./pages/ClientOnboarding'));
const SalesFunnelOnboarding = lazy(() => import('./pages/SalesFunnelOnboarding'));
const ConsultingSOWList = lazy(() => import('./pages/consulting/ConsultingSOWList'));
const ConsultingProjectTasks = lazy(() => import('./pages/consulting/ConsultingProjectTasks'));
const MyProjects = lazy(() => import('./pages/consulting/MyProjects'));
const AssignTeam = lazy(() => import('./pages/consulting/AssignTeam'));
const SOWChangeRequests = lazy(() => import('./pages/consulting/SOWChangeRequests'));
const PaymentReminders = lazy(() => import('./pages/consulting/PaymentReminders'));
const Consultants = lazy(() => import('./pages/Consultants'));
const ConsultantDashboard = lazy(() => import('./pages/ConsultantDashboard'));
const ProjectTasks = lazy(() => import('./pages/ProjectTasks'));
const Timesheets = lazy(() => import('./pages/Timesheets'));
const HandoverAlerts = lazy(() => import('./pages/HandoverAlerts'));
const KickoffMeeting = lazy(() => import('./pages/KickoffMeeting'));
const KickoffRequests = lazy(() => import('./pages/KickoffRequests'));
const ManagerLeadsDashboard = lazy(() => import('./pages/ManagerLeadsDashboard'));
const TargetManagement = lazy(() => import('./pages/TargetManagement'));
const UserProfile = lazy(() => import('./pages/UserProfile'));
const UserManagement = lazy(() => import('./pages/UserManagement'));
const Employees = lazy(() => import('./pages/Employees'));
const ApprovalsCenter = lazy(() => import('./pages/ApprovalsCenter'));
const Clients = lazy(() => import('./pages/Clients'));
const Expenses = lazy(() => import('./pages/Expenses'));
const Reports = lazy(() => import('./pages/Reports'));
const SecurityAuditLog = lazy(() => import('./pages/SecurityAuditLog'));
const GanttChart = lazy(() => import('./pages/GanttChart'));
const Downloads = lazy(() => import('./pages/Downloads'));
const SalesDashboard = lazy(() => import('./pages/SalesDashboard'));
const SalesDashboardEnhanced = lazy(() => import('./pages/SalesDashboardEnhanced'));
const SalesTeamPerformance = lazy(() => import('./pages/SalesTeamPerformance'));
const ConsultingDashboard = lazy(() => import('./pages/ConsultingDashboard'));
const HRDashboard = lazy(() => import('./pages/HRDashboard'));
const AdminMasters = lazy(() => import('./pages/AdminMasters'));
const PermissionManager = lazy(() => import('./pages/PermissionManager'));
const PermissionDashboard = lazy(() => import('./pages/PermissionDashboard'));
const EmployeePermissions = lazy(() => import('./pages/EmployeePermissions'));
const DepartmentAccessManager = lazy(() => import('./pages/DepartmentAccessManager'));
const ExpenseApprovals = lazy(() => import('./pages/ExpenseApprovals'));
const EmployeeScorecard = lazy(() => import('./pages/EmployeeScorecard'));
const RoleManagement = lazy(() => import('./pages/RoleManagement'));
const LetterheadSettings = lazy(() => import('./pages/LetterheadSettings'));
const AcceptOfferPage = lazy(() => import('./pages/AcceptOfferPage'));
const AdminDashboardMockups = lazy(() => import('./pages/admin/AdminDashboardMockups'));
const FlowDiagram = lazy(() => import('./pages/FlowDiagram'));
const ProjectPayments = lazy(() => import('./pages/ProjectPayments'));
const ProjectPaymentDetails = lazy(() => import('./pages/ProjectPaymentDetails'));

// Layouts - keep as regular imports (small files)
import Layout from './components/Layout';
import SalesLayout from './components/SalesLayout';
import HRLayout from './components/HRLayout';

// Continue lazy loading remaining pages
const SalesLogin = lazy(() => import('./pages/SalesLogin'));
const HRLogin = lazy(() => import('./pages/HRLogin'));
const HRPortalDashboard = lazy(() => import('./pages/HRPortalDashboard'));
const HRTeamWorkload = lazy(() => import('./pages/HRTeamWorkload'));
const HRStaffingRequests = lazy(() => import('./pages/HRStaffingRequests'));
const HROnboarding = lazy(() => import('./pages/HROnboarding'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const PerformanceDashboard = lazy(() => import('./pages/PerformanceDashboard'));
const EmployeeMobileApp = lazy(() => import('./pages/EmployeeMobileApp'));
const HRAttendanceApprovals = lazy(() => import('./pages/hr/HRAttendanceApprovals'));
const HRAttendanceInput = lazy(() => import('./pages/hr/HRAttendanceInput'));
const HRLeaveInput = lazy(() => import('./pages/hr/HRLeaveInput'));
const PayrollSummaryReport = lazy(() => import('./pages/hr/PayrollSummaryReport'));
const AttendanceLeaveSettings = lazy(() => import('./pages/hr/AttendanceLeaveSettings'));
const OfficeLocationsSettings = lazy(() => import('./pages/OfficeLocationsSettings'));
const MobileAppDownload = lazy(() => import('./pages/MobileAppDownload'));
const TravelReimbursement = lazy(() => import('./pages/TravelReimbursement'));
const WorkflowPage = lazy(() => import('./pages/WorkflowPage'));
const OnboardingTutorial = lazy(() => import('./pages/OnboardingTutorial'));
const PasswordManagement = lazy(() => import('./pages/PasswordManagement'));
const GoLiveDashboard = lazy(() => import('./pages/GoLiveDashboard'));
const Notifications = lazy(() => import('./pages/Notifications'));
const FollowUps = lazy(() => import('./pages/FollowUps'));
const Invoices = lazy(() => import('./pages/Invoices'));
const Chat = lazy(() => import('./pages/Chat'));
const AIAssistant = lazy(() => import('./pages/AIAssistant'));
const EmailSettings = lazy(() => import('./pages/admin/EmailSettings'));

import PWAInstallPrompt from './components/PWAInstallPrompt';
import { setupAxiosInterceptors } from './utils/useApi';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Re-export error handling utilities for easy access
export { handleApiError, useApi } from './utils/useApi';
export { parseError, ERROR_TYPES } from './utils/errorHandler';
export { ErrorDisplay, InlineError } from './components/ErrorDisplay';

export const AuthContext = React.createContext(null);

// Setup axios interceptors once
let interceptorsSetup = false;

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
  const SALES_ROLES = ['executive', 'sales_manager', 'manager'];
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
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full" />
      </div>
    }>
    <Routes>
      <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />
      
      {/* Public Letter Acceptance Routes - No auth required */}
      <Route path="/accept-offer/:token" element={<AcceptOfferPage />} />
      
      {/* Mobile Employee App - dedicated mobile view */}
      <Route path="/mobile" element={user ? <EmployeeMobileApp /> : <Navigate to="/login" />} />
      
      {/* Unified Portal - Redirect HR and Sales logins to main login */}
      <Route path="/sales/login" element={<Navigate to="/login" replace />} />
      <Route path="/hr/login" element={<Navigate to="/login" replace />} />
      
      {/* Sales Portal Routes - restricted to sales roles */}
      <Route
        path="/sales"
        element={
          user 
            ? (isSalesUser ? <SalesLayout /> : <Navigate to="/" />) 
            : <Navigate to="/login" />
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
        <Route path="manager-leads" element={<ManagerLeadsDashboard />} />
        <Route path="team-leads" element={<ManagerLeadsDashboard />} />
        <Route path="clients" element={<Clients />} />
        <Route path="meetings" element={<SalesMeetings />} />
        <Route path="reports" element={<Reports />} />
        <Route path="team-performance" element={<SalesTeamPerformance />} />
        {/* Employee Workspace */}
        <Route path="my-attendance" element={<MyAttendance />} />
        <Route path="my-leaves" element={<MyLeaves />} />
        <Route path="my-salary" element={<MySalarySlips />} />
        <Route path="my-expenses" element={<MyExpenses />} />
        <Route path="my-bank-details" element={<Navigate to="/my-details" replace />} />
        <Route path="my-details" element={<MyDetails />} />
      </Route>
      
      {/* HR Portal Routes - restricted to HR roles */}
      <Route
        path="/hr"
        element={
          user 
            ? (['hr_manager', 'hr_executive', 'admin'].includes(user.role) ? <HRLayout /> : <Navigate to="/" />) 
            : <Navigate to="/login" />
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
        <Route path="hr-attendance-input" element={<HRAttendanceInput />} />
        <Route path="hr-leave-input" element={<HRLeaveInput />} />
        <Route path="payroll-summary-report" element={<PayrollSummaryReport />} />
        <Route path="attendance-leave-settings" element={<AttendanceLeaveSettings />} />
        {/* Self Service */}
        <Route path="my-attendance" element={<MyAttendance />} />
        <Route path="my-leaves" element={<MyLeaves />} />
        <Route path="my-salary" element={<MySalarySlips />} />
        <Route path="my-expenses" element={<MyExpenses />} />
        <Route path="my-bank-details" element={<Navigate to="/my-details" replace />} />
        <Route path="my-details" element={<MyDetails />} />
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
        <Route path="my-bank-details" element={<Navigate to="/my-details" replace />} />
        <Route path="my-details" element={<MyDetails />} />
        <Route path="project-roadmap" element={<ProjectRoadmap />} />
        <Route path="consultant-performance" element={<ConsultantPerformance />} />
        <Route path="email-templates" element={<EmailTemplates />} />
        <Route path="sales-funnel/pricing-plans" element={<PricingPlanBuilder />} />
        <Route path="sales-funnel/meeting/record" element={<MeetingRecord />} />
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
        <Route path="client-onboarding" element={<ClientOnboarding />} />
        <Route path="sales-funnel-onboarding" element={<SalesFunnelOnboarding />} />
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
        <Route path="manager-leads" element={<ManagerLeadsDashboard />} />
        <Route path="team-leads" element={<ManagerLeadsDashboard />} />
        <Route path="target-management" element={<TargetManagement />} />
        <Route path="targets" element={<TargetManagement />} />
        <Route path="clients" element={<Clients />} />
        <Route path="expenses" element={<Expenses />} />
        <Route path="travel-reimbursement" element={<TravelReimbursement />} />
        <Route path="reports" element={<Reports />} />
        <Route path="security-audit" element={<SecurityAuditLog />} />
        <Route path="gantt-chart" element={<GanttChart />} />
        <Route path="downloads" element={<Downloads />} />
        <Route path="sales-dashboard" element={<SalesDashboard />} />
        <Route path="consulting-dashboard" element={<ConsultingDashboard />} />
        <Route path="hr-dashboard" element={<HRDashboard />} />
        <Route path="admin-masters" element={<AdminMasters />} />
        <Route path="permission-manager" element={<PermissionManager />} />
        <Route path="permission-dashboard" element={<PermissionDashboard />} />
        <Route path="employee-permissions" element={<EmployeePermissions />} />
        <Route path="department-access" element={<DepartmentAccessManager />} />
        <Route path="expense-approvals" element={<ExpenseApprovals />} />
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
        <Route path="hr-attendance-input" element={<HRAttendanceInput />} />
        <Route path="hr-leave-input" element={<HRLeaveInput />} />
        <Route path="payroll-summary-report" element={<PayrollSummaryReport />} />
        <Route path="attendance-leave-settings" element={<AttendanceLeaveSettings />} />
        <Route path="mobile-app" element={<MobileAppDownload />} />
        <Route path="go-live" element={<GoLiveDashboard />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="follow-ups" element={<FollowUps />} />
        <Route path="invoices" element={<Invoices />} />
        <Route path="chat" element={<Chat />} />
        <Route path="ai-assistant" element={<AIAssistant />} />
        <Route path="email-settings" element={<EmailSettings />} />
      </Route>
    </Routes>
    </Suspense>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Setup axios interceptors once
  useEffect(() => {
    if (!interceptorsSetup) {
      setupAxiosInterceptors(() => {
        // On auth error, logout user
        localStorage.removeItem('token');
        delete axios.defaults.headers.common['Authorization'];
        setUser(null);
      });
      interceptorsSetup = true;
    }
  }, []);

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
            <GuidanceProvider>
              <Toaster position="top-right" />
              <PWAInstallPrompt />
              <BrowserRouter>
                <StageGuardProvider>
                  <StageGuardDialog />
                  <AppRouter user={user} login={login} logout={logout} loading={loading} />
                </StageGuardProvider>
              </BrowserRouter>
            </GuidanceProvider>
          </ApprovalProvider>
        </PermissionProvider>
      </AuthContext.Provider>
    </ThemeProvider>
  );
}

export default App;
