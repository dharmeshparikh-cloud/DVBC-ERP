import React, { useState, useEffect, useRef, useCallback, useContext, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API } from '../App';
import { AuthContext } from '../App';
import { Bell, Check, CheckCheck, X, ExternalLink, Wifi, WifiOff, Filter } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const WS_URL = API_URL.replace('https://', 'wss://').replace('http://', 'ws://');

const NOTIF_ICONS = {
  // Actionable notifications
  go_live_approval: { color: 'bg-emerald-500', label: 'Go-Live', actionable: true, category: 'go_live' },
  ctc_approval: { color: 'bg-purple-500', label: 'CTC', actionable: true, category: 'ctc' },
  permission_change: { color: 'bg-indigo-500', label: 'Permission', actionable: true, category: 'permission' },
  approval_request: { color: 'bg-amber-500', label: 'Approval', actionable: true, category: 'approval' },
  employee_modification: { color: 'bg-orange-500', label: 'Employee', actionable: true, category: 'employee' },
  
  // Information notifications
  employee_onboarded: { color: 'bg-blue-500', label: 'New Employee', actionable: false, category: 'employee' },
  approval_completed: { color: 'bg-emerald-500', label: 'Approved', actionable: false, category: 'approval' },
  approval_rejected: { color: 'bg-red-500', label: 'Rejected', actionable: false, category: 'approval' },
  leave_request: { color: 'bg-blue-500', label: 'Leave', actionable: false, category: 'leave' },
  expense_submitted: { color: 'bg-purple-500', label: 'Expense', actionable: false, category: 'expense' },
  sow_completion: { color: 'bg-teal-500', label: 'SOW', actionable: false, category: 'sow' },
  bank_change_approved: { color: 'bg-emerald-500', label: 'Bank', actionable: false, category: 'bank' },
  bank_change: { color: 'bg-amber-500', label: 'Bank', actionable: true, category: 'bank' },
  go_live_approved: { color: 'bg-emerald-500', label: 'Go-Live', actionable: false, category: 'go_live' },
  go_live_rejected: { color: 'bg-red-500', label: 'Rejected', actionable: false, category: 'go_live' },
  chat_mention: { color: 'bg-orange-500', label: 'Chat', actionable: false, category: 'chat' },
  action_taken: { color: 'bg-green-500', label: 'Action', actionable: false, category: 'other' },
  default: { color: 'bg-zinc-400', label: 'Info', actionable: false, category: 'other' },
};

// Category tabs configuration
const CATEGORY_TABS = [
  { id: 'all', label: 'All' },
  { id: 'go_live', label: 'Go-Live' },
  { id: 'permission', label: 'Permission' },
  { id: 'employee', label: 'Employee' },
  { id: 'leave', label: 'Leave' },
  { id: 'expense', label: 'Expense' },
  { id: 'ctc', label: 'CTC' },
  { id: 'other', label: 'Other' },
];

const timeAgo = (dateStr) => {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
};

const NotificationBell = () => {
  const { user } = useContext(AuthContext);
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [activeTab, setActiveTab] = useState('all');
  const dropdownRef = useRef(null);
  const lastCountRef = useRef(0);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const navigate = useNavigate();

  const fetchUnreadCount = useCallback(async () => {
    try {
      const resp = await axios.get(`${API}/notifications/unread-count`);
      const newCount = resp.data.count;

      // Browser push notification if count increased
      if (newCount > lastCountRef.current && lastCountRef.current > 0) {
        triggerBrowserNotification(newCount - lastCountRef.current);
      }
      lastCountRef.current = newCount;
      setUnreadCount(newCount);
    } catch {
      // silent fail
    }
  }, []);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const resp = await axios.get(`${API}/notifications`);
      setNotifications(resp.data);
    } catch {
      // silent fail
    } finally {
      setLoading(false);
    }
  };

  const triggerBrowserNotification = (count, title = null, body = null) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title || 'DVBC - NETRA', {
        body: body || `You have ${count} new notification${count > 1 ? 's' : ''}`,
        icon: 'https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png',
      });
    }
  };

  const requestBrowserPermission = () => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  };

  // WebSocket connection for real-time notifications
  const connectWebSocket = useCallback(() => {
    if (!user?.id || wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_URL}/api/chat/ws/${user.id}`);
    
    ws.onopen = () => {
      console.log('Notification WebSocket connected');
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'notification') {
        // Real-time notification received
        const notif = data.notification;
        
        // Add to notifications list (at the beginning for newest first)
        setNotifications(prev => [notif, ...prev]);
        
        // Increment unread count
        setUnreadCount(prev => prev + 1);
        lastCountRef.current += 1;
        
        // Trigger browser notification
        triggerBrowserNotification(1, notif.title, notif.message);
      }
      
      if (data.type === 'new_message') {
        // Chat message notification (if not in chat)
        if (!window.location.pathname.includes('/chat')) {
          setUnreadCount(prev => prev + 1);
        }
      }
    };

    ws.onclose = () => {
      console.log('Notification WebSocket disconnected');
      setWsConnected(false);
      
      // Attempt to reconnect after 5 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connectWebSocket();
      }, 5000);
    };

    ws.onerror = (error) => {
      console.error('Notification WebSocket error:', error);
    };

    wsRef.current = ws;
  }, [user?.id]);

  useEffect(() => {
    requestBrowserPermission();
    fetchUnreadCount();
    connectWebSocket();
    
    // Fallback polling every 30s if WebSocket fails
    const interval = setInterval(() => {
      if (!wsConnected) {
        fetchUnreadCount();
      }
    }, 30000);
    
    return () => {
      clearInterval(interval);
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [fetchUnreadCount, connectWebSocket]);

  useEffect(() => {
    if (open) fetchNotifications();
  }, [open]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const markAsRead = async (id) => {
    await axios.patch(`${API}/notifications/${id}/read`);
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    setUnreadCount(prev => Math.max(0, prev - 1));
  };

  const markAllRead = async () => {
    await axios.patch(`${API}/notifications/mark-all-read`);
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
    setUnreadCount(0);
  };

  // Sort notifications by newest first and filter by category
  const filteredNotifications = useMemo(() => {
    // Sort by created_at descending (newest first)
    const sorted = [...notifications].sort((a, b) => 
      new Date(b.created_at) - new Date(a.created_at)
    );
    
    // Filter by active tab
    if (activeTab === 'all') return sorted;
    
    return sorted.filter(notif => {
      const notifType = notif.type || notif.notification_type || 'default';
      const meta = NOTIF_ICONS[notifType] || NOTIF_ICONS.default;
      return meta.category === activeTab;
    });
  }, [notifications, activeTab]);

  // Get counts per category for badges
  const categoryCounts = useMemo(() => {
    const counts = {};
    notifications.forEach(notif => {
      if (!notif.is_read) {
        const notifType = notif.type || notif.notification_type || 'default';
        const meta = NOTIF_ICONS[notifType] || NOTIF_ICONS.default;
        counts[meta.category] = (counts[meta.category] || 0) + 1;
      }
    });
    return counts;
  }, [notifications]);

  return (
    <div className="relative" ref={dropdownRef} data-tour="notification-bell">
      <button
        onClick={() => setOpen(!open)}
        data-testid="notification-bell"
        className="relative p-2 rounded-md hover:bg-zinc-100 transition-colors"
      >
        <Bell className="w-5 h-5 text-zinc-600" strokeWidth={1.5} />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center" data-testid="unread-badge">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
        {/* WebSocket connection indicator */}
        <span 
          className={`absolute bottom-0 right-0 w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-gray-400'}`} 
          title={wsConnected ? 'Real-time connected' : 'Connecting...'} 
          data-tour="ws-status"
        />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-[420px] bg-white border border-zinc-200 rounded-lg shadow-lg z-50 overflow-hidden" data-testid="notification-dropdown" data-tour="notification-panel">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-100 bg-zinc-50/50">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-zinc-900">Notifications</span>
              {wsConnected ? (
                <Wifi className="w-3 h-3 text-green-500" title="Real-time" />
              ) : (
                <WifiOff className="w-3 h-3 text-gray-400" title="Connecting..." />
              )}
            </div>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button onClick={markAllRead} className="text-[11px] text-zinc-500 hover:text-zinc-900 flex items-center gap-1 transition-colors" data-testid="mark-all-read">
                  <CheckCheck className="w-3.5 h-3.5" /> Mark all read
                </button>
              )}
              <button onClick={() => setOpen(false)} className="p-0.5 hover:bg-zinc-200 rounded transition-colors">
                <X className="w-4 h-4 text-zinc-400" />
              </button>
            </div>
          </div>

          {/* Category Tabs */}
          <div className="flex overflow-x-auto border-b border-zinc-100 bg-zinc-50/30 px-2 py-1.5 gap-1 scrollbar-hide">
            {CATEGORY_TABS.map(tab => {
              const count = tab.id === 'all' ? unreadCount : (categoryCounts[tab.id] || 0);
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    px-2.5 py-1 text-[11px] font-medium rounded-md whitespace-nowrap transition-all flex items-center gap-1
                    ${isActive 
                      ? 'bg-orange-500 text-white shadow-sm' 
                      : 'text-zinc-600 hover:bg-zinc-100'
                    }
                  `}
                >
                  {tab.label}
                  {count > 0 && (
                    <span className={`
                      px-1 py-0.5 text-[9px] rounded-full min-w-[16px] text-center
                      ${isActive ? 'bg-orange-600 text-white' : 'bg-zinc-200 text-zinc-600'}
                    `}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* List - Sorted newest first */}
          <div className="max-h-[350px] overflow-y-auto">
            {loading ? (
              <div className="p-6 text-center text-xs text-zinc-400">Loading...</div>
            ) : filteredNotifications.length === 0 ? (
              <div className="p-8 text-center">
                <Bell className="w-8 h-8 text-zinc-200 mx-auto mb-2" />
                <p className="text-xs text-zinc-400">
                  {activeTab === 'all' ? 'No notifications yet' : `No ${activeTab.replace('_', ' ')} notifications`}
                </p>
              </div>
            ) : (
              filteredNotifications.slice(0, 15).map(notif => {
                const notifType = notif.type || notif.notification_type || 'default';
                const meta = NOTIF_ICONS[notifType] || NOTIF_ICONS.default;
                const isActioned = notif.status === 'actioned';
                return (
                  <div
                    key={notif.id}
                    data-testid={`notif-${notif.id}`}
                    className={`flex gap-3 px-4 py-3 border-b border-zinc-50 hover:bg-zinc-50/80 transition-colors cursor-pointer ${
                      notif.is_read ? 'opacity-60' : ''
                    }`}
                    onClick={() => {
                      if (!notif.is_read) markAsRead(notif.id);
                      setOpen(false);
                      if (notif.link) {
                        navigate(notif.link);
                      } else {
                        navigate('/notifications');
                      }
                    }}
                  >
                    <div className={`w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${meta.color}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <p className="text-xs font-medium text-zinc-900 leading-snug">{notif.title}</p>
                          {meta.actionable && !isActioned && (
                            <span className="px-1.5 py-0.5 text-[9px] font-medium bg-amber-100 text-amber-700 rounded">
                              Action
                            </span>
                          )}
                          <span className={`px-1.5 py-0.5 text-[9px] font-medium rounded ${meta.color} text-white`}>
                            {meta.label}
                          </span>
                        </div>
                        {!notif.is_read && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0 mt-1" />
                        )}
                      </div>
                      <p className="text-[11px] text-zinc-500 mt-0.5 leading-snug line-clamp-2">{notif.message}</p>
                      <p className="text-[10px] text-zinc-400 mt-1">{timeAgo(notif.created_at)}</p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
          
          {/* Footer - View All */}
          <div className="px-4 py-2 border-t border-zinc-100 bg-zinc-50/50">
            <button 
              onClick={() => { setOpen(false); navigate('/notifications'); }}
              className="w-full text-center text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center justify-center gap-1"
              data-testid="view-all-notifications"
            >
              View All Notifications <ExternalLink className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
