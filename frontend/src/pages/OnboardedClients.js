import React, { useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import {
  Building2, Eye, Phone, Mail, DollarSign,
  CheckCircle, Search, ArrowLeft
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';

const FUNNEL_LABELS = {
  closed: 'Complete',
  closed_won: 'Won',
  kickoff: 'Kickoff',
};

const FUNNEL_COLORS = {
  closed: 'bg-emerald-100 text-emerald-700',
  closed_won: 'bg-blue-100 text-blue-700',
  kickoff: 'bg-violet-100 text-violet-700',
};

export default function OnboardedClients() {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [search, setSearch] = useState('');

  const { data: clients, isLoading } = useQuery({
    queryKey: ['onboarded-clients'],
    queryFn: async () => {
      const res = await axios.get(`${API}/leads?page_size=200`);
      const allLeads = res.data?.data || [];
      return allLeads.filter(l => ['closed', 'closed_won', 'kickoff'].includes(l.status));
    },
    staleTime: 3 * 60 * 1000,
  });

  const filtered = (clients || []).filter(c => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.company?.toLowerCase().includes(q) ||
      c.first_name?.toLowerCase().includes(q) ||
      c.last_name?.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q)
    );
  });

  if (isLoading) {
    return <div className="flex items-center justify-center h-96 text-zinc-500">Loading...</div>;
  }

  return (
    <div data-testid="onboarded-clients-page">
      <div className="mb-6">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate('/leads')}
          className="-ml-2 mb-3 text-zinc-500 hover:text-zinc-900"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          Back to Leads
        </Button>
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-1">
          Onboarded Clients
        </h1>
        <p className="text-zinc-500 text-sm">
          Leads that completed the sales funnel. View-only access to full funnel details.
        </p>
      </div>

      <div className="flex items-center gap-4 mb-6">
        <div className="relative w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, company, email..."
            className="pl-10 rounded-sm"
            data-testid="onboarded-search"
          />
        </div>
        <span className="text-sm text-zinc-400">{filtered.length} client{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-16 text-zinc-500">
          <CheckCircle className="w-12 h-12 mx-auto mb-3 text-zinc-300" />
          <p className="font-medium">No onboarded clients yet</p>
          <p className="text-sm mt-1">Leads that complete the full 9-step sales funnel will appear here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(lead => (
            <Card
              key={lead.id}
              className="border-zinc-200 shadow-none rounded-sm hover:border-emerald-300 transition-colors"
              data-testid={`onboarded-client-${lead.id}`}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-sm bg-emerald-50 flex items-center justify-center">
                      <Building2 className="w-5 h-5 text-emerald-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-zinc-950 text-sm">
                        {lead.company || `${lead.first_name} ${lead.last_name}`}
                      </h3>
                      <p className="text-xs text-zinc-500">{lead.first_name} {lead.last_name}</p>
                    </div>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${FUNNEL_COLORS[lead.status] || 'bg-zinc-100 text-zinc-600'}`}>
                    {FUNNEL_LABELS[lead.status] || lead.status}
                  </span>
                </div>

                <div className="space-y-1.5 text-xs text-zinc-500 mb-4">
                  {lead.email && (
                    <div className="flex items-center gap-2"><Mail className="w-3 h-3" />{lead.email}</div>
                  )}
                  {lead.phone && (
                    <div className="flex items-center gap-2"><Phone className="w-3 h-3" />{lead.phone}</div>
                  )}
                  {lead.deal_value && (
                    <div className="flex items-center gap-2">
                      <DollarSign className="w-3 h-3" />
                      Deal: {Number(lead.deal_value).toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}
                    </div>
                  )}
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  className="w-full rounded-sm border-zinc-200 text-xs h-8"
                  onClick={() => navigate(`/sales-funnel-onboarding?leadId=${lead.id}&readOnly=true`)}
                  data-testid={`view-funnel-${lead.id}`}
                >
                  <Eye className="w-3 h-3 mr-1.5" />
                  View Funnel
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
