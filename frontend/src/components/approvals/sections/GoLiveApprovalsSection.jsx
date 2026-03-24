/**
 * GoLiveApprovalsSection - Go-Live Approval Requests
 * Admin-only section for reviewing employee activation requests
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { Rocket, Eye, CheckCircle, XCircle } from 'lucide-react';

export const GoLiveApprovalsSection = ({
  isDark,
  goLiveApprovals = [],
  onViewGoLive,
  onApproveGoLive,
  onRejectGoLive,
  actionLoading
}) => {
  if (goLiveApprovals.length === 0) return null;

  return (
    <Card className={`mb-6 ${isDark ? 'border-zinc-700 bg-zinc-800' : 'border-zinc-200'}`}>
      <CardHeader className="pb-3">
        <CardTitle className={`text-base flex items-center gap-2 ${isDark ? 'text-zinc-100' : ''}`}>
          <Rocket className="w-5 h-5 text-emerald-500" />
          Pending Go-Live Approvals ({goLiveApprovals.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {(goLiveApprovals || []).map((request, idx) => (
            <div 
              key={request.id || idx}
              className={`p-4 rounded-lg border ${isDark ? 'border-zinc-700 bg-zinc-900/50' : 'border-zinc-200 bg-zinc-50'}`}
              data-testid={`golive-item-${request.id}`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                      {request.employee_name || 'Unknown Employee'}
                    </span>
                    <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                      Go-Live Request
                    </Badge>
                  </div>
                  <div className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                    <span>Employee ID: <strong>{request.generated_employee_id || 'Pending'}</strong></span>
                    <span className="mx-2">•</span>
                    <span>Department: {request.department || 'N/A'}</span>
                  </div>
                  <div className={`text-xs mt-1 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                    Submitted by: {request.submitted_by || 'HR'} on {new Date(request.created_at).toLocaleDateString()}
                    {request.notes && <span className="ml-2">• Note: {request.notes}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onViewGoLive(request)}
                    className={isDark ? 'border-zinc-600' : ''}
                    data-testid={`view-golive-${request.id}`}
                  >
                    <Eye className="w-4 h-4 mr-1" /> View
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => onApproveGoLive(request)}
                    className="bg-emerald-600 hover:bg-emerald-700"
                    disabled={actionLoading}
                    data-testid={`approve-golive-${request.id}`}
                  >
                    <CheckCircle className="w-4 h-4 mr-1" /> Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => onRejectGoLive(request)}
                    disabled={actionLoading}
                    data-testid={`reject-golive-${request.id}`}
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

export default GoLiveApprovalsSection;
