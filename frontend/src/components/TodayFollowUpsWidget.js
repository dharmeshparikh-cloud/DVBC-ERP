import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { CalendarCheck, AlertTriangle, ChevronRight, Clock } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const ENTITY_LABELS = {
  lead: 'Lead', meeting: 'Meeting', pricing_plan: 'Pricing', sow: 'SOW',
  quotation: 'Quote', agreement: 'Agreement', payment: 'Payment',
  kickoff: 'Kickoff', project: 'Project',
};

const ENTITY_COLORS = {
  lead: 'bg-purple-100 text-purple-700', meeting: 'bg-green-100 text-green-700',
  pricing_plan: 'bg-amber-100 text-amber-700', sow: 'bg-teal-100 text-teal-700',
  quotation: 'bg-cyan-100 text-cyan-700', agreement: 'bg-orange-100 text-orange-700',
  payment: 'bg-blue-100 text-blue-700', kickoff: 'bg-pink-100 text-pink-700',
  project: 'bg-emerald-100 text-emerald-700',
};

const TodayFollowUpsWidget = () => {
  const navigate = useNavigate();
  const API = process.env.REACT_APP_BACKEND_URL;

  const { data, isLoading } = useQuery({
    queryKey: ['follow-ups-dashboard-today'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/follow-ups/dashboard/today`);
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });

  const items = data?.items || [];
  const overdueCount = data?.overdue_count || 0;
  const todayCount = data?.today_count || 0;
  const total = data?.total || 0;

  if (isLoading || total === 0) return null;

  return (
    <Card
      className={`border-zinc-200 shadow-none rounded-sm mb-6 ${overdueCount > 0 ? 'border-red-200 bg-red-50/30' : ''}`}
      data-testid="today-follow-ups-widget"
    >
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-zinc-800">
            <CalendarCheck className="w-4 h-4" />
            Today's Follow-ups
            <Badge variant={overdueCount > 0 ? 'destructive' : 'secondary'} className="text-xs ml-1">
              {total}
            </Badge>
          </div>
          <button
            onClick={() => navigate('/follow-ups')}
            className="text-xs text-zinc-500 hover:text-zinc-700 flex items-center gap-0.5 cursor-pointer"
            data-testid="view-all-follow-ups-link"
          >
            View all <ChevronRight className="w-3 h-3" />
          </button>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        {/* Quick stats */}
        {overdueCount > 0 && (
          <div className="flex items-center gap-2 mb-3 p-2 bg-red-100 rounded text-xs text-red-700">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span className="font-medium">{overdueCount} overdue follow-up{overdueCount > 1 ? 's' : ''} need attention</span>
          </div>
        )}

        {/* List items (max 5) */}
        <div className="space-y-2">
          {items.slice(0, 5).map(fu => (
            <div
              key={fu.id}
              className={`flex items-center justify-between p-2.5 rounded border cursor-pointer hover:shadow-sm transition-shadow ${fu.is_overdue ? 'bg-red-50 border-red-200' : 'bg-white border-zinc-200'}`}
              onClick={() => navigate('/follow-ups')}
              data-testid={`dashboard-follow-up-${fu.id}`}
            >
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${fu.is_overdue ? 'bg-red-500' : 'bg-yellow-500'}`} />
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium text-zinc-800 truncate">{fu.client_name}</span>
                    <span className={`px-1 py-0 text-[9px] rounded ${ENTITY_COLORS[fu.entity_type] || 'bg-zinc-100 text-zinc-500'}`}>
                      {ENTITY_LABELS[fu.entity_type] || fu.entity_type}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 truncate">{fu.last_follow_up_summary || fu.notes || ''}</p>
                </div>
              </div>
              <div className="text-right ml-3 shrink-0">
                <p className={`text-[10px] font-medium ${fu.is_overdue ? 'text-red-600' : 'text-zinc-500'}`}>
                  {fu.is_overdue ? `${fu.days_overdue}d overdue` : 'Today'}
                </p>
              </div>
            </div>
          ))}
        </div>

        {total > 5 && (
          <button
            onClick={() => navigate('/follow-ups')}
            className="w-full mt-2 text-center text-xs text-zinc-500 hover:text-zinc-700 py-1 cursor-pointer"
          >
            + {total - 5} more follow-ups
          </button>
        )}
      </CardContent>
    </Card>
  );
};

export default TodayFollowUpsWidget;
