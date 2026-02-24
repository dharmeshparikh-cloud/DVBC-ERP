import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext, API } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Progress } from '../../components/ui/progress';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { 
  Send, Users, Clock, CheckCircle2, XCircle, RefreshCw, Eye, 
  UserPlus, Mail, Briefcase, Copy, ExternalLink, Search,
  AlertTriangle, FileText, Loader2, MoreHorizontal, ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu";

const OnboardingHub = () => {
  const { user, token } = useContext(AuthContext);
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('invite');
  const [loading, setLoading] = useState(false);
  const [submissions, setSubmissions] = useState([]);
  const [legacyRecords, setLegacyRecords] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Invite form state
  const [inviteForm, setInviteForm] = useState({
    candidate_name: '',
    candidate_email: '',
    offered_position: '',
  });
  const [sending, setSending] = useState(false);
  const [inviteResult, setInviteResult] = useState(null);

  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  // Fetch submissions
  const fetchSubmissions = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/onboarding/submissions`, authHeaders);
      setSubmissions(response.data || []);
    } catch (err) {
      console.error('Error fetching submissions:', err);
      toast.error('Failed to load submissions');
    } finally {
      setLoading(false);
    }
  };

  // Fetch legacy records
  const fetchLegacyRecords = async () => {
    try {
      const response = await axios.get(`${API}/onboarding/legacy`, authHeaders);
      setLegacyRecords(response.data || []);
    } catch (err) {
      console.error('Error fetching legacy:', err);
    }
  };

  useEffect(() => {
    if (token) {
      fetchSubmissions();
      fetchLegacyRecords();
    }
  }, [token]);

  // Send invite
  const handleSendInvite = async () => {
    if (!inviteForm.candidate_name || !inviteForm.candidate_email || !inviteForm.offered_position) {
      toast.error('Please fill all required fields');
      return;
    }

    try {
      setSending(true);
      const response = await axios.post(`${API}/onboarding/invite`, inviteForm, authHeaders);
      setInviteResult(response.data);
      toast.success('Invite sent successfully!');
      setInviteForm({ candidate_name: '', candidate_email: '', offered_position: '' });
      fetchSubmissions();
    } catch (err) {
      console.error('Error sending invite:', err);
      toast.error(err.response?.data?.detail || 'Failed to send invite');
    } finally {
      setSending(false);
    }
  };

  // Copy link to clipboard
  const copyLink = (link) => {
    navigator.clipboard.writeText(link);
    toast.success('Link copied to clipboard');
  };

  // Get status badge
  const getStatusBadge = (status) => {
    const statusConfig = {
      invited: { color: 'bg-blue-100 text-blue-700', label: 'Invited' },
      draft: { color: 'bg-zinc-100 text-zinc-700', label: 'In Progress' },
      submitted: { color: 'bg-amber-100 text-amber-700', label: 'Pending Review' },
      revision_requested: { color: 'bg-orange-100 text-orange-700', label: 'Revision Requested' },
      approved: { color: 'bg-green-100 text-green-700', label: 'Approved' },
      rejected: { color: 'bg-red-100 text-red-700', label: 'Rejected' },
      completed: { color: 'bg-emerald-100 text-emerald-700', label: 'Completed' },
    };
    const config = statusConfig[status] || { color: 'bg-zinc-100 text-zinc-700', label: status };
    return <Badge className={config.color}>{config.label}</Badge>;
  };

  // Filter submissions by tab
  const getFilteredSubmissions = (tab) => {
    let filtered = submissions;
    
    if (searchQuery) {
      filtered = filtered.filter(s =>
        s.candidate_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.candidate_email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.offered_position?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    switch (tab) {
      case 'pending':
        return filtered.filter(s => ['submitted', 'revision_requested'].includes(s.status));
      case 'inprogress':
        return filtered.filter(s => ['invited', 'draft'].includes(s.status));
      case 'completed':
        return filtered.filter(s => ['completed', 'rejected'].includes(s.status));
      default:
        return filtered;
    }
  };

  const pendingCount = submissions.filter(s => ['submitted', 'revision_requested'].includes(s.status)).length;
  const inProgressCount = submissions.filter(s => ['invited', 'draft'].includes(s.status)).length;
  const completedCount = submissions.filter(s => ['completed', 'rejected'].includes(s.status)).length;

  // Show loading if no token yet
  if (!token || !user) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="onboarding-hub">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Onboarding Hub</h1>
          <p className="text-zinc-500 text-sm">Manage candidate self-service onboarding</p>
        </div>
        <Button onClick={fetchSubmissions} variant="outline" size="sm">
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setActiveTab('pending')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Pending Review</p>
                <p className="text-3xl font-bold text-amber-600">{pendingCount}</p>
              </div>
              <Clock className="w-10 h-10 text-amber-200" />
            </div>
          </CardContent>
        </Card>
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setActiveTab('inprogress')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">In Progress</p>
                <p className="text-3xl font-bold text-blue-600">{inProgressCount}</p>
              </div>
              <Users className="w-10 h-10 text-blue-200" />
            </div>
          </CardContent>
        </Card>
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setActiveTab('completed')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Completed</p>
                <p className="text-3xl font-bold text-green-600">{completedCount}</p>
              </div>
              <CheckCircle2 className="w-10 h-10 text-green-200" />
            </div>
          </CardContent>
        </Card>
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setActiveTab('invite')}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Send Invite</p>
                <p className="text-lg font-medium">New Candidate</p>
              </div>
              <UserPlus className="w-10 h-10 text-zinc-200" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="invite" data-testid="tab-invite">
            <Send className="w-4 h-4 mr-2" />
            Send Invite
          </TabsTrigger>
          <TabsTrigger value="pending" data-testid="tab-pending">
            <Clock className="w-4 h-4 mr-2" />
            Pending ({pendingCount})
          </TabsTrigger>
          <TabsTrigger value="inprogress" data-testid="tab-inprogress">
            <Users className="w-4 h-4 mr-2" />
            In Progress ({inProgressCount})
          </TabsTrigger>
          <TabsTrigger value="completed" data-testid="tab-completed">
            <CheckCircle2 className="w-4 h-4 mr-2" />
            Completed ({completedCount})
          </TabsTrigger>
          <TabsTrigger value="legacy" data-testid="tab-legacy">
            <FileText className="w-4 h-4 mr-2" />
            Legacy ({legacyRecords.length})
          </TabsTrigger>
        </TabsList>

        {/* Send Invite Tab */}
        <TabsContent value="invite" className="mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <UserPlus className="w-5 h-5" />
                  Send Onboarding Invite
                </CardTitle>
                <CardDescription>
                  Send a secure link to the candidate to fill their onboarding details
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="candidate_name">Candidate Name *</Label>
                  <Input
                    id="candidate_name"
                    data-testid="invite-name-input"
                    value={inviteForm.candidate_name}
                    onChange={(e) => setInviteForm(prev => ({ ...prev, candidate_name: e.target.value }))}
                    placeholder="Full name"
                  />
                </div>
                <div>
                  <Label htmlFor="candidate_email">Email Address *</Label>
                  <Input
                    id="candidate_email"
                    type="email"
                    data-testid="invite-email-input"
                    value={inviteForm.candidate_email}
                    onChange={(e) => setInviteForm(prev => ({ ...prev, candidate_email: e.target.value }))}
                    placeholder="candidate@example.com"
                  />
                </div>
                <div>
                  <Label htmlFor="offered_position">Offered Position *</Label>
                  <Input
                    id="offered_position"
                    data-testid="invite-position-input"
                    value={inviteForm.offered_position}
                    onChange={(e) => setInviteForm(prev => ({ ...prev, offered_position: e.target.value }))}
                    placeholder="e.g., Consultant, Sales Executive"
                  />
                </div>
              </CardContent>
              <CardFooter>
                <Button
                  onClick={handleSendInvite}
                  disabled={sending}
                  className="w-full"
                  data-testid="send-invite-btn"
                >
                  {sending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4 mr-2" />
                  )}
                  Send Invite
                </Button>
              </CardFooter>
            </Card>

            {/* Invite Result */}
            {inviteResult && (
              <Card className="border-green-200 bg-green-50/50">
                <CardHeader>
                  <CardTitle className="text-green-700 flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5" />
                    Invite Sent Successfully
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className="text-xs text-zinc-500">Onboarding Link</Label>
                    <div className="flex items-center gap-2 mt-1">
                      <Input
                        value={inviteResult.onboarding_link}
                        readOnly
                        className="text-sm bg-white"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyLink(inviteResult.onboarding_link)}
                      >
                        <Copy className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-zinc-500">Expires:</span>
                    <span>{new Date(inviteResult.expires_at).toLocaleDateString()}</span>
                  </div>
                  <Alert>
                    <Mail className="h-4 w-4" />
                    <AlertDescription>
                      An email has been sent to the candidate with this link.
                    </AlertDescription>
                  </Alert>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Pending Review Tab */}
        <TabsContent value="pending" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Pending Review</CardTitle>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-400" />
                  <Input
                    placeholder="Search candidates..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 w-64"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <SubmissionTable
                submissions={getFilteredSubmissions('pending')}
                onReview={(id) => navigate(`/onboarding/review/${id}`)}
                loading={loading}
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* In Progress Tab */}
        <TabsContent value="inprogress" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>In Progress</CardTitle>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-400" />
                  <Input
                    placeholder="Search candidates..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 w-64"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <SubmissionTable
                submissions={getFilteredSubmissions('inprogress')}
                onReview={(id) => navigate(`/onboarding/review/${id}`)}
                loading={loading}
                showResendLink
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Completed Tab */}
        <TabsContent value="completed" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Completed Onboarding</CardTitle>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-400" />
                  <Input
                    placeholder="Search candidates..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 w-64"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <SubmissionTable
                submissions={getFilteredSubmissions('completed')}
                onReview={(id) => navigate(`/onboarding/review/${id}`)}
                loading={loading}
                showEmployeeId
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Legacy Tab */}
        <TabsContent value="legacy" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                Legacy Onboarding Records
              </CardTitle>
              <CardDescription>
                These employees were created via the old onboarding flow and may need Go-Live completion.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {legacyRecords.length === 0 ? (
                <div className="text-center py-12 text-zinc-500">
                  <CheckCircle2 className="w-12 h-12 mx-auto mb-4 text-green-300" />
                  <p>No legacy records pending!</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee ID</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Department</TableHead>
                      <TableHead>Go-Live Status</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {legacyRecords.map(emp => (
                      <TableRow key={emp.id}>
                        <TableCell className="font-mono">{emp.employee_id}</TableCell>
                        <TableCell>{emp.full_name || `${emp.first_name} ${emp.last_name}`}</TableCell>
                        <TableCell>{emp.department || 'N/A'}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{emp.go_live_status || 'not_submitted'}</Badge>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => navigate(`/go-live?employee=${emp.id}`)}
                          >
                            Go-Live
                            <ChevronRight className="w-4 h-4 ml-1" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

// Submission Table Component
const SubmissionTable = ({ submissions, onReview, loading, showResendLink, showEmployeeId }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (submissions.length === 0) {
    return (
      <div className="text-center py-12 text-zinc-500">
        <Users className="w-12 h-12 mx-auto mb-4 text-zinc-300" />
        <p>No submissions found</p>
      </div>
    );
  }

  const getStatusBadge = (status) => {
    const statusConfig = {
      invited: { color: 'bg-blue-100 text-blue-700', label: 'Invited' },
      draft: { color: 'bg-zinc-100 text-zinc-700', label: 'In Progress' },
      submitted: { color: 'bg-amber-100 text-amber-700', label: 'Pending Review' },
      revision_requested: { color: 'bg-orange-100 text-orange-700', label: 'Revision Requested' },
      approved: { color: 'bg-green-100 text-green-700', label: 'Approved' },
      rejected: { color: 'bg-red-100 text-red-700', label: 'Rejected' },
      completed: { color: 'bg-emerald-100 text-emerald-700', label: 'Completed' },
    };
    const config = statusConfig[status] || { color: 'bg-zinc-100 text-zinc-700', label: status };
    return <Badge className={config.color}>{config.label}</Badge>;
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Candidate</TableHead>
          <TableHead>Position</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Progress</TableHead>
          <TableHead>Date</TableHead>
          {showEmployeeId && <TableHead>Employee ID</TableHead>}
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {submissions.map(sub => (
          <TableRow key={sub.id}>
            <TableCell>
              <div>
                <p className="font-medium">{sub.candidate_name}</p>
                <p className="text-xs text-zinc-500">{sub.candidate_email}</p>
              </div>
            </TableCell>
            <TableCell>{sub.offered_position}</TableCell>
            <TableCell>{getStatusBadge(sub.status)}</TableCell>
            <TableCell>
              <div className="flex items-center gap-2">
                <Progress value={sub.progress?.percentage || 0} className="w-20 h-2" />
                <span className="text-xs text-zinc-500">{sub.progress?.percentage || 0}%</span>
              </div>
            </TableCell>
            <TableCell className="text-sm text-zinc-500">
              {sub.submitted_at
                ? new Date(sub.submitted_at).toLocaleDateString()
                : new Date(sub.invited_at).toLocaleDateString()}
            </TableCell>
            {showEmployeeId && (
              <TableCell className="font-mono text-green-600">
                {sub.employee_id_generated || '-'}
              </TableCell>
            )}
            <TableCell className="text-right">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onReview(sub.id)}
                data-testid={`review-btn-${sub.id}`}
              >
                <Eye className="w-4 h-4 mr-1" />
                {sub.status === 'submitted' ? 'Review' : 'View'}
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

export default OnboardingHub;
