import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { 
  Receipt, Plus, Search, Eye, Edit2, Send, Check, 
  Clock, XCircle, CheckCircle, DollarSign, Calendar,
  Building2, Trash2, FileText, Upload, Image
} from 'lucide-react';
import { toast } from 'sonner';

const EXPENSE_CATEGORIES = [
  { value: 'travel', label: 'Travel' },
  { value: 'local_conveyance', label: 'Local Conveyance' },
  { value: 'food', label: 'Food & Meals' },
  { value: 'accommodation', label: 'Accommodation' },
  { value: 'office_supplies', label: 'Office Supplies' },
  { value: 'communication', label: 'Communication' },
  { value: 'client_entertainment', label: 'Client Entertainment' },
  { value: 'other', label: 'Other' }
];

const STATUS_STYLES = {
  draft: { bg: 'bg-zinc-100', text: 'text-zinc-700', icon: FileText },
  pending: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: Clock },
  approved: { bg: 'bg-emerald-100', text: 'text-emerald-700', icon: CheckCircle },
  rejected: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle },
  reimbursed: { bg: 'bg-green-100', text: 'text-green-700', icon: Check }
};

const Expenses = () => {
  const { user } = useContext(AuthContext);
  const [expenses, setExpenses] = useState([]);
  const [clients, setClients] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('');
  const [stats, setStats] = useState(null);

  // Dialogs
  const [createDialog, setCreateDialog] = useState(false);
  const [viewDialog, setViewDialog] = useState(false);
  const [selectedExpense, setSelectedExpense] = useState(null);

  // Form data
  const [formData, setFormData] = useState({
    client_id: '',
    client_name: '',
    project_id: '',
    project_name: '',
    is_office_expense: false,
    notes: '',
    line_items: [],
    receipts: []
  });

  // Line item form
  const [lineItemForm, setLineItemForm] = useState({
    category: 'local_conveyance',
    description: '',
    amount: '',
    date: new Date().toISOString().split('T')[0],
    receipt: null
  });

  const isHROrAdmin = ['admin', 'hr_manager', 'manager'].includes(user?.role);

  useEffect(() => {
    fetchData();
  }, [filterStatus]);

  const fetchData = async () => {
    try {
      const [expensesRes, clientsRes, projectsRes] = await Promise.all([
        axios.get(`${API}/expenses${filterStatus ? `?status=${filterStatus}` : ''}`),
        axios.get(`${API}/clients`),
        axios.get(`${API}/projects`)
      ]);
      setExpenses(expensesRes.data || []);
      setClients(clientsRes.data || []);
      setProjects(projectsRes.data || []);
      
      if (isHROrAdmin) {
        try {
          const statsRes = await axios.get(`${API}/expenses/stats/summary`);
          setStats(statsRes.data);
        } catch (e) {
          console.error('Error fetching stats:', e);
        }
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load expenses');
    } finally {
      setLoading(false);
    }
  };

  const addLineItem = () => {
    if (!lineItemForm.description || !lineItemForm.amount) {
      toast.error('Description and amount are required');
      return;
    }

    const newItem = {
      ...lineItemForm,
      amount: parseFloat(lineItemForm.amount),
      date: new Date(lineItemForm.date).toISOString()
    };

    setFormData({
      ...formData,
      line_items: [...formData.line_items, newItem]
    });

    setLineItemForm({
      category: 'local_conveyance',
      description: '',
      amount: '',
      date: new Date().toISOString().split('T')[0],
      receipt: null
    });
  };

  const handleReceiptUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        toast.error('File size should be less than 5MB');
        return;
      }
      const reader = new FileReader();
      reader.onload = (event) => {
        setLineItemForm({
          ...lineItemForm,
          receipt: {
            file_data: event.target.result,
            file_name: file.name,
            file_type: file.type
          }
        });
      };
      reader.readAsDataURL(file);
    }
  };

  const removeLineItem = (index) => {
    const items = [...formData.line_items];
    items.splice(index, 1);
    setFormData({ ...formData, line_items: items });
  };

  const handleCreateExpense = async () => {
    if (formData.line_items.length === 0) {
      toast.error('Add at least one expense item');
      return;
    }

    try {
      await axios.post(`${API}/expenses`, formData);
      toast.success('Expense request created');
      setCreateDialog(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create expense');
    }
  };

  const handleSubmitExpense = async (expenseId) => {
    try {
      await axios.post(`${API}/expenses/${expenseId}/submit`);
      toast.success('Expense submitted for approval');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit expense');
    }
  };

  const handleMarkReimbursed = async (expenseId) => {
    try {
      await axios.post(`${API}/expenses/${expenseId}/mark-reimbursed`);
      toast.success('Expense marked as reimbursed');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to mark as reimbursed');
    }
  };

  const handleApproveExpense = async (expenseId) => {
    try {
      await axios.post(`${API}/expenses/${expenseId}/approve`);
      toast.success('Expense approved successfully');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve expense');
    }
  };

  const handleRejectExpense = async (expenseId, reason) => {
    try {
      await axios.post(`${API}/expenses/${expenseId}/reject`, { reason: reason || 'Rejected by HR/Admin' });
      toast.success('Expense rejected');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject expense');
    }
  };

  const resetForm = () => {
    setFormData({
      client_id: '',
      client_name: '',
      project_id: '',
      project_name: '',
      is_office_expense: false,
      notes: '',
      line_items: []
    });
    setLineItemForm({
      category: 'local_conveyance',
      description: '',
      amount: '',
      date: new Date().toISOString().split('T')[0]
    });
  };

  const openViewDialog = async (expense) => {
    try {
      const res = await axios.get(`${API}/expenses/${expense.id}`);
      setSelectedExpense(res.data);
      setViewDialog(true);
    } catch (error) {
      toast.error('Failed to load expense details');
    }
  };

  const calculateTotal = () => {
    return formData.line_items.reduce((sum, item) => sum + item.amount, 0);
  };

  const getStatusBadge = (status) => {
    const style = STATUS_STYLES[status] || STATUS_STYLES.draft;
    const Icon = style.icon;
    return (
      <span className={`flex items-center gap-1 px-2 py-1 text-xs font-medium rounded ${style.bg} ${style.text}`}>
        <Icon className="w-3 h-3" />
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96"><div className="text-zinc-500">Loading...</div></div>;
  }

  return (
    <div data-testid="expenses-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          Expenses
        </h1>
        <p className="text-zinc-500">Submit and track expense reimbursements</p>
      </div>

      {/* Stats Cards (HR/Admin only) */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">Pending</p>
                  <p className="text-2xl font-semibold text-yellow-600">{stats.pending_count}</p>
                </div>
                <Clock className="w-8 h-8 text-yellow-200" />
              </div>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">Approved</p>
                  <p className="text-2xl font-semibold text-emerald-600">{stats.approved_count}</p>
                </div>
                <CheckCircle className="w-8 h-8 text-emerald-200" />
              </div>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">Reimbursed</p>
                  <p className="text-2xl font-semibold text-green-600">{stats.reimbursed_count}</p>
                </div>
                <Check className="w-8 h-8 text-green-200" />
              </div>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">Pending Amount</p>
                  <p className="text-2xl font-semibold text-zinc-950">₹{stats.pending_amount?.toLocaleString()}</p>
                </div>
                <DollarSign className="w-8 h-8 text-zinc-300" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
          >
            <option value="">All Status</option>
            <option value="draft">Draft</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="reimbursed">Reimbursed</option>
          </select>
        </div>
        
        <Button 
          onClick={() => { resetForm(); setCreateDialog(true); }}
          className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
          data-testid="new-expense-btn"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Expense
        </Button>
      </div>

      {/* Expenses List */}
      <Card className="border-zinc-200 shadow-none rounded-sm">
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="bg-zinc-50 text-xs font-medium uppercase tracking-wide text-zinc-500">
                <th className="px-4 py-3 text-left">Date</th>
                <th className="px-4 py-3 text-left">Employee</th>
                <th className="px-4 py-3 text-left">Client/Project</th>
                <th className="px-4 py-3 text-left">Items</th>
                <th className="px-4 py-3 text-right">Amount</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {expenses.map(expense => (
                <tr key={expense.id} className="border-b border-zinc-100 hover:bg-zinc-50" data-testid={`expense-row-${expense.id}`}>
                  <td className="px-4 py-3 text-sm text-zinc-600">
                    {new Date(expense.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-medium text-zinc-900">{expense.employee_name}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-zinc-600">
                    {expense.is_office_expense ? (
                      <span className="px-2 py-1 bg-zinc-100 text-zinc-700 rounded text-xs">Office Expense</span>
                    ) : (
                      expense.client_name || expense.project_name || '-'
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-zinc-600">
                    {expense.line_items?.length || 0} item(s)
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-zinc-900">
                    ₹{expense.total_amount?.toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    {getStatusBadge(expense.status)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <Button onClick={() => openViewDialog(expense)} variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <Eye className="w-4 h-4 text-zinc-500" />
                      </Button>
                      {expense.status === 'draft' && expense.created_by === user?.id && (
                        <Button 
                          onClick={() => handleSubmitExpense(expense.id)} 
                          variant="ghost" 
                          size="sm" 
                          className="h-8 px-2 text-blue-600"
                        >
                          <Send className="w-4 h-4 mr-1" />
                          Submit
                        </Button>
                      )}
                      {expense.status === 'pending' && isHROrAdmin && (
                        <>
                          <Button 
                            onClick={() => handleApproveExpense(expense.id)} 
                            variant="ghost" 
                            size="sm" 
                            className="h-8 px-2 text-emerald-600 hover:bg-emerald-50"
                            data-testid={`approve-expense-${expense.id}`}
                          >
                            <CheckCircle className="w-4 h-4 mr-1" />
                            Approve
                          </Button>
                          <Button 
                            onClick={() => handleRejectExpense(expense.id)} 
                            variant="ghost" 
                            size="sm" 
                            className="h-8 px-2 text-red-600 hover:bg-red-50"
                            data-testid={`reject-expense-${expense.id}`}
                          >
                            <XCircle className="w-4 h-4 mr-1" />
                            Reject
                          </Button>
                        </>
                      )}
                      {expense.status === 'approved' && isHROrAdmin && (
                        <Button 
                          onClick={() => handleMarkReimbursed(expense.id)} 
                          variant="ghost" 
                          size="sm" 
                          className="h-8 px-2 text-green-600"
                        >
                          <Check className="w-4 h-4 mr-1" />
                          Reimburse
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {expenses.length === 0 && (
            <div className="text-center py-12 text-zinc-400">
              <Receipt className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No expense requests found.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Expense Dialog */}
      <Dialog open={createDialog} onOpenChange={setCreateDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">New Expense Request</DialogTitle>
          </DialogHeader>
          <div className="space-y-6">
            {/* Expense Type */}
            <div>
              <h4 className="font-medium text-zinc-950 mb-3">Expense Type</h4>
              <div className="flex gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="expense_type"
                    checked={!formData.is_office_expense}
                    onChange={() => setFormData({ ...formData, is_office_expense: false, client_id: '', client_name: '' })}
                    className="rounded-full"
                  />
                  <span>Client/Project Related</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="expense_type"
                    checked={formData.is_office_expense}
                    onChange={() => setFormData({ ...formData, is_office_expense: true, client_id: '', client_name: '' })}
                    className="rounded-full"
                  />
                  <span>Office Expense</span>
                </label>
              </div>
            </div>

            {/* Client/Project Selection */}
            {!formData.is_office_expense && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Client</Label>
                  <select
                    value={formData.client_id}
                    onChange={(e) => {
                      const client = clients.find(c => c.id === e.target.value);
                      setFormData({ 
                        ...formData, 
                        client_id: e.target.value,
                        client_name: client?.company_name || ''
                      });
                    }}
                    className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
                  >
                    <option value="">Select client...</option>
                    {clients.map(c => (
                      <option key={c.id} value={c.id}>{c.company_name}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Project</Label>
                  <select
                    value={formData.project_id}
                    onChange={(e) => {
                      const project = projects.find(p => p.id === e.target.value);
                      setFormData({ 
                        ...formData, 
                        project_id: e.target.value,
                        project_name: project?.name || ''
                      });
                    }}
                    className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
                  >
                    <option value="">Select project...</option>
                    {projects.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {/* Add Line Item */}
            <div className="border-t border-zinc-100 pt-4">
              <h4 className="font-medium text-zinc-950 mb-3">Add Expense Item</h4>
              <div className="grid grid-cols-4 gap-3">
                <div className="space-y-2">
                  <Label>Category</Label>
                  <select
                    value={lineItemForm.category}
                    onChange={(e) => setLineItemForm({ ...lineItemForm, category: e.target.value })}
                    className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
                  >
                    {EXPENSE_CATEGORIES.map(cat => (
                      <option key={cat.value} value={cat.value}>{cat.label}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Input
                    value={lineItemForm.description}
                    onChange={(e) => setLineItemForm({ ...lineItemForm, description: e.target.value })}
                    placeholder="Taxi to client office"
                    className="rounded-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Amount (₹)</Label>
                  <Input
                    type="number"
                    value={lineItemForm.amount}
                    onChange={(e) => setLineItemForm({ ...lineItemForm, amount: e.target.value })}
                    placeholder="500"
                    className="rounded-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Date</Label>
                  <Input
                    type="date"
                    value={lineItemForm.date}
                    onChange={(e) => setLineItemForm({ ...lineItemForm, date: e.target.value })}
                    className="rounded-sm"
                  />
                </div>
              </div>
              <Button 
                onClick={addLineItem} 
                variant="outline" 
                className="mt-3 rounded-sm"
              >
                <Plus className="w-4 h-4 mr-1" />
                Add Item
              </Button>
            </div>

            {/* Line Items List */}
            {formData.line_items.length > 0 && (
              <div className="border-t border-zinc-100 pt-4">
                <h4 className="font-medium text-zinc-950 mb-3">Expense Items</h4>
                <div className="space-y-2">
                  {formData.line_items.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-zinc-50 rounded-sm">
                      <div className="flex items-center gap-4">
                        <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                          {EXPENSE_CATEGORIES.find(c => c.value === item.category)?.label}
                        </span>
                        <span className="text-sm">{item.description}</span>
                        <span className="text-xs text-zinc-500">
                          {new Date(item.date).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-semibold">₹{item.amount.toLocaleString()}</span>
                        <Button 
                          onClick={() => removeLineItem(idx)} 
                          variant="ghost" 
                          size="sm" 
                          className="h-6 w-6 p-0 text-red-500"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex justify-end mt-4 pt-4 border-t border-zinc-200">
                  <div className="text-right">
                    <p className="text-sm text-zinc-500">Total Amount</p>
                    <p className="text-2xl font-semibold text-zinc-950">₹{calculateTotal().toLocaleString()}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Notes */}
            <div className="space-y-2">
              <Label>Notes (Optional)</Label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Any additional notes..."
                rows={2}
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4 border-t border-zinc-100">
              <Button onClick={() => setCreateDialog(false)} variant="outline" className="flex-1 rounded-sm">
                Cancel
              </Button>
              <Button 
                onClick={handleCreateExpense}
                disabled={formData.line_items.length === 0}
                className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                Create Expense
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* View Expense Dialog */}
      <Dialog open={viewDialog} onOpenChange={setViewDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">Expense Details</DialogTitle>
          </DialogHeader>
          {selectedExpense && (
            <div className="space-y-6">
              {/* Header */}
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-zinc-950">{selectedExpense.employee_name}</h2>
                  <p className="text-sm text-zinc-500">
                    Submitted {new Date(selectedExpense.created_at).toLocaleDateString()}
                  </p>
                </div>
                {getStatusBadge(selectedExpense.status)}
              </div>

              {/* Details */}
              <div className="grid grid-cols-2 gap-4 border-t border-zinc-100 pt-4">
                <div>
                  <Label className="text-xs text-zinc-500">Client</Label>
                  <p className="font-medium">{selectedExpense.client_name || '-'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Project</Label>
                  <p className="font-medium">{selectedExpense.project_name || '-'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Type</Label>
                  <p className="font-medium">{selectedExpense.is_office_expense ? 'Office Expense' : 'Client/Project'}</p>
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">Total Amount</Label>
                  <p className="font-semibold text-emerald-600">₹{selectedExpense.total_amount?.toLocaleString()}</p>
                </div>
              </div>

              {/* Line Items */}
              <div className="border-t border-zinc-100 pt-4">
                <h4 className="font-medium text-zinc-950 mb-3">Expense Items</h4>
                <div className="space-y-2">
                  {selectedExpense.line_items?.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-zinc-50 rounded-sm">
                      <div className="flex items-center gap-4">
                        <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                          {EXPENSE_CATEGORIES.find(c => c.value === item.category)?.label || item.category}
                        </span>
                        <span className="text-sm">{item.description}</span>
                        <span className="text-xs text-zinc-500">
                          {new Date(item.date).toLocaleDateString()}
                        </span>
                      </div>
                      <span className="font-semibold">₹{item.amount?.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Notes */}
              {selectedExpense.notes && (
                <div className="border-t border-zinc-100 pt-4">
                  <Label className="text-xs text-zinc-500">Notes</Label>
                  <p className="text-sm text-zinc-700">{selectedExpense.notes}</p>
                </div>
              )}

              {/* Rejection Reason */}
              {selectedExpense.status === 'rejected' && selectedExpense.rejection_reason && (
                <div className="border-t border-zinc-100 pt-4">
                  <Label className="text-xs text-red-500">Rejection Reason</Label>
                  <p className="text-sm text-red-700">{selectedExpense.rejection_reason}</p>
                </div>
              )}

              {/* Reimbursement Info */}
              {selectedExpense.status === 'reimbursed' && (
                <div className="border-t border-zinc-100 pt-4">
                  <Label className="text-xs text-green-500">Reimbursed</Label>
                  <p className="text-sm text-green-700">
                    {selectedExpense.reimbursed_at ? new Date(selectedExpense.reimbursed_at).toLocaleDateString() : '-'}
                  </p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Expenses;
