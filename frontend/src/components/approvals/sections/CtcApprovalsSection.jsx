/**
 * CtcApprovalsSection - CTC Structure Approvals
 * Admin-only section for reviewing and approving CTC structures
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { DollarSign, Eye, CheckCircle } from 'lucide-react';

// Format currency helper
const formatCurrency = (amount) => {
  if (!amount) return '₹0';
  if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)} Cr`;
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)} L`;
  return `₹${amount.toLocaleString('en-IN')}`;
};

export const CtcApprovalsSection = ({
  isDark,
  ctcApprovals = [],
  onViewCtc,
  onApproveCtc
}) => {
  if (ctcApprovals.length === 0) return null;

  return (
    <Card className={`mb-6 ${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`}>
      <CardHeader className="pb-3">
        <CardTitle className={`text-base flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
          <DollarSign className="w-5 h-5 text-purple-500" />
          Pending CTC Approvals ({ctcApprovals.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {ctcApprovals.map((ctc, idx) => (
            <div 
              key={ctc.id || idx}
              className={`p-4 rounded-lg border ${isDark ? 'border-zinc-700 bg-zinc-900/50' : 'border-zinc-200 bg-zinc-50'}`}
              data-testid={`ctc-item-${ctc.id}`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                      {ctc.employee_name || 'Unknown Employee'}
                    </span>
                    <Badge className="bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                      CTC Structure
                    </Badge>
                  </div>
                  <div className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                    <span>Annual CTC: <strong className="text-purple-600">{formatCurrency(ctc.annual_ctc)}</strong></span>
                    <span className="mx-2">•</span>
                    <span>Effective: {ctc.effective_date || 'N/A'}</span>
                  </div>
                  <div className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                    Submitted by: {ctc.created_by || 'HR'} on {new Date(ctc.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onViewCtc(ctc)}
                    className={isDark ? 'border-zinc-600' : ''}
                    data-testid={`view-ctc-${ctc.id}`}
                  >
                    <Eye className="w-4 h-4 mr-1" /> View
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => onApproveCtc(ctc)}
                    className="bg-emerald-600 hover:bg-emerald-700"
                    data-testid={`approve-ctc-${ctc.id}`}
                  >
                    <CheckCircle className="w-4 h-4 mr-1" /> Approve
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

export default CtcApprovalsSection;
