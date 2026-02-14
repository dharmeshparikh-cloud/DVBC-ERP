import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { ArrowLeft, Plus, FileText, CheckCircle, Clock, Send } from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../../utils/currency';

const Quotations = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');
  
  const [quotations, setQuotations] = useState([]);
  const [pricingPlans, setPricingPlans] = useState([]);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    pricing_plan_id: '',
    lead_id: leadId || '',
    base_rate_per_meeting: 12500,
    validity_days: 30,
    terms_and_conditions: 'Standard terms and conditions apply.\n\n1. Payment due within 15 days of invoice.\n2. Services subject to availability.\n3. This quotation is valid for 30 days.'
  });

  useEffect(() => {
    fetchData();
  }, [leadId]);

  const fetchData = async () => {
    try {
      const [quotationsRes, plansRes, leadsRes] = await Promise.all([
        axios.get(`${API}/quotations`, { params: leadId ? { lead_id: leadId } : {} }),
        axios.get(`${API}/pricing-plans`, { params: leadId ? { lead_id: leadId } : {} }),
        axios.get(`${API}/leads`)
      ]);
      setQuotations(quotationsRes.data);
      setPricingPlans(plansRes.data);
      setLeads(leadsRes.data);
    } catch (error) {
      toast.error('Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/quotations`, formData);
      toast.success('Quotation created successfully');
      setDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create quotation');
    }
  };

  const handleFinalize = async (quotationId) => {
    try {
      await axios.patch(`${API}/quotations/${quotationId}/finalize`);
      toast.success('Quotation finalized');
      fetchData();
    } catch (error) {
      toast.error('Failed to finalize quotation');
    }
  };

  const getStatusBadge = (status, isFinal) => {
    if (isFinal) return 'bg-emerald-50 text-emerald-700';
    const styles = {
      draft: 'bg-zinc-100 text-zinc-600',
      sent: 'bg-blue-50 text-blue-700',
      accepted: 'bg-emerald-50 text-emerald-700',
      rejected: 'bg-red-50 text-red-700'
    };
    return styles[status] || styles.draft;
  };

  const getLeadName = (leadId) => {
    const lead = leads.find(l => l.id === leadId);
    return lead ? `${lead.first_name} ${lead.last_name} - ${lead.company}` : 'Unknown Lead';
  };

  const canEdit = user?.role !== 'manager';

  return (
    <div className="max-w-6xl mx-auto" data-testid="quotations-page">
      <div className="mb-6">
        <Button
          onClick={() => navigate('/leads')}
          variant="ghost"
          className="mb-4 hover:bg-zinc-100 rounded-sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Leads
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              Quotations
            </h1>
            <p className="text-zinc-500">Manage and send quotations to clients</p>
          </div>
          {canEdit && (
            <Button
              onClick={() => setDialogOpen(true)}
              data-testid="create-quotation-btn"
              className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Create Quotation
            </Button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-zinc-500">Loading quotations...</div>
        </div>
      ) : quotations.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <FileText className="w-12 h-12 text-zinc-300 mb-4" strokeWidth={1} />
            <p className="text-zinc-500 mb-4">No quotations found</p>
            {canEdit && pricingPlans.length > 0 && (
              <Button
                onClick={() => setDialogOpen(true)}
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                Create Your First Quotation
              </Button>
            )}
            {pricingPlans.length === 0 && (
              <p className="text-sm text-zinc-400">Create a pricing plan first</p>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {quotations.map((quotation) => (
            <Card
              key={quotation.id}
              data-testid={`quotation-card-${quotation.id}`}
              className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors"
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg font-semibold text-zinc-950">
                      {quotation.quotation_number}
                    </CardTitle>
                    <p className="text-sm text-zinc-500 mt-1">
                      {getLeadName(quotation.lead_id)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 text-xs font-medium rounded-sm ${getStatusBadge(quotation.status, quotation.is_final)}`}>
                      {quotation.is_final ? 'Finalized' : quotation.status}
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wide">Meetings</div>
                    <div className="text-lg font-semibold text-zinc-950">{quotation.total_meetings}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wide">Subtotal</div>
                    <div className="text-lg font-semibold text-zinc-950">{formatINR(quotation.subtotal)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wide">GST (18%)</div>
                    <div className="text-lg font-semibold text-zinc-950">{formatINR(quotation.gst_amount)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wide">Grand Total</div>
                    <div className="text-lg font-semibold text-emerald-600">{formatINR(quotation.grand_total)}</div>
                  </div>
                </div>
                <div className="flex gap-2">
                  {!quotation.is_final && canEdit && (
                    <Button
                      onClick={() => handleFinalize(quotation.id)}
                      size="sm"
                      variant="outline"
                      className="rounded-sm border-zinc-200"
                    >
                      <CheckCircle className="w-4 h-4 mr-2" strokeWidth={1.5} />
                      Finalize
                    </Button>
                  )}
                  {quotation.is_final && canEdit && (
                    <Button
                      onClick={() => navigate(`/sales-funnel/agreements?quotationId=${quotation.id}&leadId=${quotation.lead_id}`)}
                      size="sm"
                      className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                    >
                      <Send className="w-4 h-4 mr-2" strokeWidth={1.5} />
                      Create Agreement
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Create Quotation
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Generate a quotation from a pricing plan
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Lead</Label>
              <select
                value={formData.lead_id}
                onChange={(e) => setFormData({ ...formData, lead_id: e.target.value })}
                required
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              >
                <option value="">Select a lead</option>
                {leads.map(lead => (
                  <option key={lead.id} value={lead.id}>
                    {lead.first_name} {lead.last_name} - {lead.company}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Pricing Plan</Label>
              <select
                value={formData.pricing_plan_id}
                onChange={(e) => setFormData({ ...formData, pricing_plan_id: e.target.value })}
                required
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              >
                <option value="">Select a pricing plan</option>
                {pricingPlans.filter(p => !formData.lead_id || p.lead_id === formData.lead_id).map(plan => (
                  <option key={plan.id} value={plan.id}>
                    {plan.id.slice(0, 8)} - {plan.project_duration_months} months
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Base Rate per Meeting (₹)</Label>
              <Input
                type="number"
                value={formData.base_rate_per_meeting}
                onChange={(e) => setFormData({ ...formData, base_rate_per_meeting: parseFloat(e.target.value) })}
                className="rounded-sm border-zinc-200"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Validity (Days)</Label>
              <Input
                type="number"
                value={formData.validity_days}
                onChange={(e) => setFormData({ ...formData, validity_days: parseInt(e.target.value) })}
                className="rounded-sm border-zinc-200"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Terms & Conditions</Label>
              <textarea
                value={formData.terms_and_conditions}
                onChange={(e) => setFormData({ ...formData, terms_and_conditions: e.target.value })}
                rows={4}
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              Create Quotation
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Quotations;
