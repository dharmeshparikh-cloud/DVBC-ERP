import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { 
  TrendingUp, Users, FileText, CheckCircle, Clock, 
  DollarSign, Target, ArrowRight, Send, Building2
} from 'lucide-react';
import { Link } from 'react-router-dom';

const SalesDashboard = () => {
  const { user } = useContext(AuthContext);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API}/api/stats/sales-dashboard`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch sales stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-zinc-900"></div>
      </div>
    );
  }

  const pipeline = stats?.pipeline || {};
  const clients = stats?.clients || {};

  return (
    <div className="space-y-6" data-testid="sales-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Sales Dashboard</h1>
          <p className="text-sm text-zinc-500">Track your pipeline, conversions and revenue</p>
        </div>
        <Badge className="bg-blue-100 text-blue-700">
          {stats?.conversion_rate || 0}% Conversion Rate
        </Badge>
      </div>

      {/* Pipeline Funnel */}
      <Card className="border-zinc-200">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Target className="w-4 h-4" />
            Sales Pipeline
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-6 gap-2">
            {[
              { label: 'New', count: pipeline.new, color: 'bg-gray-100 text-gray-700' },
              { label: 'Contacted', count: pipeline.contacted, color: 'bg-blue-100 text-blue-700' },
              { label: 'Qualified', count: pipeline.qualified, color: 'bg-indigo-100 text-indigo-700' },
              { label: 'Proposal', count: pipeline.proposal, color: 'bg-purple-100 text-purple-700' },
              { label: 'Closed', count: pipeline.closed, color: 'bg-green-100 text-green-700' },
              { label: 'Total', count: pipeline.total, color: 'bg-zinc-900 text-white' },
            ].map((stage, i) => (
              <div key={i} className="text-center">
                <div className={`rounded-lg py-3 px-2 ${stage.color}`}>
                  <p className="text-2xl font-bold">{stage.count || 0}</p>
                  <p className="text-xs mt-1">{stage.label}</p>
                </div>
                {i < 5 && (
                  <ArrowRight className="w-4 h-4 mx-auto mt-2 text-zinc-300" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4">
        {/* My Clients */}
        <Card className="border-zinc-200 hover:border-zinc-300 transition-colors">
          <Link to="/clients" className="block">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-zinc-500">My Clients</p>
                  <p className="text-3xl font-bold text-zinc-900 mt-1">{clients.my_clients || 0}</p>
                  <p className="text-xs text-zinc-400 mt-1">of {clients.total_clients || 0} total</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
                  <Building2 className="w-6 h-6 text-emerald-600" />
                </div>
              </div>
            </CardContent>
          </Link>
        </Card>

        {/* Pending Quotations */}
        <Card className="border-zinc-200 hover:border-zinc-300 transition-colors">
          <Link to="/quotations" className="block">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-zinc-500">Pending Quotations</p>
                  <p className="text-3xl font-bold text-zinc-900 mt-1">{stats?.quotations?.pending || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center">
                  <FileText className="w-6 h-6 text-amber-600" />
                </div>
              </div>
            </CardContent>
          </Link>
        </Card>

        {/* Pending Agreements */}
        <Card className="border-zinc-200 hover:border-zinc-300 transition-colors">
          <Link to="/agreements" className="block">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-zinc-500">Pending Agreements</p>
                  <p className="text-3xl font-bold text-zinc-900 mt-1">{stats?.agreements?.pending || 0}</p>
                  <p className="text-xs text-green-600 mt-1">{stats?.agreements?.approved || 0} approved</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                  <CheckCircle className="w-6 h-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Link>
        </Card>

        {/* Revenue */}
        <Card className="border-zinc-200">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Total Revenue</p>
                <p className="text-3xl font-bold text-zinc-900 mt-1">
                  ₹{((stats?.revenue?.total || 0) / 100000).toFixed(1)}L
                </p>
              </div>
              <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Kickoff Requests */}
      <Card className="border-zinc-200">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Send className="w-4 h-4" />
              Kickoff Requests
            </CardTitle>
            <Link to="/kickoff-requests" className="text-sm text-blue-600 hover:underline">
              View All
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between p-4 bg-zinc-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center">
                <Clock className="w-5 h-5 text-orange-600" />
              </div>
              <div>
                <p className="font-medium text-zinc-900">Pending Handoffs</p>
                <p className="text-sm text-zinc-500">Awaiting PM acceptance</p>
              </div>
            </div>
            <Badge className="bg-orange-100 text-orange-700 text-lg px-4">
              {stats?.kickoffs?.pending || 0}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'New Lead', href: '/leads', icon: Users, color: 'bg-blue-600' },
          { label: 'Create Quotation', href: '/quotations', icon: FileText, color: 'bg-purple-600' },
          { label: 'View Pipeline', href: '/sales-funnel', icon: TrendingUp, color: 'bg-indigo-600' },
          { label: 'Send Kickoff', href: '/kickoff-requests', icon: Send, color: 'bg-green-600' },
        ].map((action, i) => (
          <Link key={i} to={action.href}>
            <Card className="border-zinc-200 hover:border-zinc-300 transition-colors cursor-pointer">
              <CardContent className="pt-4 pb-4 flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg ${action.color} flex items-center justify-center`}>
                  <action.icon className="w-5 h-5 text-white" />
                </div>
                <span className="font-medium text-zinc-700">{action.label}</span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default SalesDashboard;
