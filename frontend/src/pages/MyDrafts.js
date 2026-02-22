import React, { useState, useEffect, useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { FileText, Clock, Trash2, ArrowRight, Plus, FileSignature, DollarSign, Users, Filter, Briefcase, CalendarDays, Receipt, FileCheck, Plane, Building2 } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

// Universal Draft type configuration - covers ALL modules
const DRAFT_TYPES = {
  // Sales Module
  pricing_plan: {
    label: 'Pricing Plan',
    icon: DollarSign,
    color: 'text-emerald-600 bg-emerald-100',
    continueUrl: (draft) => `/sales-funnel/pricing-plans?draft=${draft.id}`,
  },
  lead: {
    label: 'Lead',
    icon: Users,
    color: 'text-blue-600 bg-blue-100',
    continueUrl: (draft) => `/leads/new?draft=${draft.id}`,
  },
  leads: {
    label: 'Lead',
    icon: Users,
    color: 'text-blue-600 bg-blue-100',
    continueUrl: (draft) => draft.route || `/leads/new?draft=${draft.id}`,
  },
  sow: {
    label: 'Statement of Work',
    icon: FileSignature,
    color: 'text-purple-600 bg-purple-100',
    continueUrl: (draft) => draft.entity_id ? `/sales-funnel/sow/${draft.entity_id}?draft=${draft.id}` : `/sales-funnel/sow`,
  },
  quotation: {
    label: 'Quotation',
    icon: FileCheck,
    color: 'text-orange-600 bg-orange-100',
    continueUrl: (draft) => draft.route || `/sales-funnel/quotations?draft=${draft.id}`,
  },
  agreement: {
    label: 'Agreement',
    icon: FileSignature,
    color: 'text-indigo-600 bg-indigo-100',
    continueUrl: (draft) => draft.route || `/sales-funnel/agreements?draft=${draft.id}`,
  },
  // HR Module
  employees: {
    label: 'Employee',
    icon: Users,
    color: 'text-teal-600 bg-teal-100',
    continueUrl: (draft) => draft.route || `/employees/new?draft=${draft.id}`,
  },
  onboarding: {
    label: 'Onboarding',
    icon: Briefcase,
    color: 'text-cyan-600 bg-cyan-100',
    continueUrl: (draft) => draft.route || `/onboarding?draft=${draft.id}`,
  },
  leaves: {
    label: 'Leave Request',
    icon: CalendarDays,
    color: 'text-pink-600 bg-pink-100',
    continueUrl: (draft) => draft.route || `/my-leaves?draft=${draft.id}`,
  },
  payroll: {
    label: 'Payroll',
    icon: DollarSign,
    color: 'text-green-600 bg-green-100',
    continueUrl: (draft) => draft.route || `/ctc-payroll?draft=${draft.id}`,
  },
  // Projects Module
  projects: {
    label: 'Project',
    icon: Briefcase,
    color: 'text-violet-600 bg-violet-100',
    continueUrl: (draft) => draft.route || `/projects?draft=${draft.id}`,
  },
  consulting: {
    label: 'Consulting',
    icon: Building2,
    color: 'text-amber-600 bg-amber-100',
    continueUrl: (draft) => draft.route || `/projects?draft=${draft.id}`,
  },
  // Finance Module
  expenses: {
    label: 'Expense',
    icon: Receipt,
    color: 'text-red-600 bg-red-100',
    continueUrl: (draft) => draft.route || `/my-expenses?draft=${draft.id}`,
  },
  travel: {
    label: 'Travel Request',
    icon: Plane,
    color: 'text-sky-600 bg-sky-100',
    continueUrl: (draft) => draft.route || `/travel-requests?draft=${draft.id}`,
  },
  // Generic
  general: {
    label: 'Form',
    icon: FileText,
    color: 'text-gray-600 bg-gray-100',
    continueUrl: (draft) => draft.route || '/',
  },
};

const MyDrafts = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    fetchDrafts();
  }, [filter]);

  const fetchDrafts = async () => {
    try {
      const token = localStorage.getItem('token');
      const url = filter === 'all' 
        ? `${API}/drafts` 
        : `${API}/drafts?draft_type=${filter}`;
      
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setDrafts(data);
      }
    } catch (error) {
      console.error('Error fetching drafts:', error);
      toast.error('Failed to load drafts');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (draftId) => {
    if (!window.confirm('Are you sure you want to delete this draft?')) return;
    
    setDeleting(draftId);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/drafts/${draftId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success('Draft deleted');
        setDrafts(drafts.filter(d => d.id !== draftId));
      } else {
        toast.error('Failed to delete draft');
      }
    } catch (error) {
      toast.error('Failed to delete draft');
    } finally {
      setDeleting(null);
    }
  };

  const handleContinue = (draft) => {
    // First try to use the stored route directly (universal auto-save)
    if (draft.route && draft.route !== '/') {
      const url = draft.route.includes('?') 
        ? `${draft.route}&draft=${draft.id}`
        : `${draft.route}?draft=${draft.id}`;
      navigate(url);
      return;
    }
    
    // Fall back to draft type configuration
    const config = DRAFT_TYPES[draft.draft_type] || DRAFT_TYPES[draft.module];
    if (config) {
      navigate(config.continueUrl(draft));
    } else {
      // Ultimate fallback - just use the route
      navigate(draft.route || '/');
    }
  };

  const getTimeSince = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hr ago`;
    if (diffDays < 7) return `${diffDays} days ago`;
    return format(date, 'MMM d, yyyy');
  };

  const DraftCard = ({ draft }) => {
    // Try draft_type first, then module for universal drafts
    const config = DRAFT_TYPES[draft.draft_type] || DRAFT_TYPES[draft.module] || {
      label: draft.draft_type || draft.module || 'Draft',
      icon: FileText,
      color: 'text-gray-600 bg-gray-100',
    };
    const Icon = config.icon;
    
    return (
      <Card className="hover:shadow-md transition-shadow" data-testid={`draft-card-${draft.id}`}>
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 flex-1 min-w-0">
              <div className={`p-2 rounded-lg ${config.color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-zinc-900 dark:text-zinc-100 truncate">
                  {draft.title || 'Untitled Draft'}
                </h3>
                <div className="flex items-center gap-2 mt-1 text-sm text-zinc-500 flex-wrap">
                  <span className="px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 rounded text-xs">
                    {config.label}
                  </span>
                  {draft.step > 0 && (
                    <span className="px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded text-xs">
                      Step {draft.step}
                    </span>
                  )}
                  {draft.active_tab && (
                    <span className="px-2 py-0.5 bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded text-xs">
                      {draft.active_tab}
                    </span>
                  )}
                  {draft.version > 1 && (
                    <span className="px-2 py-0.5 bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 rounded text-xs">
                      v{draft.version}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1 mt-2 text-xs text-zinc-400">
                  <Clock className="w-3 h-3" />
                  <span>Last edited {getTimeSince(draft.last_saved_at || draft.updated_at)}</span>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleContinue(draft)}
                className="gap-1"
                data-testid={`continue-draft-${draft.id}`}
              >
                Continue
                <ArrowRight className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleDelete(draft.id)}
                disabled={deleting === draft.id}
                className="text-red-500 hover:text-red-600 hover:bg-red-50"
                data-testid={`delete-draft-${draft.id}`}
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-6 p-6" data-testid="my-drafts-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">My Drafts</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Continue working on your saved drafts
          </p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        <Button
          variant={filter === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('all')}
          data-testid="filter-all"
        >
          All Drafts
        </Button>
        {Object.entries(DRAFT_TYPES).map(([key, config]) => (
          <Button
            key={key}
            variant={filter === key ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter(key)}
            data-testid={`filter-${key}`}
          >
            <config.icon className="w-4 h-4 mr-1" />
            {config.label}
          </Button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : drafts.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <FileText className="w-12 h-12 mx-auto text-zinc-300 dark:text-zinc-600 mb-4" />
              <h3 className="text-lg font-medium text-zinc-900 dark:text-zinc-100">
                No drafts found
              </h3>
              <p className="text-sm text-zinc-500 mt-1">
                {filter === 'all' 
                  ? "You don't have any saved drafts yet"
                  : `No ${DRAFT_TYPES[filter]?.label || filter} drafts found`}
              </p>
              <div className="mt-6 flex justify-center gap-3">
                <Link to="/sales-funnel/pricing-plans">
                  <Button variant="outline" className="gap-2">
                    <Plus className="w-4 h-4" />
                    New Pricing Plan
                  </Button>
                </Link>
                <Link to="/leads">
                  <Button variant="outline" className="gap-2">
                    <Plus className="w-4 h-4" />
                    New Lead
                  </Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {drafts.map(draft => (
            <DraftCard key={draft.id} draft={draft} />
          ))}
        </div>
      )}
    </div>
  );
};

export default MyDrafts;
