import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import { Toaster } from './components/ui/sonner';
import Login from './pages/Login';
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
import EmailTemplates from './pages/EmailTemplates';
import PricingPlanBuilder from './pages/sales-funnel/PricingPlanBuilder';
import SOWBuilder from './pages/sales-funnel/SOWBuilder';
import Quotations from './pages/sales-funnel/Quotations';
import Agreements from './pages/sales-funnel/Agreements';
import ManagerApprovals from './pages/sales-funnel/ManagerApprovals';
import Consultants from './pages/Consultants';
import ConsultantDashboard from './pages/ConsultantDashboard';
import ProjectTasks from './pages/ProjectTasks';
import HandoverAlerts from './pages/HandoverAlerts';
import KickoffMeeting from './pages/KickoffMeeting';
import UserProfile from './pages/UserProfile';
import UserManagement from './pages/UserManagement';
import Employees from './pages/Employees';
import ApprovalsCenter from './pages/ApprovalsCenter';
import Clients from './pages/Clients';
import Expenses from './pages/Expenses';
import Reports from './pages/Reports';
import Layout from './components/Layout';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const AuthContext = React.createContext(null);

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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  // Determine default route based on user role
  const getDefaultDashboard = () => {
    if (user?.role === 'consultant') {
      return <ConsultantDashboard />;
    }
    return <Dashboard />;
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      <Toaster position="top-right" />
      <BrowserRouter>
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
            <Route path="email-templates" element={<EmailTemplates />} />
            <Route path="sales-funnel/pricing-plans" element={<PricingPlanBuilder />} />
            <Route path="sales-funnel/sow/:pricingPlanId" element={<SOWBuilder />} />
            <Route path="sales-funnel/quotations" element={<Quotations />} />
            <Route path="sales-funnel/agreements" element={<Agreements />} />
            <Route path="sales-funnel/approvals" element={<ManagerApprovals />} />
            <Route path="consultants" element={<Consultants />} />
            <Route path="consultant-dashboard" element={<ConsultantDashboard />} />
            <Route path="projects/:projectId/tasks" element={<ProjectTasks />} />
            <Route path="projects/:projectId/kickoff" element={<KickoffMeeting />} />
            <Route path="handover-alerts" element={<HandoverAlerts />} />
            <Route path="profile" element={<UserProfile />} />
            <Route path="user-management" element={<UserManagement />} />
            <Route path="employees" element={<Employees />} />
            <Route path="approvals" element={<ApprovalsCenter />} />
            <Route path="clients" element={<Clients />} />
            <Route path="expenses" element={<Expenses />} />
            <Route path="reports" element={<Reports />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

export default App;
