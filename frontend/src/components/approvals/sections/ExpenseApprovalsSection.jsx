import React, { useState, useMemo } from 'react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { Eye, CheckCircle, XCircle, RotateCcw, DollarSign, FileText, MapPin, Calendar, Send, ChevronDown, ChevronRight } from 'lucide-react';
import CollapsibleSection from '../CollapsibleSection';

const TAB_KEYS = ['pending', 'approved', 'rejected', 'revision_required'];
const TAB_LABELS = { pending: 'Pending', approved: 'Approved', rejected: 'Rejected', revision_required: 'Sent Back' };
const TAB_COLORS = { pending: 'bg-yellow-100 text-yellow-700', approved: 'bg-emerald-100 text-emerald-700', rejected: 'bg-red-100 text-red-700', revision_required: 'bg-orange-100 text-orange-700' };

const ExpenseApprovalsSection = ({
  isDark,
  expenseApprovals = [],
  onViewExpense,
  onApproveExpense,
  onRejectExpense,
  onSendBackExpense,
}) => {
  const [activeTab, setActiveTab] = useState('pending');
  const [expandedId, setExpandedId] = useState(null);

  const tabCounts = useMemo(() => {
    const counts = {};
    TAB_KEYS.forEach(k => { counts[k] = (expenseApprovals || []).filter(e => e.status === k || (k === 'pending' && e.status === 'manager_approved')).length; });
    return counts;
  }, [expenseApprovals]);

  const filteredExpenses = useMemo(() => {
    return (expenseApprovals || []).filter(e => {
      if (activeTab === 'pending') return ['pending', 'manager_approved'].includes(e.status);
      return e.status === activeTab;
    });
  }, [expenseApprovals, activeTab]);

  const totalPending = tabCounts.pending + tabCounts.revision_required;

  return (
    <CollapsibleSection
      title="Expense Approvals"
      icon={DollarSign}
      count={totalPending}
      isDark={isDark}
      testId="expense-approvals-section"
    >
      {/* Tabs */}
      <div className="flex gap-1 mb-4 p-1 bg-zinc-100 dark:bg-zinc-800 rounded-sm" data-testid="expense-tabs">
        {TAB_KEYS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-colors ${
              activeTab === tab
                ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-sm'
                : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-700'
            }`}
            data-testid={`expense-tab-${tab}`}
          >
            {TAB_LABELS[tab]}
            {tabCounts[tab] > 0 && (
              <span className={`ml-1.5 px-1.5 py-0.5 rounded-full text-[10px] ${TAB_COLORS[tab]}`}>
                {tabCounts[tab]}
              </span>
            )}
          </button>
        ))}
      </div>

      {!filteredExpenses.length ? (
        <div className="text-center py-8 text-zinc-500 dark:text-zinc-400">
          <DollarSign className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p className="text-sm">No {TAB_LABELS[activeTab]?.toLowerCase()} expenses</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredExpenses.map((expense, idx) => (
            <div key={expense.id || idx}
              className={`rounded-sm border ${isDark ? 'border-zinc-700 bg-zinc-900/50' : 'border-zinc-200 bg-white'}`}
            >
              {/* Expense Header - Always visible */}
              <div
                className="flex items-center justify-between p-3 cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800"
                onClick={() => setExpandedId(expandedId === expense.id ? null : expense.id)}
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`font-medium text-sm ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                        {expense.employee_name || 'Unknown'}
                      </span>
                      <Badge className={TAB_COLORS[expense.status] || 'bg-zinc-100 text-zinc-600'}>
                        {TAB_LABELS[expense.status] || expense.status}
                      </Badge>
                      {expense.linked_meeting_id && (
                        <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                          <FileText className="w-3 h-3 mr-1" /> Meeting Linked
                        </Badge>
                      )}
                    </div>
                    <div className={`text-xs mt-0.5 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                      {expense.category || 'General'} - {expense.expense_date || ''} - {expense.description?.slice(0, 60) || ''}
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className={`font-semibold text-sm ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                      {expense.currency || 'INR'} {(expense.total_amount || expense.amount || 0).toLocaleString()}
                    </div>
                  </div>
                  {expandedId === expense.id ? <ChevronDown className="w-4 h-4 text-zinc-400 ml-2" /> : <ChevronRight className="w-4 h-4 text-zinc-400 ml-2" />}
                </div>
              </div>

              {/* Expanded Detail */}
              {expandedId === expense.id && (
                <div className={`border-t px-3 py-3 ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                  {/* Line Items */}
                  {expense.line_items?.length > 0 && (
                    <div className="mb-3">
                      <div className="text-xs font-medium text-zinc-500 mb-1">Line Items</div>
                      <div className="space-y-1">
                        {expense.line_items.map((item, li) => (
                          <div key={li} className="flex justify-between text-xs py-1 border-b border-zinc-100 dark:border-zinc-700 last:border-0">
                            <span className="text-zinc-700 dark:text-zinc-300">{item.description || item.category}</span>
                            <span className="font-medium">{expense.currency || 'INR'} {(item.amount || 0).toLocaleString()}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Meeting/MOM Context */}
                  {(expense.meeting_summary || expense.linked_meeting_id) && (
                    <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-sm border border-blue-200 dark:border-blue-800">
                      <div className="text-xs font-medium text-blue-700 dark:text-blue-400 mb-1">
                        <FileText className="w-3 h-3 inline mr-1" /> Meeting Context
                      </div>
                      {expense.meeting_summary && <p className="text-xs text-zinc-600 dark:text-zinc-400">{expense.meeting_summary}</p>}
                      {expense.meeting_mom && <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1"><strong>MOM:</strong> {expense.meeting_mom}</p>}
                    </div>
                  )}

                  {/* Travel Details */}
                  {expense.travel_details && (
                    <div className="mb-3 p-2 bg-amber-50 dark:bg-amber-900/20 rounded-sm border border-amber-200 dark:border-amber-800">
                      <div className="text-xs font-medium text-amber-700 dark:text-amber-400 mb-1">
                        <MapPin className="w-3 h-3 inline mr-1" /> Travel Details
                      </div>
                      <p className="text-xs text-zinc-600 dark:text-zinc-400">{expense.travel_details.reason || expense.travel_details.from_location}</p>
                      {expense.travel_details.documents?.length > 0 && (
                        <div className="mt-1 text-xs text-zinc-500">{expense.travel_details.documents.length} document(s) attached</div>
                      )}
                    </div>
                  )}

                  {/* Sent-Back Comments */}
                  {expense.status === 'revision_required' && expense.revision_comments && (
                    <div className="mb-3 p-2 bg-orange-50 dark:bg-orange-900/20 rounded-sm border border-orange-200 dark:border-orange-800">
                      <div className="text-xs font-medium text-orange-700 dark:text-orange-400 mb-1">
                        <RotateCcw className="w-3 h-3 inline mr-1" /> Reviewer Comments
                      </div>
                      <p className="text-xs text-zinc-600 dark:text-zinc-400">{expense.revision_comments}</p>
                    </div>
                  )}

                  {/* Revision History */}
                  {expense.revision_history?.length > 0 && (
                    <div className="mb-3">
                      <div className="text-xs font-medium text-zinc-500 mb-1">Revision History</div>
                      {expense.revision_history.map((rev, ri) => (
                        <div key={ri} className="text-xs text-zinc-500 py-0.5">
                          {rev.action_by_name}: {rev.action} - {rev.comments || 'No comment'}
                          <span className="text-zinc-400 ml-2">{rev.action_at ? new Date(rev.action_at).toLocaleDateString() : ''}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="flex items-center gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-700">
                    <Button size="sm" variant="outline" onClick={() => onViewExpense?.(expense)} data-testid={`view-expense-${expense.id}`}>
                      <Eye className="w-3 h-3 mr-1" /> Details
                    </Button>
                    {activeTab === 'pending' && (
                      <>
                        <Button size="sm" onClick={() => onApproveExpense?.(expense)} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid={`approve-expense-${expense.id}`}>
                          <CheckCircle className="w-3 h-3 mr-1" /> Approve
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => onSendBackExpense?.(expense)} className="text-amber-600 border-amber-200" data-testid={`sendback-expense-${expense.id}`}>
                          <Send className="w-3 h-3 mr-1" /> Send Back
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => onRejectExpense?.(expense)} className="text-red-600 border-red-200" data-testid={`reject-expense-${expense.id}`}>
                          <XCircle className="w-3 h-3 mr-1" /> Reject
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </CollapsibleSection>
  );
};

export default ExpenseApprovalsSection;
