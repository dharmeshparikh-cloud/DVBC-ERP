import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { API } from '../App';
import { Bell, Check, CheckCheck, X, ExternalLink } from 'lucide-react';

const NOTIF_ICONS = {
  // Actionable notifications
  go_live_approval: { color: 'bg-emerald-500', label: 'Go-Live', actionable: true },
  ctc_approval: { color: 'bg-purple-500', label: 'CTC', actionable: true },
  permission_change: { color: 'bg-indigo-500', label: 'Permission', actionable: true },
  approval_request: { color: 'bg-amber-500', label: 'Approval', actionable: true },
  
  // Information notifications
  employee_onboarded: { color: 'bg-blue-500', label: 'New Employee', actionable: false },
  approval_completed: { color: 'bg-emerald-500', label: 'Approved', actionable: false },
  approval_rejected: { color: 'bg-red-500', label: 'Rejected', actionable: false },
  leave_request: { color: 'bg-blue-500', label: 'Leave', actionable: false },
  expense_submitted: { color: 'bg-purple-500', label: 'Expense', actionable: false },
  sow_completion: { color: 'bg-teal-500', label: 'SOW', actionable: false },
  bank_change_approved: { color: 'bg-emerald-500', label: 'Bank', actionable: false },
  go_live_approved: { color: 'bg-emerald-500', label: 'Go-Live', actionable: false },
  go_live_rejected: { color: 'bg-red-500', label: 'Rejected', actionable: false },
  default: { color: 'bg-zinc-400', label: 'Info', actionable: false },
};

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
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);
  const lastCountRef = useRef(0);
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

  const triggerBrowserNotification = (count) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('DVBC - NETRA', {
        body: `You have ${count} new notification${count > 1 ? 's' : ''}`,
        icon: 'https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png',
      });
    }
  };

  const requestBrowserPermission = () => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  };

  useEffect(() => {
    requestBrowserPermission();
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 15000); // poll every 15s
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

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

  return (
    <div className="relative" ref={dropdownRef}>
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
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-[380px] bg-white border border-zinc-200 rounded-lg shadow-lg z-50 overflow-hidden" data-testid="notification-dropdown">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-100 bg-zinc-50/50">
            <span className="text-sm font-semibold text-zinc-900">Notifications</span>
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

          {/* List */}
          <div className="max-h-[400px] overflow-y-auto">
            {loading ? (
              <div className="p-6 text-center text-xs text-zinc-400">Loading...</div>
            ) : notifications.length === 0 ? (
              <div className="p-8 text-center">
                <Bell className="w-8 h-8 text-zinc-200 mx-auto mb-2" />
                <p className="text-xs text-zinc-400">No notifications yet</p>
              </div>
            ) : (
              notifications.slice(0, 20).map(notif => {
                const notifType = notif.type || notif.notification_type || 'default';
                const meta = NOTIF_ICONS[notifType] || NOTIF_ICONS.default;
                return (
                  <div
                    key={notif.id}
                    data-testid={`notif-${notif.id}`}
                    className={`flex gap-3 px-4 py-3 border-b border-zinc-50 hover:bg-zinc-50/80 transition-colors cursor-pointer ${
                      notif.is_read ? 'opacity-60' : ''
                    }`}
                    onClick={() => !notif.is_read && markAsRead(notif.id)}
                  >
                    <div className={`w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${meta.color}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs font-medium text-zinc-900 leading-snug">{notif.title}</p>
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
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
