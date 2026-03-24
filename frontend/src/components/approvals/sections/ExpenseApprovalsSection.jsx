/**
 * ExpenseApprovalsSection - Expense Approval Requests
 * For Manager/HR to review expense submissions
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { Receipt, Eye, CheckCircle, XCircle, RotateCcw, Loader2 } from 'lucide-react';

// Format currency helper
const formatCurrency = (amount) => {
  if (!amount) return '₹0';
  return `₹${amount.toLocaleString('en-IN')}`;
};

// Get status badge styles
const getExpenseStatusBadge = (status) => {
  const styles = {
    pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    approved: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    revision: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
  };
  return styles[status] || styles.pending;
};

export const ExpenseApprovalsSection = ({
  isDark,
  expenseApprovals = [],
  onViewExpense,
  onApproveExpense,
  onRejectExpense,
  onSendBackExpense,
  actionLoading
}) => {
  if (expenseApprovals.length === 0) return null;

  return (
    <Card className={`mb-6 ${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`}>
      <CardHeader className="pb-3">
        <CardTitle className={`text-base flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
          <Receipt className="w-5 h-5 text-emerald-500" />
          Pending Expense Approvals ({expenseApprovals.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {(expenseApprovals || []).map((expense, idx) => (
            <div 
              key={expense.id || idx}
              className={`p-4 rounded-lg border ${isDark ? 'border-zinc-700 bg-zinc-900/50' : 'border-zinc-200 bg-zinc-50'}`}
              data-testid={`expense-item-${expense.id}`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                      {expense.employee_name || expense.submitted_by_name || 'Unknown'}
                    </span>
                    <Badge className={getExpenseStatusBadge(expense.status)}>
                      {expense.is_office_expense ? 'Office Expense' : expense.client_name || 'Client Expense'}
                    </Badge>
                    {expense.status === 'revision' && (
                      <Badge className="bg-amber-100 text-amber-700">Revision Requested</Badge>
                    )}
                  </div>
                  <div className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                    <span>Amount: <strong className="text-emerald-600">{formatCurrency(expense.total_amount || expense.amount)}</strong></span>
                    <span className="mx-2">•</span>
                    <span>Items: {expense.line_items?.length || expense.item_count || 1}</span>
                    {expense.project_name && (
                      <>
                        <span className="mx-2">•</span>
                        <span>Project: {expense.project_name}</span>
                      </>
                    )}
                  </div>
                  <div className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                    Submitted: {new Date(expense.created_at || expense.submitted_at).toLocaleDateString()}
                    {expense.notes && <span className="ml-2">• {expense.notes}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onViewExpense(expense)}
                    className={isDark ? 'border-zinc-600' : ''}
                    data-testid={`view-expense-${expense.id}`}
                  >
                    <Eye className="w-4 h-4 mr-1" /> View
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => onApproveExpense(expense)}
                    className="bg-emerald-600 hover:bg-emerald-700"
                    disabled={actionLoading}
                    data-testid={`approve-expense-${expense.id}`}
                  >
                    {actionLoading ? (
                      <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                    ) : (
                      <CheckCircle className="w-4 h-4 mr-1" />
                    )}
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onSendBackExpense(expense)}
                    className="border-amber-300 text-amber-600 hover:bg-amber-50"
                    disabled={actionLoading}
                    data-testid={`sendback-expense-${expense.id}`}
                  >
                    <RotateCcw className="w-4 h-4 mr-1" /> Send Back
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => onRejectExpense(expense)}
                    disabled={actionLoading}
                    data-testid={`reject-expense-${expense.id}`}
                  >
                    <XCircle className="w-4 h-4 mr-1" /> Reject
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default ExpenseApprovalsSection;
