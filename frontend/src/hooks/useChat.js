/**
 * Chat Domain Hooks
 * All chat/messaging API operations via React Query
 * Note: WebSocket connections are handled separately for real-time features
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
export const chatKeys = {
  all: ['chat'],
  conversations: (userId) => [...chatKeys.all, 'conversations', userId],
  messages: (conversationId) => [...chatKeys.all, 'messages', conversationId],
  users: (search) => [...chatKeys.all, 'users', search],
  unread: (userId) => [...chatKeys.all, 'unread', userId],
};

// ==================== QUERIES ====================

/**
 * Fetch user conversations
 */
export const useConversations = (userId) => {
  return useQuery({
    queryKey: chatKeys.conversations(userId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/chat/conversations`, {
        params: { user_id: userId },
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!userId,
    staleTime: 30 * 1000, // 30 seconds for chat (more frequent updates)
  });
};

/**
 * Fetch messages for a conversation
 */
export const useMessages = (conversationId) => {
  return useQuery({
    queryKey: chatKeys.messages(conversationId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/chat/conversations/${conversationId}/messages`, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!conversationId,
    staleTime: 10 * 1000, // 10 seconds for messages
  });
};

/**
 * Fetch users for new chat/group
 */
export const useChatUsers = (search = '') => {
  return useQuery({
    queryKey: chatKeys.users(search),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/chat/users`, {
        params: { search },
        headers: getAuthHeaders(),
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Fetch unread count
 */
export const useUnreadCount = (userId) => {
  return useQuery({
    queryKey: chatKeys.unread(userId),
    queryFn: async () => {
      const { data } = await axios.get(`${API}/api/chat/unread-count`, {
        params: { user_id: userId },
        headers: getAuthHeaders(),
      });
      return data;
    },
    enabled: !!userId,
    staleTime: 30 * 1000,
  });
};

// ==================== MUTATIONS ====================

/**
 * Create new conversation (DM or Group)
 */
export const useCreateConversation = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (conversationData) => {
      const { data } = await axios.post(`${API}/api/chat/conversations`, conversationData, {
        headers: getAuthHeaders(),
      });
      return data;
    },
    onSuccess: (data, variables) => {
      // Invalidate conversations for all participants
      variables.participant_ids?.forEach(userId => {
        queryClient.invalidateQueries({ queryKey: chatKeys.conversations(userId) });
      });
    },
  });
};

/**
 * Send message
 */
export const useSendMessage = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ conversationId, senderId, content, messageType = 'text' }) => {
      const { data } = await axios.post(
        `${API}/api/chat/conversations/${conversationId}/messages`,
        { content, message_type: messageType },
        { 
          params: { sender_id: senderId },
          headers: getAuthHeaders() 
        }
      );
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: chatKeys.messages(variables.conversationId) });
    },
  });
};

/**
 * Mark messages as read
 */
export const useMarkAsRead = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ conversationId, userId }) => {
      const { data } = await axios.post(
        `${API}/api/chat/conversations/${conversationId}/read-all`,
        {},
        { 
          params: { user_id: userId },
          headers: getAuthHeaders() 
        }
      );
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: chatKeys.unread(variables.userId) });
      queryClient.invalidateQueries({ queryKey: chatKeys.messages(variables.conversationId) });
    },
  });
};

/**
 * Execute action on message (pin, bookmark, etc.)
 */
export const useMessageAction = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ messageId, userId, action }) => {
      const { data } = await axios.post(
        `${API}/api/chat/messages/${messageId}/action`,
        { action },
        { 
          params: { user_id: userId },
          headers: getAuthHeaders() 
        }
      );
      return data;
    },
    onSuccess: () => {
      // Invalidate all messages as we don't know the conversation ID here
      queryClient.invalidateQueries({ queryKey: ['chat', 'messages'] });
    },
  });
};

/**
 * Delete conversation
 */
export const useDeleteConversation = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ conversationId, userId }) => {
      const { data } = await axios.delete(
        `${API}/api/chat/conversations/${conversationId}`,
        { 
          params: { user_id: userId },
          headers: getAuthHeaders() 
        }
      );
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: chatKeys.conversations(variables.userId) });
    },
  });
};

export default {
  useConversations,
  useMessages,
  useChatUsers,
  useUnreadCount,
  useCreateConversation,
  useSendMessage,
  useMarkAsRead,
  useMessageAction,
  useDeleteConversation,
};
