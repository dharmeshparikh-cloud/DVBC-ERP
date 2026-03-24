/**
 * WebSocket Hook for Real-Time Updates
 * =====================================
 * 
 * Connects to backend WebSocket for real-time data updates.
 * Automatically invalidates React Query cache when data changes.
 * 
 * Usage:
 *   import { useRealtimeUpdates } from '../hooks/useWebSocket';
 *   
 *   function MyComponent() {
 *     const { isConnected, subscribe } = useRealtimeUpdates();
 *     
 *     useEffect(() => {
 *       subscribe(['employees', 'leads']);
 *     }, []);
 *   }
 */

import { useEffect, useRef, useState, useCallback, useContext } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { AuthContext } from '../App';
import { invalidateCache } from '../lib/queryClient';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Convert HTTP URL to WebSocket URL
const getWebSocketUrl = () => {
  const url = API_URL.replace(/^http/, 'ws');
  return `${url}/api/ws`;
};

/**
 * WebSocket connection states
 */
const WS_STATES = {
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3
};

/**
 * Hook for WebSocket connection and real-time updates
 */
export const useRealtimeUpdates = (options = {}) => {
  const { 
    autoConnect = true,
    reconnectAttempts = 5,
    reconnectDelay = 3000,
    showNotifications = true
  } = options;
  
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  
  const wsRef = useRef(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [subscriptions, setSubscriptions] = useState([]);
  
  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback((event) => {
    try {
      const message = JSON.parse(event.data);
      setLastMessage(message);
      
      switch (message.type) {
        case 'connected':
          console.log('WebSocket connected:', message.user_id);
          break;
          
        case 'ping':
          // Respond with pong
          if (wsRef.current?.readyState === WS_STATES.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'pong' }));
          }
          break;
          
        case 'data_update':
          handleDataUpdate(message);
          break;
          
        case 'notification':
          handleNotification(message);
          break;
          
        case 'announcement':
          if (showNotifications) {
            toast.info(message.message);
          }
          break;
          
        case 'subscribed':
          console.log('Subscribed to:', message.topics);
          break;
          
        default:
          console.log('Unknown message type:', message.type);
      }
    } catch (e) {
      console.error('Error parsing WebSocket message:', e);
    }
  }, [showNotifications]);
  
  /**
   * Handle data update messages - invalidate relevant caches
   */
  const handleDataUpdate = useCallback((message) => {
    const { entity, action, data } = message;
    
    console.log(`Real-time update: ${entity}.${action}`, data);
    
    // Invalidate relevant React Query caches based on entity
    switch (entity) {
      case 'employees':
        invalidateCache.employees();
        if (data?.employee_id) {
          invalidateCache.employee(data.employee_id);
        }
        break;
        
      case 'leads':
        invalidateCache.leads();
        if (data?.lead_id) {
          invalidateCache.lead(data.lead_id);
        }
        break;
        
      case 'onboarding':
        invalidateCache.onboarding();
        break;
        
      case 'attendance':
        invalidateCache.attendance();
        break;
        
      case 'leaves':
        invalidateCache.leaves();
        break;
        
      case 'payroll':
        invalidateCache.payroll();
        break;
        
      case 'approvals':
        invalidateCache.approvals();
        break;
        
      case 'projects':
        invalidateCache.projects();
        if (data?.project_id) {
          invalidateCache.project(data.project_id);
        }
        break;
        
      case 'dashboard':
        invalidateCache.dashboardStats();
        break;
        
      case 'notifications':
        invalidateCache.notifications();
        break;
        
      case 'documents':
        invalidateCache.documents();
        break;
        
      case 'expenses':
        invalidateCache.expenses();
        break;
        
      case 'agreements':
        invalidateCache.agreements();
        break;
        
      case 'kickoffs':
        invalidateCache.kickoffs();
        break;
        
      default:
        // For unknown entities, do a broad invalidation
        queryClient.invalidateQueries({ queryKey: [entity] });
    }
    
    // Show toast for certain actions
    if (showNotifications && ['approve', 'reject', 'complete'].includes(action)) {
      toast.info(`${entity} ${action}d - data refreshed`);
    }
  }, [queryClient, showNotifications]);
  
  /**
   * Handle notification messages
   */
  const handleNotification = useCallback((message) => {
    if (!showNotifications) return;
    
    const { notification_type, title, message: text } = message;
    
    switch (notification_type) {
      case 'success':
        toast.success(title, { description: text });
        break;
      case 'error':
        toast.error(title, { description: text });
        break;
      case 'warning':
        toast.warning(title, { description: text });
        break;
      default:
        toast.info(title, { description: text });
    }
    
    // Also invalidate notifications cache
    invalidateCache.notifications();
  }, [showNotifications]);
  
  /**
   * Connect to WebSocket server
   */
  const connect = useCallback(() => {
    if (!user?.id) {
      console.log('Cannot connect WebSocket: No user ID');
      return;
    }
    
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    const wsUrl = `${getWebSocketUrl()}/${user.id}`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    try {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        reconnectCountRef.current = 0;
        
        // Subscribe to default topics
        if (subscriptions.length > 0) {
          subscribe(subscriptions);
        } else {
          // Default subscriptions
          subscribe(['dashboard', 'notifications', 'employees', 'onboarding']);
        }
      };
      
      wsRef.current.onmessage = handleMessage;
      
      wsRef.current.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        
        // Attempt reconnection if not intentionally closed
        if (event.code !== 1000 && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current += 1;
          console.log(`Reconnecting... attempt ${reconnectCountRef.current}/${reconnectAttempts}`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  }, [user?.id, handleMessage, reconnectAttempts, reconnectDelay, subscriptions]);
  
  /**
   * Disconnect from WebSocket server
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }
    
    setIsConnected(false);
  }, []);
  
  /**
   * Subscribe to topics
   */
  const subscribe = useCallback((topics) => {
    if (!Array.isArray(topics)) {
      topics = [topics];
    }
    
    setSubscriptions(prev => [...new Set([...prev, ...topics])]);
    
    if (wsRef.current?.readyState === WS_STATES.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe',
        topics
      }));
    }
  }, []);
  
  /**
   * Unsubscribe from topics
   */
  const unsubscribe = useCallback((topics) => {
    if (!Array.isArray(topics)) {
      topics = [topics];
    }
    
    setSubscriptions(prev => (prev || []).filter(t => !topics.includes(t)));
    
    if (wsRef.current?.readyState === WS_STATES.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'unsubscribe',
        topics
      }));
    }
  }, []);
  
  /**
   * Send a message through WebSocket
   */
  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WS_STATES.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);
  
  // Auto-connect when user is available
  useEffect(() => {
    if (autoConnect && user?.id) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [autoConnect, user?.id, connect, disconnect]);
  
  return {
    isConnected,
    lastMessage,
    subscriptions,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    sendMessage
  };
};

/**
 * Simple hook just to check WebSocket status
 */
export const useWebSocketStatus = () => {
  const { isConnected } = useRealtimeUpdates({ autoConnect: true, showNotifications: false });
  return isConnected;
};

export default useRealtimeUpdates;
