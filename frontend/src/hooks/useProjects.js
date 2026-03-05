/**
 * Projects Domain Hooks
 * All project/consulting API operations via React Query
 * 
 * REACT QUERY ENFORCEMENT - March 2026
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// Query Keys
export const projectKeys = {
  all: ['projects'],
  lists: () => [...projectKeys.all, 'list'],
  list: (filters) => [...projectKeys.lists(), filters],
  details: () => [...projectKeys.all, 'detail'],
  detail: (id) => [...projectKeys.details(), id],
  meetings: (projectId) => [...projectKeys.all, 'meetings', projectId],
  milestones: (projectId) => [...projectKeys.all, 'milestones', projectId],
  team: (projectId) => [...projectKeys.all, 'team', projectId],
  stats: () => [...projectKeys.all, 'stats'],
};

// ==================== QUERIES ====================

/**
 * Fetch all projects with filters
 */
export const useProjects = (filters = {}) => {
  const { page = 1, pageSize = 50, status, client_id, consultant_id } = filters;
  
  return useQuery({
    queryKey: projectKeys.list({ page, pageSize, status, client_id, consultant_id }),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('page_size', pageSize);
      if (status) params.append('status', status);
      if (client_id) params.append('client_id', client_id);
      if (consultant_id) params.append('consultant_id', consultant_id);
      
      const { data } = await axios.get(`${API}/api/projects?${params}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
    keepPreviousData: true,
  });
};

/**
 * Fetch single project by ID
 */
export const useProject = (id) => {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/projects/${id}`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch project meetings
 */
export const useProjectMeetings = (projectId, filters = {}) => {
  const { page = 1, pageSize = 20 } = filters;
  
  return useQuery({
    queryKey: projectKeys.meetings(projectId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/projects/${projectId}/meetings`, {
        params: { page, page_size: pageSize },
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch project milestones
 */
export const useProjectMilestones = (projectId) => {
  return useQuery({
    queryKey: projectKeys.milestones(projectId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/projects/${projectId}/milestones`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch project team
 */
export const useProjectTeam = (projectId) => {
  return useQuery({
    queryKey: projectKeys.team(projectId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/projects/${projectId}/team`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch project stats
 */
export const useProjectStats = () => {
  return useQuery({
    queryKey: projectKeys.stats(),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/projects/stats`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

// ==================== MUTATIONS ====================

/**
 * Create new project
 */
export const useCreateProject = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (projectData) => {
      const { data } = await axios.post(`${API}/api/projects`, projectData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
      queryClient.invalidateQueries({ queryKey: ['consulting', 'stats'] });
    },
  });
};

/**
 * Update project
 */
export const useUpdateProject = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, ...projectData }) => {
      const { data } = await axios.patch(`${API}/api/projects/${id}`, projectData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(variables.id) });
    },
  });
};

/**
 * Add meeting to project
 */
export const useAddMeeting = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ projectId, meetingData }) => {
      const { data } = await axios.post(
        `${API}/api/projects/${projectId}/meetings`,
        meetingData,
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.meetings(variables.projectId) });
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(variables.projectId) });
    },
  });
};

/**
 * Update milestone
 */
export const useUpdateMilestone = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ projectId, milestoneId, milestoneData }) => {
      const { data } = await axios.patch(
        `${API}/api/projects/${projectId}/milestones/${milestoneId}`,
        milestoneData,
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.milestones(variables.projectId) });
    },
  });
};

/**
 * Assign team member
 */
export const useAssignTeamMember = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ projectId, employeeId, role }) => {
      const { data } = await axios.post(
        `${API}/api/projects/${projectId}/team`,
        { employee_id: employeeId, role },
        { headers: getAuthHeaders() }
      );
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.team(variables.projectId) });
    },
  });
};

export default {
  useProjects,
  useProject,
  useProjectMeetings,
  useProjectMilestones,
  useProjectTeam,
  useProjectStats,
  useCreateProject,
  useUpdateProject,
  useAddMeeting,
  useUpdateMilestone,
  useAssignTeamMember,
};
