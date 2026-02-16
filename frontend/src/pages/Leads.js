import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Mail, Phone, Briefcase, ExternalLink, Bell, TrendingUp, DollarSign, Eye } from 'lucide-react';
import { toast } from 'sonner';
import ViewToggle from '../components/ViewToggle';

const Leads = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState('');
  const [suggestions, setSuggestions] = useState({});
  const [viewMode, setViewMode] = useState('card');
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    company: '',
    job_title: '',
    email: '',
    phone: '',
    linkedin_url: '',
    source: '',
    notes: '',
  });

  useEffect(() => {
    fetchLeads();
  }, [selectedStatus]);

  const fetchLeads = async () => {
    try {
      const params = selectedStatus ? { status: selectedStatus } : {};
      const response = await axios.get(`${API}/leads`, { params });
      // Sort by lead score descending
      const sortedLeads = response.data.sort((a, b) => (b.lead_score || 0) - (a.lead_score || 0));
      setLeads(sortedLeads);
      
      // Fetch suggestions for high-scoring leads
      sortedLeads.forEach(async (lead) => {
        if (lead.lead_score >= 60) {
          try {
            const suggestionsRes = await axios.get(`${API}/leads/${lead.id}/suggestions`);
            if (suggestionsRes.data.suggestions.length > 0) {
              setSuggestions(prev => ({
                ...prev,
                [lead.id]: suggestionsRes.data.suggestions
              }));
            }
          } catch (error) {
            console.error('Failed to fetch suggestions for lead:', lead.id);
          }
        }
      });
    } catch (error) {
      toast.error('Failed to fetch leads');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/leads`, formData);
      toast.success('Lead created successfully');
      setDialogOpen(false);
      setFormData({
        first_name: '',
        last_name: '',
        company: '',
        job_title: '',
        email: '',
        phone: '',
        linkedin_url: '',
        source: '',
        notes: '',
      });
      fetchLeads();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create lead');
    }
  };

  const getStatusBadge = (status) => {
    const statusStyles = {
      new: 'bg-zinc-100 text-zinc-600',
      contacted: 'bg-blue-50 text-blue-700',
      qualified: 'bg-purple-50 text-purple-700',
      proposal: 'bg-yellow-50 text-yellow-700',
      agreement: 'bg-orange-50 text-orange-700',
      closed: 'bg-emerald-50 text-emerald-700',
      lost: 'bg-red-50 text-red-700',
    };
    return statusStyles[status] || statusStyles.new;
  };

  const getScoreBadge = (score) => {
    if (score >= 80) return { color: 'bg-emerald-600', label: 'Hot', text: 'text-white' };
    if (score >= 60) return { color: 'bg-blue-600', label: 'Warm', text: 'text-white' };
    if (score >= 40) return { color: 'bg-yellow-600', label: 'Medium', text: 'text-white' };
    return { color: 'bg-zinc-400', label: 'Cold', text: 'text-white' };
  };

  const canEdit = user?.role !== 'manager';

  return (
    <div data-testid="leads-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
            Leads
          </h1>
          <p className="text-zinc-500">Manage your sales pipeline</p>
        </div>
        <div className="flex items-center gap-3">
          <ViewToggle viewMode={viewMode} onChange={setViewMode} />
          {canEdit && (
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button
                  data-testid="add-lead-button"
                  className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                >
                  <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Add Lead
                </Button>
              </DialogTrigger>
            <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
                  Add New Lead
                </DialogTitle>
                <DialogDescription className="text-zinc-500">
                  Enter lead information to add to your pipeline
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="first_name" className="text-sm font-medium text-zinc-950">
                      First Name *
                    </Label>
                    <Input
                      id="first_name"
                      data-testid="lead-first-name"
                      value={formData.first_name}
                      onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                      required
                      className="rounded-sm border-zinc-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name" className="text-sm font-medium text-zinc-950">
                      Last Name *
                    </Label>
                    <Input
                      id="last_name"
                      data-testid="lead-last-name"
                      value={formData.last_name}
                      onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                      required
                      className="rounded-sm border-zinc-200"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="company" className="text-sm font-medium text-zinc-950">
                    Company *
                  </Label>
                  <Input
                    id="company"
                    data-testid="lead-company"
                    value={formData.company}
                    onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                    required
                    className="rounded-sm border-zinc-200"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="job_title" className="text-sm font-medium text-zinc-950">
                    Job Title
                  </Label>
                  <Input
                    id="job_title"
                    data-testid="lead-job-title"
                    value={formData.job_title}
                    onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                    className="rounded-sm border-zinc-200"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-sm font-medium text-zinc-950">
                      Email
                    </Label>
                    <Input
                      id="email"
                      data-testid="lead-email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="rounded-sm border-zinc-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone" className="text-sm font-medium text-zinc-950">
                      Phone
                    </Label>
                    <Input
                      id="phone"
                      data-testid="lead-phone"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      className="rounded-sm border-zinc-200"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="linkedin_url" className="text-sm font-medium text-zinc-950">
                    LinkedIn URL
                  </Label>
                  <Input
                    id="linkedin_url"
                    data-testid="lead-linkedin"
                    value={formData.linkedin_url}
                    onChange={(e) => setFormData({ ...formData, linkedin_url: e.target.value })}
                    placeholder="https://linkedin.com/in/..."
                    className="rounded-sm border-zinc-200"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="source" className="text-sm font-medium text-zinc-950">
                    Lead Source
                  </Label>
                  <Input
                    id="source"
                    data-testid="lead-source"
                    value={formData.source}
                    onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                    placeholder="e.g., Website, Referral, RocketReach"
                    className="rounded-sm border-zinc-200"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="notes" className="text-sm font-medium text-zinc-950">
                    Notes
                  </Label>
                  <textarea
                    id="notes"
                    data-testid="lead-notes"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                  />
                </div>

                <Button
                  type="submit"
                  data-testid="submit-lead-button"
                  className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                >
                  Create Lead
                </Button>
              </form>
            </DialogContent>
          </Dialog>
          )}
        </div>
      </div>

      <div className="mb-6">
        <div className="flex gap-2">
          {['', 'new', 'contacted', 'qualified', 'proposal', 'agreement', 'closed', 'lost'].map(
            (status) => (
              <button
                key={status}
                data-testid={`filter-${status || 'all'}`}
                onClick={() => setSelectedStatus(status)}
                className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-colors ${
                  selectedStatus === status
                    ? 'bg-zinc-950 text-white'
                    : 'bg-white text-zinc-600 border border-zinc-200 hover:bg-zinc-50'
                }`}
              >
                {status ? status.charAt(0).toUpperCase() + status.slice(1) : 'All'}
              </button>
            )
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-zinc-500">Loading leads...</div>
        </div>
      ) : leads.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <p className="text-zinc-500 mb-4">No leads found</p>
            {canEdit && (
              <Button
                onClick={() => setDialogOpen(true)}
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Add Your First Lead
              </Button>
            )}
          </CardContent>
        </Card>
      ) : viewMode === 'list' ? (
        /* List View */
        <div className="border border-zinc-200 rounded-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-zinc-50 border-b border-zinc-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Name</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Company</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Email</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Score</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Status</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {leads.map((lead) => {
                const scoreBadge = getScoreBadge(lead.lead_score || 0);
                return (
                  <tr 
                    key={lead.id} 
                    className="hover:bg-zinc-50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/sales-funnel/pricing-plans?leadId=${lead.id}`)}
                    data-testid={`lead-row-${lead.id}`}
                  >
                    <td className="px-4 py-3">
                      <span className="font-medium text-zinc-900">{lead.first_name} {lead.last_name}</span>
                      {lead.job_title && <p className="text-xs text-zinc-500">{lead.job_title}</p>}
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-600">{lead.company}</td>
                    <td className="px-4 py-3 text-sm text-zinc-600">{lead.email}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-sm ${scoreBadge.color} ${scoreBadge.text}`}>
                        {lead.lead_score || 0} - {scoreBadge.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-sm ${getStatusStyle(lead.status)}`}>
                        {lead.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex justify-end gap-2">
                        <Button
                          onClick={() => navigate(`/sales-funnel/pricing-plans?leadId=${lead.id}`)}
                          size="sm"
                          variant="outline"
                          className="rounded-sm h-8"
                        >
                          <TrendingUp className="w-3 h-3" />
                        </Button>
                        {lead.linkedin_url && (
                          <Button
                            onClick={() => window.open(lead.linkedin_url, '_blank')}
                            size="sm"
                            variant="outline"
                            className="rounded-sm h-8"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        /* Card View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {leads.map((lead) => {
            const scoreBadge = getScoreBadge(lead.lead_score || 0);
            const leadSuggestions = suggestions[lead.id] || [];
            return (
              <Card
                key={lead.id}
                data-testid={`lead-card-${lead.id}`}
                className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors cursor-pointer"
                onClick={() => navigate(`/sales-funnel/pricing-plans?leadId=${lead.id}`)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-base font-semibold text-zinc-950">
                        {lead.first_name} {lead.last_name}
                      </CardTitle>
                      <div className="flex items-center gap-2 text-sm text-zinc-500 mt-1">
                        <Briefcase className="w-3 h-3" strokeWidth={1.5} />
                        {lead.job_title || 'N/A'}
                      </div>
                    </div>
                    <div className="flex flex-col gap-2">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded-sm ${getStatusBadge(
                          lead.status
                        )}`}
                      >
                        {lead.status}
                      </span>
                      <div className="flex items-center gap-1">
                        <span
                          className={`px-2 py-1 text-xs font-semibold rounded-sm ${scoreBadge.color} ${scoreBadge.text}`}
                        >
                          {lead.lead_score || 0}
                        </span>
                        <span className="text-xs text-zinc-500 data-text">{scoreBadge.label}</span>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="text-sm font-medium text-zinc-950">{lead.company}</div>
                  
                  {/* Automated Suggestions */}
                  {leadSuggestions.length > 0 && (
                    <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-sm">
                      <div className="flex items-start gap-2">
                        <TrendingUp className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" strokeWidth={1.5} />
                        <div className="flex-1">
                          <div className="text-xs font-semibold text-blue-900 mb-1">
                            Suggested Action
                          </div>
                          <p className="text-xs text-blue-700 leading-relaxed">
                            {leadSuggestions[0].suggestion_message}
                          </p>
                          <div className="mt-2 flex gap-2">
                            <button
                              onClick={() => window.location.href = '/email-templates'}
                              className="px-2 py-1 text-xs font-medium bg-blue-600 text-white rounded-sm hover:bg-blue-700 transition-colors"
                            >
                              View Templates
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {lead.email && (
                    <div className="flex items-center gap-2 text-sm text-zinc-600">
                      <Mail className="w-3 h-3" strokeWidth={1.5} />
                      <span className="truncate">{lead.email}</span>
                    </div>
                  )}
                  {lead.phone && (
                    <div className="flex items-center gap-2 text-sm text-zinc-600">
                      <Phone className="w-3 h-3" strokeWidth={1.5} />
                      {lead.phone}
                    </div>
                  )}
                  {lead.linkedin_url && (
                    <a
                      href={lead.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
                    >
                      <ExternalLink className="w-3 h-3" strokeWidth={1.5} />
                      LinkedIn Profile
                    </a>
                  )}
                  {lead.source && (
                    <div className="text-xs text-zinc-500 mt-2">Source: {lead.source}</div>
                  )}
                  {lead.score_breakdown && (
                    <div className="pt-2 mt-2 border-t border-zinc-200">
                      <div className="text-xs uppercase tracking-wide text-zinc-500 mb-1">
                        Score Breakdown
                      </div>
                      <div className="text-xs text-zinc-600 space-y-0.5">
                        <div>Title: {lead.score_breakdown.title_score}/40</div>
                        <div>Contact: {lead.score_breakdown.contact_score}/30</div>
                        <div>Engagement: {lead.score_breakdown.engagement_score}/30</div>
                      </div>
                    </div>
                  )}
                  
                  {/* Start Sales Flow Button */}
                  {canEdit && lead.status !== 'closed' && lead.status !== 'lost' && (
                    <div className="pt-3 mt-3 border-t border-zinc-200">
                      <button
                        onClick={() => navigate(`/sales-funnel/pricing-plans?leadId=${lead.id}`)}
                        className="w-full px-3 py-2 text-xs font-medium bg-zinc-950 text-white rounded-sm hover:bg-zinc-800 transition-colors flex items-center justify-center gap-2"
                        data-testid={`start-sales-flow-${lead.id}`}
                      >
                        <DollarSign className="w-3 h-3" strokeWidth={1.5} />
                        Start Sales Flow
                      </button>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Leads;
