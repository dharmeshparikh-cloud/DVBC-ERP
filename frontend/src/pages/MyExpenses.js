import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '../components/ui/dialog';
import { Plus, Receipt, Clock, CheckCircle, XCircle, DollarSign, Trash2, Send, Save, Cloud } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import useDraft from '../hooks/useDraft';
import DraftIndicator from '../components/DraftIndicator';
import DraftSelector from '../components/DraftSelector';

const CATEGORIES = ['Travel', 'Local Conveyance', 'Food', 'Accommodation', 'Office Supplies', 'Communication', 'Client Entertainment', 'Other'];

const STATUS_STYLES = {
  draft: 'bg-zinc-100 text-zinc-600 border-zinc-200',
  pending: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  rejected: 'bg-red-50 text-red-700 border-red-200',
  reimbursed: 'bg-blue-50 text-blue-700 border-blue-200'
};

// Generate draft title from expense data
const generateExpenseDraftTitle = (data) => {
  const total = data.line_items?.reduce((s, i) => s + (i.amount || 0), 0) || 0;
  const category = data.line_items?.[0]?.category || 'Expense';
  return `${category} - ₹${total.toLocaleString()}`;
};

const MyExpenses = () => {
  const { user } = useContext(AuthContext);
  const [data, setData] = useState({ expenses: [], summary: {} });
  const [clients, setClients] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  
  // Draft support
  const {
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
  } = useDraft('expense', generateExpenseDraftTitle);
  
  const [formData, setFormData] = useState({
    client_id: '', client_name: '', project_id: '', project_name: '',
    is_office_expense: false, notes: '',
    line_items: [{ category: 'Travel', description: '', amount: 0, date: new Date().toISOString().split('T')[0] }]
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

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [expRes, clientsRes, projectsRes] = await Promise.all([
        axios.get(`${API}/my/expenses`),
        axios.get(`${API}/clients`).catch(() => ({ data: [] })),
        axios.get(`${API}/projects`).catch(() => ({ data: [] }))
      ]);
      setData(expRes.data);
      setClients(clientsRes.data);
      setProjects(projectsRes.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to fetch expenses');
    } finally {
      setLoading(false);
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
      setFormData({ ...formData, line_items: formData.line_items.filter((_, i) => i !== idx) });
    }
  };

  const totalAmount = formData.line_items.reduce((s, i) => s + (i.amount || 0), 0);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        line_items: formData.line_items.map(li => ({
          ...li, amount: parseFloat(li.amount) || 0,
          date: new Date(li.date).toISOString()
        }))
      };
      await axios.post(`${API}/expenses`, payload);
      toast.success('Expense created as draft');
      convertDraft(); // Mark draft as converted
      clearDraft(); // Clear the draft
      setDialogOpen(false);
      setFormData({ client_id: '', client_name: '', project_id: '', project_name: '', is_office_expense: false, notes: '', line_items: [{ category: 'Travel', description: '', amount: 0, date: new Date().toISOString().split('T')[0] }] });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create expense');
    }
  };

  // Load a saved draft
  const handleLoadDraft = async (draft) => {
    const loadedDraft = await loadDraft(draft.id);
    if (loadedDraft) {
      setFormData(loadedDraft.data);
      toast.success('Draft loaded');
    }
  };

  const handleSubmitForApproval = async (expenseId) => {
    try {
      await axios.post(`${API}/expenses/${expenseId}/submit`);
      toast.success('Expense submitted for approval');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit');
    }
  };

  const handleDeleteExpense = async (expenseId) => {
    if (!window.confirm('Are you sure you want to delete this expense?')) return;
    try {
      await axios.delete(`${API}/expenses/${expenseId}`);
      toast.success('Expense deleted');
      fetchData();
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        toast.error(detail.map(e => e.msg || 'Validation error').join(', '));
      } else if (typeof detail === 'string') {
        toast.error(detail);
      } else {
        toast.error('Failed to delete expense');
      }
    }
  };

  const fmt = (v) => `₹${(v || 0).toLocaleString('en-IN')}`;
  const sm = data.summary;

  return (
    <div data-testid="my-expenses-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">My Expenses</h1>
          <p className="text-zinc-500">Submit expenses and track reimbursement status</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="add-expense-btn" className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
              <Plus className="w-4 h-4 mr-2" /> New Expense
            </Button>
          </DialogTrigger>
          <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">New Expense</DialogTitle>
              <DialogDescription className="text-zinc-500">Add expense items for reimbursement</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={formData.is_office_expense}
                    onChange={(e) => setFormData({ ...formData, is_office_expense: e.target.checked })} className="w-4 h-4 rounded border-zinc-200" />
                  Office Expense
                </label>
              </div>
              {!formData.is_office_expense && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Client</Label>
                    <select value={formData.client_id} onChange={(e) => {
                      const c = clients.find(cl => cl.id === e.target.value);
                      setFormData({ ...formData, client_id: e.target.value, client_name: c?.company_name || '' });
                    }} className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm">
                      <option value="">Select client</option>
                      {clients.map(c => <option key={c.id} value={c.id}>{c.company_name}</option>)}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-medium text-zinc-950">Project</Label>
                    <select value={formData.project_id} onChange={(e) => {
                      const p = projects.find(pr => pr.id === e.target.value);
                      setFormData({ ...formData, project_id: e.target.value, project_name: p?.name || '' });
                    }} className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent text-sm">
                      <option value="">Select project</option>
                      {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
                  </div>
                </div>
              )}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-zinc-950">Line Items</Label>
                {formData.line_items.map((li, idx) => (
                  <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                    <div className="col-span-3">
                      <select value={li.category} onChange={(e) => updateLineItem(idx, 'category', e.target.value)}
                        className="w-full h-9 px-2 rounded-sm border border-zinc-200 bg-transparent text-xs">
                        {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
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
                      line_items: formData.line_items.map(li => ({
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
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 mb-6">
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

      {/* Expense List */}
      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="text-zinc-500">Loading...</div></div>
      ) : data.expenses.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-40">
            <Receipt className="w-10 h-10 text-zinc-300 mb-3" />
            <p className="text-zinc-500">No expenses yet</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {data.expenses.map(exp => (
            <Card key={exp.id} className="border-zinc-200 shadow-none rounded-sm hover:border-zinc-300 transition-colors" data-testid={`expense-${exp.id}`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="font-medium text-sm text-zinc-950">
                        {exp.is_office_expense ? 'Office Expense' : (exp.client_name || exp.project_name || 'Expense')}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-sm border ${STATUS_STYLES[exp.status] || STATUS_STYLES.draft}`}>
                        {exp.status?.charAt(0).toUpperCase() + exp.status?.slice(1)}
                      </span>
                    </div>
                    <div className="text-xs text-zinc-500">
                      {exp.line_items?.length || 0} items | Created {exp.created_at ? format(new Date(exp.created_at), 'MMM dd, yyyy') : '-'}
                      {exp.notes && ` | ${exp.notes}`}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-zinc-950">{fmt(exp.total_amount)}</span>
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
                    {(exp.status === 'pending' || exp.status === 'rejected') && (
                      <Button onClick={() => handleDeleteExpense(exp.id)} variant="ghost" size="sm" className="text-red-500 hover:text-red-700 hover:bg-red-50" data-testid={`delete-exp-${exp.id}`}>
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default MyExpenses;
