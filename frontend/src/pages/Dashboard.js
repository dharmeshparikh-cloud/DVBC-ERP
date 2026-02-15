import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Users, UserCheck, TrendingUp, Briefcase, Target, DollarSign, FileText, ClipboardCheck, ArrowRight, Shield, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { toast } from 'sonner';

const Dashboard = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [highPriorityLeads, setHighPriorityLeads] = useState([]);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    fetchHighPriorityLeads();
    if (user?.role === 'manager' || user?.role === 'admin') {
      fetchPendingApprovals();
    }
  }, [user]);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats/dashboard`);
      setStats(response.data);
    } catch (error) {
      toast.error('Failed to fetch dashboard stats');
    } finally {
      setLoading(false);
    }
  };

  const fetchHighPriorityLeads = async () => {
    try {
      const response = await axios.get(`${API}/leads`);
      // Get top 3 leads with highest scores
      const topLeads = response.data
        .sort((a, b) => (b.lead_score || 0) - (a.lead_score || 0))
        .slice(0, 3);
      setHighPriorityLeads(topLeads);
    } catch (error) {
      console.error('Failed to fetch high priority leads');
    }
  };

  const fetchPendingApprovals = async () => {
    try {
      const response = await axios.get(`${API}/agreements/pending-approval`);
      setPendingApprovalsCount(response.data.length);
    } catch (error) {
      console.error('Failed to fetch pending approvals');
    }
  };

  const statCards = [
    {
      title: 'Total Leads',
      value: stats?.total_leads || 0,
      icon: Users,
      color: 'text-zinc-950',
      link: '/leads',
    },
    {
      title: 'New Leads',
      value: stats?.new_leads || 0,
      icon: Target,
      color: 'text-blue-600',
      link: '/leads?status=new',
    },
    {
      title: 'Qualified Leads',
      value: stats?.qualified_leads || 0,
      icon: UserCheck,
      color: 'text-purple-600',
      link: '/leads?status=qualified',
    },
    {
      title: 'Closed Deals',
      value: stats?.closed_deals || 0,
      icon: TrendingUp,
      color: 'text-emerald-600',
      link: '/leads?status=closed',
    },
    {
      title: 'Active Projects',
      value: stats?.active_projects || 0,
      icon: Briefcase,
      color: 'text-zinc-950',
      link: '/projects',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-zinc-500">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div data-testid="dashboard-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          Dashboard
        </h1>
        <p className="text-zinc-500">Welcome back, {user?.full_name}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card
              key={stat.title}
              data-testid={`stat-card-${stat.title.toLowerCase().replace(/\s+/g, '-')}`}
              className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-400 hover:bg-zinc-50 transition-all cursor-pointer group"
              onClick={() => navigate(stat.link)}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                  {stat.title}
                </CardTitle>
                <Icon className={`w-4 h-4 ${stat.color}`} strokeWidth={1.5} />
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="text-3xl font-semibold text-zinc-950 data-text">
                    {stat.value}
                  </div>
                  <ArrowRight className="w-4 h-4 text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity" strokeWidth={1.5} />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Pending Approvals Alert for Managers */}
      {(user?.role === 'manager' || user?.role === 'admin') && pendingApprovalsCount > 0 && (
        <Card 
          className="border-yellow-300 bg-yellow-50 shadow-none rounded-sm mb-8 cursor-pointer hover:border-yellow-400 transition-colors"
          onClick={() => navigate('/sales-funnel/approvals')}
          data-testid="pending-approvals-alert"
        >
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <ClipboardCheck className="w-5 h-5 text-yellow-600" strokeWidth={1.5} />
                <div>
                  <div className="font-medium text-yellow-900">
                    {pendingApprovalsCount} Agreement{pendingApprovalsCount > 1 ? 's' : ''} Pending Approval
                  </div>
                  <div className="text-sm text-yellow-700">Click to review and approve</div>
                </div>
              </div>
              <ArrowRight className="w-5 h-5 text-yellow-600" strokeWidth={1.5} />
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
              Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <button
              onClick={() => navigate('/leads')}
              data-testid="quick-action-add-lead"
              className="w-full text-left px-4 py-3 rounded-sm border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 transition-colors text-sm text-zinc-950 flex items-center justify-between group"
            >
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-zinc-500" strokeWidth={1.5} />
                Add New Lead
              </div>
              <ArrowRight className="w-4 h-4 text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity" strokeWidth={1.5} />
            </button>
            <button
              onClick={() => navigate('/sales-funnel/pricing-plans')}
              data-testid="quick-action-create-pricing"
              className="w-full text-left px-4 py-3 rounded-sm border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 transition-colors text-sm text-zinc-950 flex items-center justify-between group"
            >
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-zinc-500" strokeWidth={1.5} />
                Create Pricing Plan
              </div>
              <ArrowRight className="w-4 h-4 text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity" strokeWidth={1.5} />
            </button>
            <button
              onClick={() => navigate('/sales-funnel/quotations')}
              data-testid="quick-action-view-quotations"
              className="w-full text-left px-4 py-3 rounded-sm border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 transition-colors text-sm text-zinc-950 flex items-center justify-between group"
            >
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-zinc-500" strokeWidth={1.5} />
                View Quotations
              </div>
              <ArrowRight className="w-4 h-4 text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity" strokeWidth={1.5} />
            </button>
            <button
              onClick={() => navigate('/projects')}
              data-testid="quick-action-create-project"
              className="w-full text-left px-4 py-3 rounded-sm border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 transition-colors text-sm text-zinc-950 flex items-center justify-between group"
            >
              <div className="flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-zinc-500" strokeWidth={1.5} />
                Create Project
              </div>
              <ArrowRight className="w-4 h-4 text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity" strokeWidth={1.5} />
            </button>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
              High-Priority Leads
            </CardTitle>
            <button 
              onClick={() => navigate('/leads')}
              className="text-xs text-zinc-500 hover:text-zinc-950 transition-colors"
            >
              View All
            </button>
          </CardHeader>
          <CardContent>
            {highPriorityLeads.length === 0 ? (
              <div className="text-sm text-zinc-500 text-center py-4">No leads yet</div>
            ) : (
              <div className="space-y-3">
                {highPriorityLeads.map((lead) => (
                  <div
                    key={lead.id}
                    className="p-3 rounded-sm border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 transition-colors cursor-pointer group"
                    onClick={() => navigate('/leads')}
                  >
                    <div className="flex items-start justify-between mb-1">
                      <div className="font-medium text-sm text-zinc-950">
                        {lead.first_name} {lead.last_name}
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="px-2 py-0.5 text-xs font-semibold rounded-sm bg-emerald-600 text-white">
                          {lead.lead_score || 0}
                        </span>
                      </div>
                    </div>
                    <div className="text-xs text-zinc-500">{lead.company}</div>
                    <div className="text-xs text-zinc-500 mt-1">{lead.job_title || 'N/A'}</div>
                    <div className="mt-2 flex items-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/sales-funnel/pricing-plans?leadId=${lead.id}`);
                        }}
                        className="px-2 py-1 text-xs font-medium bg-zinc-950 text-white rounded-sm hover:bg-zinc-800 transition-colors flex items-center gap-1"
                        data-testid={`start-sales-flow-${lead.id}`}
                      >
                        <DollarSign className="w-3 h-3" strokeWidth={1.5} />
                        Start Sales Flow
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
