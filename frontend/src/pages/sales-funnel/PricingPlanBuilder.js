import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Plus, Trash2, ArrowLeft, Users, Calculator } from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../../utils/currency';

// Duration type to months mapping
const DURATION_TYPE_MONTHS = {
  'monthly': 1,
  'quarterly': 3,
  'half_yearly': 6,
  'yearly': 12,
  'custom': null // User enters manually
};

// Consultant roles
const CONSULTANT_ROLES = [
  'Project Manager',
  'Principal Consultant',
  'Lead Consultant',
  'Senior Consultant',
  'Lean Consultant',
  'HR Consultant',
  'Sales Trainer',
  'Operations Consultant',
  'Data Analyst',
  'Digital Marketing Manager',
  'Subject Matter Expert',
  'Account Manager'
];

// Meeting types
const MEETING_TYPES = [
  'Monthly Review',
  'Weekly Review',
  'Daily Standup',
  'Online Review',
  'On-site Visit',
  'Strategy Session',
  'Training Session',
  'Progress Update',
  'Kickoff Meeting',
  'Quarterly Business Review',
  'Data Analysis Review',
  'Marketing Review',
  'HR Consultation'
];

// Frequency options with per-month multiplier
const FREQUENCY_OPTIONS = [
  { value: '1 per day', label: '1 per day (Daily)', perMonth: 22 }, // 22 working days
  { value: '2 per day', label: '2 per day', perMonth: 44 },
  { value: '5 per week', label: '5 per week', perMonth: 20 },
  { value: '4 per week', label: '4 per week', perMonth: 16 },
  { value: '3 per week', label: '3 per week', perMonth: 12 },
  { value: '2 per week', label: '2 per week', perMonth: 8 },
  { value: '1 per week', label: '1 per week', perMonth: 4 },
  { value: 'Bi-weekly', label: 'Bi-weekly', perMonth: 2 },
  { value: '4 per month', label: '4 per month', perMonth: 4 },
  { value: '3 per month', label: '3 per month', perMonth: 3 },
  { value: '2 per month', label: '2 per month', perMonth: 2 },
  { value: '1 per month', label: '1 per month', perMonth: 1 },
  { value: '1 per quarter', label: '1 per quarter', perMonth: 0.33 },
  { value: 'As needed', label: 'As needed', perMonth: 0 },
  { value: 'On demand', label: 'On demand', perMonth: 0 }
];

// Meeting modes
const MEETING_MODES = ['Online', 'Offline', 'Mixed'];

// Helper function to calculate committed meetings
const calculateCommittedMeetings = (frequency, durationMonths) => {
  const freqOption = FREQUENCY_OPTIONS.find(f => f.value === frequency);
  if (!freqOption || freqOption.perMonth === 0) return 0;
  return Math.round(freqOption.perMonth * durationMonths);
};

const PricingPlanBuilder = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');
  
  const [lead, setLead] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Team deployment (replaces old consultants array)
  const [teamDeployment, setTeamDeployment] = useState([]);
  
  // New team member form
  const [newMember, setNewMember] = useState({
    role: '',
    meeting_type: '',
    frequency: '',
    mode: 'Online',
    rate_per_meeting: 12500,
    count: 1
  });
  
  const [formData, setFormData] = useState({
    project_duration_type: 'yearly',
    project_duration_months: 12,
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

  // Handle duration type change - auto-fill months
  const handleDurationTypeChange = (type) => {
    const months = DURATION_TYPE_MONTHS[type];
    if (months !== null) {
      // Auto-fill months and recalculate all team members
      const updatedTeam = teamDeployment.map(member => ({
        ...member,
        committed_meetings: calculateCommittedMeetings(member.frequency, months)
      }));
      setTeamDeployment(updatedTeam);
      setFormData(prev => ({
        ...prev,
        project_duration_type: type,
        project_duration_months: months
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        project_duration_type: type
      }));
    }
  };

  // Handle duration months change - recalculate all team members
  const handleDurationMonthsChange = (months) => {
    const updatedTeam = teamDeployment.map(member => ({
      ...member,
      committed_meetings: calculateCommittedMeetings(member.frequency, months)
    }));
    setTeamDeployment(updatedTeam);
    setFormData(prev => ({
      ...prev,
      project_duration_months: months,
      // If months doesn't match a preset, set to custom
      project_duration_type: Object.entries(DURATION_TYPE_MONTHS).find(([_, v]) => v === months)?.[0] || 'custom'
    }));
  };

  // Add team member
  const addTeamMember = () => {
    if (!newMember.role || !newMember.meeting_type || !newMember.frequency) {
      toast.error('Please fill Role, Meeting Type, and Frequency');
      return;
    }
    
    const committedMeetings = calculateCommittedMeetings(newMember.frequency, formData.project_duration_months);
    const memberData = {
      ...newMember,
      committed_meetings: committedMeetings,
      id: Date.now()
    };
    
    setTeamDeployment(prev => [...prev, memberData]);
    setNewMember({
      role: '',
      meeting_type: '',
      frequency: '',
      mode: 'Online',
      rate_per_meeting: 12500,
      count: 1
    });
  };

  // Remove team member
  const removeTeamMember = (index) => {
    setTeamDeployment(prev => prev.filter((_, i) => i !== index));
  };

  // Calculate totals
  const calculateTotals = () => {
    const totalMeetings = teamDeployment.reduce((sum, m) => sum + ((m.committed_meetings || 0) * (m.count || 1)), 0);
    const subtotal = teamDeployment.reduce((sum, m) => sum + ((m.committed_meetings || 0) * (m.count || 1) * (m.rate_per_meeting || 12500)), 0);
    const discount = subtotal * (formData.discount_percentage / 100);
    const afterDiscount = subtotal - discount;
    const gst = afterDiscount * 0.18;
    const total = afterDiscount + gst;
    
    return { totalMeetings, subtotal, discount, gst, total };
  };

  const totals = calculateTotals();

  // Convert team deployment to consultants format for backend compatibility
  const convertToConsultantsFormat = () => {
    return teamDeployment.map(member => ({
      consultant_type: member.role.toLowerCase().replace(/\s+/g, '_'),
      role: member.role,
      meeting_type: member.meeting_type,
      frequency: member.frequency,
      mode: member.mode,
      count: member.count || 1,
      meetings: member.committed_meetings || 0,
      rate_per_meeting: member.rate_per_meeting || 12500,
      committed_meetings: member.committed_meetings || 0
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (teamDeployment.length === 0) {
      toast.error('Please add at least one team member');
      return;
    }
    
    setLoading(true);

    try {
      const pricingPlan = {
        lead_id: leadId,
        ...formData,
        consultants: convertToConsultantsFormat(),
        team_deployment: teamDeployment,
        sow_items: []
      };

      const response = await axios.post(`${API}/pricing-plans`, pricingPlan);
      toast.success('Pricing plan created successfully');
      navigate(`/sales-funnel/sow/${response.data.id}?lead_id=${leadId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create pricing plan');
    } finally {
      setLoading(false);
    }
  };

  // Preview calculation for new member
  const previewMeetings = newMember.frequency ? calculateCommittedMeetings(newMember.frequency, formData.project_duration_months) : 0;
  const previewCost = previewMeetings * (newMember.count || 1) * (newMember.rate_per_meeting || 12500);

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
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Duration Type</Label>
                <select
                  value={formData.project_duration_type}
                  onChange={(e) => handleDurationTypeChange(e.target.value)}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                  data-testid="duration-type-select"
                >
                  <option value="monthly">Monthly (1 month)</option>
                  <option value="quarterly">Quarterly (3 months)</option>
                  <option value="half_yearly">Half Yearly (6 months)</option>
                  <option value="yearly">Yearly (12 months)</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Duration (Months)</Label>
                <Input
                  type="number"
                  min="1"
                  max="60"
                  value={formData.project_duration_months}
                  onChange={(e) => handleDurationMonthsChange(parseInt(e.target.value) || 1)}
                  className="rounded-sm border-zinc-200"
                  data-testid="duration-months-input"
                  disabled={formData.project_duration_type !== 'custom'}
                />
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
            </div>
            
            {/* Duration info box */}
            <div className="p-3 bg-blue-50 rounded-sm text-sm text-blue-700">
              <Calculator className="w-4 h-4 inline mr-2" />
              Project Duration: <span className="font-semibold">{formData.project_duration_months} months</span>
              {formData.project_duration_type !== 'custom' && (
                <span className="text-blue-500"> (auto-set from {formData.project_duration_type.replace('_', ' ')})</span>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Team Deployment */}
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader className="flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-zinc-700" />
              <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
                Team Deployment Structure
              </CardTitle>
            </div>
            {teamDeployment.length > 0 && (
              <div className="text-sm text-zinc-600">
                Total: <span className="font-semibold text-emerald-600">{totals.totalMeetings}</span> meetings | 
                <span className="font-semibold text-emerald-600"> {formatINR(totals.subtotal)}</span>
              </div>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Add Team Member Form */}
            <div className="p-4 bg-zinc-50 rounded-sm space-y-4">
              <div className="text-xs font-medium text-zinc-500 uppercase">Add Team Member</div>
              <div className="grid grid-cols-7 gap-2 items-end">
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-500">Role *</Label>
                  <select
                    value={newMember.role}
                    onChange={(e) => setNewMember({ ...newMember, role: e.target.value })}
                    className="w-full h-9 px-2 rounded-sm border border-zinc-200 bg-white text-sm"
                    data-testid="team-role-select"
                  >
                    <option value="">Select</option>
                    {CONSULTANT_ROLES.map(role => (
                      <option key={role} value={role}>{role}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-500">Meeting Type *</Label>
                  <select
                    value={newMember.meeting_type}
                    onChange={(e) => setNewMember({ ...newMember, meeting_type: e.target.value })}
                    className="w-full h-9 px-2 rounded-sm border border-zinc-200 bg-white text-sm"
                    data-testid="team-meeting-type-select"
                  >
                    <option value="">Select</option>
                    {MEETING_TYPES.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-500">Frequency *</Label>
                  <select
                    value={newMember.frequency}
                    onChange={(e) => setNewMember({ ...newMember, frequency: e.target.value })}
                    className="w-full h-9 px-2 rounded-sm border border-zinc-200 bg-white text-sm"
                    data-testid="team-frequency-select"
                  >
                    <option value="">Select</option>
                    {FREQUENCY_OPTIONS.map(freq => (
                      <option key={freq.value} value={freq.value}>{freq.label}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-500">Rate/Meeting (₹)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={newMember.rate_per_meeting}
                    onChange={(e) => setNewMember({ ...newMember, rate_per_meeting: parseFloat(e.target.value) || 0 })}
                    className="h-9 text-sm rounded-sm border-zinc-200"
                    data-testid="team-rate-input"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-500">Count</Label>
                  <Input
                    type="number"
                    min="1"
                    value={newMember.count}
                    onChange={(e) => setNewMember({ ...newMember, count: parseInt(e.target.value) || 1 })}
                    className="h-9 text-sm rounded-sm border-zinc-200"
                    data-testid="team-count-input"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-500">Mode</Label>
                  <select
                    value={newMember.mode}
                    onChange={(e) => setNewMember({ ...newMember, mode: e.target.value })}
                    className="w-full h-9 px-2 rounded-sm border border-zinc-200 bg-white text-sm"
                    data-testid="team-mode-select"
                  >
                    {MEETING_MODES.map(mode => (
                      <option key={mode} value={mode}>{mode}</option>
                    ))}
                  </select>
                </div>
                <Button 
                  type="button" 
                  onClick={addTeamMember} 
                  size="sm" 
                  className="h-9"
                  data-testid="add-team-member-btn"
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              
              {/* Preview */}
              {newMember.frequency && (
                <div className="text-xs text-blue-600 bg-blue-50 px-3 py-2 rounded-sm">
                  <Calculator className="w-3 h-3 inline mr-1" />
                  Preview: <span className="font-semibold">{previewMeetings}</span> meetings × {newMember.count || 1} resource(s) = <span className="font-semibold">{previewMeetings * (newMember.count || 1)}</span> total meetings @ {formatINR(newMember.rate_per_meeting)}/meeting = <span className="font-semibold">{formatINR(previewCost)}</span>
                </div>
              )}
            </div>

            {/* Team Members Table */}
            {teamDeployment.length > 0 && (
              <div className="space-y-2">
                <div className="grid grid-cols-8 gap-2 text-xs font-medium text-zinc-500 px-3 py-2 bg-zinc-100 rounded-t-sm">
                  <div>Role</div>
                  <div>Meeting Type</div>
                  <div>Frequency</div>
                  <div>Rate (₹)</div>
                  <div>Count</div>
                  <div>Committed</div>
                  <div>Subtotal</div>
                  <div></div>
                </div>
                {teamDeployment.map((member, index) => {
                  const memberMeetings = (member.committed_meetings || 0) * (member.count || 1);
                  const memberCost = memberMeetings * (member.rate_per_meeting || 12500);
                  return (
                    <div 
                      key={member.id || index} 
                      className="grid grid-cols-8 gap-2 items-center px-3 py-2 bg-white border border-zinc-100 rounded-sm text-sm"
                      data-testid={`team-member-${index}`}
                    >
                      <div className="font-medium truncate" title={member.role}>{member.role}</div>
                      <div className="truncate" title={member.meeting_type}>{member.meeting_type}</div>
                      <div className="truncate">{member.frequency}</div>
                      <div>{formatINR(member.rate_per_meeting || 12500)}</div>
                      <div>{member.count || 1}</div>
                      <div className="font-semibold text-blue-600">{memberMeetings}</div>
                      <div className="font-semibold text-emerald-600">{formatINR(memberCost)}</div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeTeamMember(index)}
                        className="h-7 w-7 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                        data-testid={`remove-team-member-${index}`}
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  );
                })}
                
                {/* Totals Row */}
                <div className="grid grid-cols-8 gap-2 items-center px-3 py-2 bg-zinc-100 border border-zinc-200 rounded-b-sm text-sm font-semibold">
                  <div className="col-span-5 text-right">Total:</div>
                  <div className="text-blue-700">{totals.totalMeetings}</div>
                  <div className="text-emerald-700">{formatINR(totals.subtotal)}</div>
                  <div></div>
                </div>
              </div>
            )}
            
            {teamDeployment.length === 0 && (
              <p className="text-sm text-zinc-400 text-center py-8">
                No team members added. Add your team deployment structure above.
              </p>
            )}
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
                className="rounded-sm border-zinc-200 bg-white"
                data-testid="discount-input"
              />
            </div>
            <div className="space-y-2 pt-4 border-t border-zinc-200">
              <div className="flex justify-between text-sm">
                <span className="text-zinc-600">Total Meetings:</span>
                <span className="font-semibold text-zinc-950" data-testid="total-meetings">{totals.totalMeetings}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-zinc-600">Subtotal:</span>
                <span className="font-semibold text-zinc-950" data-testid="subtotal">{formatINR(totals.subtotal)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-zinc-600">Discount ({formData.discount_percentage}%):</span>
                <span className="font-semibold text-red-600" data-testid="discount">- {formatINR(totals.discount)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-zinc-600">GST (18%):</span>
                <span className="font-semibold text-zinc-950" data-testid="gst">+ {formatINR(totals.gst)}</span>
              </div>
              <div className="flex justify-between text-lg font-bold pt-2 border-t border-zinc-300">
                <span className="text-zinc-950">Grand Total:</span>
                <span className="text-emerald-600" data-testid="grand-total">{formatINR(totals.total)}</span>
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
                placeholder="Describe the growth consulting plan..."
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-zinc-950">Growth Guarantee</Label>
              <textarea
                value={formData.growth_guarantee}
                onChange={(e) => setFormData({ ...formData, growth_guarantee: e.target.value })}
                rows={3}
                placeholder="Specific growth metrics and guarantees..."
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
            disabled={loading || teamDeployment.length === 0}
            className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            data-testid="create-pricing-plan-btn"
          >
            {loading ? 'Creating...' : 'Create Pricing Plan & Continue to SOW'}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default PricingPlanBuilder;
