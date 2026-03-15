/**
 * FocusDealCard Component
 * 
 * Single deal focus view for action-driven workflow.
 * Design: Focus Stream (Zen Mode) concept
 * 
 * Reuses existing components:
 * - Card, CardContent, CardHeader
 * - Badge
 * - Button
 * - Tabs, TabsList, TabsTrigger
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Tabs, TabsList, TabsTrigger } from './ui/tabs';
import { 
  Building2, User, Mail, Phone, Calendar, 
  DollarSign, Clock, ChevronRight, MessageSquare,
  FileText, ArrowRight, CheckCircle
} from 'lucide-react';

// Stage colors matching existing SalesDashboard getStageColor function
const STAGE_COLORS = {
  lead: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-300', border: 'border-blue-300 dark:border-blue-700' },
  meeting: { bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-700 dark:text-purple-300', border: 'border-purple-300 dark:border-purple-700' },
  pricing: { bg: 'bg-orange-100 dark:bg-orange-900/30', text: 'text-orange-700 dark:text-orange-300', border: 'border-orange-300 dark:border-orange-700' },
  sow: { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-300', border: 'border-amber-300 dark:border-amber-700' },
  quote: { bg: 'bg-yellow-100 dark:bg-yellow-900/30', text: 'text-yellow-700 dark:text-yellow-300', border: 'border-yellow-300 dark:border-yellow-700' },
  agreement: { bg: 'bg-lime-100 dark:bg-lime-900/30', text: 'text-lime-700 dark:text-lime-300', border: 'border-lime-300 dark:border-lime-700' },
  payment: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-300', border: 'border-green-300 dark:border-green-700' },
  kickoff: { bg: 'bg-teal-100 dark:bg-teal-900/30', text: 'text-teal-700 dark:text-teal-300', border: 'border-teal-300 dark:border-teal-700' },
  complete: { bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-300 dark:border-emerald-700' }
};

const STAGES = ['lead', 'meeting', 'pricing', 'sow', 'quote', 'agreement', 'payment', 'kickoff', 'complete'];

const FocusDealCard = ({
  deal,
  currentStage = 'lead',
  onStageChange,
  onAction,
  showStageTabs = true,
  className = ''
}) => {
  const [selectedStage, setSelectedStage] = useState(currentStage);
  
  if (!deal) {
    return (
      <Card className={`bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 ${className}`}>
        <CardContent className="p-8 text-center">
          <div className="text-zinc-400 dark:text-zinc-500">
            <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-lg font-medium">No deal selected</p>
            <p className="text-sm">Select a deal from the pipeline to view details</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const stageColors = STAGE_COLORS[currentStage] || STAGE_COLORS.lead;
  const currentStageIndex = STAGES.indexOf(currentStage);
  const nextStage = currentStageIndex < STAGES.length - 1 ? STAGES[currentStageIndex + 1] : null;

  // Format currency
  const formatCurrency = (amount) => {
    if (!amount) return '₹0';
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(1)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(0)}K`;
    return `₹${amount.toLocaleString()}`;
  };

  // Calculate days in stage
  const daysInStage = deal.stage_entered_at 
    ? Math.floor((new Date() - new Date(deal.stage_entered_at)) / (1000 * 60 * 60 * 24))
    : 0;

  const handleStageTabClick = (stage) => {
    setSelectedStage(stage);
    onStageChange?.(stage);
  };

  return (
    <Card className={`bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 overflow-hidden ${className}`}>
      {/* Stage Tabs */}
      {showStageTabs && (
        <div className="border-b border-zinc-200 dark:border-zinc-800 overflow-x-auto">
          <Tabs value={selectedStage} onValueChange={handleStageTabClick}>
            <TabsList className="w-full justify-start bg-transparent rounded-none h-auto p-0">
              {STAGES.map((stage, index) => {
                const isActive = stage === currentStage;
                const isPast = index < currentStageIndex;
                const colors = STAGE_COLORS[stage];
                
                return (
                  <TabsTrigger
                    key={stage}
                    value={stage}
                    className={`
                      relative px-4 py-3 rounded-none border-b-2 text-xs uppercase tracking-wide font-medium
                      transition-all duration-200
                      ${isActive 
                        ? `${colors.border} ${colors.text} border-b-2` 
                        : isPast 
                          ? 'border-transparent text-zinc-400 dark:text-zinc-500'
                          : 'border-transparent text-zinc-400 dark:text-zinc-600'
                      }
                      hover:text-zinc-900 dark:hover:text-zinc-100
                      data-[state=active]:shadow-none
                    `}
                  >
                    {isPast && <CheckCircle className="h-3 w-3 mr-1 inline text-green-500" />}
                    {stage}
                  </TabsTrigger>
                );
              })}
            </TabsList>
          </Tabs>
        </div>
      )}

      {/* Deal Content */}
      <CardContent className="p-6">
        <div className="space-y-6">
          {/* Header: Company & Value */}
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className={`p-3 rounded-lg ${stageColors.bg}`}>
                <Building2 className={`h-6 w-6 ${stageColors.text}`} />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
                  {deal.company_name || deal.client_name || 'Unknown Company'}
                </h2>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">
                  {deal.product_interest || deal.service_type || 'General Inquiry'}
                </p>
                <Badge className={`mt-2 ${stageColors.bg} ${stageColors.text} border-0`}>
                  {currentStage.toUpperCase()}
                </Badge>
              </div>
            </div>
            
            <div className="text-right">
              <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-100">
                {formatCurrency(deal.deal_value || deal.expected_value || 0)}
              </p>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">Deal Value</p>
            </div>
          </div>

          {/* Contact Details */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg">
            <div className="flex items-center gap-3">
              <User className="h-4 w-4 text-zinc-400" />
              <div>
                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {deal.contact_person || `${deal.first_name || ''} ${deal.last_name || ''}`.trim() || 'No contact'}
                </p>
                <p className="text-xs text-zinc-500">Contact Person</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <Mail className="h-4 w-4 text-zinc-400" />
              <div>
                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
                  {deal.email || deal.contact_email || '-'}
                </p>
                <p className="text-xs text-zinc-500">Email</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <Phone className="h-4 w-4 text-zinc-400" />
              <div>
                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {deal.phone || deal.contact_phone || '-'}
                </p>
                <p className="text-xs text-zinc-500">Phone</p>
              </div>
            </div>
          </div>

          {/* Stage Info */}
          <div className="flex items-center justify-between p-4 border border-zinc-200 dark:border-zinc-700 rounded-lg">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-zinc-400" />
                <span className="text-sm text-zinc-600 dark:text-zinc-400">
                  <span className="font-semibold text-zinc-900 dark:text-zinc-100">{daysInStage}</span> days in stage
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-zinc-400" />
                <span className="text-sm text-zinc-600 dark:text-zinc-400">
                  Created: <span className="font-medium text-zinc-900 dark:text-zinc-100">
                    {deal.created_at ? new Date(deal.created_at).toLocaleDateString() : '-'}
                  </span>
                </span>
              </div>
            </div>

            {deal.assigned_to_name && (
              <Badge variant="outline" className="text-xs">
                Owner: {deal.assigned_to_name}
              </Badge>
            )}
          </div>

          {/* Notes */}
          {deal.notes && (
            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
              <div className="flex items-start gap-2">
                <MessageSquare className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-800 dark:text-amber-200">Notes</p>
                  <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">{deal.notes}</p>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => onAction?.('call', deal)}
            >
              <Phone className="h-4 w-4 mr-2" />
              Call
            </Button>
            
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => onAction?.('email', deal)}
            >
              <Mail className="h-4 w-4 mr-2" />
              Email
            </Button>
            
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => onAction?.('note', deal)}
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              Add Note
            </Button>

            {nextStage && (
              <Button
                className="flex-1 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200"
                onClick={() => onAction?.('move', { deal, nextStage })}
              >
                Move to {nextStage.charAt(0).toUpperCase() + nextStage.slice(1)}
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default FocusDealCard;
