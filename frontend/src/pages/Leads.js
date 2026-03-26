import React, { useState, useContext, useMemo, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../App';
import { usePermissions } from '../contexts/PermissionContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Mail, Phone, Briefcase, ExternalLink, TrendingUp, DollarSign, Search, Calendar, Upload, FileSpreadsheet, Download, X, FolderOpen, Pause, Play, CheckCircle, Circle, Building2, ArrowRightLeft } from 'lucide-react';
import { toast } from 'sonner';
import ViewToggle from '../components/ViewToggle';
import FollowUpActionButton from '../components/FollowUpActionButton';
import PageHeader from '../components/ui/page-header';
import useDraft from '../hooks/useDraft';
import DraftSelector, { DraftIndicator } from '../components/DraftSelector';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/tooltip';
import { useQueryClient } from '@tanstack/react-query';
import { GovernedDropdown } from '../components/GovernedDropdown';
import { useIndustryOptions, useLeadSources, useLeadStatusOptions } from '../hooks/useSOWsByProject';
import { LeadsTable } from '../components/sales';
import {
  useLeads as useLeadsQuery,
  useBulkLeadProgress,
  useLeadProgress,
  useCreateLead,
  useUpdateLead,
  usePauseLead,
  useResumeLead,
  useBulkCreateLeads,
  leadKeys,
} from '../hooks/useLeads';

// Funnel Progress Indicator Component
const FunnelProgressIndicator = ({ progress, onClick }) => {
  if (!progress || !progress.completed_steps) {
    return <span className="text-xs text-zinc-400">--</span>;
  }

  const steps = [
    { key: 'meeting', label: 'Meeting', abbr: 'M' },
    { key: 'pricing', label: 'Pricing', abbr: 'P' },
    { key: 'sow', label: 'SOW', abbr: 'S' },
    { key: 'quotation', label: 'Quote', abbr: 'Q' },
    { key: 'agreement', label: 'Agreement', abbr: 'A' },
    { key: 'kickoff', label: 'Kickoff', abbr: 'K' },
    { key: 'project', label: 'Project', abbr: 'P' },
  ];

  const completedCount = progress.completed_count || 1;
  const totalSteps = progress.total_steps || 9;
  const percentage = progress.progress_percentage || 0;

  // Determine stage label
  const getStageLabel = () => {
    if (progress.project) return 'Complete';
    if (progress.kickoff) return 'Kickoff';
    if (progress.agreement) return 'Agreement';
    if (progress.quotation) return 'Quotation';
    if (progress.sow) return 'SOW';
    if (progress.pricing) return 'Pricing';
    if (progress.meeting) return 'Meeting';
    return 'Lead';
  };

  // Get stage color
  const getStageColor = () => {
    if (progress.project) return 'bg-emerald-500';
    if (progress.kickoff) return 'bg-purple-500';
    if (progress.agreement) return 'bg-blue-500';
    if (progress.quotation) return 'bg-cyan-500';
    if (progress.sow) return 'bg-teal-500';
    if (progress.pricing) return 'bg-amber-500';
    if (progress.meeting) return 'bg-orange-500';
    return 'bg-zinc-400';
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div 
            className="flex flex-col gap-1 cursor-pointer hover:opacity-80 transition-opacity min-w-[100px]"
            onClick={onClick}
            data-testid="funnel-progress-indicator"
          >
            {/* Progress Bar */}
            <div className="h-1.5 w-full bg-zinc-100 rounded-full overflow-hidden">
              <div 
                className={`h-full ${getStageColor()} transition-all duration-300`}
                style={{ width: `${percentage}%` }}
              />
            </div>
            {/* Stage Label */}
            <div className="flex items-center justify-between">
              <span className={`text-[10px] font-medium ${getStageColor().replace('bg-', 'text-').replace('-500', '-600')}`}>
                {getStageLabel()}
              </span>
              <span className="text-[10px] text-zinc-400">
                {completedCount}/{totalSteps}
              </span>
            </div>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="p-3 max-w-xs">
          <div className="space-y-2">
            <div className="text-xs font-semibold">Funnel Progress</div>
            <div className="flex flex-wrap gap-1">
              {(steps || []).map((step) => (
                <div 
                  key={step.key}
                  className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] ${
                    progress[step.key] 
                      ? 'bg-emerald-100 text-emerald-700' 
                      : 'bg-zinc-100 text-zinc-400'
                  }`}
                >
                  {progress[step.key] ? (
                    <CheckCircle className="w-2.5 h-2.5" />
                  ) : (
                    <Circle className="w-2.5 h-2.5" />
                  )}
                  {step.label}
                </div>
              ))}
            </div>
            <div className="text-[10px] text-zinc-500 pt-1 border-t">
              Click to open Sales Funnel
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

const Leads = () => {
  const { user } = useContext(AuthContext);
  const { isManagerOrAbove, canApproveRequests, level } = usePermissions();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [csvDialogOpen, setCsvDialogOpen] = useState(false);
  const [csvData, setCsvData] = useState('');
  const [csvPreview, setCsvPreview] = useState([]);
  const fileInputRef = useRef(null);
  const [selectedStatus, setSelectedStatus] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [timelineFilter, setTimelineFilter] = useState('all');
  const [suggestions, setSuggestions] = useState({});
  const [viewMode, setViewMode] = useState('list'); // Default to list view
  const [editLead, setEditLead] = useState(null);
  
  // Auto-switch to card view on mobile
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) setViewMode('card');
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  const [showDraftSelector, setShowDraftSelector] = useState(false);

  // React Query hooks for data fetching
  const { data: leadsResponse, isLoading: loading, refetch: refetchLeads } = useLeadsQuery({ status: selectedStatus });
  const { data: leadProgress = {} } = useBulkLeadProgress();

  // Sort leads by lead score descending
  // API returns data as { items: [...] } or { leads: [...] } or just array
  const leads = useMemo(() => {
    const data = leadsResponse?.items || leadsResponse?.leads || leadsResponse || [];
    return Array.isArray(data) ? [...data].sort((a, b) => (b.lead_score || 0) - (a.lead_score || 0)) : [];
  }, [leadsResponse]);

  // React Query mutations
  const createLeadMutation = useCreateLead();
  const updateLeadMutation = useUpdateLead();
  const pauseLeadMutation = usePauseLead();
  const resumeLeadMutation = useResumeLead();
  const bulkCreateLeadsMutation = useBulkCreateLeads();
  
  // Reassign state
  const [reassignLead, setReassignLead] = useState(null);
  const [showReassignDialog, setShowReassignDialog] = useState(false);
  const [showBulkReassign, setShowBulkReassign] = useState(false);
  const [reassignUserId, setReassignUserId] = useState('');
  const [bulkFromUserId, setBulkFromUserId] = useState('');
  const [bulkToUserId, setBulkToUserId] = useState('');
  const [reassignReason, setReassignReason] = useState('');
  const [salesUsers, setSalesUsers] = useState([]);
  
  // Fetch sales team users for reassign dropdowns
  useEffect(() => {
    const fetchSalesUsers = async () => {
      try {
        const API = process.env.REACT_APP_BACKEND_URL;
        const token = localStorage.getItem('token');
        const res = await fetch(`${API}/api/leads/team-members`, { headers: { Authorization: `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          const users = Array.isArray(data) ? data : [];
          setSalesUsers(users);
        }
      } catch { /* silent */ }
    };
    fetchSalesUsers();
  }, []);

  // Reassign mutation
  const handleReassign = async () => {
    if (!reassignLead || !reassignUserId) return;
    try {
      const API = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('token');
      const res = await fetch(`${API}/api/leads/${reassignLead.id}/reassign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ new_owner_id: reassignUserId, reason: reassignReason, transfer_all_data: true }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
      const result = await res.json();
      toast.success(result.message);
      setShowReassignDialog(false);
      setReassignLead(null);
      setReassignUserId('');
      setReassignReason('');
      refetchLeads();
    } catch (e) {
      toast.error(e.message || 'Failed to reassign lead');
    }
  };
  
  // Bulk reassign mutation
  const handleBulkReassign = async () => {
    if (!bulkFromUserId || !bulkToUserId) return;
    try {
      const API = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('token');
      const res = await fetch(`${API}/api/leads/bulk-reassign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ from_user_id: bulkFromUserId, to_user_id: bulkToUserId, reason: reassignReason }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
      const result = await res.json();
      toast.success(result.message);
      setShowBulkReassign(false);
      setBulkFromUserId('');
      setBulkToUserId('');
      setReassignReason('');
      refetchLeads();
    } catch (e) {
      toast.error(e.message || 'Failed to bulk reassign');
    }
  };

  // Suggestions are now fetched via prefetching in a controlled way
  // We prefetch suggestions for high-scoring leads when the leads list loads
  useEffect(() => {
    if (leads.length > 0) {
      (leads || []).forEach((lead) => {
        if (lead.lead_score >= 60 && !suggestions[lead.id]) {
          // Prefetch suggestions query - it will be cached by React Query
          queryClient.prefetchQuery({
            queryKey: leadKeys.suggestions(lead.id),
            queryFn: async () => {
              const API = process.env.REACT_APP_BACKEND_URL;
              const token = localStorage.getItem('token');
              const headers = token ? { Authorization: `Bearer ${token}` } : {};
              const res = await fetch(`${API}/api/leads/${lead.id}/suggestions`, { headers });
              if (!res.ok) return [];
              const data = await res.json();
              return data?.suggestions || [];
            },
            staleTime: 10 * 60 * 1000,
          }).then((data) => {
            if (data?.length > 0) {
              setSuggestions(prev => ({ ...prev, [lead.id]: data }));
            }
          }).catch(() => {
            // Silently fail for suggestions
          });
        }
      });
    }
  }, [leads, queryClient, suggestions]);
  
  // Lead status options for dropdown filter
  const leadStatusOptions = [
    { value: '', label: 'All Leads' },
    { value: 'new', label: 'New' },
    { value: 'meeting', label: 'Meeting' },
    { value: 'pricing_plan', label: 'Pricing Plan' },
    { value: 'sow', label: 'SOW' },
    { value: 'quotation', label: 'Quotation' },
    { value: 'agreement', label: 'Agreement' },
    { value: 'payment', label: 'Payment' },
    { value: 'kickoff_request', label: 'Kickoff Request' },
    { value: 'kick_accept', label: 'Kick Accept' },
    { value: 'closed', label: 'Closed' },
    { value: 'paused', label: 'Paused' },
    { value: 'lost', label: 'Lost' }
  ];
  
  // Draft system for leads
  const generateLeadDraftTitle = useCallback((data) => {
    if (data.first_name || data.last_name || data.company) {
      return `${data.first_name || ''} ${data.last_name || ''} - ${data.company || 'New Lead'}`.trim();
    }
    return 'New Lead Draft';
  }, []);
  
  const {
    draftId,
    drafts,
    loadingDrafts,
    saving: savingDraft,
    lastSaved,
    loadDraft,
    saveDraft,
    autoSave,
    deleteDraft,
    convertDraft,
    clearDraft,
    registerFormDataGetter
  } = useDraft('lead', generateLeadDraftTitle);
  
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
    next_follow_up: '',
    follow_up_notes: '',
    // Company details (for Client Master integration)
    industry: '',
    website: '',
    city: '',
    state: '',
    country: 'India',
    address: '',
  });

  // Use governed hooks for industry options
  const { data: industryOptionsData } = useIndustryOptions();
  const industryOptions = useMemo(() => 
    (industryOptionsData || []).map(i => typeof i === 'string' ? i : i.name),
    [industryOptionsData]
  );
  
  // Lead status options from hook
  const { data: leadStatusOptionsData } = useLeadStatusOptions();

  // Register form data getter for save-on-leave
  const formDataRef = useRef(formData);
  useEffect(() => {
    formDataRef.current = formData;
  }, [formData]);

  useEffect(() => {
    if (dialogOpen) {
      registerFormDataGetter(() => formDataRef.current);
    }
    return () => {
      registerFormDataGetter(null);
    };
  }, [dialogOpen, registerFormDataGetter]);

  // Update form data with auto-save
  const updateFormData = (field, value) => {
    setFormData(prev => {
      const updated = { ...prev, [field]: value };
      // Auto-save draft when dialog is open
      if (dialogOpen) {
        autoSave(updated);
      }
      return updated;
    });
  };

  // Load draft into form
  const handleLoadDraft = async (draft) => {
    const loadedDraft = await loadDraft(draft.id);
    if (loadedDraft) {
      setFormData(loadedDraft.data);
      setShowDraftSelector(false);
      setDialogOpen(true);
      toast.success('Draft loaded');
    }
  };

  // Manual save draft
  const handleSaveDraft = () => {
    saveDraft(formData);
  };

  // Start new lead
  const handleNewLead = () => {
    clearDraft();
    setFormData({
      first_name: '', last_name: '', company: '', job_title: '',
      email: '', phone: '', linkedin_url: '', source: '', notes: '',
      next_follow_up: '', follow_up_notes: '',
      industry: '', website: '', city: '', state: '', country: 'India', address: '',
    });
    setShowDraftSelector(false);
    setDialogOpen(true);
  };

  // Refetch helper for cache invalidation
  const fetchLeads = () => {
    refetchLeads();
    queryClient.invalidateQueries({ queryKey: leadKeys.progressBulk() });
  };

  // Navigate to funnel onboarding when clicking on lead
  const handleLeadClick = (lead) => {
    // Don't navigate if lead is paused
    if (lead.status === 'paused') {
      toast.info('This lead is paused. Resume it to continue the sales flow.');
      return;
    }
    navigate(`/sales-funnel-onboarding?leadId=${lead.id}`);
  };

  // Pause/Resume lead functions (for managers)
  const handlePauseLead = async (leadId, e) => {
    e?.stopPropagation();
    try {
      await pauseLeadMutation.mutateAsync(leadId);
      toast.success('Lead paused successfully');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to pause lead');
    }
  };

  const handleResumeLead = async (leadId, e) => {
    e?.stopPropagation();
    try {
      await resumeLeadMutation.mutateAsync(leadId);
      toast.success('Lead resumed successfully');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to resume lead');
    }
  };

  const handleStatusChange = async (leadId, newStatus) => {
    try {
      await updateLeadMutation.mutateAsync({ id: leadId, status: newStatus });
      toast.success(`Lead status updated to ${newStatus}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update status');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...formData };
      // Convert date string to ISO datetime for backend
      if (payload.next_follow_up) {
        payload.next_follow_up = new Date(payload.next_follow_up).toISOString();
      } else {
        delete payload.next_follow_up;
      }
      if (!payload.follow_up_notes) {
        delete payload.follow_up_notes;
      }
      
      if (editLead) {
        // Update existing lead - only send fields that LeadUpdate accepts
        const updatePayload = {};
        const allowedFields = ['first_name', 'last_name', 'company', 'job_title', 'email', 'phone', 
          'linkedin_url', 'source', 'notes', 'industry', 'city', 'state', 'country', 'website'];
        for (const key of allowedFields) {
          if (payload[key] !== undefined && payload[key] !== '') {
            updatePayload[key] = payload[key];
          }
        }
        // Handle follow-up date conversion
        if (payload.next_follow_up) {
          updatePayload.next_follow_up = new Date(payload.next_follow_up).toISOString();
        }
        if (payload.follow_up_notes) {
          updatePayload.follow_up_notes = payload.follow_up_notes;
        }
        await updateLeadMutation.mutateAsync({ id: editLead.id, ...updatePayload });
        toast.success('Lead updated successfully!');
        setEditLead(null);
      } else {
        // Create new lead
        const newLead = await createLeadMutation.mutateAsync(payload);
        toast.success('Lead created successfully! Redirecting to Sales Funnel...');
        // Mark draft as converted
        await convertDraft();
        // Auto-redirect to Sales Funnel with the new lead
        navigate(`/sales-funnel-onboarding?leadId=${newLead.id}`);
      }
      
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
        next_follow_up: '',
        follow_up_notes: '',
      });
    } catch (error) {
      // Handle validation errors which may be an array or object
      const detail = error.response?.data?.detail;
      let errorMessage = editLead ? 'Failed to update lead' : 'Failed to create lead';
      if (typeof detail === 'string') {
        errorMessage = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        errorMessage = (detail || []).map(d => d.msg || d.message || String(d)).join(', ');
      } else if (detail && typeof detail === 'object') {
        errorMessage = detail.msg || detail.message || JSON.stringify(detail);
      }
      toast.error(errorMessage);
    }
  };

  // CSV Upload Functions
  const parseCSV = (text) => {
    const lines = text.trim().split('\n');
    if (lines.length < 2) return [];
    
    const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/['"]/g, ''));
    const data = [];
    
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',').map(v => v.trim().replace(/['"]/g, ''));
      if (values.length === headers.length) {
        const row = {};
        (headers || []).forEach((header, idx) => {
          row[header] = values[idx];
        });
        data.push(row);
      }
    }
    return data;
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    if (!file.name.endsWith('.csv')) {
      toast.error('Please upload a CSV file');
      return;
    }
    
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;
      setCsvData(text);
      const parsed = parseCSV(text);
      setCsvPreview(parsed.slice(0, 5)); // Show first 5 rows
      if (parsed.length > 0) {
        toast.success(`Parsed ${parsed.length} leads from CSV`);
      } else {
        toast.error('No valid data found in CSV');
      }
    };
    reader.readAsText(file);
  };

  const handleBulkUpload = async () => {
    const parsed = parseCSV(csvData);
    if (parsed.length === 0) {
      toast.error('No valid data to upload');
      return;
    }
    
    // Map CSV rows to lead data format
    const leadsToCreate = (parsed || []).map(row => ({
      first_name: row.first_name || row.firstname || row.name?.split(' ')[0] || '',
      last_name: row.last_name || row.lastname || row.name?.split(' ').slice(1).join(' ') || '',
      company: row.company || row.organization || '',
      job_title: row.job_title || row.title || row.designation || '',
      email: row.email || '',
      phone: row.phone || row.mobile || '',
      linkedin_url: row.linkedin || row.linkedin_url || '',
      source: row.source || 'CSV Import',
      notes: row.notes || ''
    }));
    
    try {
      const results = await bulkCreateLeadsMutation.mutateAsync(leadsToCreate);
      setCsvDialogOpen(false);
      setCsvData('');
      setCsvPreview([]);
      
      if (results.success > 0) {
        toast.success(`Successfully imported ${results.success} leads${results.failed > 0 ? `, ${results.failed} failed` : ''}`);
      } else {
        toast.error('Failed to import leads');
      }
    } catch (error) {
      toast.error('Failed to import leads');
    }
  };

  const downloadTemplate = () => {
    const template = 'first_name,last_name,company,job_title,email,phone,source,notes\nJohn,Doe,Acme Corp,CEO,john@acme.com,9876543210,Website,Initial contact';
    const blob = new Blob([template], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'leads_template.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getStatusBadge = (status) => {
    const statusStyles = {
      new: 'bg-zinc-100 text-zinc-600',
      meeting: 'bg-blue-50 text-blue-700',
      pricing_plan: 'bg-indigo-50 text-indigo-700',
      sow: 'bg-purple-50 text-purple-700',
      quotation: 'bg-yellow-50 text-yellow-700',
      agreement: 'bg-orange-50 text-orange-700',
      payment: 'bg-cyan-50 text-cyan-700',
      kickoff_request: 'bg-pink-50 text-pink-700',
      kick_accept: 'bg-teal-50 text-teal-700',
      closed: 'bg-emerald-50 text-emerald-700',
      paused: 'bg-amber-100 text-amber-800',
      lost: 'bg-red-50 text-red-700',
      // Legacy statuses for backward compatibility
      contacted: 'bg-blue-50 text-blue-700',
      qualified: 'bg-purple-50 text-purple-700',
      proposal: 'bg-yellow-50 text-yellow-700',
    };
    return statusStyles[status] || statusStyles.new;
  };

  const getScoreBadge = (score) => {
    if (score >= 80) return { color: 'bg-emerald-600', label: 'Hot', text: 'text-white' };
    if (score >= 60) return { color: 'bg-blue-600', label: 'Warm', text: 'text-white' };
    if (score >= 40) return { color: 'bg-yellow-600', label: 'Medium', text: 'text-white' };
    return { color: 'bg-zinc-400', label: 'Cold', text: 'text-white' };
  };

  // Filter leads by search query and timeline
  const filteredLeads = useMemo(() => {
    let result = leads;
    
    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = (result || []).filter(lead => 
        lead.first_name?.toLowerCase().includes(query) ||
        lead.last_name?.toLowerCase().includes(query) ||
        lead.company?.toLowerCase().includes(query) ||
        lead.email?.toLowerCase().includes(query) ||
        lead.phone?.includes(query) ||
        `${lead.first_name || ''} ${lead.last_name || ''}`.toLowerCase().includes(query)
      );
    }
    
    // Timeline filter
    if (timelineFilter !== 'all') {
      const now = new Date();
      result = (result || []).filter(lead => {
        const createdAt = new Date(lead.created_at);
        const daysDiff = Math.floor((now - createdAt) / (1000 * 60 * 60 * 24));
        
        switch(timelineFilter) {
          case 'today': return daysDiff === 0;
          case 'week': return daysDiff <= 7;
          case 'month': return daysDiff <= 30;
          case 'quarter': return daysDiff <= 90;
          default: return true;
        }
      });
    }
    
    return result.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  }, [leads, searchQuery, timelineFilter]);

  // Permission-based edit rights: Managers can only view (level-based, not role-based)
  const canEdit = level !== 'executive' || user?.role === 'admin' || !['manager'].includes(user?.role);

  return (
    <div data-testid="leads-page">
      {/* Draft Selector Dialog */}
      <DraftSelector
        drafts={drafts}
        loading={loadingDrafts}
        onSelect={handleLoadDraft}
        onDelete={deleteDraft}
        onNewDraft={handleNewLead}
        isOpen={showDraftSelector}
        onClose={() => setShowDraftSelector(false)}
        title="Lead Drafts"
        description="Continue editing a lead or start a new one"
      />

      <PageHeader
        title="Leads"
        subtitle={`Manage your sales pipeline (${filteredLeads.length} of ${leads.length} leads)`}
        onRefresh={() => refetchLeads()}
        loading={loading}
        actions={<>
          <ViewToggle viewMode={viewMode} onChange={setViewMode} />
          {canEdit && (<>
            {drafts.length > 0 && (
              <Button variant="outline" onClick={() => setShowDraftSelector(true)} className="border-zinc-200 gap-2">
                <FolderOpen className="w-4 h-4" /> Drafts ({drafts.length})
              </Button>
            )}
            <Button variant="outline" onClick={() => setCsvDialogOpen(true)} className="border-zinc-200" data-testid="csv-upload-btn">
              <Upload className="w-4 h-4 mr-2" /> Import CSV
            </Button>
            <Button variant="outline" onClick={async () => {
              try {
                const API = process.env.REACT_APP_BACKEND_URL;
                const token = localStorage.getItem('token');
                const res = await fetch(`${API}/api/leads/export/csv`, { headers: { Authorization: `Bearer ${token}` } });
                if (!res.ok) throw new Error('Failed to export');
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `leads_export_${new Date().toISOString().slice(0,10)}.csv`;
                a.click();
                URL.revokeObjectURL(url);
                toast.success('Leads exported to CSV');
              } catch (e) {
                toast.error(e.message || 'Failed to export leads');
              }
            }} className="border-zinc-200" data-testid="csv-download-btn">
              <Download className="w-4 h-4 mr-2" /> Export CSV
            </Button>
            {isManagerOrAbove && (
              <Button variant="outline" onClick={() => setShowBulkReassign(true)} className="border-zinc-200 text-blue-700" data-testid="bulk-reassign-btn">
                <ArrowRightLeft className="w-4 h-4 mr-2" /> Migrate Leads
              </Button>
            )}
            <Button onClick={() => setDialogOpen(true)} data-testid="add-lead-button" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
              <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} /> Add Lead
            </Button>
          </>)}
        </>}
      />
              <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) setEditLead(null); }}>
              <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="text-xl font-semibold uppercase text-zinc-950 flex items-center justify-between">
                    <span>{editLead ? 'Edit Lead' : 'Add New Lead'}</span>
                    {!editLead && <DraftIndicator saving={savingDraft} lastSaved={lastSaved} onSave={handleSaveDraft} />}
                  </DialogTitle>
                  <DialogDescription className="text-zinc-500">
                    {editLead ? 'Update lead information' : 'Enter lead information to add to your pipeline'}
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
                      onChange={(e) => updateFormData('first_name', e.target.value)}
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
                      onChange={(e) => updateFormData('last_name', e.target.value)}
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
                    onChange={(e) => updateFormData('company', e.target.value)}
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
                    onChange={(e) => updateFormData('job_title', e.target.value)}
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
                      onChange={(e) => updateFormData('email', e.target.value)}
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
                      onChange={(e) => updateFormData('phone', e.target.value)}
                      className="rounded-sm border-zinc-200"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="source" className="text-sm font-medium text-zinc-950">
                    Lead Source *
                  </Label>
                  <Select value={formData.source || ''} onValueChange={(val) => updateFormData('source', val)}>
                    <SelectTrigger className="rounded-sm border-zinc-200" data-testid="lead-source">
                      <SelectValue placeholder="Select lead source" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Website">Website</SelectItem>
                      <SelectItem value="Referral">Referral</SelectItem>
                      <SelectItem value="LinkedIn">LinkedIn</SelectItem>
                      <SelectItem value="Cold Call">Cold Call</SelectItem>
                      <SelectItem value="Email Campaign">Email Campaign</SelectItem>
                      <SelectItem value="Conference/Event">Conference/Event</SelectItem>
                      <SelectItem value="Partner">Partner</SelectItem>
                      <SelectItem value="RocketReach">RocketReach</SelectItem>
                      <SelectItem value="Social Media">Social Media</SelectItem>
                      <SelectItem value="Google Ads">Google Ads</SelectItem>
                      <SelectItem value="Direct">Direct</SelectItem>
                      <SelectItem value="Other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Company Details Section */}
                <div className="border-t pt-4 mt-4">
                  <h4 className="text-sm font-semibold text-zinc-700 mb-3 flex items-center gap-2">
                    <Building2 className="w-4 h-4" />
                    Company Details (Optional)
                  </h4>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="industry" className="text-sm font-medium text-zinc-950">
                        Industry
                      </Label>
                      <GovernedDropdown
                        value={formData.industry}
                        onChange={(val) => updateFormData('industry', val)}
                        options={(industryOptionsData || []).map(i => ({
                          id: typeof i === 'string' ? i : i.id,
                          name: typeof i === 'string' ? i : i.name
                        }))}
                        placeholder="Select Industry"
                        data-testid="lead-industry"
                        valueKey="id"
                        labelKey="name"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="website" className="text-sm font-medium text-zinc-950">
                        Website
                      </Label>
                      <Input
                        id="website"
                        data-testid="lead-website"
                        value={formData.website}
                        onChange={(e) => updateFormData('website', e.target.value)}
                        placeholder="https://example.com"
                        className="rounded-sm border-zinc-200"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mt-3">
                    <div className="space-y-2">
                      <Label htmlFor="city" className="text-sm font-medium text-zinc-950">
                        City
                      </Label>
                      <Input
                        id="city"
                        data-testid="lead-city"
                        value={formData.city}
                        onChange={(e) => updateFormData('city', e.target.value)}
                        placeholder="City"
                        className="rounded-sm border-zinc-200"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="state" className="text-sm font-medium text-zinc-950">
                        State
                      </Label>
                      <Input
                        id="state"
                        data-testid="lead-state"
                        value={formData.state}
                        onChange={(e) => updateFormData('state', e.target.value)}
                        placeholder="State"
                        className="rounded-sm border-zinc-200"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="country" className="text-sm font-medium text-zinc-950">
                        Country
                      </Label>
                      <Input
                        id="country"
                        data-testid="lead-country"
                        value={formData.country}
                        onChange={(e) => updateFormData('country', e.target.value)}
                        placeholder="Country"
                        className="rounded-sm border-zinc-200"
                      />
                    </div>
                  </div>

                  <div className="space-y-2 mt-3">
                    <Label htmlFor="address" className="text-sm font-medium text-zinc-950">
                      Full Address
                    </Label>
                    <Input
                      id="address"
                      data-testid="lead-address"
                      value={formData.address}
                      onChange={(e) => updateFormData('address', e.target.value)}
                      placeholder="Street address"
                      className="rounded-sm border-zinc-200"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="notes" className="text-sm font-medium text-zinc-950">
                    Notes
                  </Label>
                  <textarea
                    id="notes"
                    data-testid="lead-notes"
                    value={formData.notes}
                    onChange={(e) => updateFormData('notes', e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="next_follow_up" className="text-sm font-medium text-zinc-950">
                      Next Follow-up Date
                    </Label>
                    <Input
                      id="next_follow_up"
                      data-testid="lead-next-follow-up"
                      type="date"
                      value={formData.next_follow_up}
                      onChange={(e) => updateFormData('next_follow_up', e.target.value)}
                      className="rounded-sm border-zinc-200"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="follow_up_notes" className="text-sm font-medium text-zinc-950">
                      Follow-up Notes
                    </Label>
                    <Input
                      id="follow_up_notes"
                      data-testid="lead-follow-up-notes"
                      value={formData.follow_up_notes}
                      onChange={(e) => updateFormData('follow_up_notes', e.target.value)}
                      placeholder="e.g., Call to discuss proposal"
                      className="rounded-sm border-zinc-200"
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  data-testid="submit-lead-button"
                  className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                >
                  {editLead ? 'Update Lead' : 'Create Lead'}
                </Button>
              </form>
            </DialogContent>
          </Dialog>

      {/* CSV Upload Dialog */}
      <Dialog open={csvDialogOpen} onOpenChange={setCsvDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950 flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5" />
              Import Leads from CSV
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Upload a CSV file or paste data directly to bulk import leads
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Download Template */}
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <div className="text-sm text-blue-700">
                Need a template? Download our sample CSV format
              </div>
              <Button variant="outline" size="sm" onClick={downloadTemplate} className="text-blue-700 border-blue-200">
                <Download className="w-4 h-4 mr-1" />
                Template
              </Button>
            </div>
            
            {/* File Upload */}
            <div className="border-2 border-dashed border-zinc-300 rounded-lg p-6 text-center">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                className="hidden"
                data-testid="csv-file-input"
              />
              <Upload className="w-10 h-10 text-zinc-400 mx-auto mb-3" />
              <p className="text-sm text-zinc-600 mb-2">Drag & drop or click to upload CSV</p>
              <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
                Choose File
              </Button>
            </div>
            
            {/* Or paste directly */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-zinc-200" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-2 bg-white text-zinc-500">or paste CSV data</span>
              </div>
            </div>
            
            <textarea
              value={csvData}
              onChange={(e) => {
                setCsvData(e.target.value);
                const parsed = parseCSV(e.target.value);
                setCsvPreview(parsed.slice(0, 5));
              }}
              placeholder="first_name,last_name,company,job_title,email,phone,source&#10;John,Doe,Acme Corp,CEO,john@acme.com,9876543210,Website"
              className="w-full h-32 px-3 py-2 rounded-sm border border-zinc-200 text-sm font-mono"
              data-testid="csv-paste-area"
            />
            
            {/* Preview */}
            {csvPreview.length > 0 && (
              <div className="border border-zinc-200 rounded-lg overflow-hidden">
                <div className="bg-zinc-50 px-3 py-2 text-sm font-medium text-zinc-700 flex items-center justify-between">
                  <span>Preview ({csvPreview.length} of {parseCSV(csvData).length} rows)</span>
                  <Button variant="ghost" size="sm" onClick={() => { setCsvData(''); setCsvPreview([]); }}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-zinc-100">
                      <tr>
                        <th className="px-2 py-1 text-left">Name</th>
                        <th className="px-2 py-1 text-left">Company</th>
                        <th className="px-2 py-1 text-left">Email</th>
                        <th className="px-2 py-1 text-left">Phone</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(csvPreview || []).map((row, idx) => (
                        <tr key={idx} className="border-t border-zinc-100">
                          <td className="px-2 py-1">{row.first_name || row.firstname} {row.last_name || row.lastname}</td>
                          <td className="px-2 py-1">{row.company}</td>
                          <td className="px-2 py-1">{row.email}</td>
                          <td className="px-2 py-1">{row.phone}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setCsvDialogOpen(false)} className="flex-1">
                Cancel
              </Button>
              <Button 
                onClick={handleBulkUpload} 
                disabled={bulkCreateLeadsMutation.isPending || parseCSV(csvData).length === 0}
                className="flex-1 bg-zinc-950 text-white"
                data-testid="import-csv-btn"
              >
                {bulkCreateLeadsMutation.isPending ? 'Importing...' : `Import ${parseCSV(csvData).length} Leads`}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Search and Filters */}
      <div className="mb-6 space-y-4">
        {/* Search Box */}
        <div className="flex gap-4 flex-wrap">
          <div className="relative flex-1 min-w-[250px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <Input
              type="text"
              placeholder="Search by name, company, email, phone..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-10 rounded-sm border-zinc-200"
              data-testid="lead-search-input"
            />
          </div>
          
          {/* Timeline Filter */}
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-zinc-400" />
            <select
              value={timelineFilter}
              onChange={(e) => setTimelineFilter(e.target.value)}
              className="h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm text-zinc-700"
              data-testid="timeline-filter"
            >
              <option value="all">All Time</option>
              <option value="today">Today</option>
              <option value="week">This Week</option>
              <option value="month">This Month</option>
              <option value="quarter">This Quarter</option>
            </select>
          </div>
        </div>

        {/* Status Filter Dropdown */}
        <div className="flex items-center gap-3">
          <Label className="text-xs text-zinc-500 whitespace-nowrap">Stage:</Label>
          <GovernedDropdown
            value={selectedStatus}
            onChange={setSelectedStatus}
            options={leadStatusOptions.map(o => ({ id: o.value, name: o.label + (o.value === '' && filteredLeads ? ` (${leads.length})` : '') }))}
            placeholder="Select Stage"
            data-testid="lead-status-filter"
            valueKey="id"
            labelKey="name"
            className="min-w-[160px]"
          />
          {selectedStatus && (
            <button
              onClick={() => setSelectedStatus('')}
              className="text-xs text-zinc-400 hover:text-zinc-600 underline"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-zinc-500">Loading leads...</div>
        </div>
      ) : filteredLeads.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <p className="text-zinc-500 mb-4">
              {searchQuery || timelineFilter !== 'all' ? 'No leads match your search criteria' : 'No leads found'}
            </p>
            {canEdit && !searchQuery && (
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
        /* List View - Using SalesDataTable (GOVERNANCE: No manual tables) */
        <LeadsTable
          onRowClick={handleLeadClick}
          onEdit={(lead) => {
            setEditLead(lead);
            setFormData({
              first_name: lead.first_name || '',
              last_name: lead.last_name || '',
              email: lead.email || '',
              phone: lead.phone || '',
              company: lead.company || '',
              job_title: lead.job_title || '',
              industry: lead.industry || '',
              linkedin_url: lead.linkedin_url || '',
              address: lead.address || '',
              source: lead.source || lead.lead_source || '',
              notes: lead.notes || '',
              next_follow_up: lead.next_follow_up ? new Date(lead.next_follow_up).toISOString().split('T')[0] : '',
              follow_up_notes: lead.follow_up_notes || '',
              website: lead.website || '',
              city: lead.city || '',
              state: lead.state || '',
              country: lead.country || '',
            });
            setDialogOpen(true);
          }}
          onPause={(lead) => handlePauseLead(lead.id)}
          onResume={(lead) => handleResumeLead(lead.id)}
          onReassign={(lead) => {
            setReassignLead(lead);
            setShowReassignDialog(true);
          }}
          className="border border-zinc-200 rounded-sm"
        />
      ) : (
        /* Card View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(filteredLeads || []).map((lead) => {
            const leadSuggestions = suggestions[lead.id] || [];
            const progress = leadProgress[lead.id] || {};
            return (
              <Card
                key={lead.id}
                data-testid={`lead-card-${lead.id}`}
                className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors cursor-pointer"
                onClick={() => handleLeadClick(lead)}
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
                    <div className="flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
                      <select
                        value={lead.status}
                        onChange={(e) => handleStatusChange(lead.id, e.target.value)}
                        className={`px-2 py-1 text-xs font-medium rounded-sm border-0 cursor-pointer ${getStatusBadge(lead.status)}`}
                        data-testid={`status-select-card-${lead.id}`}
                      >
                        {['new', 'contacted', 'qualified', 'proposal', 'agreement', 'closed', 'lost'].map(s => (
                          <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  
                  {/* Sales Funnel Progress Indicator */}
                  <div className="mt-3" onClick={(e) => e.stopPropagation()}>
                    <FunnelProgressIndicator 
                      progress={progress}
                      onClick={() => navigate(`/sales-funnel-onboarding?leadId=${lead.id}`)}
                    />
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
                    <div className="pt-3 mt-3 border-t border-zinc-200" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleLeadClick(lead); }}
                        className="w-full px-3 py-2 text-xs font-medium bg-zinc-950 text-white rounded-sm hover:bg-zinc-800 transition-colors flex items-center justify-center gap-2"
                        data-testid={`start-sales-flow-${lead.id}`}
                      >
                        <DollarSign className="w-3 h-3" strokeWidth={1.5} />
                        {progress.current_stage > 1 ? 'Continue Sales Flow' : 'Start Sales Flow'}
                      </button>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Reassign Lead Dialog */}
      <Dialog open={showReassignDialog} onOpenChange={(open) => { setShowReassignDialog(open); if (!open) { setReassignLead(null); setReassignUserId(''); setReassignReason(''); } }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Reassign Lead</DialogTitle>
            <DialogDescription>
              Transfer {reassignLead?.company || 'this lead'} and all associated data to another team member.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="p-3 bg-zinc-50 rounded border border-zinc-200 text-sm">
              <p className="font-medium">{reassignLead?.company || `${reassignLead?.first_name} ${reassignLead?.last_name}`}</p>
              <p className="text-zinc-500 text-xs mt-0.5">Current: {reassignLead?.assigned_to_name || 'Unassigned'}</p>
            </div>
            <div className="space-y-1">
              <Label className="text-sm font-medium">Assign To *</Label>
              <Select value={reassignUserId} onValueChange={setReassignUserId}>
                <SelectTrigger data-testid="reassign-user-select"><SelectValue placeholder="Select team member" /></SelectTrigger>
                <SelectContent>
                  {salesUsers.filter(u => u.id !== reassignLead?.assigned_to && u.id !== reassignLead?.lead_owner).map(u => (
                    <SelectItem key={u.id} value={u.id}>{u.full_name} ({u.role})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-sm">Reason</Label>
              <Input data-testid="reassign-reason" value={reassignReason} onChange={(e) => setReassignReason(e.target.value)} placeholder="e.g., Role change, territory realignment" />
            </div>
            <p className="text-xs text-zinc-500">This will transfer the lead along with all meetings, pricing plans, SOWs, quotations, agreements, and follow-ups.</p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowReassignDialog(false)} className="flex-1">Cancel</Button>
              <Button onClick={handleReassign} disabled={!reassignUserId} className="flex-1 bg-blue-600 text-white hover:bg-blue-700" data-testid="confirm-reassign-btn">
                Reassign Lead
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Bulk Reassign Dialog (Managers only) */}
      {isManagerOrAbove && (
        <Dialog open={showBulkReassign} onOpenChange={(open) => { setShowBulkReassign(open); if (!open) { setBulkFromUserId(''); setBulkToUserId(''); setReassignReason(''); } }}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Bulk Lead Migration</DialogTitle>
              <DialogDescription>
                Transfer ALL leads from one team member to another. Used for resignations or role changes.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3">
              <div className="space-y-1">
                <Label className="text-sm font-medium">Transfer From *</Label>
                <Select value={bulkFromUserId} onValueChange={setBulkFromUserId}>
                  <SelectTrigger data-testid="bulk-from-select"><SelectValue placeholder="Select source user" /></SelectTrigger>
                  <SelectContent>
                    {salesUsers.map(u => (
                      <SelectItem key={u.id} value={u.id}>{u.full_name} ({u.role})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-sm font-medium">Transfer To *</Label>
                <Select value={bulkToUserId} onValueChange={setBulkToUserId}>
                  <SelectTrigger data-testid="bulk-to-select"><SelectValue placeholder="Select target user" /></SelectTrigger>
                  <SelectContent>
                    {salesUsers.filter(u => u.id !== bulkFromUserId).map(u => (
                      <SelectItem key={u.id} value={u.id}>{u.full_name} ({u.role})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-sm">Reason</Label>
                <Input data-testid="bulk-reason" value={reassignReason} onChange={(e) => setReassignReason(e.target.value)} placeholder="e.g., Resignation, team restructure" />
              </div>
              <p className="text-xs text-amber-600 font-medium">Warning: This will transfer ALL leads, meetings, pricing plans, SOWs, quotations, agreements, and follow-ups.</p>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setShowBulkReassign(false)} className="flex-1">Cancel</Button>
                <Button onClick={handleBulkReassign} disabled={!bulkFromUserId || !bulkToUserId} className="flex-1 bg-red-600 text-white hover:bg-red-700" data-testid="confirm-bulk-reassign-btn">
                  Transfer All Leads
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default Leads;
