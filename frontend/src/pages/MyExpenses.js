import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Receipt, Clock, CheckCircle, XCircle, DollarSign, Trash2, Send, Save, Cloud, FileText, Download, Car, Bike, Train, Users, MapPin, Calendar, Building2, ChevronDown, ChevronUp, Edit, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import useDraft from '../hooks/useDraft';
import DraftIndicator from '../components/DraftIndicator';
import DraftSelector from '../components/DraftSelector';
import PageHeader from '../components/ui/page-header';
import MyWorkspaceNav from '../components/MyWorkspaceNav';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { sortByLatest } from '../utils/sortUtils';
import { GovernedDropdown } from '../components/GovernedDropdown';
import { useExpenseCategories, useNormalizedProjects } from '../hooks/useSOWsByProject';

const CATEGORIES = ['Travel', 'Local Conveyance', 'Food', 'Accommodation', 'Office Supplies', 'Communication', 'Client Entertainment', 'Other'];

// Category options for GovernedDropdown
const CATEGORY_OPTIONS = CATEGORIES.map(c => ({ id: c, name: c }));

const STATUS_STYLES = {
  draft: 'bg-zinc-100 text-zinc-600 border-zinc-200',
  pending: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  rejected: 'bg-red-50 text-red-700 border-red-200',
  reimbursed: 'bg-blue-50 text-blue-700 border-blue-200',
  hr_approved: 'bg-blue-50 text-blue-700 border-blue-200',
  revision_required: 'bg-orange-50 text-orange-700 border-orange-200',
  manager_approved: 'bg-teal-50 text-teal-700 border-teal-200'
};

const EXP_TABS = [
  { key: 'all', label: 'All' },
  { key: 'draft', label: 'Draft' },
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
  { key: 'revision_required', label: 'Sent Back' },
];

const TRAVEL_MODE_ICONS = {
  DRIVING: Car,
  TWO_WHEELER: Bike,
  TRANSIT: Train,
  ACCOMPANIED: Users,
  WALKING: MapPin
};

// Generate draft title from expense data
const generateExpenseDraftTitle = (data) => {
  const total = data.line_items?.reduce((s, i) => s + (i.amount || 0), 0) || 0;
  const category = data.line_items?.[0]?.category || 'Expense';
  return `${category} - ₹${total.toLocaleString()}`;
};

const MyExpenses = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [showMonthlyReport, setShowMonthlyReport] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState(new Date().toISOString().slice(0, 7));
  const [activeTab, setActiveTab] = useState('all');
  const [editingExpense, setEditingExpense] = useState(null);
  const [editExpenseData, setEditExpenseData] = useState({});
  const [filterCategory, setFilterCategory] = useState('');
  const [showExpenseDetail, setShowExpenseDetail] = useState(null);
  
  // Draft support
  const {
    drafts = [],
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
  } = useDraft('expense', generateExpenseDraftTitle);
  
  const [formData, setFormData] = useState({
    client_id: '', client_name: '', project_id: '', project_name: '',
    is_office_expense: true, notes: '',  // Always office expense
    line_items: [{ category: 'Office Supplies', description: '', amount: 0, date: new Date().toISOString().split('T')[0] }]
  });
  
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
  
  // Auto-save when form data changes
  useEffect(() => {
    if (dialogOpen && formData.line_items?.some(li => li.description || li.amount > 0)) {
      autoSave(formData);
    }
  }, [formData, dialogOpen, autoSave]);

  // React Query: My Expenses Data
  const { data: expenseData, isLoading: loading, refetch: refetchExpenses } = useQuery({
    queryKey: ['my', 'expenses'],
    queryFn: async () => {
      const res = await axios.get(`${API}/my/expenses`);
      return res.data || { expenses: [], summary: {} };
    },
    staleTime: 2 * 60 * 1000,
  });
  const data = expenseData || { expenses: [], summary: {} };

  // React Query: Clients
  const { data: clients = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: async () => {
      const res = await axios.get(`${API}/clients`);
      return res.data || [];
    },
    staleTime: 5 * 60 * 1000,
  });

  // React Query: Projects
  const { data: projects = [] } = useQuery({
    queryKey: ['projects', 'list'],
    queryFn: async () => {
      const res = await axios.get(`${API}/projects`);
      return res.data || [];
    },
    staleTime: 5 * 60 * 1000,
  });

  // React Query: Monthly Expense Report
  const { data: monthlyReport, isLoading: reportLoading, refetch: refetchReport } = useQuery({
    queryKey: ['expense-report', selectedMonth],
    queryFn: async () => {
      const res = await axios.get(`${API}/expenses/report/monthly-meeting-expenses?month=${selectedMonth}`);
      return res.data;
    },
    enabled: showMonthlyReport,
    staleTime: 5 * 60 * 1000,
  });

  // PDF Generation Function
  const generatePDF = () => {
    if (!monthlyReport || !monthlyReport.expenses?.length) {
      toast.error('No data to export');
      return;
    }

    const doc = new jsPDF('landscape', 'mm', 'a4');
    const pageWidth = doc.internal.pageSize.getWidth();
    
    // Header
    doc.setFillColor(24, 24, 27); // zinc-950
    doc.rect(0, 0, pageWidth, 25, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(18);
    doc.setFont('helvetica', 'bold');
    doc.text('EXPENSE REPORT', 14, 15);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text(`Month: ${new Date(selectedMonth + '-01').toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}`, pageWidth - 70, 10);
    doc.text(`Employee: ${user?.full_name || 'N/A'}`, pageWidth - 70, 16);
    doc.text(`Generated: ${new Date().toLocaleDateString('en-IN')}`, pageWidth - 70, 22);

    // Summary Section
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text('Summary', 14, 35);
    
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    const summary = monthlyReport.summary;
    doc.text(`Total Expenses: ${summary.total_expenses}`, 14, 42);
    doc.text(`Total Amount: Rs. ${summary.total_amount?.toLocaleString('en-IN')}`, 14, 48);
    doc.text(`Approved: Rs. ${summary.approved_amount?.toLocaleString('en-IN')} (${summary.approved_count} items)`, 80, 42);
    doc.text(`Pending: Rs. ${summary.pending_amount?.toLocaleString('en-IN')} (${summary.pending_count} items)`, 80, 48);
    doc.text(`Rejected: Rs. ${summary.rejected_amount?.toLocaleString('en-IN')} (${summary.rejected_count} items)`, 160, 42);

    // Table Data
    const tableData = (monthlyReport?.expenses || []).map((exp, idx) => [
      idx + 1,
      exp.lead_name || 'N/A',
      exp.company || 'N/A',
      exp.stage || 'N/A',
      exp.expense_date || '',
      exp.travel_mode?.replace('_', ' ') || 'N/A',
      `${exp.total_km || exp.distance_km || 0} km`,
      exp.is_round_trip ? 'Yes' : 'No',
      `Rs. ${exp.amount?.toLocaleString('en-IN')}`,
      exp.status?.toUpperCase() || 'PENDING',
      exp.payroll_linked ? exp.payroll_period : 'Not Linked'
    ]);

    // Table
    autoTable(doc, {
      startY: 55,
      head: [['#', 'Lead Name', 'Company', 'Stage', 'Date', 'Travel Mode', 'Distance', 'Round Trip', 'Amount', 'Status', 'Payroll']],
      body: tableData,
      theme: 'striped',
      headStyles: { 
        fillColor: [24, 24, 27], 
        textColor: 255,
        fontStyle: 'bold',
        fontSize: 8
      },
      bodyStyles: { fontSize: 8 },
      columnStyles: {
        0: { cellWidth: 8 },
        1: { cellWidth: 30 },
        2: { cellWidth: 30 },
        3: { cellWidth: 20 },
        4: { cellWidth: 22 },
        5: { cellWidth: 22 },
        6: { cellWidth: 18 },
        7: { cellWidth: 15 },
        8: { cellWidth: 22 },
        9: { cellWidth: 18 },
        10: { cellWidth: 22 }
      },
      margin: { left: 14, right: 14 },
      didDrawPage: function(data) {
        // Footer on each page
        const pageCount = doc.internal.getNumberOfPages();
        doc.setFontSize(8);
        doc.setTextColor(128, 128, 128);
        doc.text(`Page ${data.pageNumber} of ${pageCount}`, pageWidth - 25, doc.internal.pageSize.getHeight() - 10);
      }
    });

    // Total Row - get finalY from the table
    const finalY = (doc.lastAutoTable?.finalY || 100) + 5;
    doc.setFillColor(240, 240, 240);
    doc.rect(14, finalY, pageWidth - 28, 10, 'F');
    doc.setTextColor(0, 0, 0);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.text(`TOTAL: Rs. ${summary.total_amount?.toLocaleString('en-IN')}`, pageWidth - 60, finalY + 7);

    // Save
    doc.save(`Expense_Report_${selectedMonth}_${user?.full_name?.replace(/\s+/g, '_') || 'Employee'}.pdf`);
    toast.success('PDF downloaded successfully');
  };

  // Mutation: Create Expense
  const createExpenseMutation = useMutation({
    mutationFn: async (payload) => {
      await axios.post(`${API}/expenses`, payload);
    },
    onSuccess: () => {
      toast.success('Expense created as draft');
      convertDraft();
      clearDraft();
      setDialogOpen(false);
      setFormData({ client_id: '', client_name: '', project_id: '', project_name: '', is_office_expense: false, notes: '', line_items: [{ category: 'Travel', description: '', amount: 0, date: new Date().toISOString().split('T')[0] }] });
      queryClient.invalidateQueries({ queryKey: ['my', 'expenses'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create expense');
    },
  });

  // Mutation: Submit for Approval
  const submitMutation = useMutation({
    mutationFn: async (expenseId) => {
      await axios.post(`${API}/expenses/${expenseId}/submit`);
    },
    onSuccess: () => {
      toast.success('Expense submitted for approval');
      queryClient.invalidateQueries({ queryKey: ['my', 'expenses'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to submit');
    },
  });

  // Mutation: Delete Expense
  const deleteMutation = useMutation({
    mutationFn: async (expenseId) => {
      await axios.delete(`${API}/expenses/${expenseId}`);
    },
    onSuccess: () => {
      toast.success('Expense deleted');
      queryClient.invalidateQueries({ queryKey: ['my', 'expenses'] });
    },
    onError: (error) => {
      const detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        toast.error((detail || []).map(e => e.msg || 'Validation error').join(', '));
      } else if (typeof detail === 'string') {
        toast.error(detail);
      } else {
        toast.error('Failed to delete expense');
      }
    },
  });

  // Mutation: Update and Resubmit sent-back expense
  const resubmitMutation = useMutation({
    mutationFn: async ({ expenseId, updatedData }) => {
      await axios.put(`${API}/expenses/${expenseId}`, updatedData);
      await axios.post(`${API}/expenses/${expenseId}/resubmit`);
    },
    onSuccess: () => {
      toast.success('Expense updated and resubmitted');
      setEditingExpense(null);
      queryClient.invalidateQueries({ queryKey: ['my', 'expenses'] });
    },
    onError: (error) => toast.error(error.response?.data?.detail || 'Failed to resubmit'),
  });

  // Fetch expense detail with meeting context for slide-out
  const fetchExpenseDetail = async (expenseId) => {
    try {
      const res = await axios.get(`${API}/expenses/${expenseId}`);
      setShowExpenseDetail(res.data);
    } catch (e) {
      toast.error('Failed to load expense details');
    }
  };

  const addLineItem = () => {
    setFormData({ ...formData, line_items: [...formData.line_items, { category: 'Travel', description: '', amount: 0, date: new Date().toISOString().split('T')[0] }] });
  };

  const updateLineItem = (idx, field, value) => {
    const items = [...formData.line_items];
    items[idx] = { ...items[idx], [field]: field === 'amount' ? parseFloat(value) || 0 : value };
    setFormData({ ...formData, line_items: items });
  };

  const removeLineItem = (idx) => {
    if (formData.line_items.length > 1) {
      setFormData({ ...formData, line_items: (formData.line_items || []).filter((_, i) => i !== idx) });
    }
  };

  const totalAmount = (formData?.line_items || []).reduce((s, i) => s + (i.amount || 0), 0);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      ...formData,
      line_items: (formData.line_items || []).map(li => ({
        ...li, amount: parseFloat(li.amount) || 0,
        date: new Date(li.date).toISOString()
      }))
    };
    createExpenseMutation.mutate(payload);
  };

  // Load a saved draft
  const handleLoadDraft = async (draft) => {
    const loadedDraft = await loadDraft(draft.id);
    if (loadedDraft) {
      setFormData(loadedDraft.data);
      toast.success('Draft loaded');
    }
  };

  const handleSubmitForApproval = (expenseId) => {
    submitMutation.mutate(expenseId);
  };

  const handleDeleteExpense = (expenseId) => {
    if (!window.confirm('Are you sure you want to delete this expense?')) return;
    deleteMutation.mutate(expenseId);
  };

  const fmt = (v) => `₹${(v || 0).toLocaleString('en-IN')}`;
  const sm = data.summary || {};

  // Only HR and Admin can create manual expenses (office expenses only)
  const canCreateManualExpense = ['admin', 'hr_manager', 'hr_executive', 'accounts', 'finance_manager', 'finance_executive'].includes(user?.role);

  return (
    <div data-testid="my-expenses-page">
      <MyWorkspaceNav />
      <PageHeader
        title="My Expenses"
        subtitle="View your expense claims and track reimbursement status"
        onRefresh={() => refetchExpenses()}
        loading={loading}
        actions={
          canCreateManualExpense ? (
            <Button onClick={() => setDialogOpen(true)} data-testid="add-expense-btn" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
              <Plus className="w-4 h-4 mr-2" /> Office Expense
            </Button>
          ) : null
        }
      />
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <div className="flex items-center justify-between">
                <div>
                  <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Office Expense</DialogTitle>
                  <DialogDescription className="text-zinc-500">Add office expense items for reimbursement (not client/meeting related)</DialogDescription>
                </div>
                <DraftIndicator saving={savingDraft} lastSaved={lastSaved} onSave={() => saveDraft(formData)} />
              </div>
            </DialogHeader>
            
            {/* Draft Selector */}
            {drafts && drafts.length > 0 && (
              <DraftSelector 
                drafts={drafts}
                onLoadDraft={handleLoadDraft}
                onDeleteDraft={deleteDraft}
                loadingDrafts={loadingDrafts}
              />
            )}
            
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Office Expense is always true for manual expenses - hidden but enforced */}
              <input type="hidden" value="true" name="is_office_expense" />
              <div className="bg-blue-50 border border-blue-200 rounded-sm p-3 text-sm text-blue-700">
                <strong>Note:</strong> This form is for office expenses only (supplies, equipment, etc.). 
                Travel expenses for client meetings should be claimed through the Sales/Consulting Funnel.
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Line Items</Label>
                {(formData.line_items || []).map((li, idx) => (
                  <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                    <div className="col-span-3">
                      <GovernedDropdown
                        value={li.category}
                        onChange={(val) => updateLineItem(idx, 'category', val)}
                        options={CATEGORY_OPTIONS}
                        placeholder="Select Category"
                        data-testid={`expense-category-${idx}`}
                        valueKey="id"
                        labelKey="name"
                      />
                    </div>
                    <div className="col-span-4">
                      <Input value={li.description} onChange={(e) => updateLineItem(idx, 'description', e.target.value)}
                        placeholder="Description" className="rounded-sm border-zinc-200 h-9 text-xs" />
                    </div>
                    <div className="col-span-2">
                      <Input type="number" value={li.amount} onChange={(e) => updateLineItem(idx, 'amount', e.target.value)}
                        placeholder="Amount" className="rounded-sm border-zinc-200 h-9 text-xs" />
                    </div>
                    <div className="col-span-2">
                      <Input type="date" value={li.date} onChange={(e) => updateLineItem(idx, 'date', e.target.value)}
                        className="rounded-sm border-zinc-200 h-9 text-xs" />
                    </div>
                    <div className="col-span-1">
                      {formData.line_items.length > 1 && (
                        <Button type="button" onClick={() => removeLineItem(idx)} variant="ghost" className="h-9 px-2">
                          <Trash2 className="w-3 h-3 text-red-500" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
                <Button type="button" onClick={addLineItem} variant="outline" size="sm" className="rounded-sm text-xs">
                  <Plus className="w-3 h-3 mr-1" /> Add Item
                </Button>
              </div>
              <div className="flex justify-between items-center bg-zinc-50 p-3 rounded-sm border border-zinc-200">
                <span className="text-sm text-zinc-600">Total</span>
                <span className="text-lg font-semibold text-zinc-950">{fmt(totalAmount)}</span>
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Notes</Label>
                <Input value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  className="rounded-sm border-zinc-200" placeholder="Optional" />
              </div>
              <div className="flex gap-2">
                <Button type="submit" data-testid="save-draft-btn" variant="outline" className="flex-1 rounded-sm shadow-none">
                  Save as Draft
                </Button>
                <Button type="button" data-testid="submit-expense" onClick={async (e) => {
                  e.preventDefault();
                  try {
                    const payload = {
                      ...formData,
                      line_items: (formData.line_items || []).map(li => ({
                        ...li, amount: parseFloat(li.amount) || 0,
                        date: new Date(li.date).toISOString()
                      }))
                    };
                    const res = await axios.post(`${API}/expenses`, payload);
                    // Auto-submit for approval
                    await axios.post(`${API}/expenses/${res.data.expense_id}/submit`);
                    toast.success('Expense submitted for approval');
                    setDialogOpen(false);
                    setFormData({ client_id: '', client_name: '', project_id: '', project_name: '', is_office_expense: false, notes: '', line_items: [{ category: 'Travel', description: '', amount: 0, date: new Date().toISOString().split('T')[0] }] });
                    fetchData();
                  } catch (error) {
                    toast.error(error.response?.data?.detail || 'Failed to submit expense');
                  }
                }} className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                  <Send className="w-4 h-4 mr-2" /> Submit for Approval
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-3 mb-6">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <Clock className="w-5 h-5 text-yellow-500" />
            <div><div className="text-xs text-zinc-500">Pending</div><div className="text-xl font-semibold text-zinc-950" data-testid="exp-pending">{sm.pending || 0}</div></div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-500" />
            <div><div className="text-xs text-zinc-500">Approved</div><div className="text-xl font-semibold text-zinc-950">{sm.approved || 0}</div></div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm border-orange-200">
          <CardContent className="p-3 flex items-center gap-2">
            <RotateCcw className="w-5 h-5 text-orange-500" />
            <div><div className="text-xs text-orange-600">Sent Back</div><div className="text-xl font-semibold text-orange-700">{(data.expenses || []).filter(e => e.status === 'revision_required').length}</div></div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-blue-500" />
            <div><div className="text-xs text-zinc-500">Reimbursed</div><div className="text-xl font-semibold text-zinc-950">{fmt(sm.reimbursed_amount || 0)}</div></div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-3 flex items-center gap-2">
            <Receipt className="w-5 h-5 text-zinc-400" />
            <div><div className="text-xs text-zinc-500">Total Claims</div><div className="text-xl font-semibold text-zinc-950">{fmt(sm.total_amount || 0)}</div></div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs + Filters */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-1 p-1 bg-zinc-100 rounded-sm" data-testid="expense-list-tabs">
          {EXP_TABS.map(tab => {
            const count = tab.key === 'all' ? (data.expenses || []).length : (data.expenses || []).filter(e => e.status === tab.key).length;
            return (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-colors ${activeTab === tab.key ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'}`}
                data-testid={`exp-tab-${tab.key}`}>
                {tab.label}
                {count > 0 && <span className="ml-1.5 text-[10px] px-1 rounded-full bg-zinc-200 text-zinc-600">{count}</span>}
              </button>
            );
          })}
        </div>
        <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)} className="h-8 px-2 text-xs border border-zinc-200 rounded-sm bg-white" data-testid="exp-filter-category">
          <option value="">All Categories</option>
          {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* Expense List */}
      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : (() => {
        let expenses = sortByLatest(data?.expenses || [], 'created_at');
        if (activeTab !== 'all') expenses = expenses.filter(e => e.status === activeTab);
        if (filterCategory) expenses = expenses.filter(e => (e.line_items || []).some(li => li.category === filterCategory) || e.category === filterCategory);
        
        if (!expenses.length) return (
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="flex flex-col items-center justify-center h-40">
              <Receipt className="w-10 h-10 text-zinc-300 mb-3" />
              <p className="text-zinc-500">{activeTab === 'all' ? 'No expenses yet' : `No ${EXP_TABS.find(t => t.key === activeTab)?.label || ''} expenses`}</p>
            </CardContent>
          </Card>
        );
        
        return (
          <div className="space-y-2">
            {expenses.map(exp => {
              const isSentBack = exp.status === 'revision_required';
              const isEditingThis = editingExpense === exp.id;
              
              return (
                <Card key={exp?.id} className={`border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors ${isSentBack ? 'border-orange-300 bg-orange-50/30' : ''}`} data-testid={`expense-${exp?.id}`}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <span className="font-medium text-sm text-zinc-950">
                            {exp?.is_office_expense ? 'Office Expense' : (exp?.description || exp?.client_name || exp?.project_name || 'Expense')}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded-sm border ${STATUS_STYLES[exp?.status] || STATUS_STYLES.draft}`}>
                            {exp?.status === 'revision_required' ? 'Sent Back' : exp?.status?.charAt(0).toUpperCase() + exp?.status?.slice(1)}
                          </span>
                          {exp.expense_type === 'meeting_expense' && (
                            <span className="text-xs px-2 py-0.5 rounded-sm bg-blue-50 text-blue-600 border border-blue-200">Meeting</span>
                          )}
                        </div>
                        <div className="text-xs text-zinc-500">
                          {exp.expense_type === 'meeting_expense' ? (
                            <>{exp.travel_details?.travel_mode?.replace('_', ' ')} | {exp.travel_details?.total_km || exp.travel_details?.distance_km || 0} km{exp.travel_details?.is_round_trip && ' (Round Trip)'}{exp.lead_name && ` | ${exp.lead_name}`}</>
                          ) : (
                            <>{exp.line_items?.length || 0} items | Created {exp.created_at ? format(new Date(exp.created_at), 'dd/MM/yyyy') : '-'}{exp.notes && ` | ${exp.notes}`}</>
                          )}
                        </div>
                        {/* Reviewer comments for sent-back expenses */}
                        {isSentBack && exp.revision_comments && (
                          <div className="mt-2 p-2 bg-orange-100 border border-orange-200 rounded-sm" data-testid={`sentback-comments-${exp.id}`}>
                            <div className="text-xs font-medium text-orange-700 mb-0.5">Reviewer Comments:</div>
                            <div className="text-xs text-orange-800">{exp.revision_comments}</div>
                            {exp.revision_history?.length > 0 && (
                              <div className="text-[10px] text-orange-600 mt-1">
                                By: {exp.revision_history[exp.revision_history.length - 1]?.action_by_name} on {new Date(exp.revision_history[exp.revision_history.length - 1]?.action_at).toLocaleDateString()}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-semibold text-zinc-950">{fmt(exp.total_amount || exp.amount)}</span>
                        
                        {/* View Detail Button - for all statuses */}
                        <Button onClick={() => fetchExpenseDetail(exp.id)} variant="ghost" size="sm" className="text-zinc-500 hover:text-zinc-700" data-testid={`view-exp-${exp.id}`}>
                          <FileText className="w-4 h-4" />
                        </Button>
                        
                        {exp.status === 'draft' && (
                          <>
                            <Button onClick={() => handleSubmitForApproval(exp.id)} variant="outline" size="sm" className="rounded-sm" data-testid={`submit-exp-${exp.id}`}>
                              <Send className="w-3 h-3 mr-1" /> Submit
                            </Button>
                            <Button onClick={() => handleDeleteExpense(exp.id)} variant="ghost" size="sm" className="text-red-500 hover:text-red-700 hover:bg-red-50" data-testid={`delete-exp-${exp.id}`}>
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </>
                        )}
                        
                        {/* Sent-back: Edit & Resubmit */}
                        {isSentBack && (
                          <Button onClick={() => {
                            setEditingExpense(exp.id);
                            setEditExpenseData({
                              notes: exp.notes || '',
                              line_items: exp.line_items || [],
                              description: exp.description || ''
                            });
                          }} variant="outline" size="sm" className="text-orange-600 border-orange-200 hover:bg-orange-50" data-testid={`edit-sentback-${exp.id}`}>
                            <Edit className="w-3 h-3 mr-1" /> Edit & Resubmit
                          </Button>
                        )}
                        
                        {(exp.status === 'pending' || exp.status === 'rejected') && (
                          <Button onClick={() => handleDeleteExpense(exp.id)} variant="ghost" size="sm" className="text-red-500 hover:text-red-700 hover:bg-red-50" data-testid={`delete-exp-${exp.id}`}>
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                    
                    {/* Inline Edit form for sent-back expenses */}
                    {isEditingThis && (
                      <div className="mt-3 pt-3 border-t border-orange-200 space-y-3" data-testid={`edit-form-${exp.id}`}>
                        <div className="text-xs font-medium text-orange-700">Edit and resubmit your expense claim:</div>
                        {(editExpenseData.line_items || []).map((li, idx) => (
                          <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                            <div className="col-span-3">
                              <Input value={li.category || ''} onChange={(e) => {
                                const items = [...editExpenseData.line_items];
                                items[idx] = { ...items[idx], category: e.target.value };
                                setEditExpenseData({...editExpenseData, line_items: items});
                              }} placeholder="Category" className="h-8 text-xs rounded-sm" />
                            </div>
                            <div className="col-span-5">
                              <Input value={li.description || ''} onChange={(e) => {
                                const items = [...editExpenseData.line_items];
                                items[idx] = { ...items[idx], description: e.target.value };
                                setEditExpenseData({...editExpenseData, line_items: items});
                              }} placeholder="Description" className="h-8 text-xs rounded-sm" />
                            </div>
                            <div className="col-span-2">
                              <Input type="number" value={li.amount || 0} onChange={(e) => {
                                const items = [...editExpenseData.line_items];
                                items[idx] = { ...items[idx], amount: parseFloat(e.target.value) || 0 };
                                setEditExpenseData({...editExpenseData, line_items: items});
                              }} placeholder="Amount" className="h-8 text-xs rounded-sm" />
                            </div>
                          </div>
                        ))}
                        <div className="space-y-2">
                          <Input value={editExpenseData.notes} onChange={(e) => setEditExpenseData({...editExpenseData, notes: e.target.value})} placeholder="Add notes / corrections" className="h-8 text-xs rounded-sm" />
                        </div>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm" onClick={() => setEditingExpense(null)} className="text-xs">Cancel</Button>
                          <Button size="sm" onClick={() => resubmitMutation.mutate({ expenseId: exp.id, updatedData: editExpenseData })}
                            disabled={resubmitMutation.isPending}
                            className="text-xs bg-orange-600 hover:bg-orange-700 text-white" data-testid={`resubmit-${exp.id}`}>
                            <Send className="w-3 h-3 mr-1" /> {resubmitMutation.isPending ? 'Resubmitting...' : 'Resubmit'}
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        );
      })()}

      {/* Expense Detail Slide-out */}
      {showExpenseDetail && (
        <Dialog open={!!showExpenseDetail} onOpenChange={() => setShowExpenseDetail(null)}>
          <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-zinc-600" /> Expense Details
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className={`text-xs px-2 py-0.5 rounded-sm border ${STATUS_STYLES[showExpenseDetail.status] || ''}`}>
                  {showExpenseDetail.status === 'revision_required' ? 'Sent Back' : showExpenseDetail.status?.charAt(0).toUpperCase() + showExpenseDetail.status?.slice(1)}
                </span>
                <span className="text-lg font-semibold">{fmt(showExpenseDetail.total_amount || showExpenseDetail.amount)}</span>
              </div>

              {/* Line Items */}
              {showExpenseDetail.line_items?.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-zinc-500 mb-2">Line Items</div>
                  <div className="border border-zinc-200 rounded-sm">
                    {showExpenseDetail.line_items.map((li, i) => (
                      <div key={i} className="flex justify-between px-3 py-2 text-xs border-b border-zinc-100 last:border-0">
                        <span className="text-zinc-700">{li.category} - {li.description}</span>
                        <span className="font-medium">{fmt(li.amount)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Meeting Context - MOM */}
              {showExpenseDetail.meeting_context && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-sm">
                  <div className="text-xs font-medium text-blue-700 mb-1">Meeting Context (Read Only)</div>
                  <div className="text-xs text-zinc-700 space-y-1">
                    <div><strong>Title:</strong> {showExpenseDetail.meeting_context.title}</div>
                    <div><strong>Type:</strong> {showExpenseDetail.meeting_context.meeting_type}</div>
                    <div><strong>Date:</strong> {showExpenseDetail.meeting_context.date}</div>
                    {showExpenseDetail.meeting_context.location && <div><strong>Location:</strong> {showExpenseDetail.meeting_context.location}</div>}
                    {showExpenseDetail.meeting_context.mom_summary && (
                      <div className="mt-2 p-2 bg-white rounded-sm border border-blue-100">
                        <strong>MOM Summary:</strong>
                        <p className="mt-1 whitespace-pre-wrap">{showExpenseDetail.meeting_context.mom_summary}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Travel Context */}
              {(showExpenseDetail.travel_context || showExpenseDetail.travel_details) && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-sm">
                  <div className="text-xs font-medium text-amber-700 mb-1">Travel Details</div>
                  <div className="text-xs text-zinc-700 space-y-1">
                    {showExpenseDetail.travel_context && (
                      <>
                        <div><strong>From:</strong> {showExpenseDetail.travel_context.from_city}</div>
                        <div><strong>To:</strong> {showExpenseDetail.travel_context.to_city}</div>
                        <div><strong>Purpose:</strong> {showExpenseDetail.travel_context.purpose}</div>
                      </>
                    )}
                    {showExpenseDetail.travel_details && (
                      <>
                        <div><strong>Mode:</strong> {showExpenseDetail.travel_details.travel_mode}</div>
                        <div><strong>Distance:</strong> {showExpenseDetail.travel_details.total_km || showExpenseDetail.travel_details.distance_km} km</div>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Revision History */}
              {showExpenseDetail.revision_history?.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-zinc-500 mb-2">Approval History</div>
                  <div className="space-y-1">
                    {showExpenseDetail.revision_history.map((rev, i) => (
                      <div key={i} className="text-xs px-2 py-1.5 bg-zinc-50 rounded-sm border border-zinc-100">
                        <span className="font-medium">{rev.action_by_name}</span>: {rev.action}
                        {rev.comments && <span className="text-zinc-500"> — "{rev.comments}"</span>}
                        <span className="text-zinc-400 ml-2">{rev.action_at ? new Date(rev.action_at).toLocaleDateString() : ''}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Monthly Expense Report Section */}
      <Card className="border-zinc-200 shadow-none rounded-sm mt-6">
        <CardHeader 
          className="cursor-pointer hover:bg-zinc-50 transition-colors"
          onClick={() => setShowMonthlyReport(!showMonthlyReport)}
        >
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="w-5 h-5 text-emerald-600" />
              Monthly Expense Report
            </CardTitle>
            {showMonthlyReport ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </div>
        </CardHeader>
        
        {showMonthlyReport && (
          <CardContent className="border-t">
            {/* Controls */}
            <div className="flex flex-wrap items-end gap-4 mb-4">
              <div>
                <Label className="text-xs text-zinc-500 mb-1 block">Select Month</Label>
                <Input
                  type="month"
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(e.target.value)}
                  className="w-40 h-9 rounded-sm"
                />
              </div>
              <Button 
                onClick={() => refetchReport()} 
                variant="outline" 
                size="sm" 
                className="rounded-sm"
              >
                Load Report
              </Button>
              <Button 
                onClick={generatePDF} 
                size="sm" 
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm"
                disabled={!monthlyReport?.expenses?.length}
              >
                <Download className="w-4 h-4 mr-2" />
                Download PDF
              </Button>
            </div>

            {/* Summary Cards */}
            {monthlyReport?.summary && (
              <div className="grid grid-cols-4 gap-3 mb-4">
                <div className="bg-zinc-50 p-3 rounded-sm border border-zinc-200">
                  <div className="text-xs text-zinc-500">Total</div>
                  <div className="text-lg font-bold">{monthlyReport.summary.total_expenses}</div>
                  <div className="text-sm font-semibold">{fmt(monthlyReport.summary.total_amount)}</div>
                </div>
                <div className="bg-emerald-50 p-3 rounded-sm border border-emerald-200">
                  <div className="text-xs text-emerald-600">Approved</div>
                  <div className="text-lg font-bold text-emerald-700">{monthlyReport.summary.approved_count}</div>
                  <div className="text-sm font-semibold text-emerald-600">{fmt(monthlyReport.summary.approved_amount)}</div>
                </div>
                <div className="bg-yellow-50 p-3 rounded-sm border border-yellow-200">
                  <div className="text-xs text-yellow-600">Pending</div>
                  <div className="text-lg font-bold text-yellow-700">{monthlyReport.summary.pending_count}</div>
                  <div className="text-sm font-semibold text-yellow-600">{fmt(monthlyReport.summary.pending_amount)}</div>
                </div>
                <div className="bg-red-50 p-3 rounded-sm border border-red-200">
                  <div className="text-xs text-red-600">Rejected</div>
                  <div className="text-lg font-bold text-red-700">{monthlyReport.summary.rejected_count}</div>
                  <div className="text-sm font-semibold text-red-600">{fmt(monthlyReport.summary.rejected_amount)}</div>
                </div>
              </div>
            )}

            {/* Expense Table */}
            {reportLoading ? (
              <div className="text-center py-8 text-zinc-500">Loading report...</div>
            ) : !monthlyReport?.expenses?.length ? (
              <div className="text-center py-8 text-zinc-500">
                <FileText className="w-10 h-10 mx-auto mb-2 text-zinc-300" />
                No meeting expenses found for this month. Click "Load Report" to fetch data.
              </div>
            ) : (
              <div className="overflow-x-auto border border-zinc-200 rounded-sm">
                <table className="w-full text-sm">
                  <thead className="bg-zinc-100">
                    <tr>
                      <th className="px-3 py-2 text-left font-semibold text-xs">#</th>
                      <th className="px-3 py-2 text-left font-semibold text-xs">Lead / Company</th>
                      <th className="px-3 py-2 text-left font-semibold text-xs">Stage</th>
                      <th className="px-3 py-2 text-left font-semibold text-xs">Date</th>
                      <th className="px-3 py-2 text-left font-semibold text-xs">Travel</th>
                      <th className="px-3 py-2 text-left font-semibold text-xs">Distance</th>
                      <th className="px-3 py-2 text-right font-semibold text-xs">Amount</th>
                      <th className="px-3 py-2 text-center font-semibold text-xs">Status</th>
                      <th className="px-3 py-2 text-left font-semibold text-xs">Payroll</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {(monthlyReport?.expenses || []).map((exp, idx) => {
                      const TravelIcon = TRAVEL_MODE_ICONS[exp.travel_mode] || MapPin;
                      return (
                        <tr key={exp.expense_id || idx} className="hover:bg-zinc-50">
                          <td className="px-3 py-2 text-xs">{idx + 1}</td>
                          <td className="px-3 py-2">
                            <div className="font-medium text-xs">{exp.lead_name || 'N/A'}</div>
                            <div className="text-xs text-zinc-500 flex items-center gap-1">
                              <Building2 className="w-3 h-3" />
                              {exp.company || 'N/A'}
                            </div>
                          </td>
                          <td className="px-3 py-2">
                            <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700">
                              {exp.stage || 'N/A'}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-xs">
                            <div className="flex items-center gap-1">
                              <Calendar className="w-3 h-3 text-zinc-400" />
                              {exp.expense_date}
                            </div>
                          </td>
                          <td className="px-3 py-2 text-xs">
                            <div className="flex items-center gap-1">
                              <TravelIcon className="w-3 h-3 text-zinc-500" />
                              {exp.travel_mode?.replace('_', ' ') || 'N/A'}
                            </div>
                            {exp.is_round_trip && (
                              <span className="text-xs text-blue-500">(Round Trip)</span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-xs">
                            {exp.total_km || exp.distance_km || 0} km
                            {exp.rate_per_km > 0 && (
                              <div className="text-zinc-400">@ ₹{exp.rate_per_km}/km</div>
                            )}
                          </td>
                          <td className="px-3 py-2 text-right font-semibold text-xs">
                            {fmt(exp.amount)}
                          </td>
                          <td className="px-3 py-2 text-center">
                            <span className={`text-xs px-2 py-0.5 rounded-sm border ${STATUS_STYLES[exp.status] || STATUS_STYLES.pending}`}>
                              {exp.status?.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-xs">
                            {exp.payroll_linked ? (
                              <span className="text-emerald-600 flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" />
                                {exp.payroll_period}
                              </span>
                            ) : (
                              <span className="text-zinc-400">Not linked</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot className="bg-zinc-100 font-semibold">
                    <tr>
                      <td colSpan="6" className="px-3 py-2 text-right text-xs">
                        Total ({monthlyReport.expenses.length} expenses):
                      </td>
                      <td className="px-3 py-2 text-right text-sm">
                        {fmt((monthlyReport?.expenses || []).reduce((sum, e) => sum + (e.amount || 0), 0))}
                      </td>
                      <td colSpan="2"></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </CardContent>
        )}
      </Card>
    </div>
  );
};

export default MyExpenses;
