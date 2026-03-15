/**
 * useFunnelEligibility Hook
 * 
 * Checks if there are eligible leads for each funnel stage.
 * Used to enable/disable Create buttons based on funnel progression.
 */

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Check if leads exist for a specific funnel stage
 * @param {string} funnelStage - 'has_meeting', 'has_pricing_plan', 'has_quotation'
 * @returns {{ hasEligibleLeads: boolean, isLoading: boolean, count: number }}
 */
export const useFunnelEligibility = (funnelStage) => {
  const { data, isLoading } = useQuery({
    queryKey: ['funnel-eligibility', funnelStage],
    queryFn: async () => {
      const response = await axios.get(`${API}/api/leads/ssot/search`, {
        params: { q: '', limit: 1, funnel_stage: funnelStage }
      });
      return response.data;
    },
    staleTime: 30 * 1000, // Cache for 30 seconds
    retry: 1
  });

  return {
    hasEligibleLeads: (data?.total || 0) > 0,
    isLoading,
    count: data?.total || 0
  };
};

/**
 * Get tooltip message for disabled Create button
 * @param {string} funnelStage 
 * @returns {string}
 */
export const getFunnelTooltip = (funnelStage) => {
  const messages = {
    'has_meeting': 'No leads with meetings (MOM) found. Record a meeting first.',
    'has_pricing_plan': 'No leads with pricing plans found. Create a Pricing Plan first.',
    'has_quotation': 'No leads with quotations found. Create a Quotation first.'
  };
  return messages[funnelStage] || 'No eligible leads found.';
};

export default useFunnelEligibility;
