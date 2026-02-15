import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { 
  ArrowRight, Search, FileText, Clock, CheckCircle, 
  AlertCircle, Loader2, Eye, Edit2, Send, Filter,
  Building2, Calendar, Users, MoreHorizontal
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const STATUS_CONFIG = {
  draft: { label: 'Draft', color: 'bg-zinc-100 text-zinc-700', icon: FileText },
  pending_handover: { label: 'Pending Handover', color: 'bg-yellow-100 text-yellow-700', icon: Clock },
  handed_over: { label: 'Handed Over', color: 'bg-blue-100 text-blue-700', icon: Send },
  in_progress: { label: 'In Progress', color: 'bg-blue-100 text-blue-700', icon: Clock },
  completed: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
};

const SalesSOWList = () => {
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [loading, setLoading] = useState(true);
  const [sowList, setSowList] = useState([]);
  const [pricingPlans, setPricingPlans] = useState([]);
  const [leads, setLeads] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [sowRes, plansRes, leadsRes] = await Promise.all([
        axios.get(`${API}/enhanced-sow/list?role=sales`).catch(() => ({ data: [] })),
        axios.get(`${API}/pricing-plans`),
        axios.get(`${API}/leads`)
      ]);
      
      setSowList(sowRes.data || []);
      setPricingPlans(plansRes.data || []);
      setLeads(leadsRes.data || []);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load SOW list');
    } finally {
      setLoading(false);
    }
  };

  // Get lead info for a SOW
  const getLeadInfo = (sow) => {
    const plan = pricingPlans.find(p => p.id === sow.pricing_plan_id);
    if (plan?.lead_id) {
      return leads.find(l => l.id === plan.lead_id);
    }
    return leads.find(l => l.id === sow.lead_id);
  };

  // Get pricing plan for a SOW
  const getPlanInfo = (sow) => {
    return pricingPlans.find(p => p.id === sow.pricing_plan_id);
  };

  // Determine SOW status
  const getSOWStatus = (sow) => {
    if (sow.consulting_kickoff_complete) return 'in_progress';
    if (sow.sales_handover_complete) return 'handed_over';
    return 'draft';
  };

  // Filter SOWs
  const filteredSOWs = sowList.filter(sow => {
    const lead = getLeadInfo(sow);
    const plan = getPlanInfo(sow);
    const status = getSOWStatus(sow);
    
    // Search filter
    const searchLower = searchQuery.toLowerCase();
    const matchesSearch = !searchQuery || 
      lead?.company?.toLowerCase().includes(searchLower) ||
      lead?.first_name?.toLowerCase().includes(searchLower) ||
      lead?.last_name?.toLowerCase().includes(searchLower) ||
      plan?.title?.toLowerCase().includes(searchLower);
    
    // Status filter
    const matchesStatus = statusFilter === 'all' || status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  // Stats
  const stats = {
    total: sowList.length,
    draft: sowList.filter(s => getSOWStatus(s) === 'draft').length,
    handedOver: sowList.filter(s => getSOWStatus(s) === 'handed_over').length,
    inProgress: sowList.filter(s => getSOWStatus(s) === 'in_progress').length,
  };

  const handleCompleteHandover = async (sowId) => {
    try {
      await axios.post(`${API}/enhanced-sow/${sowId}/complete-handover`, null, {
        params: {
          current_user_id: user?.id,
          current_user_role: user?.role
        }
      });
      toast.success('SOW handed over to consulting team');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to complete handover');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div data-testid="sales-sow-list-page">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          Scope of Work
        </h1>
        <p className="text-zinc-500">
          Manage and track all project scopes created by sales team
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-zinc-500 uppercase tracking-wide">Total SOWs</div>
            <div className="text-2xl font-semibold text-zinc-950">{stats.total}</div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 bg-zinc-50 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-zinc-500 uppercase tracking-wide">Draft</div>
            <div className="text-2xl font-semibold text-zinc-700">{stats.draft}</div>
          </CardContent>
        </Card>
        <Card className="border-blue-200 bg-blue-50 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-blue-600 uppercase tracking-wide">Handed Over</div>
            <div className="text-2xl font-semibold text-blue-700">{stats.handedOver}</div>
          </CardContent>
        </Card>
        <Card className="border-emerald-200 bg-emerald-50 shadow-none rounded-sm">
          <CardContent className="py-3 px-4">
            <div className="text-xs text-emerald-600 uppercase tracking-wide">In Progress</div>
            <div className="text-2xl font-semibold text-emerald-700">{stats.inProgress}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center justify-between mb-4 gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by client, company..."
            className="pl-10 rounded-sm border-zinc-200"
            data-testid="sow-search-input"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-zinc-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm"
            data-testid="status-filter"
          >
            <option value="all">All Status</option>
            <option value="draft">Draft</option>
            <option value="handed_over">Handed Over</option>
            <option value="in_progress">In Progress</option>
          </select>
        </div>
      </div>

      {/* SOW List */}
      {filteredSOWs.length > 0 ? (
        <div className="space-y-3">
          {filteredSOWs.map(sow => {
            const lead = getLeadInfo(sow);
            const plan = getPlanInfo(sow);
            const status = getSOWStatus(sow);
            const statusConfig = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
            
            return (
              <Card 
                key={sow.id} 
                className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors"
                data-testid={`sow-card-${sow.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 flex-1">
                      <div className="w-10 h-10 rounded-sm bg-zinc-100 flex items-center justify-center">
                        <FileText className="w-5 h-5 text-zinc-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-zinc-900">
                            {lead ? `${lead.first_name} ${lead.last_name}` : 'Unknown Client'}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded-sm ${statusConfig.color}`}>
                            {statusConfig.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-zinc-500">
                          {lead?.company && (
                            <span className="flex items-center gap-1">
                              <Building2 className="w-3.5 h-3.5" />
                              {lead.company}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Users className="w-3.5 h-3.5" />
                            {sow.scopes?.length || 0} scopes
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5" />
                            {sow.created_at ? format(new Date(sow.created_at), 'MMM d, yyyy') : 'N/A'}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Button
                        onClick={() => navigate(`/sales-funnel/scope-selection/${sow.pricing_plan_id}`)}
                        variant="ghost"
                        size="sm"
                        className="text-zinc-600 hover:text-zinc-900"
                        data-testid={`edit-sow-${sow.id}`}
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button
                        onClick={() => navigate(`/sales-funnel/sow-review/${sow.pricing_plan_id}`)}
                        variant="ghost"
                        size="sm"
                        className="text-zinc-600 hover:text-zinc-900"
                        data-testid={`view-sow-${sow.id}`}
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      {status === 'draft' && (
                        <Button
                          onClick={() => handleCompleteHandover(sow.id)}
                          variant="outline"
                          size="sm"
                          className="text-blue-600 border-blue-200 hover:bg-blue-50"
                          data-testid={`handover-sow-${sow.id}`}
                        >
                          <Send className="w-4 h-4 mr-1" />
                          Handover
                        </Button>
                      )}
                      <Button
                        onClick={() => navigate(`/sales-funnel/quotations?sow_id=${sow.id}`)}
                        size="sm"
                        className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                        data-testid={`quotation-sow-${sow.id}`}
                      >
                        Quotation
                        <ArrowRight className="w-4 h-4 ml-1" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FileText className="w-16 h-16 text-zinc-300 mb-4" />
            <h3 className="text-lg font-medium text-zinc-700 mb-2">No SOWs Found</h3>
            <p className="text-zinc-500 mb-4">
              {searchQuery || statusFilter !== 'all' 
                ? 'No SOWs match your filters' 
                : 'Create your first SOW from a pricing plan'}
            </p>
            <Button
              onClick={() => navigate('/sales-funnel/pricing-plans')}
              className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              Go to Pricing Plans
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default SalesSOWList;
