import React, { useState, useContext } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { AuthContext, API } from '../../App';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Textarea } from '../../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Plus, Receipt, Clock, CheckCircle, XCircle, DollarSign, 
  Trash2, Send, Building2, Calendar, AlertTriangle, Briefcase,
  FileText, RefreshCw
} from 'lucide-react';

const EXPENSE_CATEGORIES = [
  'Travel',
  'Local Conveyance', 
  'Food',
  'Accommodation',
  'Communication',
  'Client Entertainment',
  'Printing & Stationery',
  'Other'
];

const ConsultantExpenses = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [formData, setFormData] = useState({
    project_id: '',
    project_name: '',
    meeting_id: '',
    category: 'Travel',
    description: '',
    amount: 0,
    expense_date: new Date().toISOString().split('T')[0],
    notes: '',
    line_items: [{ category: 'Travel', description: '', amount: 0, date: new Date().toISOString().split('T')[0] }]
  });

  // Fetch user's assigned projects
  const { data: projects = [] } = useQuery({
    queryKey: ['my-projects', 'consultant'],
    queryFn: async () => {
      const res = await axios.get(`${API}/projects/my-projects`);
      return res.data || [];
    },
    staleTime: 5 * 60 * 1000
  });

  // Fetch my expenses
  const { data: expenseData, isLoading, refetch } = useQuery({
    queryKey: ['my', 'expenses', 'consultant'],
    queryFn: async () => {
      const res = await axios.get(`${API}/my/expenses`);
      return res.data || { expenses: [], summary: {} };
    },
    staleTime: 2 * 60 * 1000
  });

  // Fetch meetings for selected project
  const { data: meetings = [] } = useQuery({
    queryKey: ['project-meetings', formData.project_id],
    queryFn: async () => {
      if (!formData.project_id) return [];
      const res = await axios.get(`${API}/meetings?project_id=${formData.project_id}&limit=50`);
      return res.data?.meetings || res.data || [];
    },
    enabled: !!formData.project_id,
    staleTime: 2 * 60 * 1000
  });

  // Create expense mutation
  const createMutation = useMutation({
    mutationFn: async (data) => {
      const res = await axios.post(`${API}/expenses`, data);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success('Expense created successfully');
      queryClient.invalidateQueries(['my', 'expenses']);
      resetForm();
      setShowCreateDialog(false);
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create expense');
    }
  });

  // Submit for approval mutation
  const submitMutation = useMutation({
    mutationFn: async (expenseId) => {
      await axios.post(`${API}/expenses/${expenseId}/submit`);
    },
    onSuccess: () => {
      toast.success('Expense submitted for approval');
      queryClient.invalidateQueries(['my', 'expenses']);
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to submit');
    }
  });

  const resetForm = () => {
    setFormData({
      project_id: '',
      project_name: '',
      meeting_id: '',
      category: 'Travel',
      description: '',
      amount: 0,
      expense_date: new Date().toISOString().split('T')[0],
      notes: '',
      line_items: [{ category: 'Travel', description: '', amount: 0, date: new Date().toISOString().split('T')[0] }]
    });
  };

  const handleProjectChange = (projectId) => {
    const project = projects.find(p => p.id === projectId);
    setFormData({
      ...formData,
      project_id: projectId,
      project_name: project?.name || '',
      meeting_id: '' // Reset meeting when project changes
    });
  };

  const addLineItem = () => {
    setFormData({
      ...formData,
      line_items: [...formData.line_items, { 
        category: 'Travel', 
        description: '', 
        amount: 0, 
        date: new Date().toISOString().split('T')[0] 
      }]
    });
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

  const totalAmount = formData.line_items.reduce((sum, item) => sum + (item.amount || 0), 0);

  const handleSubmit = async (submitForApproval = false) => {
    if (!formData.project_id) {
      toast.error('Please select a project');
      return;
    }

    if (formData.line_items.every(li => !li.description && li.amount === 0)) {
      toast.error('Please add at least one expense item');
      return;
    }

    const payload = {
      project_id: formData.project_id,
      project_name: formData.project_name,
      meeting_id: formData.meeting_id || null,
      notes: formData.notes,
      expense_date: formData.expense_date,
      is_office_expense: false,
      line_items: formData.line_items.map(li => ({
        ...li,
        amount: parseFloat(li.amount) || 0,
        date: new Date(li.date).toISOString()
      }))
    };

    try {
      const res = await axios.post(`${API}/expenses`, payload);
      if (submitForApproval) {
        await axios.post(`${API}/expenses/${res.data.expense_id}/submit`);
        toast.success('Expense submitted for approval');
      } else {
        toast.success('Expense saved as draft');
      }
      queryClient.invalidateQueries(['my', 'expenses']);
      resetForm();
      setShowCreateDialog(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create expense');
    }
  };

  const expenses = expenseData?.expenses || [];
  const summary = expenseData?.summary || {};
  const activeProjects = projects.filter(p => !['completed', 'cancelled', 'closed'].includes(p.status));

  const getStatusBadge = (status) => {
    const styles = {
      draft: 'bg-zinc-100 text-zinc-600',
      pending: 'bg-amber-50 text-amber-700',
      approved: 'bg-green-50 text-green-700',
      rejected: 'bg-red-50 text-red-700',
      hr_approved: 'bg-blue-50 text-blue-700',
      reimbursed: 'bg-emerald-50 text-emerald-700'
    };
    return <Badge className={styles[status] || 'bg-zinc-100'}>{status}</Badge>;
  };

  return (
    <div className="p-6 space-y-6" data-testid="consultant-expenses-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Project Expenses</h1>
          <p className="text-zinc-500 mt-1">Submit and track expenses for your consulting projects</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => setShowCreateDialog(true)} data-testid="create-expense-btn">
            <Plus className="w-4 h-4 mr-2" />
            New Expense
          </Button>
        </div>
      </div>

      {/* Governance Notice */}
      <Card className="border-amber-200 bg-amber-50/50">
        <CardContent className="pt-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5" />
            <div>
              <p className="font-medium text-amber-800">Expense Governance Rules</p>
              <ul className="text-sm text-amber-700 mt-1 space-y-1">
                <li>• All expenses must be linked to an active project</li>
                <li>• Travel expenses should be linked to a specific meeting when possible</li>
                <li>• Expenses for completed/cancelled projects cannot be submitted</li>
                <li>• Travel expenses without meeting linkage require additional review</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Pending</p>
                <p className="text-2xl font-bold text-amber-600">{summary.pending || 0}</p>
              </div>
              <Clock className="w-8 h-8 text-amber-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Approved</p>
                <p className="text-2xl font-bold text-green-600">{summary.approved || 0}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Rejected</p>
                <p className="text-2xl font-bold text-red-600">{summary.rejected || 0}</p>
              </div>
              <XCircle className="w-8 h-8 text-red-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Total Claims</p>
                <p className="text-2xl font-bold text-zinc-700">₹{(summary.total_amount || 0).toLocaleString()}</p>
              </div>
              <DollarSign className="w-8 h-8 text-zinc-400" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Expense List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Expenses</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-zinc-500">Loading expenses...</div>
          ) : expenses.length === 0 ? (
            <div className="text-center py-12">
              <Receipt className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
              <p className="text-zinc-500">No expenses found</p>
              <Button variant="outline" className="mt-4" onClick={() => setShowCreateDialog(true)}>
                Create your first expense
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {expenses.slice(0, 10).map((expense) => (
                <div 
                  key={expense.id} 
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-zinc-50"
                  data-testid={`expense-row-${expense.id}`}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-zinc-100 flex items-center justify-center">
                      <Receipt className="w-5 h-5 text-zinc-600" />
                    </div>
                    <div>
                      <p className="font-medium text-zinc-900">
                        {expense.project_name || expense.description || 'Expense'}
                      </p>
                      <div className="flex items-center gap-2 text-sm text-zinc-500">
                        {expense.project_name && (
                          <span className="flex items-center gap-1">
                            <Briefcase className="w-3 h-3" />
                            {expense.project_name}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {expense.expense_date || expense.created_at?.split('T')[0]}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-semibold text-zinc-900">
                      ₹{(expense.total_amount || expense.amount || 0).toLocaleString()}
                    </span>
                    {getStatusBadge(expense.status)}
                    {expense.status === 'draft' && (
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => submitMutation.mutate(expense.id)}
                      >
                        <Send className="w-3 h-3 mr-1" />
                        Submit
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Expense Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Project Expense</DialogTitle>
            <DialogDescription>
              Submit expenses for your consulting projects. All expenses must be linked to a project.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Project Selection - Required */}
            <div className="space-y-2">
              <Label className="flex items-center gap-1">
                <Briefcase className="w-4 h-4" />
                Project <span className="text-red-500">*</span>
              </Label>
              {activeProjects.length === 0 ? (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
                  <AlertTriangle className="w-4 h-4 inline mr-2" />
                  No active projects found. You need to be assigned to a project to submit expenses.
                </div>
              ) : (
                <Select value={formData.project_id} onValueChange={handleProjectChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a project" />
                  </SelectTrigger>
                  <SelectContent>
                    {activeProjects.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.name} - {p.client_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {/* Meeting Selection - Optional but recommended for travel */}
            {formData.project_id && meetings.length > 0 && (
              <div className="space-y-2">
                <Label className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  Related Meeting (Optional)
                </Label>
                <Select value={formData.meeting_id} onValueChange={(v) => setFormData({ ...formData, meeting_id: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Link to a meeting (recommended for travel)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">No meeting linkage</SelectItem>
                    {meetings.map((m) => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.title || m.meeting_type} - {m.meeting_date?.split('T')[0]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-zinc-500">
                  Linking travel expenses to meetings helps with project cost tracking
                </p>
              </div>
            )}

            {/* Expense Date */}
            <div className="space-y-2">
              <Label>Expense Date</Label>
              <Input
                type="date"
                value={formData.expense_date}
                onChange={(e) => setFormData({ ...formData, expense_date: e.target.value })}
              />
            </div>

            {/* Line Items */}
            <div className="space-y-2">
              <Label>Expense Items</Label>
              {formData.line_items.map((li, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-3">
                    <Select value={li.category} onValueChange={(v) => updateLineItem(idx, 'category', v)}>
                      <SelectTrigger className="h-9">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {EXPENSE_CATEGORIES.map(c => (
                          <SelectItem key={c} value={c}>{c}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-5">
                    <Input
                      value={li.description}
                      onChange={(e) => updateLineItem(idx, 'description', e.target.value)}
                      placeholder="Description"
                      className="h-9"
                    />
                  </div>
                  <div className="col-span-3">
                    <Input
                      type="number"
                      value={li.amount}
                      onChange={(e) => updateLineItem(idx, 'amount', e.target.value)}
                      placeholder="Amount"
                      className="h-9"
                    />
                  </div>
                  <div className="col-span-1">
                    {formData.line_items.length > 1 && (
                      <Button type="button" variant="ghost" size="sm" onClick={() => removeLineItem(idx)}>
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
              <Button type="button" variant="outline" size="sm" onClick={addLineItem}>
                <Plus className="w-4 h-4 mr-1" />
                Add Item
              </Button>
            </div>

            {/* Total */}
            <div className="flex justify-between items-center p-3 bg-zinc-50 rounded-lg border">
              <span className="text-zinc-600">Total Amount</span>
              <span className="text-xl font-bold text-zinc-900">₹{totalAmount.toLocaleString()}</span>
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label>Notes (Optional)</Label>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Any additional notes..."
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button 
              variant="outline" 
              onClick={() => handleSubmit(false)}
              disabled={!formData.project_id || createMutation.isPending}
            >
              Save as Draft
            </Button>
            <Button 
              onClick={() => handleSubmit(true)}
              disabled={!formData.project_id || createMutation.isPending}
            >
              <Send className="w-4 h-4 mr-2" />
              Submit for Approval
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ConsultantExpenses;
