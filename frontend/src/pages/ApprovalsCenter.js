import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { 
  CheckCircle, XCircle, Clock, AlertCircle, ChevronRight, 
  FileText, Calendar, User, MessageSquare, Send
} from 'lucide-react';
import { toast } from 'sonner';

const APPROVAL_TYPE_LABELS = {
  sow_item: 'SOW Item',
  agreement: 'Agreement',
  quotation: 'Quotation',
  leave_request: 'Leave Request',
  expense: 'Expense',
  client_communication: 'Client Communication'
};

const ApprovalsCenter = () => {
  const { user } = useContext(AuthContext);
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [myRequests, setMyRequests] = useState([]);
  const [allApprovals, setAllApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('pending');
  const [selectedApproval, setSelectedApproval] = useState(null);
  const [actionDialog, setActionDialog] = useState(false);
  const [actionType, setActionType] = useState('');
  const [comments, setComments] = useState('');

  const isAdmin = user?.role === 'admin';
  const isManager = ['admin', 'manager', 'hr_manager', 'project_manager'].includes(user?.role);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [pendingRes, myRes] = await Promise.all([
        axios.get(`${API}/approvals/pending`),
        axios.get(`${API}/approvals/my-requests`)
      ]);
      
      setPendingApprovals(pendingRes.data || []);
      setMyRequests(myRes.data || []);
      
      // Fetch all approvals if admin/manager
      if (isManager) {
        const allRes = await axios.get(`${API}/approvals/all`);
        setAllApprovals(allRes.data || []);
      }
    } catch (error) {
      console.error('Error fetching approvals:', error);
      toast.error('Failed to load approvals');
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async () => {
    if (!selectedApproval) return;
    
    try {
      await axios.post(`${API}/approvals/${selectedApproval.id}/action`, {
        action: actionType,
        comments: comments
      });
      
      toast.success(`Request ${actionType === 'approve' ? 'approved' : 'rejected'} successfully`);
      setActionDialog(false);
      setComments('');
      setSelectedApproval(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${actionType} request`);
    }
  };

  const openActionDialog = (approval, action) => {
    setSelectedApproval(approval);
    setActionType(action);
    setComments('');
    setActionDialog(true);
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      approved: 'bg-emerald-100 text-emerald-700 border-emerald-200',
      rejected: 'bg-red-100 text-red-700 border-red-200',
      escalated: 'bg-purple-100 text-purple-700 border-purple-200'
    };
    return styles[status] || 'bg-zinc-100 text-zinc-700 border-zinc-200';
  };

  const getStatusIcon = (status) => {
    const icons = {
      pending: <Clock className="w-4 h-4 text-yellow-600" />,
      approved: <CheckCircle className="w-4 h-4 text-emerald-600" />,
      rejected: <XCircle className="w-4 h-4 text-red-600" />,
      escalated: <AlertCircle className="w-4 h-4 text-purple-600" />
    };
    return icons[status] || <Clock className="w-4 h-4 text-zinc-600" />;
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96"><div className="text-zinc-500">Loading...</div></div>;
  }

  return (
    <div data-testid="approvals-center">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          Approvals Center
        </h1>
        <p className="text-zinc-500">Review and manage approval requests</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase text-zinc-500">Pending My Action</p>
                <p className="text-2xl font-semibold text-yellow-600">{pendingApprovals.length}</p>
              </div>
              <Clock className="w-8 h-8 text-yellow-200" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase text-zinc-500">My Requests</p>
                <p className="text-2xl font-semibold text-blue-600">{myRequests.length}</p>
              </div>
              <Send className="w-8 h-8 text-blue-200" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase text-zinc-500">My Approved</p>
                <p className="text-2xl font-semibold text-emerald-600">
                  {myRequests.filter(r => r.overall_status === 'approved').length}
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-emerald-200" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase text-zinc-500">My Rejected</p>
                <p className="text-2xl font-semibold text-red-600">
                  {myRequests.filter(r => r.overall_status === 'rejected').length}
                </p>
              </div>
              <XCircle className="w-8 h-8 text-red-200" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-zinc-200 mb-6">
        <button
          onClick={() => setActiveTab('pending')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'pending' 
              ? 'border-zinc-950 text-zinc-950' 
              : 'border-transparent text-zinc-500 hover:text-zinc-950'
          }`}
        >
          <Clock className="w-4 h-4 inline mr-2" />
          Pending My Action ({pendingApprovals.length})
        </button>
        <button
          onClick={() => setActiveTab('my-requests')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'my-requests' 
              ? 'border-zinc-950 text-zinc-950' 
              : 'border-transparent text-zinc-500 hover:text-zinc-950'
          }`}
        >
          <Send className="w-4 h-4 inline mr-2" />
          My Requests ({myRequests.length})
        </button>
        {isManager && (
          <button
            onClick={() => setActiveTab('all')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'all' 
                ? 'border-zinc-950 text-zinc-950' 
                : 'border-transparent text-zinc-500 hover:text-zinc-950'
            }`}
          >
            <FileText className="w-4 h-4 inline mr-2" />
            All Approvals ({allApprovals.length})
          </button>
        )}
      </div>

      {/* Pending Approvals Tab */}
      {activeTab === 'pending' && (
        <div className="space-y-4">
          {pendingApprovals.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-12 text-center">
                <CheckCircle className="w-12 h-12 text-emerald-300 mx-auto mb-4" />
                <p className="text-zinc-500">No pending approvals. You're all caught up!</p>
              </CardContent>
            </Card>
          ) : (
            pendingApprovals.map(approval => (
              <Card key={approval.id} className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className={`px-2 py-1 text-xs font-medium rounded border ${getStatusBadge(approval.overall_status)}`}>
                          {APPROVAL_TYPE_LABELS[approval.approval_type] || approval.approval_type}
                        </span>
                        {approval.is_client_facing && (
                          <span className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded">Client Facing</span>
                        )}
                        {approval.requires_hr_approval && (
                          <span className="px-2 py-1 text-xs bg-pink-100 text-pink-700 rounded">HR Required</span>
                        )}
                      </div>
                      <h3 className="font-medium text-zinc-950 text-lg">{approval.reference_title}</h3>
                      <div className="flex items-center gap-4 mt-2 text-sm text-zinc-500">
                        <span className="flex items-center gap-1">
                          <User className="w-4 h-4" />
                          {approval.requester_name}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          {new Date(approval.created_at).toLocaleDateString()}
                        </span>
                        <span className="flex items-center gap-1">
                          Level {approval.current_level} of {approval.max_level}
                        </span>
                      </div>
                      
                      {/* Approval Chain */}
                      <div className="mt-4 flex items-center gap-2 text-xs">
                        {approval.approval_levels?.map((level, idx) => (
                          <React.Fragment key={idx}>
                            <div className={`flex items-center gap-1 px-2 py-1 rounded ${
                              level.status === 'approved' ? 'bg-emerald-50 text-emerald-700' :
                              level.status === 'rejected' ? 'bg-red-50 text-red-700' :
                              level.level === approval.current_level ? 'bg-yellow-50 text-yellow-700 border border-yellow-300' :
                              'bg-zinc-50 text-zinc-500'
                            }`}>
                              {getStatusIcon(level.status)}
                              <span>{level.approver_name}</span>
                              <span className="text-xs opacity-60">({level.approver_type?.replace('_', ' ')})</span>
                            </div>
                            {idx < approval.approval_levels.length - 1 && (
                              <ChevronRight className="w-4 h-4 text-zinc-300" />
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                    
                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 ml-4">
                      <Button
                        onClick={() => openActionDialog(approval, 'approve')}
                        className="bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm shadow-none"
                      >
                        <CheckCircle className="w-4 h-4 mr-1" />
                        Approve
                      </Button>
                      <Button
                        onClick={() => openActionDialog(approval, 'reject')}
                        variant="outline"
                        className="border-red-300 text-red-600 hover:bg-red-50 rounded-sm"
                      >
                        <XCircle className="w-4 h-4 mr-1" />
                        Reject
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* My Requests Tab */}
      {activeTab === 'my-requests' && (
        <div className="space-y-4">
          {myRequests.length === 0 ? (
            <Card className="border-zinc-200 shadow-none rounded-sm">
              <CardContent className="p-12 text-center">
                <Send className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
                <p className="text-zinc-500">You haven't submitted any approval requests yet.</p>
              </CardContent>
            </Card>
          ) : (
            myRequests.map(approval => (
              <Card key={approval.id} className="border-zinc-200 shadow-none rounded-sm">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className={`px-2 py-1 text-xs font-medium rounded border ${getStatusBadge(approval.overall_status)}`}>
                          {approval.overall_status}
                        </span>
                        <span className="text-xs text-zinc-400">
                          {APPROVAL_TYPE_LABELS[approval.approval_type] || approval.approval_type}
                        </span>
                      </div>
                      <h3 className="font-medium text-zinc-950">{approval.reference_title}</h3>
                      <div className="text-xs text-zinc-500 mt-1">
                        Submitted {new Date(approval.created_at).toLocaleDateString()}
                      </div>
                      
                      {/* Approval Chain */}
                      <div className="mt-3 flex items-center gap-2 text-xs">
                        {approval.approval_levels?.map((level, idx) => (
                          <React.Fragment key={idx}>
                            <div className={`flex items-center gap-1 px-2 py-1 rounded ${
                              level.status === 'approved' ? 'bg-emerald-50 text-emerald-700' :
                              level.status === 'rejected' ? 'bg-red-50 text-red-700' :
                              level.level === approval.current_level ? 'bg-yellow-50 text-yellow-700' :
                              'bg-zinc-50 text-zinc-500'
                            }`}>
                              {getStatusIcon(level.status)}
                              <span>{level.approver_name}</span>
                            </div>
                            {idx < approval.approval_levels.length - 1 && (
                              <ChevronRight className="w-4 h-4 text-zinc-300" />
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {getStatusIcon(approval.overall_status)}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* All Approvals Tab (Admin/Manager) */}
      {activeTab === 'all' && isManager && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="bg-zinc-50 text-xs font-medium uppercase tracking-wide text-zinc-500">
                  <th className="px-4 py-3 text-left">Request</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Requester</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Current Level</th>
                  <th className="px-4 py-3 text-left">Date</th>
                </tr>
              </thead>
              <tbody>
                {allApprovals.map(approval => (
                  <tr key={approval.id} className="border-b border-zinc-100 hover:bg-zinc-50">
                    <td className="px-4 py-3 font-medium text-zinc-900">{approval.reference_title}</td>
                    <td className="px-4 py-3 text-sm text-zinc-600">
                      {APPROVAL_TYPE_LABELS[approval.approval_type] || approval.approval_type}
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-600">{approval.requester_name}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded border ${getStatusBadge(approval.overall_status)}`}>
                        {approval.overall_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-600">
                      {approval.current_level} / {approval.max_level}
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-500">
                      {new Date(approval.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {allApprovals.length === 0 && (
              <div className="text-center py-12 text-zinc-400">
                No approval requests found.
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Action Dialog */}
      <Dialog open={actionDialog} onOpenChange={setActionDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              {actionType === 'approve' ? 'Approve Request' : 'Reject Request'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {selectedApproval && (
              <div className="p-4 bg-zinc-50 rounded-sm">
                <p className="font-medium text-zinc-950">{selectedApproval.reference_title}</p>
                <p className="text-sm text-zinc-500 mt-1">
                  Requested by {selectedApproval.requester_name}
                </p>
              </div>
            )}
            
            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-700">Comments {actionType === 'reject' && '(required)'}</label>
              <textarea
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder={actionType === 'approve' ? 'Optional comments...' : 'Reason for rejection...'}
                rows={3}
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
            
            <div className="flex gap-3 pt-4">
              <Button onClick={() => setActionDialog(false)} variant="outline" className="flex-1 rounded-sm">
                Cancel
              </Button>
              <Button 
                onClick={handleAction}
                disabled={actionType === 'reject' && !comments}
                className={`flex-1 rounded-sm shadow-none ${
                  actionType === 'approve' 
                    ? 'bg-emerald-600 text-white hover:bg-emerald-700' 
                    : 'bg-red-600 text-white hover:bg-red-700'
                }`}
              >
                {actionType === 'approve' ? 'Approve' : 'Reject'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ApprovalsCenter;
