/**
 * useSOWsByProject.js - Data Governance Hooks Library
 * 
 * Phase 1: ConsultingMeetings - SOWs, Projects, Meeting Types
 * Phase 2: All Modules - Clients, Employees, Categories, etc.
 * 
 * Fetches data with normalization layer for consistent field naming.
 * Used with GovernedDropdown for loading/error/empty states.
 */

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const getHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json'
});

// ═══════════════════════════════════════════════════════════════════
// TRANSFORMERS - Normalize API responses for consistent dropdown usage
// ═══════════════════════════════════════════════════════════════════

// Step 4: Transformer — normalizes SOW response for consistent dropdown usage
const normalizeSOW = (sow) => ({
  ...sow,
  // Ensure `name` always exists (backend returns `title`)
  name: sow.name || sow.title || sow.client_name || `SOW-${(sow.id || '').slice(0, 8)}`,
  // Ensure `id` always exists
  id: sow.id || sow._id || '',
  // Preserve original fields untouched
  project_id: sow.project_id || sow.projectId || '',
  client_id: sow.client_id || sow.clientId || '',
  client_name: sow.client_name || '',
  status: sow.status || 'unknown',
});

// Step 4: Transformer — normalizes Project response
export const normalizeProject = (project) => ({
  ...project,
  id: project.id || project._id || '',
  name: project.name || project.project_name || project.title || 'Unnamed Project',
  client_id: project.client_id || project.clientId || '',
  client_name: project.client_name || project.company_name || 'Unknown Client',
  status: project.status || 'unknown',
});

// Step 4: Transformer — normalizes Client response
export const normalizeClient = (client) => ({
  ...client,
  id: client.id || client._id || '',
  name: client.name || client.company_name || client.client_name || 'Unknown Client',
  client_id: client.client_id || client.id || '',
});

// Phase 2: Transformer — normalizes Employee response
export const normalizeEmployee = (employee) => ({
  ...employee,
  id: employee.id || employee.user_id || employee._id || '',
  name: employee.full_name || `${employee.first_name || ''} ${employee.last_name || ''}`.trim() || employee.name || 'Unknown',
  employee_id: employee.employee_id || employee.emp_id || '',
  department: employee.department || '',
  designation: employee.designation || employee.role || '',
  email: employee.email || '',
});

// Phase 2: Transformer — normalizes Lead response
export const normalizeLead = (lead) => ({
  ...lead,
  id: lead.id || lead._id || '',
  name: `${lead.first_name || ''} ${lead.last_name || ''}`.trim() || lead.company || 'Unknown Lead',
  company: lead.company || '',
  status: lead.status || 'new',
  email: lead.email || '',
});

// Phase 2: Transformer — normalizes Expense Category
export const normalizeCategory = (category) => ({
  id: category.id || category.code || category.name?.toLowerCase().replace(/\s+/g, '_') || '',
  name: category.name || category.label || category,
  code: category.code || category.name?.toLowerCase().replace(/\s+/g, '_') || '',
});

/**
 * Step 3: NEW hook — useSOWsByProject(project_id)
 * Fetches SOWs for a specific project from server-side endpoint.
 * Falls back to global SOW list + client-side filter if per-project endpoint fails.
 */
export const useSOWsByProject = (projectId, options = {}) => {
  return useQuery({
    queryKey: ['sows-by-project', projectId],
    queryFn: async () => {
      if (!projectId) return [];
      
      try {
        // Try project-specific SOW endpoint first (server-side filter)
        const res = await axios.get(
          `${API}/api/enhanced-sow/project/${projectId}/sow`,
          { headers: getHeaders() }
        );
        // Handle different response shapes: array, {sow: ...}, {items: [...]}, etc
        let raw = [];
        if (Array.isArray(res.data)) {
          raw = res.data;
        } else if (res.data?.sow) {
          // Single SOW wrapped: {sow: {...}, can_edit, ...}
          raw = [res.data.sow];
        } else if (res.data?.items) {
          raw = res.data.items;
        } else if (res.data?.sows) {
          raw = res.data.sows;
        }
        console.log(`[useSOWsByProject] project=${projectId} → ${raw.length} SOWs (server-side)`);
        return raw.map(normalizeSOW);
      } catch (err) {
        // Fallback: fetch all SOWs and filter client-side
        console.warn(`[useSOWsByProject] Server-side endpoint failed (${err.response?.status}), falling back to global + filter`);
        try {
          const res = await axios.get(`${API}/api/enhanced-sow`, { headers: getHeaders() });
          const all = Array.isArray(res.data) ? res.data : (res.data?.items || res.data?.sows || []);
          const filtered = all.filter(s => s.project_id === projectId);
          console.log(`[useSOWsByProject] project=${projectId} → ${filtered.length}/${all.length} SOWs (client-side fallback)`);
          return filtered.map(normalizeSOW);
        } catch (fallbackErr) {
          console.error(`[useSOWsByProject] Both endpoints failed`, fallbackErr);
          return [];
        }
      }
    },
    enabled: !!projectId,
    staleTime: 3 * 60 * 1000,
    ...options
  });
};

/**
 * Normalized project list hook — wrapper that adds transformer.
 * DOES NOT replace existing useProjects. Additive only.
 */
export const useNormalizedProjects = (options = {}) => {
  return useQuery({
    queryKey: ['normalized-projects'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/projects`, { headers: getHeaders() });
      const raw = Array.isArray(res.data) ? res.data : (res.data?.items || res.data?.projects || []);
      console.log(`[useNormalizedProjects] → ${raw.length} projects loaded`);
      return raw.map(normalizeProject);
    },
    staleTime: 5 * 60 * 1000,
    ...options
  });
};

/**
 * Normalized meeting types hook.
 * DOES NOT replace existing inline fetch. Additive only.
 */
export const useNormalizedMeetingTypes = (options = {}) => {
  return useQuery({
    queryKey: ['normalized-meeting-types'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/masters/meeting-types`, { headers: getHeaders() });
      const raw = Array.isArray(res.data) ? res.data : [];
      console.log(`[useNormalizedMeetingTypes] → ${raw.length} meeting types loaded`);
      return raw;
    },
    staleTime: 10 * 60 * 1000,
    ...options
  });
};


// ═══════════════════════════════════════════════════════════════════
// PHASE 2: ADDITIONAL NORMALIZED HOOKS
// ═══════════════════════════════════════════════════════════════════

/**
 * Normalized clients hook - for Client dropdowns across modules.
 */
export const useNormalizedClients = (options = {}) => {
  return useQuery({
    queryKey: ['normalized-clients'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/clients`, { headers: getHeaders() });
      const raw = Array.isArray(res.data) ? res.data : (res.data?.items || res.data?.clients || []);
      console.log(`[useNormalizedClients] → ${raw.length} clients loaded`);
      return raw.map(normalizeClient);
    },
    staleTime: 5 * 60 * 1000,
    ...options
  });
};

/**
 * Normalized employees hook - for Employee/Assigned To dropdowns.
 */
export const useNormalizedEmployees = (options = {}) => {
  return useQuery({
    queryKey: ['normalized-employees'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/employees-dropdown`, { headers: getHeaders() });
      const raw = Array.isArray(res.data) ? res.data : (res.data?.items || res.data?.employees || []);
      console.log(`[useNormalizedEmployees] → ${raw.length} employees loaded`);
      return raw.map(normalizeEmployee);
    },
    staleTime: 5 * 60 * 1000,
    ...options
  });
};

/**
 * Normalized leads hook - for Lead selection dropdowns.
 */
export const useNormalizedLeads = (status = '', options = {}) => {
  return useQuery({
    queryKey: ['normalized-leads', status],
    queryFn: async () => {
      const url = status ? `${API}/api/leads?status=${status}` : `${API}/api/leads`;
      const res = await axios.get(url, { headers: getHeaders() });
      const raw = Array.isArray(res.data) ? res.data : (res.data?.items || res.data?.leads || []);
      console.log(`[useNormalizedLeads] → ${raw.length} leads loaded`);
      return raw.map(normalizeLead);
    },
    staleTime: 3 * 60 * 1000,
    ...options
  });
};

/**
 * Expense categories hook - predefined categories with normalization.
 */
export const useExpenseCategories = (options = {}) => {
  // Predefined expense categories (can be fetched from API if needed)
  const categories = [
    { id: 'travel', name: 'Travel', code: 'travel' },
    { id: 'local_conveyance', name: 'Local Conveyance', code: 'local_conveyance' },
    { id: 'food', name: 'Food', code: 'food' },
    { id: 'accommodation', name: 'Accommodation', code: 'accommodation' },
    { id: 'office_supplies', name: 'Office Supplies', code: 'office_supplies' },
    { id: 'communication', name: 'Communication', code: 'communication' },
    { id: 'client_entertainment', name: 'Client Entertainment', code: 'client_entertainment' },
    { id: 'other', name: 'Other', code: 'other' },
  ];
  
  return useQuery({
    queryKey: ['expense-categories'],
    queryFn: async () => {
      // Try to fetch from API first, fallback to predefined
      try {
        const res = await axios.get(`${API}/api/masters/expense-categories`, { headers: getHeaders() });
        if (res.data && Array.isArray(res.data) && res.data.length > 0) {
          return res.data.map(normalizeCategory);
        }
      } catch {
        // API doesn't exist, use predefined
      }
      return categories;
    },
    staleTime: 30 * 60 * 1000, // 30 minutes - categories rarely change
    ...options
  });
};

/**
 * Leave types hook - for leave management.
 */
export const useLeaveTypes = (options = {}) => {
  return useQuery({
    queryKey: ['leave-types'],
    queryFn: async () => {
      try {
        const res = await axios.get(`${API}/api/masters/leave-types`, { headers: getHeaders() });
        if (res.data && Array.isArray(res.data)) {
          return res.data.map(lt => ({
            id: lt.id || lt.code || lt.name?.toLowerCase().replace(/\s+/g, '_'),
            name: lt.name || lt.label,
            code: lt.code || lt.name?.toLowerCase().replace(/\s+/g, '_'),
            ...lt
          }));
        }
      } catch {
        // Fallback to common leave types
      }
      return [
        { id: 'casual', name: 'Casual Leave', code: 'casual' },
        { id: 'sick', name: 'Sick Leave', code: 'sick' },
        { id: 'earned', name: 'Earned Leave', code: 'earned' },
        { id: 'maternity', name: 'Maternity Leave', code: 'maternity' },
        { id: 'paternity', name: 'Paternity Leave', code: 'paternity' },
        { id: 'unpaid', name: 'Leave Without Pay', code: 'unpaid' },
        { id: 'compensatory', name: 'Compensatory Off', code: 'compensatory' },
      ];
    },
    staleTime: 30 * 60 * 1000,
    ...options
  });
};

/**
 * Industry options hook - for lead/client creation.
 */
export const useIndustryOptions = (options = {}) => {
  const industries = [
    'Manufacturing', 'IT/Software', 'Healthcare', 'Finance/Banking',
    'Retail', 'Education', 'Real Estate', 'Consulting', 'Logistics',
    'Hospitality', 'Agriculture', 'Energy', 'Telecom', 'Automotive',
    'Pharma', 'FMCG', 'Construction', 'Media', 'Government', 'Other'
  ];
  
  return useQuery({
    queryKey: ['industry-options'],
    queryFn: async () => {
      try {
        const res = await axios.get(`${API}/api/masters/industries`, { headers: getHeaders() });
        if (res.data && Array.isArray(res.data) && res.data.length > 0) {
          return res.data.map(i => ({
            id: i.id || i.code || i.name?.toLowerCase().replace(/\s+/g, '_'),
            name: i.name || i.label || i,
          }));
        }
      } catch {
        // Use predefined
      }
      return industries.map(name => ({ id: name.toLowerCase().replace(/[\s/]+/g, '_'), name }));
    },
    staleTime: 30 * 60 * 1000,
    ...options
  });
};

/**
 * Lead sources hook - for lead creation.
 */
export const useLeadSources = (options = {}) => {
  const sources = [
    'Referral', 'Website', 'LinkedIn', 'Cold Call', 'Event',
    'Partner', 'Advertisement', 'Social Media', 'Email Campaign', 'Other'
  ];
  
  return useQuery({
    queryKey: ['lead-sources'],
    queryFn: async () => {
      try {
        const res = await axios.get(`${API}/api/masters/lead-sources`, { headers: getHeaders() });
        if (res.data && Array.isArray(res.data) && res.data.length > 0) {
          return res.data.map(s => ({
            id: s.id || s.code || s.name?.toLowerCase().replace(/\s+/g, '_'),
            name: s.name || s.label || s,
          }));
        }
      } catch {
        // Use predefined
      }
      return sources.map(name => ({ id: name.toLowerCase().replace(/\s+/g, '_'), name }));
    },
    staleTime: 30 * 60 * 1000,
    ...options
  });
};

/**
 * Lead status options hook - for lead filtering/updating.
 */
export const useLeadStatusOptions = () => {
  const statusOptions = [
    { id: '', name: 'All Leads' },
    { id: 'new', name: 'New' },
    { id: 'meeting', name: 'Meeting' },
    { id: 'pricing_plan', name: 'Pricing Plan' },
    { id: 'sow', name: 'SOW' },
    { id: 'quotation', name: 'Quotation' },
    { id: 'agreement', name: 'Agreement' },
    { id: 'payment', name: 'Payment' },
    { id: 'kickoff_request', name: 'Kickoff Request' },
    { id: 'kick_accept', name: 'Kick Accept' },
    { id: 'closed', name: 'Closed' },
    { id: 'paused', name: 'Paused' },
    { id: 'lost', name: 'Lost' },
  ];
  
  return {
    data: statusOptions,
    isLoading: false,
    isError: false,
  };
};

/**
 * Project status options hook - for project filtering/updating.
 */
export const useProjectStatusOptions = () => {
  const statusOptions = [
    { id: 'active', name: 'Active' },
    { id: 'on_hold', name: 'On Hold' },
    { id: 'completed', name: 'Completed' },
    { id: 'cancelled', name: 'Cancelled' },
    { id: 'at_risk', name: 'At Risk' },
    { id: 'delayed', name: 'Delayed' },
  ];
  
  return {
    data: statusOptions,
    isLoading: false,
    isError: false,
  };
};
