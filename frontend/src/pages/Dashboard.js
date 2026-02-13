import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Users, UserCheck, TrendingUp, Briefcase, Target } from 'lucide-react';
import { toast } from 'sonner';

const Dashboard = () => {
  const { user } = useContext(AuthContext);
  const [stats, setStats] = useState(null);
  const [highPriorityLeads, setHighPriorityLeads] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    fetchHighPriorityLeads();
  }, []);

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

  const statCards = [
    {
      title: 'Total Leads',
      value: stats?.total_leads || 0,
      icon: Users,
      color: 'text-zinc-950',
    },
    {
      title: 'New Leads',
      value: stats?.new_leads || 0,
      icon: Target,
      color: 'text-blue-600',
    },
    {
      title: 'Qualified Leads',
      value: stats?.qualified_leads || 0,
      icon: UserCheck,
      color: 'text-purple-600',
    },
    {
      title: 'Closed Deals',
      value: stats?.closed_deals || 0,
      icon: TrendingUp,
      color: 'text-emerald-600',
    },
    {
      title: 'Active Projects',
      value: stats?.active_projects || 0,
      icon: Briefcase,
      color: 'text-zinc-950',
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
              className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors"
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                  {stat.title}
                </CardTitle>
                <Icon className={`w-4 h-4 ${stat.color}`} strokeWidth={1.5} />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold text-zinc-950 data-text">
                  {stat.value}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
              Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <button
              onClick={() => (window.location.href = '/leads')}
              data-testid="quick-action-add-lead"
              className="w-full text-left px-4 py-3 rounded-sm border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 transition-colors text-sm text-zinc-950"
            >
              Add New Lead
            </button>
            <button
              onClick={() => (window.location.href = '/projects')}
              data-testid="quick-action-create-project"
              className="w-full text-left px-4 py-3 rounded-sm border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 transition-colors text-sm text-zinc-950"
            >
              Create Project
            </button>
            <button
              onClick={() => (window.location.href = '/meetings')}
              data-testid="quick-action-schedule-meeting"
              className="w-full text-left px-4 py-3 rounded-sm border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 transition-colors text-sm text-zinc-950"
            >
              Schedule Meeting
            </button>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
              Access Level
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">Role</div>
                <div className="text-lg font-medium text-zinc-950">{user?.role}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">
                  Permissions
                </div>
                <div className="text-sm text-zinc-600">
                  {user?.role === 'admin' && 'Full access to all modules'}
                  {user?.role === 'manager' && 'View and download reports'}
                  {user?.role === 'executive' && 'Edit and view access'}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
