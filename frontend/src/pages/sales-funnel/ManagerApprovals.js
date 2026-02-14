import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { ArrowLeft, CheckCircle, XCircle, Clock, FileCheck, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../../utils/currency';

const ManagerApprovals = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [selectedAgreement, setSelectedAgreement] = useState(null);
  const [rejectReason, setRejectReason] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [approvalsRes, leadsRes] = await Promise.all([
        axios.get(`${API}/agreements/pending-approval`),
        axios.get(`${API}/leads`)
      ]);
      setPendingApprovals(approvalsRes.data);
      setLeads(leadsRes.data);
    } catch (error) {
      toast.error('Failed to fetch pending approvals');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (agreementId) => {
    try {
      await axios.patch(`${API}/agreements/${agreementId}/approve`);
      toast.success('Agreement approved successfully');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve agreement');
    }
  };

  const openRejectDialog = (agreement) => {
    setSelectedAgreement(agreement);
    setRejectReason('');
    setRejectDialogOpen(true);
  };

  const handleReject = async (e) => {
    e.preventDefault();
    if (!selectedAgreement) return;
    
    try {
      await axios.patch(`${API}/agreements/${selectedAgreement.id}/reject`, {
        rejection_reason: rejectReason
      });
      toast.success('Agreement rejected');
      setRejectDialogOpen(false);
      setSelectedAgreement(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject agreement');
    }
  };

  const getLeadInfo = (leadId) => {
    const lead = leads.find(l => l.id === leadId);
    return lead ? {
      name: `${lead.first_name} ${lead.last_name}`,
      company: lead.company,
      email: lead.email
    } : { name: 'Unknown', company: 'Unknown', email: '' };
  };

  const canApprove = user?.role === 'manager' || user?.role === 'admin';

  if (!canApprove) {
    return (
      <div className="max-w-6xl mx-auto" data-testid="manager-approvals-page">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <AlertTriangle className="w-12 h-12 text-yellow-500 mb-4" strokeWidth={1} />
            <p className="text-zinc-700 font-medium mb-2">Access Restricted</p>
            <p className="text-zinc-500">Only managers and admins can access approvals</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto" data-testid="manager-approvals-page">
      <div className="mb-6">
        <Button
          onClick={() => navigate('/')}
          variant="ghost"
          className="mb-4 hover:bg-zinc-100 rounded-sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Dashboard
        </Button>
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
            Pending Approvals
          </h1>
          <p className="text-zinc-500">Review and approve agreements submitted by sales team</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-zinc-500">Loading pending approvals...</div>
        </div>
      ) : pendingApprovals.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <CheckCircle className="w-12 h-12 text-emerald-500 mb-4" strokeWidth={1} />
            <p className="text-zinc-700 font-medium mb-2">All caught up!</p>
            <p className="text-zinc-500">No agreements pending approval</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {pendingApprovals.map((item) => {
            const leadInfo = getLeadInfo(item.agreement.lead_id);
            return (
              <Card
                key={item.agreement.id}
                data-testid={`approval-card-${item.agreement.id}`}
                className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors"
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-lg font-semibold text-zinc-950">
                        {item.agreement.agreement_number}
                      </CardTitle>
                      <p className="text-sm text-zinc-500 mt-1">
                        {leadInfo.name} - {leadInfo.company}
                      </p>
                      {leadInfo.email && (
                        <p className="text-xs text-zinc-400">{leadInfo.email}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-1 px-2 py-1 bg-yellow-50 text-yellow-700 rounded-sm">
                      <Clock className="w-3 h-3" strokeWidth={1.5} />
                      <span className="text-xs font-medium">Pending</span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {/* Quotation Details */}
                  {item.quotation && (
                    <div className="mb-4 p-4 bg-zinc-50 rounded-sm">
                      <div className="text-xs text-zinc-500 uppercase tracking-wide mb-3">
                        Quotation Details ({item.quotation.quotation_number})
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <div className="text-xs text-zinc-500">Meetings</div>
                          <div className="text-sm font-semibold text-zinc-950">{item.quotation.total_meetings}</div>
                        </div>
                        <div>
                          <div className="text-xs text-zinc-500">Subtotal</div>
                          <div className="text-sm font-semibold text-zinc-950">{formatINR(item.quotation.subtotal)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-zinc-500">GST</div>
                          <div className="text-sm font-semibold text-zinc-950">{formatINR(item.quotation.gst_amount)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-zinc-500">Grand Total</div>
                          <div className="text-sm font-semibold text-emerald-600">{formatINR(item.quotation.grand_total)}</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Agreement Details */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Type</div>
                      <div className="text-sm font-medium text-zinc-950 capitalize">{item.agreement.agreement_type}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Payment Terms</div>
                      <div className="text-sm font-medium text-zinc-950">{item.agreement.payment_terms}</div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Start Date</div>
                      <div className="text-sm font-medium text-zinc-950">
                        {item.agreement.start_date ? new Date(item.agreement.start_date).toLocaleDateString() : 'Not set'}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-zinc-500 uppercase tracking-wide">Submitted</div>
                      <div className="text-sm font-medium text-zinc-950">
                        {new Date(item.agreement.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>

                  {item.agreement.special_conditions && (
                    <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-sm">
                      <div className="text-xs text-blue-700 uppercase tracking-wide mb-1">Special Conditions</div>
                      <p className="text-sm text-blue-900">{item.agreement.special_conditions}</p>
                    </div>
                  )}

                  <div className="flex gap-3 pt-4 border-t border-zinc-200">
                    <Button
                      onClick={() => handleApprove(item.agreement.id)}
                      data-testid={`approve-btn-${item.agreement.id}`}
                      className="bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm shadow-none"
                    >
                      <CheckCircle className="w-4 h-4 mr-2" strokeWidth={1.5} />
                      Approve
                    </Button>
                    <Button
                      onClick={() => openRejectDialog(item.agreement)}
                      data-testid={`reject-btn-${item.agreement.id}`}
                      variant="outline"
                      className="border-red-200 text-red-600 hover:bg-red-50 rounded-sm"
                    >
                      <XCircle className="w-4 h-4 mr-2" strokeWidth={1.5} />
                      Reject
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Reject Agreement
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {selectedAgreement && `Rejecting ${selectedAgreement.agreement_number}`}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleReject} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-950">Reason for Rejection</label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                rows={4}
                required
                placeholder="Please provide a reason for rejecting this agreement..."
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
            <div className="flex gap-3">
              <Button
                type="button"
                onClick={() => setRejectDialogOpen(false)}
                variant="outline"
                className="flex-1 rounded-sm border-zinc-200"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="flex-1 bg-red-600 text-white hover:bg-red-700 rounded-sm shadow-none"
              >
                Reject Agreement
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ManagerApprovals;
