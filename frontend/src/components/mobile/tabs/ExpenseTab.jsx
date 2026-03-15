/**
 * ExpenseTab - Mobile Expense Management Tab
 * Shows expense summary and recent claims
 * Extracted from EmployeeMobileApp.js for better maintainability
 */

import React, { memo, useContext } from 'react';
import { Wallet, Plus, Receipt, Info } from 'lucide-react';
import { AuthContext } from '../../../App';

// Roles that can create manual expenses (office expenses only)
const EXPENSE_CREATION_ROLES = ['admin', 'hr_manager', 'hr_executive', 'accounts', 'finance_manager', 'finance_executive'];

export const ExpenseTab = memo(({
  expenses = [],
  onAddExpense
}) => {
  const { user } = useContext(AuthContext);
  const canCreateManualExpense = EXPENSE_CREATION_ROLES.includes(user?.role);
  
  const totalClaims = expenses.reduce((sum, e) => sum + (e.total_amount || 0), 0);
  const pendingCount = expenses.filter(e => e.status === 'pending').length;
  const approvedCount = expenses.filter(e => e.status === 'approved').length;
  const reimbursedCount = expenses.filter(e => e.status === 'reimbursed').length;

  return (
    <div className="space-y-4 pb-24">
      <div className="bg-gradient-to-br from-amber-500 to-orange-600 rounded-3xl p-6 text-white shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-amber-100 text-sm">Total Claims</p>
            <p className="text-3xl font-bold">₹{totalClaims.toLocaleString()}</p>
          </div>
          <Wallet className="w-12 h-12 opacity-50" />
        </div>
        <div className="grid grid-cols-3 gap-2 mt-4">
          <div className="bg-white/20 rounded-xl p-2 text-center">
            <p className="text-xl font-bold">{pendingCount}</p>
            <p className="text-xs opacity-80">Pending</p>
          </div>
          <div className="bg-white/20 rounded-xl p-2 text-center">
            <p className="text-xl font-bold">{approvedCount}</p>
            <p className="text-xs opacity-80">Approved</p>
          </div>
          <div className="bg-white/20 rounded-xl p-2 text-center">
            <p className="text-xl font-bold">{reimbursedCount}</p>
            <p className="text-xs opacity-80">Paid</p>
          </div>
        </div>
      </div>

      {canCreateManualExpense ? (
        <button 
          onClick={onAddExpense}
          onTouchEnd={(e) => { e.preventDefault(); onAddExpense(); }}
          className="w-full py-4 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-2xl font-semibold shadow-lg flex items-center justify-center gap-2 active:scale-95 transition touch-manipulation cursor-pointer"
          style={{ WebkitTapHighlightColor: 'transparent', touchAction: 'manipulation' }}
          data-testid="add-expense-btn"
        >
          <Plus className="w-5 h-5" />
          Add Office Expense
        </button>
      ) : (
        <div className="w-full py-4 px-4 bg-zinc-100 dark:bg-zinc-800 rounded-2xl flex items-center gap-3 text-sm">
          <Info className="w-5 h-5 text-blue-500 flex-shrink-0" />
          <span className="text-zinc-600 dark:text-zinc-400">
            Travel expenses are claimed through meeting records in the Sales/Consulting funnel.
          </span>
        </div>
      )}

      <div className="bg-white rounded-2xl shadow-sm border border-zinc-100 overflow-hidden">
        <div className="p-4 border-b border-zinc-100">
          <h3 className="font-semibold text-zinc-900">Recent Expenses</h3>
        </div>
        {expenses.length > 0 ? (
          <div className="divide-y divide-zinc-100">
            {expenses.slice(0, 5).map((expense, i) => (
              <div key={i} className="flex items-center gap-3 p-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  expense.status === 'approved' ? 'bg-emerald-100 text-emerald-600' :
                  expense.status === 'pending' ? 'bg-amber-100 text-amber-600' :
                  expense.status === 'reimbursed' ? 'bg-blue-100 text-blue-600' :
                  'bg-red-100 text-red-600'
                }`}>
                  <Receipt className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-zinc-900">{expense.description || 'Expense'}</p>
                  <p className="text-xs text-zinc-500">{expense.expense_date || expense.created_at?.split('T')[0]}</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-zinc-900">₹{(expense.total_amount || 0).toLocaleString()}</p>
                  <p className={`text-xs ${
                    expense.status === 'approved' ? 'text-emerald-600' :
                    expense.status === 'pending' ? 'text-amber-600' :
                    expense.status === 'reimbursed' ? 'text-blue-600' : 'text-red-600'
                  }`}>
                    {expense.status}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-zinc-500">
            <Receipt className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
            <p>No expense claims yet</p>
          </div>
        )}
      </div>
    </div>
  );
});

ExpenseTab.displayName = 'ExpenseTab';

export default ExpenseTab;
