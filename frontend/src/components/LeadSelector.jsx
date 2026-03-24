/**
 * LeadSelector Component
 * 
 * SSOT (Single Source of Truth) Component
 * Searchable dropdown for selecting a lead as master record.
 * Auto-fills and locks master fields in downstream forms.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from './ui/command';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent } from './ui/card';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { 
  Search, Building2, User, Mail, Phone, MapPin, 
  ChevronDown, Check, Lock, ExternalLink, AlertTriangle
} from 'lucide-react';
import { cn } from '../lib/utils';
import { toast } from 'sonner';
import debounce from 'lodash/debounce';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * LeadSelector - Searchable lead dropdown with SSOT auto-fill
 * 
 * @param {string} value - Selected lead ID
 * @param {function} onChange - Callback when lead is selected
 * @param {function} onMasterDataLoad - Callback with master data for auto-filling
 * @param {boolean} disabled - Whether selector is disabled
 * @param {string} placeholder - Placeholder text
 * @param {boolean} required - Whether selection is required
 * @param {string} funnelStage - Required funnel stage: 'any', 'has_meeting', 'has_pricing_plan', 'has_quotation'
 * @param {string} noEligibleMessage - Message when no eligible leads found
 */
const LeadSelector = ({
  value,
  onChange,
  onMasterDataLoad,
  disabled = false,
  placeholder = "Select a lead...",
  required = false,
  className = "",
  funnelStage = "any",
  noEligibleMessage = "No eligible leads found"
}) => {
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLead, setSelectedLead] = useState(null);

  // Search leads with funnel stage filter
  const { data: searchResults, isLoading: searchLoading, refetch: searchLeads } = useQuery({
    queryKey: ['lead-search', searchQuery, funnelStage],
    queryFn: async () => {
      const response = await axios.get(`${API}/api/leads/ssot/search`, {
        params: { q: searchQuery, limit: 20, funnel_stage: funnelStage }
      });
      return response.data;
    },
    enabled: open
  });

  // Fetch master data when lead is selected
  const { data: masterData, isLoading: masterLoading } = useQuery({
    queryKey: ['lead-master-data', value],
    queryFn: async () => {
      const response = await axios.get(`${API}/api/leads/ssot/master-data/${value}`);
      return response.data;
    },
    enabled: !!value,
    onSuccess: (data) => {
      if (onMasterDataLoad) {
        onMasterDataLoad(data.master_data);
      }
    }
  });

  // Debounced search
  const debouncedSearch = useCallback(
    debounce((query) => {
      setSearchQuery(query);
    }, 300),
    []
  );

  // Update selected lead display when value changes
  useEffect(() => {
    if (value && masterData?.master_data) {
      setSelectedLead({
        id: value,
        company: masterData.master_data.company,
        contact: masterData.master_data.contact_person,
        email: masterData.master_data.email
      });
    }
  }, [value, masterData]);

  const handleSelect = (lead) => {
    setSelectedLead(lead);
    onChange(lead.id);
    setOpen(false);
    toast.success(`Lead selected: ${lead.company}`);
  };

  const leads = searchResults?.leads || [];

  return (
    <div className={cn("space-y-2", className)} data-testid="lead-selector">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled}
            className={cn(
              "w-full justify-between text-left font-normal",
              !selectedLead && "text-muted-foreground"
            )}
            data-testid="lead-selector-trigger"
          >
            {selectedLead ? (
              <span className="flex items-center gap-2 truncate">
                <Building2 className="h-4 w-4 shrink-0" />
                <span className="truncate">{selectedLead.company}</span>
                <span className="text-xs text-muted-foreground truncate">
                  - {selectedLead.contact}
                </span>
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Search className="h-4 w-4" />
                {placeholder}
              </span>
            )}
            <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[400px] p-0" align="start">
          <Command>
            <CommandInput 
              placeholder="Search by company, name, or email..." 
              onValueChange={debouncedSearch}
              data-testid="lead-search-input"
            />
            <CommandList>
              {searchLoading ? (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  Searching...
                </div>
              ) : leads.length === 0 ? (
                <div className="p-4 text-center">
                  <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto mb-2" />
                  <p className="text-sm font-medium text-zinc-700">{noEligibleMessage}</p>
                  {funnelStage === "has_pricing_plan" && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Create a Pricing Plan for your leads first
                    </p>
                  )}
                  {funnelStage === "has_quotation" && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Create a Quotation for your leads first
                    </p>
                  )}
                  {funnelStage === "has_meeting" && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Record a meeting with MOM for your leads first
                    </p>
                  )}
                </div>
              ) : (
                <CommandGroup heading={`Leads ${searchResults?.filtered ? '(Eligible)' : ''}`}>
                  {(leads || []).map((lead) => (
                    <CommandItem
                      key={lead.id}
                      value={lead.id}
                      onSelect={() => handleSelect(lead)}
                      className="flex flex-col items-start gap-1 cursor-pointer"
                      data-testid={`lead-option-${lead.id}`}
                    >
                      <div className="flex items-center gap-2 w-full">
                        {value === lead.id && (
                          <Check className="h-4 w-4 text-green-500" />
                        )}
                        <Building2 className="h-4 w-4 text-zinc-500" />
                        <span className="font-medium">{lead.company}</span>
                        <Badge variant="outline" className="ml-auto text-xs">
                          {lead.status}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground pl-6">
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {lead.contact}
                        </span>
                        {lead.city && (
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {lead.city}
                          </span>
                        )}
                      </div>
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {/* Selected Lead Info */}
      {selectedLead && masterData?.master_data && (
        <Card className="bg-zinc-50 dark:bg-zinc-800/50 border-dashed" data-testid="lead-master-info">
          <CardContent className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <Lock className="h-4 w-4 text-amber-500" />
              <span className="text-xs font-medium text-amber-700 dark:text-amber-400">
                Master Fields (Auto-filled & Locked)
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center gap-1">
                <Building2 className="h-3 w-3 text-zinc-400" />
                <span className="text-zinc-600 dark:text-zinc-300">{masterData.master_data.company}</span>
              </div>
              <div className="flex items-center gap-1">
                <User className="h-3 w-3 text-zinc-400" />
                <span className="text-zinc-600 dark:text-zinc-300">{masterData.master_data.contact_person}</span>
              </div>
              <div className="flex items-center gap-1">
                <Mail className="h-3 w-3 text-zinc-400" />
                <span className="text-zinc-600 dark:text-zinc-300">{masterData.master_data.email || 'N/A'}</span>
              </div>
              <div className="flex items-center gap-1">
                <Phone className="h-3 w-3 text-zinc-400" />
                <span className="text-zinc-600 dark:text-zinc-300">{masterData.master_data.phone || 'N/A'}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

/**
 * LeadSourceSelect - Dropdown for lead source selection
 */
export const LeadSourceSelect = ({
  value,
  onChange,
  disabled = false,
  className = ""
}) => {
  const { data: sources } = useQuery({
    queryKey: ['lead-sources'],
    queryFn: async () => {
      const response = await axios.get(`${API}/api/leads/ssot/lead-sources`);
      return response.data.sources;
    },
    staleTime: Infinity
  });

  return (
    <select
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className={cn(
        "w-full px-3 py-2 border rounded-md bg-white dark:bg-zinc-900",
        "border-zinc-200 dark:border-zinc-700",
        "focus:outline-none focus:ring-2 focus:ring-zinc-400",
        disabled && "opacity-50 cursor-not-allowed",
        className
      )}
      data-testid="lead-source-select"
    >
      <option value="">Select source...</option>
      {sources?.map((source) => (
        <option key={source.id} value={source.id}>
          {source.label}
        </option>
      ))}
    </select>
  );
};

/**
 * DuplicateLeadWarning - Shows warning when duplicate detected
 */
export const DuplicateLeadWarning = ({
  duplicates,
  onUseDuplicate,
  onContinueAnyway
}) => {
  if (!duplicates || duplicates.length === 0) return null;

  return (
    <Card className="border-amber-300 bg-amber-50 dark:bg-amber-900/20" data-testid="duplicate-warning">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-medium text-amber-800 dark:text-amber-200">
              Potential Duplicate Found
            </h4>
            <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
              A lead with similar details already exists:
            </p>
            
            {(duplicates || []).map((dup, idx) => (
              <div key={idx} className="mt-2 p-2 bg-white dark:bg-zinc-800 rounded border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">
                      {dup.existing_lead.company}
                    </p>
                    <p className="text-xs text-zinc-500">
                      Match: {dup.field} = {dup.value}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onUseDuplicate(dup.existing_lead.id)}
                    data-testid={`use-existing-${idx}`}
                  >
                    <ExternalLink className="h-3 w-3 mr-1" />
                    Use This
                  </Button>
                </div>
              </div>
            ))}

            <div className="mt-3 flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={onContinueAnyway}
                data-testid="continue-anyway-btn"
              >
                Create Anyway
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

/**
 * LockedField - Displays a locked/read-only field from SSOT
 */
export const LockedField = ({
  label,
  value,
  icon: Icon = Lock
}) => {
  return (
    <div className="space-y-1" data-testid={`locked-field-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <Label className="flex items-center gap-1 text-zinc-500">
        <Lock className="h-3 w-3" />
        {label}
      </Label>
      <div className="flex items-center gap-2 px-3 py-2 bg-zinc-100 dark:bg-zinc-800 rounded-md border border-zinc-200 dark:border-zinc-700">
        {Icon && <Icon className="h-4 w-4 text-zinc-400" />}
        <span className="text-sm text-zinc-600 dark:text-zinc-300">
          {value || 'Not set'}
        </span>
      </div>
    </div>
  );
};

export default LeadSelector;
