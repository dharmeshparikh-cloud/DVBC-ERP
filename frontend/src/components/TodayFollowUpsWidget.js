import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { CalendarCheck, AlertTriangle, ChevronRight } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const ENTITY_LABELS = {
  lead: 'Lead', meeting: 'Meeting', pricing_plan: 'Pricing', sow: 'SOW',
  quotation: 'Quote', agreement: 'Agreement', payment: 'Payment',
  kickoff: 'Kickoff', project: 'Project',
};

const TodayFollowUpsWidget = () => {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const dk = theme === 'dark';

  const { data, isLoading } = useQuery({
    queryKey: ['follow-ups-dashboard-today'],
    queryFn: async () => {
      const res = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/api/follow-ups/dashboard/today`);
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
  });

  const items = data?.items || [];
  const overdueCount = data?.overdue_count || 0;
  const total = data?.total || 0;

  if (isLoading || total === 0) return null;

  const badgeColor = (type) => {
    const map = {
      lead: dk ? 'bg-purple-900/40 text-purple-300' : 'bg-purple-100 text-purple-700',
      meeting: dk ? 'bg-green-900/40 text-green-300' : 'bg-green-100 text-green-700',
      pricing_plan: dk ? 'bg-amber-900/40 text-amber-300' : 'bg-amber-100 text-amber-700',
      sow: dk ? 'bg-teal-900/40 text-teal-300' : 'bg-teal-100 text-teal-700',
      quotation: dk ? 'bg-indigo-900/40 text-indigo-300' : 'bg-indigo-100 text-indigo-700',
      agreement: dk ? 'bg-orange-900/40 text-orange-300' : 'bg-orange-100 text-orange-700',
      payment: dk ? 'bg-blue-900/40 text-blue-300' : 'bg-blue-100 text-blue-700',
      kickoff: dk ? 'bg-pink-900/40 text-pink-300' : 'bg-pink-100 text-pink-700',
      project: dk ? 'bg-emerald-900/40 text-emerald-300' : 'bg-emerald-100 text-emerald-700',
    };
    return map[type] || (dk ? 'bg-zinc-800 text-zinc-400' : 'bg-zinc-100 text-zinc-500');
  };

  return (
    <Card
      className={`shadow-none rounded-sm mb-6 ${
        dk
          ? `bg-[#1A1A1C] border-[#2A2A2E] ${overdueCount > 0 ? 'border-red-900/40' : ''}`
          : `border-zinc-200 ${overdueCount > 0 ? 'border-red-200' : ''}`
      }`}
      data-testid="today-follow-ups-widget"
    >
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between">
          <div className={`flex items-center gap-2 text-sm font-semibold ${dk ? 'text-zinc-100' : 'text-zinc-800'}`}>
            <CalendarCheck className="w-4 h-4" />
            Today's Follow-ups
            <Badge variant={overdueCount > 0 ? 'destructive' : 'secondary'} className="text-xs ml-1">{total}</Badge>
          </div>
          <button
            onClick={() => navigate('/follow-ups')}
            className={`text-xs flex items-center gap-0.5 cursor-pointer ${dk ? 'text-zinc-400 hover:text-zinc-200' : 'text-zinc-500 hover:text-zinc-700'}`}
            data-testid="view-all-follow-ups-link"
          >
            View all <ChevronRight className="w-3 h-3" />
          </button>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        {overdueCount > 0 && (
          <div className={`flex items-center gap-2 mb-3 p-2 rounded text-xs ${dk ? 'bg-red-950/30 text-red-400' : 'bg-red-100 text-red-700'}`}>
            <AlertTriangle className="w-3.5 h-3.5" />
            <span className="font-medium">{overdueCount} overdue follow-up{overdueCount > 1 ? 's' : ''} need attention</span>
          </div>
        )}

        <div className="space-y-2">
          {items.slice(0, 5).map(fu => (
            <div
              key={fu.id}
              onClick={() => navigate('/follow-ups')}
              data-testid={`dashboard-follow-up-${fu.id}`}
              className={`flex items-center justify-between p-2.5 rounded border cursor-pointer transition-colors ${
                fu.is_overdue
                  ? dk ? 'bg-red-950/20 border-red-900/30 hover:bg-red-950/30' : 'bg-red-50 border-red-200 hover:bg-red-100'
                  : dk ? 'bg-[#222226] border-[#2A2A2E] hover:bg-[#2A2A2E]' : 'bg-white border-zinc-200 hover:bg-zinc-50'
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${fu.is_overdue ? 'bg-red-500' : 'bg-yellow-500'}`} />
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className={`text-sm font-medium truncate ${dk ? 'text-zinc-100' : 'text-zinc-800'}`}>{fu.client_name}</span>
                    <span className={`px-1.5 py-0.5 text-[11px] rounded font-semibold ${badgeColor(fu.entity_type)}`}>
                      {ENTITY_LABELS[fu.entity_type] || fu.entity_type}
                    </span>
                  </div>
                  <p className={`text-xs truncate ${dk ? 'text-zinc-500' : 'text-zinc-400'}`}>{fu.last_follow_up_summary || fu.notes || ''}</p>
                </div>
              </div>
              <div className="text-right ml-3 shrink-0">
                <p className={`text-[10px] font-medium ${fu.is_overdue ? (dk ? 'text-red-400' : 'text-red-600') : (dk ? 'text-zinc-400' : 'text-zinc-500')}`}>
                  {fu.is_overdue ? `${fu.days_overdue}d overdue` : 'Today'}
                </p>
              </div>
            </div>
          ))}
        </div>

        {total > 5 && (
          <button
            onClick={() => navigate('/follow-ups')}
            className={`w-full mt-2 text-center text-xs py-1 cursor-pointer ${dk ? 'text-zinc-400 hover:text-zinc-200' : 'text-zinc-500 hover:text-zinc-700'}`}
          >
            + {total - 5} more follow-ups
          </button>
        )}
      </CardContent>
    </Card>
  );
};

export default TodayFollowUpsWidget;
