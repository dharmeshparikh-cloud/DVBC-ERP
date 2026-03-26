import React, { useState } from 'react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { CalendarCheck } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

/**
 * Reusable Follow-up action button for any funnel stage list row.
 * 
 * Props:
 * - entityType: 'lead'|'meeting'|'pricing_plan'|'sow'|'quotation'|'agreement'|'payment'|'kickoff'|'project'
 * - entityId: the ID of the entity
 * - leadId: (optional) the lead ID for ownership linking
 * - clientName: display name for the client/company
 * - variant: 'icon' (just icon) | 'button' (icon + text) | 'small' (tiny icon)
 */
const FollowUpActionButton = ({ entityType, entityId, leadId, clientName, variant = 'icon' }) => {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [dueDate, setDueDate] = useState('');
  const [notes, setNotes] = useState('');
  const [priority, setPriority] = useState('medium');

  const createMutation = useMutation({
    mutationFn: async (data) => {
      const res = await axios.post(`${API}/follow-ups`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['follow-ups'] });
      queryClient.invalidateQueries({ queryKey: ['follow-ups-dashboard-today'] });
      toast.success(`Follow-up created for ${clientName || 'client'}`);
      setOpen(false);
      setDueDate('');
      setNotes('');
      setPriority('medium');
    },
    onError: (err) => {
      toast.error(err?.response?.data?.detail || 'Failed to create follow-up');
    },
  });

  const handleSubmit = () => {
    if (!dueDate) {
      toast.error('Please select a due date');
      return;
    }
    createMutation.mutate({
      entity_type: entityType,
      entity_id: entityId || 'manual',
      lead_id: leadId || (entityType === 'lead' ? entityId : undefined),
      client_name: clientName || 'Unknown',
      due_date: new Date(dueDate).toISOString(),
      notes,
      priority,
    });
  };

  const ENTITY_LABELS = {
    lead: 'Lead', meeting: 'Meeting', pricing_plan: 'Pricing', sow: 'SOW',
    quotation: 'Proforma Invoice', agreement: 'Agreement', payment: 'Payment',
    kickoff: 'Kickoff', project: 'Project',
  };

  return (
    <>
      {variant === 'button' ? (
        <Button
          onClick={(e) => { e.stopPropagation(); setOpen(true); }}
          variant="outline"
          size="sm"
          className="gap-1 text-xs"
          data-testid={`create-followup-${entityType}-${entityId}`}
        >
          <CalendarCheck className="w-3.5 h-3.5" /> Follow-up
        </Button>
      ) : (
        <Button
          onClick={(e) => { e.stopPropagation(); setOpen(true); }}
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          title="Schedule Follow-up"
          data-testid={`create-followup-${entityType}-${entityId}`}
        >
          <CalendarCheck className={variant === 'small' ? 'w-3.5 h-3.5 text-zinc-500' : 'w-4 h-4 text-zinc-600'} />
        </Button>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">Schedule Follow-up</DialogTitle>
            <DialogDescription>
              {clientName && <span className="font-medium">{clientName}</span>}
              {' — '}
              <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-100">{ENTITY_LABELS[entityType] || entityType} Stage</span>
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label className="text-xs">Due Date *</Label>
              <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} data-testid="followup-due-date" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Notes</Label>
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Follow-up details..." rows={2} className="w-full px-3 py-2 rounded border border-zinc-200 text-sm" data-testid="followup-notes" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Priority</Label>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger data-testid="followup-priority"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2 pt-1">
              <Button variant="outline" onClick={() => setOpen(false)} className="flex-1" size="sm">Cancel</Button>
              <Button onClick={handleSubmit} disabled={!dueDate || createMutation.isPending} className="flex-1 bg-zinc-950 text-white" size="sm" data-testid="confirm-followup-create">
                {createMutation.isPending ? 'Creating...' : 'Create'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default FollowUpActionButton;
