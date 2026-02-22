import React, { useState, useEffect, useContext, useMemo, useCallback } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../../App';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Checkbox } from '../../components/ui/checkbox';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../../components/ui/tooltip';
import { Textarea } from '../../components/ui/textarea';
import { Plus, Trash2, ArrowLeft, Users, Calculator, IndianRupee, AlertCircle, Info, Lock, Calendar, Receipt, Bell, HelpCircle, FileText, Settings, Eye, EyeOff, FolderOpen, Save } from 'lucide-react';
import { toast } from 'sonner';
import { formatINR } from '../../utils/currency';
import useDraft from '../../hooks/useDraft';
import DraftSelector, { DraftIndicator } from '../../components/DraftSelector';
import { DualApprovalPanel } from '../../components/sales-funnel/BusinessLogicUI';

// Duration type to months mapping
const DURATION_TYPE_MONTHS = {
  'monthly': 1,
  'quarterly': 3,
  'half_yearly': 6,
  'yearly': 12,
  'custom': null
};

// Meeting modes
const MEETING_MODES = ['Online', 'Offline', 'Mixed'];

// Payment components with default values
// GST and TDS are percentage-based, Conveyance is lumpsum
const PAYMENT_COMPONENTS = [
  { id: 'gst', name: 'GST', defaultPercent: 18, type: 'add', editable: false, isPercentage: true },
  { id: 'tds', name: 'TDS', defaultPercent: 10, type: 'subtract', editable: true, isPercentage: true },
  { id: 'conveyance', name: 'Conveyance', defaultValue: 0, type: 'add', editable: true, isPercentage: false, isLumpsum: true }
];

const PricingPlanBuilder = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('leadId');
  
  const [lead, setLead] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mastersLoading, setMastersLoading] = useState(true);
  const [showDraftSelector, setShowDraftSelector] = useState(false);
  const [meetingAccessBlocked, setMeetingAccessBlocked] = useState(false);
  const [meetingAccessReason, setMeetingAccessReason] = useState('');
  
  // Draft system
  const generatePricingDraftTitle = useCallback((data) => {
    if (lead?.company) return `Pricing - ${lead.company}`;
    if (data.totalInvestment) return `Pricing Plan - ₹${data.totalInvestment.toLocaleString()}`;
    return 'New Pricing Plan';
  }, [lead]);

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
    clearDraft
  } = useDraft('pricing_plan', generatePricingDraftTitle);
  
  // Masters data from Admin
  const [tenureTypes, setTenureTypes] = useState([]);
  const [consultantRoles, setConsultantRoles] = useState([]);
  const [meetingTypes, setMeetingTypes] = useState([]);
  
  // TOP-DOWN: Total Investment is the primary input
  const [totalInvestment, setTotalInvestment] = useState(0);
  
  // Team deployment
  const [teamDeployment, setTeamDeployment] = useState([]);
  
  // New team member form
  const [newMember, setNewMember] = useState({
    role: '',
    tenure_type_code: '',
    meeting_type: '',
    mode: 'Online',
    count: 1
  });
  
  const [formData, setFormData] = useState({
    project_duration_type: 'yearly',
    project_duration_months: 12,
    payment_schedule: 'monthly',
    discount_percentage: 0
  });

  // Payment Plan Breakup State
  // Note: conveyance is now a lumpsum amount (not percentage)
  const [paymentPlan, setPaymentPlan] = useState({
    start_date: '',
    selected_components: ['gst'], // GST selected by default
    component_values: {
      gst: 18,
      tds: 10
    },
    conveyance_lumpsum: 0,  // Lumpsum amount distributed across all tenures
    custom_payments: []  // For custom payment schedule [{id, date, amount, description}]
  });

  // Section notes for agreement
  const [sectionNotes, setSectionNotes] = useState({
    pricing: '',
    team_deployment: '',
    payment_plan: '',
    general: ''
  });

  // Agreement sections to include (checkboxes)
  const [agreementSections, setAgreementSections] = useState({
    pricing_summary: true,
    team_deployment: true,
    payment_schedule: true,
    gst_details: true,
    tds_details: true,
    conveyance_details: true,
    discount_details: true,
    notes: true
  });

  useEffect(() => {
    fetchMasters();
    if (leadId) {
      fetchLead();
    }
    // Set default start date to today
    setPaymentPlan(prev => ({
      ...prev,
      start_date: new Date().toISOString().split('T')[0]
    }));
    // Show draft selector if drafts exist
    if (drafts.length > 0 && !draftId) {
      setShowDraftSelector(true);
    }
  }, [leadId, drafts.length, draftId]);

  // Auto-save draft when key fields change
  useEffect(() => {
    if (totalInvestment > 0 || teamDeployment.length > 0) {
      autoSave({
        totalInvestment,
        teamDeployment,
        formData,
        paymentPlan,
        leadId
      });
    }
  }, [totalInvestment, teamDeployment, formData, paymentPlan]);

  // Load draft
  const handleLoadDraft = async (draft) => {
    const loadedDraft = await loadDraft(draft.id);
    if (loadedDraft?.data) {
      if (loadedDraft.data.totalInvestment) setTotalInvestment(loadedDraft.data.totalInvestment);
      if (loadedDraft.data.teamDeployment) setTeamDeployment(loadedDraft.data.teamDeployment);
      if (loadedDraft.data.formData) setFormData(loadedDraft.data.formData);
      if (loadedDraft.data.paymentPlan) setPaymentPlan(loadedDraft.data.paymentPlan);
      setShowDraftSelector(false);
      toast.success('Draft loaded');
    }
  };

  // Start new pricing plan
  const handleNewPlan = () => {
    clearDraft();
    setTotalInvestment(0);
    setTeamDeployment([]);
    setFormData({
      project_duration_type: 'yearly',
      project_duration_months: 12,
      payment_schedule: 'monthly',
      discount_percentage: 0
    });
    setShowDraftSelector(false);
  };

  // Recalculate allocations when total investment or team changes
  useEffect(() => {
    if (totalInvestment > 0 && teamDeployment.length > 0) {
      recalculateAllocations();
    }
  }, [totalInvestment, formData.project_duration_months]);

  const fetchMasters = async () => {
    try {
      setMastersLoading(true);
      const [tenureRes, rolesRes, meetingsRes] = await Promise.all([
        axios.get(`${API}/masters/tenure-types`),
        axios.get(`${API}/masters/consultant-roles`),
        axios.get(`${API}/masters/meeting-types`)
      ]);
      setTenureTypes(tenureRes.data);
      setConsultantRoles(rolesRes.data);
      setMeetingTypes(meetingsRes.data);
    } catch (error) {
      toast.error('Failed to fetch master data. Please ensure masters are seeded.');
    } finally {
      setMastersLoading(false);
    }
  };

  const fetchLead = async () => {
    try {
      const response = await axios.get(`${API}/leads/${leadId}`);
      setLead(response.data);
    } catch (error) {
      toast.error('Failed to fetch lead');
    }
  };

  // Check if user can access pricing plan (requires meeting record)
  const checkMeetingAccess = async () => {
    if (!leadId) return;
    try {
      const response = await axios.get(`${API}/leads/${leadId}/can-access-pricing`);
      if (!response.data.can_access) {
        setMeetingAccessBlocked(true);
        setMeetingAccessReason(response.data.reason);
      } else {
        setMeetingAccessBlocked(false);
        setMeetingAccessReason('');
      }
    } catch (error) {
      console.error('Error checking meeting access:', error);
    }
  };

  // Check meeting access on mount
  useEffect(() => {
    if (leadId) {
      checkMeetingAccess();
    }
  }, [leadId]);

  // Handle duration type change
  const handleDurationTypeChange = (type) => {
    const months = DURATION_TYPE_MONTHS[type];
    if (months !== null) {
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

  // Recalculate all team member allocations based on total investment
  const recalculateAllocations = (currentTeam = null) => {
    const team = currentTeam || teamDeployment;
    if (team.length === 0 || totalInvestment <= 0) return;
    
    // Calculate total allocation percentage
    const totalAllocationPercent = team.reduce((sum, m) => {
      const tenure = tenureTypes.find(t => t.code === m.tenure_type_code);
      return sum + (tenure?.allocation_percentage || 0);
    }, 0);
    
    if (totalAllocationPercent === 0) return;
    
    // Recalculate each member
    const updatedTeam = team.map(member => {
      const tenure = tenureTypes.find(t => t.code === member.tenure_type_code);
      if (!tenure) return member;
      
      // Normalize allocation percentage
      const normalizedPercent = (tenure.allocation_percentage / totalAllocationPercent) * 100;
      
      // Calculate breakup amount
      const breakupAmount = totalInvestment * (normalizedPercent / 100);
      
      // Calculate total meetings
      const meetingsPerMonth = tenure.meetings_per_month || 1;
      const totalMeetings = Math.round(meetingsPerMonth * formData.project_duration_months * (member.count || 1));
      
      // Calculate rate per meeting
      const ratePerMeeting = totalMeetings > 0 ? Math.round(breakupAmount / totalMeetings) : 0;
      
      return {
        ...member,
        allocation_percentage: normalizedPercent,
        breakup_amount: breakupAmount,
        meetings_per_month: meetingsPerMonth,
        committed_meetings: totalMeetings,
        rate_per_meeting: ratePerMeeting
      };
    });
    
    setTeamDeployment(updatedTeam);
  };

  // Add team member
  const addTeamMember = () => {
    if (!newMember.role || !newMember.tenure_type_code || !newMember.meeting_type) {
      toast.error('Please fill Role, Tenure Type, and Meeting Type');
      return;
    }
    
    const tenure = tenureTypes.find(t => t.code === newMember.tenure_type_code);
    const role = consultantRoles.find(r => r.name === newMember.role);
    
    if (!tenure) {
      toast.error('Invalid tenure type selected');
      return;
    }
    
    // Calculate total allocation after adding this member
    const currentTotalAllocation = teamDeployment.reduce((sum, m) => {
      const t = tenureTypes.find(tt => tt.code === m.tenure_type_code);
      return sum + (t?.allocation_percentage || 0);
    }, 0);
    const newTotalAllocation = currentTotalAllocation + tenure.allocation_percentage;
    
    // Calculate allocation for new member based on total investment
    const normalizedPercent = totalInvestment > 0 
      ? (tenure.allocation_percentage / newTotalAllocation) * 100
      : tenure.allocation_percentage;
    
    const breakupAmount = totalInvestment > 0 
      ? totalInvestment * (normalizedPercent / 100)
      : 0;
    
    const meetingsPerMonth = tenure.meetings_per_month || 1;
    const totalMeetings = Math.round(meetingsPerMonth * formData.project_duration_months * (newMember.count || 1));
    const ratePerMeeting = totalMeetings > 0 ? Math.round(breakupAmount / totalMeetings) : 0;
    
    const memberData = {
      ...newMember,
      id: Date.now(),
      allocation_percentage: normalizedPercent,
      breakup_amount: breakupAmount,
      meetings_per_month: meetingsPerMonth,
      committed_meetings: totalMeetings,
      rate_per_meeting: ratePerMeeting,
      default_rate: role?.default_rate || 12500
    };
    
    const updatedTeam = [...teamDeployment, memberData];
    
    // Recalculate all allocations with the new member (pass the updated team directly)
    recalculateAllocations(updatedTeam);
    
    setNewMember({
      role: '',
      tenure_type_code: '',
      meeting_type: '',
      mode: 'Online',
      count: 1
    });
  };

  // Remove team member
  const removeTeamMember = (index) => {
    const updated = teamDeployment.filter((_, i) => i !== index);
    
    // Recalculate allocations after removal (pass the updated team directly)
    if (updated.length > 0 && totalInvestment > 0) {
      recalculateAllocations(updated);
    } else {
      setTeamDeployment(updated);
    }
  };

  // Handle total investment change
  const handleTotalInvestmentChange = (value) => {
    const amount = parseFloat(value) || 0;
    setTotalInvestment(amount);
  };

  // Toggle payment component selection
  const togglePaymentComponent = (componentId) => {
    setPaymentPlan(prev => {
      const isSelected = prev.selected_components.includes(componentId);
      return {
        ...prev,
        selected_components: isSelected
          ? prev.selected_components.filter(id => id !== componentId)
          : [...prev.selected_components, componentId]
      };
    });
  };

  // Update component percentage
  const updateComponentValue = (componentId, value) => {
    setPaymentPlan(prev => ({
      ...prev,
      component_values: {
        ...prev.component_values,
        [componentId]: parseFloat(value) || 0
      }
    }));
  };

  // Calculate totals (before discount, without GST)
  const calculateTotals = () => {
    const totalMeetings = teamDeployment.reduce((sum, m) => sum + (m.committed_meetings || 0), 0);
    const subtotal = totalInvestment;
    const discount = subtotal * (formData.discount_percentage / 100);
    const afterDiscount = subtotal - discount;
    
    // Calculate GST based on selection
    const gstPercent = paymentPlan.selected_components.includes('gst') 
      ? paymentPlan.component_values.gst : 0;
    const gst = afterDiscount * (gstPercent / 100);
    
    const total = afterDiscount + gst;
    
    // Validate allocation percentages
    const allocatedTotal = teamDeployment.reduce((sum, m) => sum + (m.breakup_amount || 0), 0);
    const allocationDiff = Math.abs(allocatedTotal - subtotal);
    const isAllocationValid = allocationDiff < 1;
    
    return { totalMeetings, subtotal, discount, gst, total, allocatedTotal, isAllocationValid, afterDiscount };
  };

  const totals = calculateTotals();

  // Custom payment handlers
  const addCustomPayment = () => {
    const newPayment = {
      id: Date.now(),
      date: paymentPlan.start_date || new Date().toISOString().split('T')[0],
      amount: 0,
      description: ''
    };
    setPaymentPlan(prev => ({
      ...prev,
      custom_payments: [...prev.custom_payments, newPayment]
    }));
  };

  const updateCustomPayment = (id, field, value) => {
    setPaymentPlan(prev => ({
      ...prev,
      custom_payments: prev.custom_payments.map(p => 
        p.id === id ? { ...p, [field]: field === 'amount' ? parseFloat(value) || 0 : value } : p
      )
    }));
  };

  const removeCustomPayment = (id) => {
    setPaymentPlan(prev => ({
      ...prev,
      custom_payments: prev.custom_payments.filter(p => p.id !== id)
    }));
  };

  // Calculate custom payments total
  const customPaymentsTotal = useMemo(() => {
    return paymentPlan.custom_payments.reduce((sum, p) => sum + (p.amount || 0), 0);
  }, [paymentPlan.custom_payments]);

  // Calculate number of payments based on schedule
  const numberOfPayments = useMemo(() => {
    const schedule = formData.payment_schedule;
    if (schedule === 'custom') {
      return paymentPlan.custom_payments.length;
    }
    const durationMonths = formData.project_duration_months;
    const frequencyMap = {
      'monthly': 1,
      'quarterly': 3,
      'milestone': durationMonths,
      'upfront': durationMonths
    };
    const frequencyMonths = frequencyMap[schedule] || 1;
    return Math.ceil(durationMonths / frequencyMonths);
  }, [formData.payment_schedule, formData.project_duration_months, paymentPlan.custom_payments.length]);

  // Generate payment schedule breakdown
  const paymentScheduleBreakdown = useMemo(() => {
    if (!paymentPlan.start_date || totalInvestment <= 0) return [];
    
    const schedule = formData.payment_schedule;
    const afterDiscount = totals.afterDiscount;
    
    // Handle custom payment schedule
    if (schedule === 'custom') {
      return paymentPlan.custom_payments.map(payment => {
        const basicAmount = payment.amount;
        let gst = 0, tds = 0, conveyance = 0;
        
        if (paymentPlan.selected_components.includes('gst')) {
          gst = Math.round(basicAmount * (paymentPlan.component_values.gst / 100));
        }
        if (paymentPlan.selected_components.includes('tds')) {
          tds = Math.round(basicAmount * (paymentPlan.component_values.tds / 100));
        }
        if (paymentPlan.selected_components.includes('conveyance') && paymentPlan.custom_payments.length > 0) {
          conveyance = Math.round(paymentPlan.conveyance_lumpsum / paymentPlan.custom_payments.length);
        }
        
        return {
          frequency: payment.description || `Payment ${paymentPlan.custom_payments.indexOf(payment) + 1}`,
          due_date: new Date(payment.date),
          basic: basicAmount,
          gst,
          tds,
          conveyance,
          net: basicAmount + gst + conveyance - tds,
          is_custom: true
        };
      });
    }
    
    // Standard payment schedule logic
    const startDate = new Date(paymentPlan.start_date);
    const durationMonths = formData.project_duration_months;
    
    // Determine payment frequency in months
    const frequencyMap = {
      'monthly': 1,
      'quarterly': 3,
      'milestone': durationMonths, // Single payment
      'upfront': durationMonths // Single payment upfront
    };
    
    const frequencyMonths = frequencyMap[schedule] || 1;
    const numberOfPayments = Math.ceil(durationMonths / frequencyMonths);
    const basicPerPayment = Math.round(afterDiscount / numberOfPayments);
    
    // Calculate conveyance per payment (lumpsum distributed evenly)
    const conveyanceLumpsum = paymentPlan.conveyance_lumpsum || 0;
    const conveyancePerPayment = numberOfPayments > 0 ? Math.round(conveyanceLumpsum / numberOfPayments) : 0;
    
    const breakdown = [];
    let currentDate = new Date(startDate);
    
    for (let i = 0; i < numberOfPayments; i++) {
      const payment = {
        frequency: schedule === 'monthly' ? `Month ${i + 1}` 
          : schedule === 'quarterly' ? `Q${i + 1}`
          : schedule === 'upfront' ? 'Upfront'
          : `Milestone ${i + 1}`,
        due_date: new Date(currentDate),
        basic: basicPerPayment,
        gst: 0,
        tds: 0,
        conveyance: 0,
        net: basicPerPayment
      };
      
      // Calculate selected components
      if (paymentPlan.selected_components.includes('gst')) {
        payment.gst = Math.round(basicPerPayment * (paymentPlan.component_values.gst / 100));
      }
      if (paymentPlan.selected_components.includes('tds')) {
        payment.tds = Math.round(basicPerPayment * (paymentPlan.component_values.tds / 100));
      }
      // Conveyance is now lumpsum distributed evenly
      if (paymentPlan.selected_components.includes('conveyance')) {
        payment.conveyance = conveyancePerPayment;
      }
      
      // Net = Basic + GST + Conveyance - TDS
      payment.net = payment.basic + payment.gst + payment.conveyance - payment.tds;
      
      breakdown.push(payment);
      
      // Move to next payment date
      currentDate.setMonth(currentDate.getMonth() + frequencyMonths);
    }
    
    return breakdown;
  }, [paymentPlan, totalInvestment, formData.payment_schedule, formData.project_duration_months, formData.discount_percentage, totals.afterDiscount]);

  // Format date for display
  const formatDate = (date) => {
    return new Date(date).toLocaleDateString('en-IN', { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric' 
    });
  };

  // Convert team deployment for backend
  const convertToBackendFormat = () => {
    return teamDeployment.map(member => ({
      consultant_type: member.role.toLowerCase().replace(/\s+/g, '_'),
      role: member.role,
      meeting_type: member.meeting_type,
      tenure_type_code: member.tenure_type_code,
      frequency: `${member.meetings_per_month || 1} per month`,
      mode: member.mode,
      count: member.count || 1,
      meetings: member.committed_meetings || 0,
      rate_per_meeting: member.rate_per_meeting || 0,
      committed_meetings: member.committed_meetings || 0,
      allocation_percentage: member.allocation_percentage || 0,
      breakup_amount: member.breakup_amount || 0
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (teamDeployment.length === 0) {
      toast.error('Please add at least one team member');
      return;
    }
    
    if (totalInvestment <= 0) {
      toast.error('Please enter Total Client Investment');
      return;
    }

    if (!paymentPlan.start_date) {
      toast.error('Please select a project start date');
      return;
    }
    
    setLoading(true);

    try {
      const pricingPlan = {
        lead_id: leadId,
        ...formData,
        total_investment: totalInvestment,
        consultants: convertToBackendFormat(),
        team_deployment: teamDeployment,
        sow_items: [],
        payment_plan: {
          start_date: paymentPlan.start_date,
          selected_components: paymentPlan.selected_components,
          component_values: paymentPlan.component_values,
          conveyance_lumpsum: paymentPlan.conveyance_lumpsum || 0,
          custom_payments: formData.payment_schedule === 'custom' ? paymentPlan.custom_payments : [],
          schedule_breakdown: paymentScheduleBreakdown.map(p => ({
            ...p,
            due_date: p.due_date.toISOString()
          }))
        },
        section_notes: sectionNotes,
        agreement_sections: agreementSections
      };

      const response = await axios.post(`${API}/pricing-plans`, pricingPlan);
      toast.success('Pricing plan created successfully');
      // Navigate to new scope selection flow
      navigate(`/sales-funnel/scope-selection/${response.data.id}?lead_id=${leadId}`);
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        toast.error(detail.map(e => e.msg || 'Validation error').join(', '));
      } else if (typeof detail === 'string') {
        toast.error(detail);
      } else {
        toast.error('Failed to create pricing plan');
      }
    } finally {
      setLoading(false);
    }
  };

  // Get tenure type name
  const getTenureTypeName = (code) => {
    const tenure = tenureTypes.find(t => t.code === code);
    return tenure?.name || code;
  };

  // Preview calculation for new member
  const getNewMemberPreview = () => {
    if (!newMember.tenure_type_code || totalInvestment <= 0) return null;
    
    const tenure = tenureTypes.find(t => t.code === newMember.tenure_type_code);
    if (!tenure) return null;
    
    const currentTotalAllocation = teamDeployment.reduce((sum, m) => {
      const t = tenureTypes.find(tt => tt.code === m.tenure_type_code);
      return sum + (t?.allocation_percentage || 0);
    }, 0);
    const newTotalAllocation = currentTotalAllocation + tenure.allocation_percentage;
    const normalizedPercent = (tenure.allocation_percentage / newTotalAllocation) * 100;
    const breakupAmount = totalInvestment * (normalizedPercent / 100);
    const meetingsPerMonth = tenure.meetings_per_month || 1;
    const totalMeetings = Math.round(meetingsPerMonth * formData.project_duration_months * (newMember.count || 1));
    const ratePerMeeting = totalMeetings > 0 ? Math.round(breakupAmount / totalMeetings) : 0;
    
    return { breakupAmount, totalMeetings, ratePerMeeting, normalizedPercent };
  };

  const preview = getNewMemberPreview();

  if (mastersLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-zinc-500">Loading master data...</div>
      </div>
    );
  }

  // Block access if no meeting recorded
  if (meetingAccessBlocked) {
    return (
      <div className="max-w-2xl mx-auto py-16">
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="pt-6 text-center">
            <AlertCircle className="w-16 h-16 text-amber-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-zinc-800 mb-2">Meeting Required</h2>
            <p className="text-zinc-600 mb-6">{meetingAccessReason}</p>
            <p className="text-sm text-zinc-500 mb-6">
              Please record at least one meeting with this lead before creating a pricing plan.
            </p>
            <div className="flex justify-center gap-4">
              <Button
                variant="outline"
                onClick={() => navigate('/leads')}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Leads
              </Button>
              <Button
                onClick={() => leadId && navigate(`/sales-funnel/meeting/record?leadId=${leadId}`)}
                className="bg-amber-500 hover:bg-amber-600"
              >
                <Calendar className="w-4 h-4 mr-2" />
                Record Meeting
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto" data-testid="pricing-plan-builder">
      {/* Draft Selector */}
      <DraftSelector
        drafts={drafts}
        loading={loadingDrafts}
        onSelect={handleLoadDraft}
        onDelete={deleteDraft}
        onNewDraft={handleNewPlan}
        isOpen={showDraftSelector}
        onClose={() => setShowDraftSelector(false)}
        title="Pricing Plan Drafts"
        description="Continue editing a pricing plan or start a new one"
      />

      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <Button
            onClick={() => navigate('/leads')}
            variant="ghost"
            className="hover:bg-zinc-100 rounded-sm"
          >
            <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Back to Leads
          </Button>
          <div className="flex items-center gap-3">
            <DraftIndicator saving={savingDraft} lastSaved={lastSaved} onSave={() => saveDraft({ totalInvestment, teamDeployment, formData, paymentPlan, leadId })} />
            {drafts.length > 0 && (
              <Button variant="outline" onClick={() => setShowDraftSelector(true)} className="gap-2">
                <FolderOpen className="w-4 h-4" /> Drafts ({drafts.length})
              </Button>
            )}
          </div>
        </div>
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
        {/* TOTAL INVESTMENT - PRIMARY INPUT */}
        <Card className="border-2 border-emerald-200 shadow-none rounded-sm bg-emerald-50">
          <CardHeader>
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-emerald-800 flex items-center gap-2">
              <IndianRupee className="w-5 h-5" />
              Total Client Investment (Top-Down Pricing)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <Label className="text-sm font-medium text-emerald-800 mb-2 block">
                  Enter Total Project Investment *
                </Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-emerald-600 font-medium">₹</span>
                  <Input
                    type="number"
                    min="0"
                    step="1000"
                    value={totalInvestment || ''}
                    onChange={(e) => handleTotalInvestmentChange(e.target.value)}
                    placeholder="Enter total investment amount"
                    className="pl-8 h-12 text-xl font-semibold border-emerald-300 bg-white"
                    data-testid="total-investment-input"
                  />
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs text-emerald-600 mb-1">Total Investment</p>
                <p className="text-2xl font-bold text-emerald-700" data-testid="total-investment-display">
                  {formatINR(totalInvestment)}
                </p>
              </div>
            </div>
            <p className="text-xs text-emerald-600 mt-3 flex items-center gap-1">
              <Info className="w-3 h-3" />
              The system will auto-allocate this amount to team members based on tenure type allocation percentages.
            </p>
          </CardContent>
        </Card>

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
                  onChange={(e) => setFormData({ ...formData, project_duration_months: parseInt(e.target.value) || 1 })}
                  className="rounded-sm border-zinc-200"
                  data-testid="duration-months-input"
                  disabled={formData.project_duration_type !== 'custom'}
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Payment Schedule</Label>
                <select
                  value={formData.payment_schedule}
                  onChange={(e) => {
                    setFormData({ ...formData, payment_schedule: e.target.value });
                    // Initialize with one custom payment when switching to custom
                    if (e.target.value === 'custom' && paymentPlan.custom_payments.length === 0) {
                      setPaymentPlan(prev => ({
                        ...prev,
                        custom_payments: [{
                          id: Date.now(),
                          date: prev.start_date || new Date().toISOString().split('T')[0],
                          amount: totals.afterDiscount,
                          description: 'Payment 1'
                        }]
                      }));
                    }
                  }}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
                  data-testid="payment-schedule-select"
                >
                  <option value="monthly">Monthly</option>
                  <option value="quarterly">Quarterly</option>
                  <option value="milestone">Milestone Based</option>
                  <option value="upfront">Upfront</option>
                  <option value="custom">Custom (Irregular)</option>
                </select>
              </div>
            </div>
            
            <div className="p-3 bg-blue-50 rounded-sm text-sm text-blue-700">
              <Calculator className="w-4 h-4 inline mr-2" />
              Project Duration: <span className="font-semibold">{formData.project_duration_months} months</span>
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
                Total: <span className="font-semibold text-emerald-600">{totals.totalMeetings}</span> meetings
              </div>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Add Team Member Form */}
            <div className="p-4 bg-zinc-50 rounded-sm space-y-4">
              <div className="text-xs font-medium text-zinc-500 uppercase">Add Team Member</div>
              <div className="grid grid-cols-6 gap-3 items-end">
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-500">Role *</Label>
                  <select
                    value={newMember.role}
                    onChange={(e) => setNewMember({ ...newMember, role: e.target.value })}
                    className="w-full h-9 px-2 rounded-sm border border-zinc-200 bg-white text-sm"
                    data-testid="team-role-select"
                  >
                    <option value="">Select Role</option>
                    {consultantRoles.map(role => (
                      <option key={role.code} value={role.name}>{role.name}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-500">Tenure Type *</Label>
                  <select
                    value={newMember.tenure_type_code}
                    onChange={(e) => setNewMember({ ...newMember, tenure_type_code: e.target.value })}
                    className="w-full h-9 px-2 rounded-sm border border-zinc-200 bg-white text-sm"
                    data-testid="team-tenure-select"
                  >
                    <option value="">Select Tenure</option>
                    {tenureTypes.map(tt => (
                      <option key={tt.code} value={tt.code}>
                        {tt.name} ({tt.allocation_percentage}%)
                      </option>
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
                    <option value="">Select Type</option>
                    {meetingTypes.map(mt => (
                      <option key={mt.code} value={mt.name}>{mt.name}</option>
                    ))}
                  </select>
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
                <Button 
                  type="button" 
                  onClick={addTeamMember} 
                  size="sm" 
                  className="h-9"
                  disabled={totalInvestment <= 0}
                  data-testid="add-team-member-btn"
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              
              {/* Preview */}
              {preview && totalInvestment > 0 && (
                <div className="text-xs text-blue-600 bg-blue-50 px-3 py-2 rounded-sm">
                  <Calculator className="w-3 h-3 inline mr-1" />
                  Preview: Allocation <span className="font-semibold">{preview.normalizedPercent.toFixed(1)}%</span> = 
                  <span className="font-semibold"> {formatINR(preview.breakupAmount)}</span> | 
                  <span className="font-semibold"> {preview.totalMeetings}</span> meetings | 
                  Rate: <span className="font-semibold">{formatINR(preview.ratePerMeeting)}</span>/meeting
                </div>
              )}
              
              {totalInvestment <= 0 && (
                <div className="text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-sm flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  Enter Total Client Investment above to enable team member addition
                </div>
              )}
            </div>

            {/* Team Members Table */}
            {teamDeployment.length > 0 && (
              <div className="space-y-2">
                <div className="grid grid-cols-9 gap-2 text-xs font-medium text-zinc-500 px-3 py-2 bg-zinc-100 rounded-t-sm">
                  <div>Role</div>
                  <div>Tenure Type</div>
                  <div>Meeting Type</div>
                  <div className="text-center">Allocation %</div>
                  <div className="text-right">Breakup (₹)</div>
                  <div className="text-center">Meetings</div>
                  <div className="text-right flex items-center justify-end gap-1">
                    Rate/Meeting <Lock className="w-3 h-3 text-zinc-400" />
                  </div>
                  <div className="text-center">Count</div>
                  <div></div>
                </div>
                {teamDeployment.map((member, index) => (
                  <div 
                    key={member.id || index} 
                    className="grid grid-cols-9 gap-2 items-center px-3 py-2 bg-white border border-zinc-100 rounded-sm text-sm"
                    data-testid={`team-member-${index}`}
                  >
                    <div className="font-medium truncate" title={member.role}>{member.role}</div>
                    <div className="truncate text-zinc-600" title={getTenureTypeName(member.tenure_type_code)}>
                      {getTenureTypeName(member.tenure_type_code)}
                    </div>
                    <div className="truncate" title={member.meeting_type}>{member.meeting_type}</div>
                    <div className="text-center font-semibold text-blue-600">
                      {(member.allocation_percentage || 0).toFixed(1)}%
                    </div>
                    <div className="text-right font-semibold text-emerald-600">
                      {formatINR(member.breakup_amount || 0)}
                    </div>
                    <div className="text-center font-semibold text-blue-600">
                      {member.committed_meetings || 0}
                    </div>
                    <div className="text-right text-zinc-600 flex items-center justify-end gap-1">
                      {formatINR(member.rate_per_meeting || 0)}
                      <Lock className="w-3 h-3 text-zinc-300" />
                    </div>
                    <div className="text-center">{member.count || 1}</div>
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
                ))}
                
                {/* Totals Row */}
                <div className="grid grid-cols-9 gap-2 items-center px-3 py-2 bg-zinc-100 border border-zinc-200 rounded-b-sm text-sm font-semibold">
                  <div className="col-span-3 text-right">Total:</div>
                  <div className="text-center">100%</div>
                  <div className="text-right text-emerald-700">{formatINR(totals.allocatedTotal)}</div>
                  <div className="text-center text-blue-700">{totals.totalMeetings}</div>
                  <div className="col-span-3"></div>
                </div>
              </div>
            )}
            
            {teamDeployment.length === 0 && (
              <p className="text-sm text-zinc-400 text-center py-8">
                No team members added. Enter Total Investment above, then add your team deployment structure.
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
                <span className="text-zinc-600">Total Client Investment:</span>
                <span className="font-semibold text-zinc-950" data-testid="subtotal">{formatINR(totals.subtotal)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-zinc-600">Total Meetings:</span>
                <span className="font-semibold text-zinc-950" data-testid="total-meetings">{totals.totalMeetings}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-zinc-600">Discount ({formData.discount_percentage}%):</span>
                <span className="font-semibold text-red-600" data-testid="discount">- {formatINR(totals.discount)}</span>
              </div>
              {paymentPlan.selected_components.includes('gst') && (
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-600">GST ({paymentPlan.component_values.gst}%):</span>
                  <span className="font-semibold text-zinc-950" data-testid="gst">+ {formatINR(totals.gst)}</span>
                </div>
              )}
              <div className="flex justify-between text-lg font-bold pt-2 border-t border-zinc-300">
                <span className="text-zinc-950">Grand Total:</span>
                <span className="text-emerald-600" data-testid="grand-total">{formatINR(totals.total)}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Payment Plan Breakup - NEW */}
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950 flex items-center gap-2">
              <Receipt className="w-5 h-5" />
              Payment Plan Breakup
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Start Date & Component Selection */}
            <div className="grid grid-cols-2 gap-6">
              {/* Start Date */}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950 flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  Project Start Date *
                </Label>
                <Input
                  type="date"
                  value={paymentPlan.start_date}
                  onChange={(e) => setPaymentPlan({ ...paymentPlan, start_date: e.target.value })}
                  className="rounded-sm border-zinc-200"
                  data-testid="start-date-input"
                />
                <p className="text-xs text-zinc-500">
                  Payment reminders will be sent 7 days before each due date
                </p>
              </div>

              {/* Variable Components Selection */}
              <div className="space-y-3">
                <Label className="text-sm font-medium text-zinc-950">
                  Payment Components (Multi-select)
                </Label>
                <div className="space-y-3">
                  {PAYMENT_COMPONENTS.map(comp => (
                    <div key={comp.id} className="flex items-center gap-4 p-2 bg-zinc-50 rounded-sm">
                      <div className="flex items-center gap-2">
                        <Checkbox
                          id={comp.id}
                          checked={paymentPlan.selected_components.includes(comp.id)}
                          onCheckedChange={() => togglePaymentComponent(comp.id)}
                          data-testid={`component-${comp.id}`}
                        />
                        <label htmlFor={comp.id} className="text-sm font-medium cursor-pointer">
                          {comp.name}
                        </label>
                      </div>
                      <div className="flex items-center gap-2 ml-auto">
                        {comp.isLumpsum ? (
                          // Lumpsum conveyance input (currency) with tooltip
                          <>
                            <span className="text-sm text-zinc-500">₹</span>
                            <Input
                              type="number"
                              min="0"
                              step="1000"
                              value={paymentPlan.conveyance_lumpsum || ''}
                              onChange={(e) => setPaymentPlan({ 
                                ...paymentPlan, 
                                conveyance_lumpsum: parseFloat(e.target.value) || 0 
                              })}
                              className="w-28 h-8 text-sm rounded-sm"
                              placeholder="Lumpsum"
                              disabled={!paymentPlan.selected_components.includes(comp.id)}
                              data-testid="conveyance-lumpsum-input"
                            />
                            <span className="text-xs text-zinc-400">
                              (split across {numberOfPayments} {numberOfPayments === 1 ? 'payment' : 'payments'})
                            </span>
                            {paymentPlan.conveyance_lumpsum > 0 && paymentPlan.selected_components.includes('conveyance') && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <HelpCircle className="w-4 h-4 text-zinc-400 cursor-help" />
                                  </TooltipTrigger>
                                  <TooltipContent className="bg-zinc-900 text-white p-3 max-w-xs">
                                    <div className="space-y-1">
                                      <p className="font-semibold">Conveyance Distribution</p>
                                      <p>Total: {formatINR(paymentPlan.conveyance_lumpsum)}</p>
                                      <p>Per {formData.payment_schedule === 'monthly' ? 'month' : 'payment'}: {formatINR(Math.round(paymentPlan.conveyance_lumpsum / numberOfPayments))}</p>
                                      <p className="text-zinc-400 text-xs mt-1">Split evenly across {numberOfPayments} {numberOfPayments === 1 ? 'payment' : 'payments'}</p>
                                    </div>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
                          </>
                        ) : comp.editable ? (
                          <>
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              step="0.1"
                              value={paymentPlan.component_values[comp.id]}
                              onChange={(e) => updateComponentValue(comp.id, e.target.value)}
                              className="w-20 h-8 text-sm rounded-sm"
                              disabled={!paymentPlan.selected_components.includes(comp.id)}
                            />
                            <span className="text-sm text-zinc-500">%</span>
                          </>
                        ) : (
                          <span className="text-sm text-zinc-600 font-medium">
                            {paymentPlan.component_values[comp.id]}% (Fixed)
                          </span>
                        )}
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          comp.type === 'add' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
                        }`}>
                          {comp.type === 'add' ? '+Add' : '-Deduct'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-zinc-500">
                  Net = Basic + GST + Conveyance - TDS
                </p>
              </div>
            </div>

            {/* Custom Payment Schedule (shown only when custom is selected) */}
            {formData.payment_schedule === 'custom' && (
              <div className="space-y-4 p-4 bg-amber-50 rounded-sm border border-amber-200">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-zinc-950 flex items-center gap-2">
                    <Settings className="w-4 h-4" />
                    Custom Payment Schedule
                  </h4>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={addCustomPayment}
                    className="h-8 text-xs"
                    data-testid="add-custom-payment-btn"
                  >
                    <Plus className="w-3 h-3 mr-1" />
                    Add Payment
                  </Button>
                </div>
                
                {/* Validation message */}
                {customPaymentsTotal !== totals.afterDiscount && paymentPlan.custom_payments.length > 0 && (
                  <div className="p-2 bg-red-50 border border-red-200 rounded-sm text-xs text-red-700 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    Total custom payments ({formatINR(customPaymentsTotal)}) does not match project value ({formatINR(totals.afterDiscount)})
                  </div>
                )}
                
                {/* Custom payments list */}
                <div className="space-y-3">
                  {paymentPlan.custom_payments.map((payment, index) => (
                    <div key={payment.id} className="grid grid-cols-12 gap-3 items-end p-3 bg-white rounded-sm border border-amber-100">
                      <div className="col-span-2 space-y-1">
                        <Label className="text-xs text-zinc-500">Payment #{index + 1}</Label>
                        <Input
                          type="date"
                          value={payment.date}
                          onChange={(e) => updateCustomPayment(payment.id, 'date', e.target.value)}
                          className="h-9 text-sm rounded-sm"
                          data-testid={`custom-payment-date-${index}`}
                        />
                      </div>
                      <div className="col-span-3 space-y-1">
                        <Label className="text-xs text-zinc-500">Amount (₹)</Label>
                        <Input
                          type="number"
                          min="0"
                          step="1000"
                          value={payment.amount || ''}
                          onChange={(e) => updateCustomPayment(payment.id, 'amount', e.target.value)}
                          placeholder="Enter amount"
                          className="h-9 text-sm rounded-sm"
                          data-testid={`custom-payment-amount-${index}`}
                        />
                      </div>
                      <div className="col-span-6 space-y-1">
                        <Label className="text-xs text-zinc-500">Description / Milestone</Label>
                        <Input
                          type="text"
                          value={payment.description}
                          onChange={(e) => updateCustomPayment(payment.id, 'description', e.target.value)}
                          placeholder="e.g., 30% Upfront, Project Kickoff, Final Delivery"
                          className="h-9 text-sm rounded-sm"
                          data-testid={`custom-payment-desc-${index}`}
                        />
                      </div>
                      <div className="col-span-1 flex justify-end">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeCustomPayment(payment.id)}
                          className="h-9 w-9 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                          disabled={paymentPlan.custom_payments.length === 1}
                          data-testid={`remove-custom-payment-${index}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
                
                {/* Custom payments summary */}
                {paymentPlan.custom_payments.length > 0 && (
                  <div className="flex justify-between items-center p-2 bg-white rounded-sm border border-amber-100">
                    <span className="text-sm text-zinc-600">Total Custom Payments:</span>
                    <span className={`text-sm font-bold ${customPaymentsTotal === totals.afterDiscount ? 'text-emerald-600' : 'text-red-600'}`}>
                      {formatINR(customPaymentsTotal)}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Payment Schedule Table */}
            {paymentScheduleBreakdown.length > 0 && totalInvestment > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-zinc-950">Payment Schedule</h4>
                  <div className="flex items-center gap-2 text-xs text-amber-600">
                    <Bell className="w-3 h-3" />
                    Auto-reminders 7 days before due date
                  </div>
                </div>
                
                <div className="rounded-lg border border-zinc-200 overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-zinc-100">
                      <tr className="text-xs font-medium text-zinc-500 uppercase">
                        <th className="px-4 py-3 text-left">Frequency</th>
                        <th className="px-4 py-3 text-left">Due Date</th>
                        <th className="px-4 py-3 text-right">Basic</th>
                        {paymentPlan.selected_components.includes('gst') && (
                          <th className="px-4 py-3 text-right">GST ({paymentPlan.component_values.gst}%)</th>
                        )}
                        {paymentPlan.selected_components.includes('tds') && (
                          <th className="px-4 py-3 text-right">TDS ({paymentPlan.component_values.tds}%)</th>
                        )}
                        {paymentPlan.selected_components.includes('conveyance') && (
                          <th className="px-4 py-3 text-right">Conveyance (Lumpsum)</th>
                        )}
                        <th className="px-4 py-3 text-right font-bold">Net Receivable</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                      {paymentScheduleBreakdown.map((payment, index) => (
                        <tr key={index} className="text-sm hover:bg-zinc-50" data-testid={`payment-row-${index}`}>
                          <td className="px-4 py-3 font-medium text-zinc-900">{payment.frequency}</td>
                          <td className="px-4 py-3 text-zinc-600">{formatDate(payment.due_date)}</td>
                          <td className="px-4 py-3 text-right text-zinc-900">{formatINR(payment.basic)}</td>
                          {paymentPlan.selected_components.includes('gst') && (
                            <td className="px-4 py-3 text-right text-emerald-600">+{formatINR(payment.gst)}</td>
                          )}
                          {paymentPlan.selected_components.includes('tds') && (
                            <td className="px-4 py-3 text-right text-red-600">-{formatINR(payment.tds)}</td>
                          )}
                          {paymentPlan.selected_components.includes('conveyance') && (
                            <td className="px-4 py-3 text-right text-emerald-600">+{formatINR(payment.conveyance)}</td>
                          )}
                          <td className="px-4 py-3 text-right font-bold text-blue-600">{formatINR(payment.net)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-zinc-100">
                      <tr className="text-sm font-bold">
                        <td className="px-4 py-3" colSpan={2}>Total</td>
                        <td className="px-4 py-3 text-right">
                          {formatINR(paymentScheduleBreakdown.reduce((sum, p) => sum + p.basic, 0))}
                        </td>
                        {paymentPlan.selected_components.includes('gst') && (
                          <td className="px-4 py-3 text-right text-emerald-600">
                            +{formatINR(paymentScheduleBreakdown.reduce((sum, p) => sum + p.gst, 0))}
                          </td>
                        )}
                        {paymentPlan.selected_components.includes('tds') && (
                          <td className="px-4 py-3 text-right text-red-600">
                            -{formatINR(paymentScheduleBreakdown.reduce((sum, p) => sum + p.tds, 0))}
                          </td>
                        )}
                        {paymentPlan.selected_components.includes('conveyance') && (
                          <td className="px-4 py-3 text-right text-emerald-600">
                            +{formatINR(paymentScheduleBreakdown.reduce((sum, p) => sum + p.conveyance, 0))}
                          </td>
                        )}
                        <td className="px-4 py-3 text-right text-blue-700">
                          {formatINR(paymentScheduleBreakdown.reduce((sum, p) => sum + p.net, 0))}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            )}

            {(paymentScheduleBreakdown.length === 0 || totalInvestment <= 0) && (
              <div className="text-center py-8 text-zinc-400 text-sm">
                Enter Total Investment and Start Date to generate payment schedule
              </div>
            )}
          </CardContent>
        </Card>

        {/* Notes Section */}
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Notes & Descriptions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-700">Pricing Notes</Label>
                <Textarea
                  value={sectionNotes.pricing}
                  onChange={(e) => setSectionNotes({ ...sectionNotes, pricing: e.target.value })}
                  placeholder="Add notes about pricing, special terms, or conditions..."
                  className="min-h-[80px] text-sm rounded-sm border-zinc-200"
                  data-testid="notes-pricing"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-700">Team Deployment Notes</Label>
                <Textarea
                  value={sectionNotes.team_deployment}
                  onChange={(e) => setSectionNotes({ ...sectionNotes, team_deployment: e.target.value })}
                  placeholder="Add notes about team structure, availability, or roles..."
                  className="min-h-[80px] text-sm rounded-sm border-zinc-200"
                  data-testid="notes-team"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-700">Payment Terms Notes</Label>
                <Textarea
                  value={sectionNotes.payment_plan}
                  onChange={(e) => setSectionNotes({ ...sectionNotes, payment_plan: e.target.value })}
                  placeholder="Add notes about payment milestones, invoicing terms..."
                  className="min-h-[80px] text-sm rounded-sm border-zinc-200"
                  data-testid="notes-payment"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-700">General Notes</Label>
                <Textarea
                  value={sectionNotes.general}
                  onChange={(e) => setSectionNotes({ ...sectionNotes, general: e.target.value })}
                  placeholder="Add any additional notes or comments..."
                  className="min-h-[80px] text-sm rounded-sm border-zinc-200"
                  data-testid="notes-general"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Agreement Sections Configuration */}
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950 flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Agreement Sections
              <span className="text-xs font-normal text-zinc-500 ml-2">
                (Select sections to include in the agreement)
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-4">
              {[
                { id: 'pricing_summary', label: 'Pricing Summary', icon: Calculator },
                { id: 'team_deployment', label: 'Team Deployment', icon: Users },
                { id: 'payment_schedule', label: 'Payment Schedule', icon: Calendar },
                { id: 'gst_details', label: 'GST Details', icon: Receipt },
                { id: 'tds_details', label: 'TDS Details', icon: Receipt },
                { id: 'conveyance_details', label: 'Conveyance Details', icon: Receipt },
                { id: 'discount_details', label: 'Discount Details', icon: IndianRupee },
                { id: 'notes', label: 'Notes & Terms', icon: FileText }
              ].map(section => (
                <div 
                  key={section.id} 
                  className={`flex items-center gap-3 p-3 rounded-sm border cursor-pointer transition-all ${
                    agreementSections[section.id] 
                      ? 'border-emerald-300 bg-emerald-50' 
                      : 'border-zinc-200 bg-zinc-50'
                  }`}
                  onClick={() => setAgreementSections(prev => ({
                    ...prev,
                    [section.id]: !prev[section.id]
                  }))}
                  data-testid={`agreement-section-${section.id}`}
                >
                  <div className={`h-4 w-4 shrink-0 rounded-sm border shadow flex items-center justify-center ${
                    agreementSections[section.id] 
                      ? 'bg-zinc-900 border-zinc-900 text-white' 
                      : 'bg-white border-zinc-300'
                  }`}>
                    {agreementSections[section.id] && (
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3">
                        <polyline points="20 6 9 17 4 12"></polyline>
                      </svg>
                    )}
                  </div>
                  {agreementSections[section.id] ? (
                    <Eye className="w-4 h-4 text-emerald-600" />
                  ) : (
                    <EyeOff className="w-4 h-4 text-zinc-400" />
                  )}
                  <span className={`text-sm ${agreementSections[section.id] ? 'text-zinc-900 font-medium' : 'text-zinc-500'}`}>
                    {section.label}
                  </span>
                </div>
              ))}
            </div>
            <p className="text-xs text-zinc-500 mt-4">
              Unchecked sections will be hidden from the final agreement document.
            </p>
          </CardContent>
        </Card>

        {/* Dual Approval Section - for editing existing plans */}
        {searchParams.get('pricingId') && (
          <DualApprovalPanel 
            entityType="pricing" 
            entityId={searchParams.get('pricingId')}
            compact={false}
          />
        )}

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
            disabled={loading || teamDeployment.length === 0 || totalInvestment <= 0 || !paymentPlan.start_date}
            className="flex-1 bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm shadow-none"
            data-testid="create-pricing-plan-btn"
          >
            {loading ? 'Creating...' : 'Save & Continue to Scope Selection →'}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default PricingPlanBuilder;
