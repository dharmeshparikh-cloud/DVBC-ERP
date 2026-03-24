/**
 * useSOWsByProject.js - NEW ADDITIVE HOOK (Step 3 + 4)
 * 
 * Fetches SOWs filtered by project_id from server.
 * Includes transformer layer for consistent field naming.
 * 
 * DOES NOT modify existing useSOWList or useSOW.js.
 * Used ONLY in ConsultingMeetings (isolated rollout).
 */

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const getHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json'
});

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
