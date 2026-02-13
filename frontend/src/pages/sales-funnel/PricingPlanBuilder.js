import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Plus, Trash2, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { formatINR, parseINR } from '../../utils/currency';

const PricingPlanBuilder = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');
  
  const [lead, setLead] = useState(null);
  const [loading, setLoading] = useState(false);
  const [consultants, setConsultants] = useState([
    { consultant_type: 'lead', count: 1, meetings: 0, hours: 0, rate_per_meeting: 12500 }
  ]);
  const [sowItems, setSOWItems] = useState([
    { category: '', sub_category: '', description: '', deliverables: [] }
  ]);
  const [formData, setFormData] = useState({
    project_duration_type: 'monthly',
    project_duration_months: 3,
    payment_schedule: 'monthly',
    discount_percentage: 0,
    growth_consulting_plan: '',
    growth_guarantee: ''
  });

  useEffect(() => {
    if (leadId) {
      fetchLead();
    }
  }, [leadId]);

  const fetchLead = async () => {
    try {
      const response = await axios.get(`${API}/leads/${leadId}`);
      setLead(response.data);
    } catch (error) {
      toast.error('Failed to fetch lead');
    }
  };

  const addConsultant = () => {
    setConsultants([...consultants, {
      consultant_type: 'lead',
      count: 1,
      meetings: 0,
      hours: 0,
      rate_per_meeting: 12500
    }]);
  };

  const removeConsultant = (index) => {
    setConsultants(consultants.filter((_, i) => i !== index));
  };

  const updateConsultant = (index, field, value) => {
    const updated = [...consultants];
    updated[index][field] = field === 'consultant_type' ? value : parseFloat(value) || 0;
    setConsultants(updated);
  };

  const calculateTotals = () => {
    const totalMeetings = consultants.reduce((sum, c) => sum + (c.meetings || 0), 0);
    const subtotal = consultants.reduce((sum, c) => sum + ((c.meetings || 0) * (c.rate_per_meeting || 12500)), 0);
    const discount = subtotal * (formData.discount_percentage / 100);
    const afterDiscount = subtotal - discount;
    const gst = afterDiscount * 0.18;
    const total = afterDiscount + gst;
    
    return { totalMeetings, subtotal, discount, gst, total };
  };

  const totals = calculateTotals();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const pricingPlan = {
        lead_id: leadId,
        ...formData,
        consultants,
        sow_items: sowItems.filter(s => s.category)
      };

      await axios.post(`${API}/pricing-plans`, pricingPlan);
      toast.success('Pricing plan created successfully');
      navigate(`/sales-funnel/quotations?leadId=${leadId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create pricing plan');
    } finally {
      setLoading(false);
    }
  };

  const consultantTypes = [
    { value: 'lead', label: 'Lead Consultant' },
    { value: 'lean', label: 'Lean Consultant' },
    { value: 'principal', label: 'Principal Consultant' },
    { value: 'hr', label: 'HR Consultant' },
    { value: 'sales', label: 'Sales Consultant' },
    { value: 'project_manager', label: 'Project Manager' },
    { value: 'trainer', label: 'Trainer' }
  ];

  return (
    <div className="max-w-6xl mx-auto" data-testid="pricing-plan-builder">
      <div className="mb-6">
        <Button
          onClick={() => navigate('/leads')}
          variant="ghost"
          className="mb-4 hover:bg-zinc-100 rounded-sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Leads
        </Button>
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          Create Pricing Plan
        </h1>
        {lead && (
          <p className="text-zinc-500">
            For: {lead.first_name} {lead.last_name} - {lead.company}
          </p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Project Duration */}
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
              Project Duration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Duration Type</Label>
                <select
                  value={formData.project_duration_type}
                  onChange={(e) => setFormData({ ...formData, project_duration_type: e.target.value })}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                >
                  <option value="monthly">Monthly</option>
                  <option value="quarterly">Quarterly</option>
                  <option value="half_yearly">Half Yearly</option>
                  <option value="yearly">Yearly</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Duration (Months)</Label>
                <Input
                  type="number"
                  min="1"
                  value={formData.project_duration_months}
                  onChange={(e) => setFormData({ ...formData, project_duration_months: parseInt(e.target.value) })}
                  className="rounded-sm border-zinc-200"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Payment Schedule</Label>
              <select
                value={formData.payment_schedule}
                onChange={(e) => setFormData({ ...formData, payment_schedule: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              >
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="milestone">Milestone Based</option>
                <option value="upfront">Upfront</option>
              </select>
            </div>
          </CardContent>
        </Card>

        {/* Consultant Allocation */}
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
              Team Deployment
            </CardTitle>
            <Button
              type="button"
              onClick={addConsultant}
              size="sm"
              className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Add Consultant
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            {consultants.map((consultant, index) => (
              <div key={index} className="p-4 border border-zinc-200 rounded-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium text-zinc-950">Consultant #{index + 1}</div>
                  {consultants.length > 1 && (
                    <Button
                      type="button"
                      onClick={() => removeConsultant(index)}
                      size="sm"
                      variant="ghost"
                      className="text-red-600 hover:bg-red-50 rounded-sm"
                    >
                      <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                    </Button>
                  )}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <div className="col-span-2">
                    <Label className="text-xs text-zinc-500">Type</Label>
                    <select
                      value={consultant.consultant_type}
                      onChange={(e) => updateConsultant(index, 'consultant_type', e.target.value)}
                      className="w-full h-9 px-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                    >
                      {consultantTypes.map(type => (
                        <option key={type.value} value={type.value}>{type.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-500">Count</Label>
                    <Input
                      type="number"
                      min="1"
                      value={consultant.count}
                      onChange={(e) => updateConsultant(index, 'count', e.target.value)}
                      className="h-9 rounded-sm border-zinc-200 text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-500">Meetings</Label>
                    <Input
                      type="number"
                      min="0"
                      value={consultant.meetings}
                      onChange={(e) => updateConsultant(index, 'meetings', e.target.value)}
                      className="h-9 rounded-sm border-zinc-200 text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-500">Hours</Label>
                    <Input
                      type="number"
                      min="0"
                      value={consultant.hours}
                      onChange={(e) => updateConsultant(index, 'hours', e.target.value)}
                      className="h-9 rounded-sm border-zinc-200 text-sm"
                    />
                  </div>
                </div>
                <div className="text-xs text-zinc-500">
                  Rate: {formatINR(consultant.rate_per_meeting)}/meeting | 
                  Subtotal: {formatINR((consultant.meetings || 0) * (consultant.rate_per_meeting || 12500))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Pricing Summary */}
        <Card className="border-zinc-200 shadow-none rounded-sm bg-zinc-50">
          <CardHeader>
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
              Pricing Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Discount (%)</Label>
              <Input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={formData.discount_percentage}
                onChange={(e) => setFormData({ ...formData, discount_percentage: parseFloat(e.target.value) || 0 })}
                className="rounded-sm border-zinc-200"
              />
            </div>
            <div className="space-y-2 pt-4 border-t border-zinc-200">
              <div className="flex justify-between text-sm">
                <span className="text-zinc-600">Total Meetings:</span>
                <span className="font-semibold text-zinc-950 data-text">{totals.totalMeetings}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-zinc-600">Subtotal:</span>
                <span className="font-semibold text-zinc-950 data-text">{formatINR(totals.subtotal)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-zinc-600">Discount ({formData.discount_percentage}%):</span>
                <span className="font-semibold text-red-600 data-text">- {formatINR(totals.discount)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-zinc-600">GST (18%):</span>
                <span className="font-semibold text-zinc-950 data-text">+ {formatINR(totals.gst)}</span>
              </div>
              <div className="flex justify-between text-lg font-bold pt-2 border-t border-zinc-300">
                <span className="text-zinc-950">Grand Total:</span>
                <span className="text-emerald-600 data-text">{formatINR(totals.total)}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Growth Plans */}
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
              Growth Consulting & Guarantee
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Growth Consulting Plan</Label>
              <textarea
                value={formData.growth_consulting_plan}
                onChange={(e) => setFormData({ ...formData, growth_consulting_plan: e.target.value })}
                rows={3}
                placeholder="e.g., 1 Principal Consultant - 12 meetings monthly, 2 Lead Consultants - 48 meetings weekly"
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Growth Guarantee</Label>
              <textarea
                value={formData.growth_guarantee}
                onChange={(e) => setFormData({ ...formData, growth_guarantee: e.target.value })}
                rows={3}
                placeholder="Specific growth metrics and guarantees"
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
          </CardContent>
        </Card>

        <div className="flex gap-4">
          <Button
            type="button"
            onClick={() => navigate('/leads')}
            variant="outline"
            className="flex-1 rounded-sm border-zinc-200"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={loading || consultants.length === 0}
            className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
          >
            {loading ? 'Creating...' : 'Create Pricing Plan'}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default PricingPlanBuilder;
