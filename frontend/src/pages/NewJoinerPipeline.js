/**
 * NewJoinerPipeline.js
 * 
 * Unified view of all new joiner stages from Invite to Active.
 * VISUAL ONLY - does not modify any workflow logic.
 * Maps to existing backend statuses:
 *   - invited, draft, submitted, revision_requested, approved, completed
 */

import React, { useState, useContext, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { AuthContext, API } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import PageHeader from '../components/ui/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { 
  Search, Send, Users, Clock, CheckCircle2, FileText, Rocket,
  ChevronRight, Eye, RefreshCw, UserPlus, AlertTriangle, 
  ArrowRight, Loader2, Mail, Briefcase, Calendar, Filter
} from 'lucide-react';
import { toast } from 'sonner';
import { isHR as checkIsHR } from '../utils/roles';

// Pipeline stages with their backend status mappings
const PIPELINE_STAGES = [
  { 
    id: 'invited', 
    label: 'Invited', 
    statuses: ['invited'],
    icon: Send,
    color: 'bg-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    textColor: 'text-blue-700 dark:text-blue-300',
    description: 'Invite sent, awaiting candidate action'
  },
  { 
    id: 'documents', 
    label: 'Documents Pending', 
    statuses: ['draft'],
    icon: FileText,
    color: 'bg-amber-500',
    bgColor: 'bg-amber-50 dark:bg-amber-950/30',
    textColor: 'text-amber-700 dark:text-amber-300',
    description: 'Candidate filling onboarding form'
  },
  { 
    id: 'review', 
    label: 'Under Review', 
    statuses: ['submitted', 'revision_requested'],
    icon: Eye,
    color: 'bg-purple-500',
    bgColor: 'bg-purple-50 dark:bg-purple-950/30',
    textColor: 'text-purple-700 dark:text-purple-300',
    description: 'HR reviewing submission'
  },
  { 
    id: 'golive', 
    label: 'Go-Live Pending', 
    statuses: ['approved'],
    icon: Rocket,
    color: 'bg-orange-500',
    bgColor: 'bg-orange-50 dark:bg-orange-950/30',
    textColor: 'text-orange-700 dark:text-orange-300',
    description: 'Awaiting final activation'
  },
  { 
    id: 'active', 
    label: 'Active', 
    statuses: ['completed'],
    icon: CheckCircle2,
    color: 'bg-emerald-500',
    bgColor: 'bg-emerald-50 dark:bg-emerald-950/30',
    textColor: 'text-emerald-700 dark:text-emerald-300',
    description: 'Onboarding complete'
  },
];

// Get auth headers helper
const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return token ? { headers: { Authorization: `Bearer ${token}` } } : {};
};

const NewJoinerPipeline = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStage, setSelectedStage] = useState(null); // null = all
  const [showInviteDialog, setShowInviteDialog] = useState(false);
  const [inviteForm, setInviteForm] = useState({
    candidate_name: '',
    candidate_email: '',
    offered_position: '',
  });
  const [sending, setSending] = useState(false);
  const [sendingReminder, setSendingReminder] = useState(null); // Track which item is sending reminder

  const isHR = checkIsHR(user);

  // Fetch all onboarding submissions using existing API
  const { data: submissions = [], isLoading, refetch } = useQuery({
    queryKey: ['onboarding-submissions', 'pipeline'],
    queryFn: async () => {
      const response = await axios.get(`${API}/onboarding/submissions`, getAuthHeaders());
      const data = response.data || [];
      // Sort by created_at descending (latest first)
      return data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    },
    enabled: !!user,
    staleTime: 2 * 60 * 1000,
  });

  // Fetch recent employees who completed onboarding (last 30 days)
  const { data: recentEmployees = [] } = useQuery({
    queryKey: ['employees', 'recent-joiners'],
    queryFn: async () => {
      const response = await axios.get(`${API}/employees`, getAuthHeaders());
      const employees = response.data?.items || response.data || [];
      // Filter to those joined in last 30 days
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      return employees.filter(e => {
        const joinDate = new Date(e.joining_date || e.created_at);
        return joinDate >= thirtyDaysAgo && e.status !== 'inactive';
      });
    },
    enabled: !!user,
    staleTime: 5 * 60 * 1000,
  });

  // Group submissions by stage
  const groupedByStage = useMemo(() => {
    const groups = {};
    
    PIPELINE_STAGES.forEach(stage => {
      groups[stage.id] = [];
    });

    // Add submissions to appropriate stages
    submissions.forEach(sub => {
      const stage = PIPELINE_STAGES.find(s => s.statuses.includes(sub.status));
      if (stage) {
        groups[stage.id].push({
          ...sub,
          type: 'submission',
        });
      }
    });

    // Add recent employees to "active" stage
    recentEmployees.forEach(emp => {
      groups['active'].push({
        ...emp,
        type: 'employee',
        candidate_name: emp.full_name || `${emp.first_name} ${emp.last_name}`,
        candidate_email: emp.email,
        offered_position: emp.designation,
      });
    });

    return groups;
  }, [submissions, recentEmployees]);

  // Filter by search
  const filteredGroups = useMemo(() => {
    if (!searchQuery) return groupedByStage;
    
    const filtered = {};
    Object.keys(groupedByStage).forEach(stageId => {
      filtered[stageId] = groupedByStage[stageId].filter(item =>
        item.candidate_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.candidate_email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.offered_position?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    });
    return filtered;
  }, [groupedByStage, searchQuery]);

  // Get stage counts
  const stageCounts = useMemo(() => {
    const counts = {};
    PIPELINE_STAGES.forEach(stage => {
      counts[stage.id] = filteredGroups[stage.id]?.length || 0;
    });
    return counts;
  }, [filteredGroups]);

  // Total pending (excluding completed/active)
  const totalPending = stageCounts.invited + stageCounts.documents + stageCounts.review + stageCounts.golive;

  // Send invite handler (uses existing API)
  const handleSendInvite = async () => {
    if (!inviteForm.candidate_name || !inviteForm.candidate_email || !inviteForm.offered_position) {
      toast.error('Please fill all required fields');
      return;
    }

    try {
      setSending(true);
      await axios.post(`${API}/onboarding/invite`, inviteForm, getAuthHeaders());
      toast.success('Invite sent successfully!');
      setInviteForm({ candidate_name: '', candidate_email: '', offered_position: '' });
      setShowInviteDialog(false);
      queryClient.invalidateQueries({ queryKey: ['onboarding-submissions'] });
      refetch();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send invite');
    } finally {
      setSending(false);
    }
  };

  // Send reminder to candidate
  const handleSendReminder = async (e, item) => {
    e.stopPropagation(); // Prevent card click navigation
    const submissionId = item.id || item._id;
    
    try {
      setSendingReminder(submissionId);
      await axios.post(
        `${API}/onboarding/submissions/${submissionId}/send-reminder`,
        {},
        getAuthHeaders()
      );
      toast.success(`Reminder sent to ${item.candidate_name}`);
      refetch();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to send reminder';
      toast.error(errorMsg);
    } finally {
      setSendingReminder(null);
    }
  };

  // Navigate to detail view
  const handleViewItem = (item) => {
    if (item.type === 'employee') {
      navigate(`/employees?id=${item.id || item._id}`);
    } else {
      navigate(`/onboarding/review/${item.id || item._id}`);
    }
  };

  // Get status badge
  const getStatusBadge = (status) => {
    const statusConfig = {
      invited: { color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300', label: 'Invited' },
      draft: { color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300', label: 'In Progress' },
      submitted: { color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300', label: 'Submitted' },
      revision_requested: { color: 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300', label: 'Revision' },
      approved: { color: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/50 dark:text-cyan-300', label: 'Approved' },
      completed: { color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300', label: 'Active' },
    };
    const config = statusConfig[status] || { color: 'bg-zinc-100 text-zinc-700', label: status };
    return <Badge className={config.color}>{config.label}</Badge>;
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="new-joiner-pipeline">
      {/* Header */}
      <PageHeader
        title="New Joiner Pipeline"
        subtitle="Track candidates from invite to active employee"
        onRefresh={() => refetch()}
        loading={isLoading}
        actions={<>
          <div className="relative">
            <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`} />
            <Input placeholder="Search candidates..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9 w-[250px]" data-testid="pipeline-search" />
          </div>
          {isHR && (
            <Button onClick={() => setShowInviteDialog(true)} data-testid="send-invite-btn">
              <UserPlus className="w-4 h-4 mr-2" /> Send Invite
            </Button>
          )}
        </>}
      />

      {/* Pipeline Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {PIPELINE_STAGES.map((stage, index) => {
          const Icon = stage.icon;
          const count = stageCounts[stage.id];
          const isSelected = selectedStage === stage.id;
          
          return (
            <Card 
              key={stage.id}
              className={`cursor-pointer transition-all ${
                isSelected 
                  ? `ring-2 ring-offset-2 ${isDark ? 'ring-zinc-500' : 'ring-zinc-400'}` 
                  : 'hover:shadow-md'
              } ${stage.bgColor}`}
              onClick={() => setSelectedStage(isSelected ? null : stage.id)}
              data-testid={`stage-card-${stage.id}`}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className={`p-2 rounded-lg ${stage.color}`}>
                    <Icon className="w-4 h-4 text-white" />
                  </div>
                  {index < PIPELINE_STAGES.length - 1 && (
                    <ArrowRight className={`w-4 h-4 ${isDark ? 'text-zinc-600' : 'text-zinc-300'}`} />
                  )}
                </div>
                <div className={`text-2xl font-bold ${stage.textColor}`}>{count}</div>
                <div className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>{stage.label}</div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Summary Alert */}
      {totalPending > 0 && (
        <div className={`flex items-center gap-3 p-4 rounded-lg ${isDark ? 'bg-amber-900/20 border border-amber-800' : 'bg-amber-50 border border-amber-200'}`}>
          <AlertTriangle className={`w-5 h-5 ${isDark ? 'text-amber-400' : 'text-amber-600'}`} />
          <span className={`text-sm ${isDark ? 'text-amber-300' : 'text-amber-700'}`}>
            <strong>{totalPending} candidate{totalPending !== 1 ? 's' : ''}</strong> pending in the pipeline
          </span>
        </div>
      )}

      {/* Pipeline View */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {PIPELINE_STAGES.map(stage => {
            const items = filteredGroups[stage.id] || [];
            const Icon = stage.icon;
            const isFiltered = selectedStage && selectedStage !== stage.id;
            
            if (isFiltered) return null;
            
            return (
              <Card 
                key={stage.id} 
                className={`${isDark ? 'bg-zinc-900/50' : 'bg-white'} ${selectedStage === stage.id ? 'lg:col-span-5' : ''}`}
              >
                <CardHeader className={`py-3 px-4 ${stage.bgColor} rounded-t-lg`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className={`w-4 h-4 ${stage.textColor}`} />
                      <CardTitle className={`text-sm font-semibold ${stage.textColor}`}>
                        {stage.label}
                      </CardTitle>
                    </div>
                    <Badge variant="secondary" className="text-xs">
                      {items.length}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-2 max-h-[400px] overflow-y-auto">
                  {items.length === 0 ? (
                    <div className={`text-center py-6 text-sm ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                      No candidates
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {items.map((item, idx) => (
                        <div
                          key={item.id || item._id || idx}
                          onClick={() => handleViewItem(item)}
                          className={`p-3 rounded-lg cursor-pointer transition-colors ${
                            isDark 
                              ? 'bg-zinc-800 hover:bg-zinc-700' 
                              : 'bg-zinc-50 hover:bg-zinc-100'
                          }`}
                          data-testid={`pipeline-item-${item.id || item._id}`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className={`font-medium text-sm truncate ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                                {item.candidate_name}
                              </div>
                              <div className={`text-xs truncate ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                                {item.offered_position}
                              </div>
                              <div className={`text-xs truncate ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                                {item.candidate_email}
                              </div>
                            </div>
                            <ChevronRight className={`w-4 h-4 flex-shrink-0 ${isDark ? 'text-zinc-600' : 'text-zinc-300'}`} />
                          </div>
                          <div className="flex items-center justify-between mt-2">
                            {item.status && getStatusBadge(item.status)}
                            {/* Show Send Reminder button for invited and draft status */}
                            {isHR && ['invited', 'draft'].includes(item.status) && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 text-xs"
                                onClick={(e) => handleSendReminder(e, item)}
                                disabled={sendingReminder === (item.id || item._id)}
                                data-testid={`send-reminder-${item.id || item._id}`}
                              >
                                {sendingReminder === (item.id || item._id) ? (
                                  <Loader2 className="w-3 h-3 animate-spin mr-1" />
                                ) : (
                                  <Mail className="w-3 h-3 mr-1" />
                                )}
                                Remind
                              </Button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Invite Dialog */}
      <Dialog open={showInviteDialog} onOpenChange={setShowInviteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send Onboarding Invite</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Candidate Name *</Label>
              <Input
                placeholder="John Doe"
                value={inviteForm.candidate_name}
                onChange={(e) => setInviteForm(prev => ({ ...prev, candidate_name: e.target.value }))}
                data-testid="invite-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Email Address *</Label>
              <Input
                type="email"
                placeholder="john@example.com"
                value={inviteForm.candidate_email}
                onChange={(e) => setInviteForm(prev => ({ ...prev, candidate_email: e.target.value }))}
                data-testid="invite-email-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Position Offered *</Label>
              <Input
                placeholder="Software Engineer"
                value={inviteForm.offered_position}
                onChange={(e) => setInviteForm(prev => ({ ...prev, offered_position: e.target.value }))}
                data-testid="invite-position-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowInviteDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleSendInvite} disabled={sending} data-testid="send-invite-submit">
              {sending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
              Send Invite
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default NewJoinerPipeline;
