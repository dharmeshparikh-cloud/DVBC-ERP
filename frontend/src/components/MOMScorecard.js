import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { 
  FileText, CheckCircle, Clock, AlertCircle, 
  Users, TrendingUp, Send, ArrowRight 
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const MOMScorecard = ({ period = 'month', isManager = false }) => {
  const navigate = useNavigate();
  
  const { data: momData, isLoading } = useQuery({
    queryKey: ['mom-scorecard', period],
    queryFn: async () => {
      const response = await axios.get(`${API}/api/analytics/mom-scorecard?period=${period}`);
      return response.data;
    },
    staleTime: 3 * 60 * 1000, // 3 minutes
  });

  if (isLoading) {
    return (
      <Card className="border-zinc-200" data-testid="mom-scorecard-loading">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            MOM Scorecard
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-zinc-100 rounded w-3/4"></div>
            <div className="h-4 bg-zinc-100 rounded w-1/2"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const summary = momData?.summary || {};
  const pendingMoms = momData?.pending_moms || [];
  const topPerformers = momData?.top_performers || [];

  const getCompletionColor = (rate) => {
    if (rate >= 90) return 'text-green-600 bg-green-100';
    if (rate >= 70) return 'text-amber-600 bg-amber-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <Card className="border-zinc-200" data-testid="mom-scorecard">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            MOM Scorecard
          </CardTitle>
          <Badge variant="outline" className="text-xs">
            {period === 'week' ? 'This Week' : period === 'month' ? 'This Month' : period === 'quarter' ? 'This Quarter' : 'This Year'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-colors" onClick={() => navigate('/sales-meetings')}>
            <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{summary.total_meetings || 0}</div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400">Total Meetings</div>
          </div>
          <div className="text-center p-3 bg-green-500/10 dark:bg-green-500/20 rounded-lg cursor-pointer hover:bg-green-500/20 dark:hover:bg-green-500/30 transition-colors" onClick={() => navigate('/sales-meetings?status=completed')}>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">{summary.meetings_with_mom || 0}</div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400">MOM Recorded</div>
          </div>
          <div className="text-center p-3 bg-amber-500/10 dark:bg-amber-500/20 rounded-lg cursor-pointer hover:bg-amber-500/20 dark:hover:bg-amber-500/30 transition-colors" onClick={() => navigate('/sales-meetings?status=pending')}>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">{summary.meetings_without_mom || 0}</div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400">Pending MOM</div>
          </div>
        </div>

        {/* Completion Rate */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-600 dark:text-zinc-400">MOM Completion Rate</span>
            <span className={`text-sm font-semibold px-2 py-0.5 rounded ${getCompletionColor(summary.mom_completion_rate || 0)}`}>
              {summary.mom_completion_rate || 0}%
            </span>
          </div>
          <Progress value={summary.mom_completion_rate || 0} className="h-2" />
        </div>

        {/* Additional Metrics */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="flex items-center gap-2 p-2 bg-zinc-50 dark:bg-zinc-800/50 rounded">
            <Clock className="w-4 h-4 text-blue-500" />
            <span className="text-zinc-600 dark:text-zinc-400">Timely MOMs:</span>
            <span className="font-medium">{summary.timely_moms || 0}</span>
          </div>
          <div className="flex items-center gap-2 p-2 bg-zinc-50 dark:bg-zinc-800/50 rounded">
            <Send className="w-4 h-4 text-green-500" />
            <span className="text-zinc-600 dark:text-zinc-400">Sent to Client:</span>
            <span className="font-medium">{summary.mom_sent_to_client || 0}</span>
          </div>
        </div>

        {/* Pending MOMs List */}
        {pendingMoms.length > 0 && (
          <div className="border-t dark:border-zinc-700 pt-3">
            <h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-500" />
              Pending MOMs ({momData?.pending_mom_count || 0})
            </h4>
            <div className="space-y-1.5">
              {(pendingMoms || []).map((meeting, idx) => (
                <Link 
                  key={meeting.id || idx}
                  to={`/leads?lead_id=${meeting.lead_id}`}
                  className="flex items-center justify-between p-2 bg-amber-500/10 dark:bg-amber-500/20 rounded hover:bg-amber-500/20 dark:hover:bg-amber-500/30 transition-colors text-sm"
                >
                  <div>
                    <span className="font-medium text-zinc-800 dark:text-zinc-200">{meeting.company || meeting.title}</span>
                    {meeting.meeting_date && (
                      <span className="text-xs text-zinc-500 ml-2">
                        {new Date(meeting.meeting_date).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  <ArrowRight className="w-4 h-4 text-amber-600" />
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Top Performers (Manager View) */}
        {isManager && topPerformers.length > 0 && (
          <div className="border-t pt-3">
            <h4 className="text-sm font-medium text-zinc-700 mb-2 flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-500" />
              Top MOM Performers
            </h4>
            <div className="space-y-1.5">
              {(topPerformers || []).map((performer, idx) => (
                <div key={performer.employee_id || idx} className="flex items-center justify-between p-2 bg-zinc-50 rounded text-sm">
                  <div className="flex items-center gap-2">
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-medium ${
                      idx === 0 ? 'bg-yellow-100 text-yellow-700' :
                      idx === 1 ? 'bg-zinc-200 text-zinc-700' :
                      idx === 2 ? 'bg-amber-100 text-amber-700' :
                      'bg-zinc-100 text-zinc-600'
                    }`}>
                      {idx + 1}
                    </span>
                    <span className="font-medium">{performer.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-500">{performer.moms_recorded}/{performer.total_meetings}</span>
                    <Badge className={getCompletionColor(performer.completion_rate)}>
                      {performer.completion_rate}%
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* View Full Report Link - Manager Only */}
        {isManager && (
          <div className="border-t pt-3">
            <Link 
              to="/manager-mom-review" 
              className="flex items-center justify-center gap-2 p-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors text-sm font-medium"
              data-testid="view-mom-review-link"
            >
              <FileText className="w-4 h-4" />
              View Full MOM Report & Download PDF
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default MOMScorecard;
