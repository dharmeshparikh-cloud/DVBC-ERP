import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { 
  Bell, CheckCircle, XCircle, Clock, Info, AlertTriangle,
  User, DollarSign, FileText, Briefcase, Building2, Shield,
  ChevronRight, Check, X, Loader2, ExternalLink
} from 'lucide-react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';

const NOTIFICATION_CONFIG = {
  // Actionable notifications - require approve/reject
  go_live_approval: { 
    icon: Shield, 
    color: 'bg-emerald-500', 
    label: 'Go-Live Approval',
    actionable: true,
    approveEndpoint: '/go-live/{id}/approve',
    rejectEndpoint: '/go-live/{id}/reject',
    onwardLink: '/go-live'
  },
  ctc_approval: { 
    icon: DollarSign, 
    color: 'bg-purple-500', 
    label: 'CTC Approval',
    actionable: true,
    approveEndpoint: '/ctc/approve/{id}',
    rejectEndpoint: '/ctc/reject/{id}',
    onwardLink: '/hr/ctc-designer'
  },
  permission_change: { 
    icon: User, 
    color: 'bg-indigo-500', 
    label: 'Permission Change',
    actionable: true,
    approveEndpoint: '/permission-change-requests/{id}/approve',
    rejectEndpoint: '/permission-change-requests/{id}/reject',
    onwardLink: '/employees'
  },
  approval_request: { 
    icon: Clock, 
    color: 'bg-amber-500', 
    label: 'Approval Request',
    actionable: true,
    onwardLink: '/approvals'
  },
  
  // Information notifications - read only
  employee_onboarded: { 
    icon: User, 
    color: 'bg-blue-500', 
    label: 'New Employee',
    actionable: false,
    onwardLink: '/employees'
  },
  bank_change_approved: { 
    icon: Building2, 
    color: 'bg-emerald-500', 
    label: 'Bank Updated',
    actionable: false,
    onwardLink: '/my-bank-details'
  },
  go_live_approved: { 
    icon: CheckCircle, 
    color: 'bg-emerald-500', 
    label: 'Go-Live Approved',
    actionable: false,
    onwardLink: '/employees'
  },
  go_live_rejected: { 
    icon: XCircle, 
    color: 'bg-red-500', 
    label: 'Go-Live Rejected',
    actionable: false,
    onwardLink: '/go-live'
  },
  approval_completed: { 
    icon: CheckCircle, 
    color: 'bg-emerald-500', 
    label: 'Approved',
    actionable: false
  },
  approval_rejected: { 
    icon: XCircle, 
    color: 'bg-red-500', 
    label: 'Rejected',
    actionable: false
  },
  leave_request: { 
    icon: FileText, 
    color: 'bg-blue-500', 
    label: 'Leave',
    actionable: false,
    onwardLink: '/leave-management'
  },
  expense_submitted: { 
    icon: DollarSign, 
    color: 'bg-purple-500', 
    label: 'Expense',
    actionable: false,
    onwardLink: '/expenses'
  },
  sow_completion: { 
    icon: Briefcase, 
    color: 'bg-teal-500', 
    label: 'SOW',
    actionable: false
  },
  default: { 
    icon: Info, 
    color: 'bg-zinc-400', 
    label: 'Info',
    actionable: false
  },
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

const Notifications = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, unread, actionable
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [actionDialog, setActionDialog] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');

  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    try {
      const resp = await axios.get(`${API}/notifications`);
      setNotifications(resp.data);
    } catch (error) {
      toast.error('Failed to load notifications');
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (id) => {
    try {
      await axios.patch(`${API}/notifications/${id}/read`);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const markAllRead = async () => {
    try {
      await axios.patch(`${API}/notifications/mark-all-read`);
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      toast.success('All notifications marked as read');
    } catch (error) {
      toast.error('Failed to mark all as read');
    }
  };

  const handleNotificationClick = (notif) => {
    const config = NOTIFICATION_CONFIG[notif.type] || NOTIFICATION_CONFIG.default;
    
    // Mark as read
    if (!notif.is_read) {
      markAsRead(notif.id);
    }
    
    // If actionable, open action dialog
    if (config.actionable && notif.status !== 'actioned') {
      setSelectedNotification(notif);
      setActionDialog(true);
    } else if (config.onwardLink) {
      // Navigate to onward link
      navigate(config.onwardLink);
    }
  };

  const handleAction = async (action) => {
    if (!selectedNotification) return;
    
    setActionLoading(true);
    const config = NOTIFICATION_CONFIG[selectedNotification.type] || {};
    
    try {
      const referenceId = selectedNotification.reference_id;
      
      if (action === 'approve' && config.approveEndpoint) {
        const endpoint = config.approveEndpoint.replace('{id}', referenceId);
        await axios.post(`${API}${endpoint}`);
        toast.success('Approved successfully');
      } else if (action === 'reject' && config.rejectEndpoint) {
        const endpoint = config.rejectEndpoint.replace('{id}', referenceId);
        await axios.post(`${API}${endpoint}`, { reason: rejectionReason || 'Rejected' });
        toast.success('Rejected successfully');
      }
      
      // Update notification status
      await axios.patch(`${API}/notifications/${selectedNotification.id}/action`, { 
        action,
        actioned_at: new Date().toISOString()
      });
      
      setNotifications(prev => prev.map(n => 
        n.id === selectedNotification.id 
          ? { ...n, status: 'actioned', action_taken: action } 
          : n
      ));
      
      setActionDialog(false);
      setSelectedNotification(null);
      setRejectionReason('');
      
      // Navigate to onward link if available
      if (config.onwardLink) {
        navigate(config.onwardLink);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${action}`);
    } finally {
      setActionLoading(false);
    }
  };

  const filteredNotifications = notifications.filter(n => {
    if (filter === 'unread') return !n.is_read;
    if (filter === 'actionable') {
      const config = NOTIFICATION_CONFIG[n.type] || NOTIFICATION_CONFIG.default;
      return config.actionable && n.status !== 'actioned';
    }
    return true;
  });

  const actionableCount = notifications.filter(n => {
    const config = NOTIFICATION_CONFIG[n.type] || NOTIFICATION_CONFIG.default;
    return config.actionable && n.status !== 'actioned';
  }).length;

  const unreadCount = notifications.filter(n => !n.is_read).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Notifications</h1>
          <p className="text-sm text-zinc-500 mt-1">
            {unreadCount} unread, {actionableCount} require action
          </p>
        </div>
        <Button 
          variant="outline" 
          onClick={markAllRead}
          disabled={unreadCount === 0}
        >
          <Check className="w-4 h-4 mr-2" />
          Mark All Read
        </Button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-6">
        {[
          { key: 'all', label: 'All', count: notifications.length },
          { key: 'unread', label: 'Unread', count: unreadCount },
          { key: 'actionable', label: 'Requires Action', count: actionableCount },
        ].map(tab => (
          <Button
            key={tab.key}
            variant={filter === tab.key ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter(tab.key)}
            className={filter === tab.key ? 'bg-zinc-900' : ''}
          >
            {tab.label}
            <Badge variant="secondary" className="ml-2 text-xs">
              {tab.count}
            </Badge>
          </Button>
        ))}
      </div>

      {/* Notifications List */}
      <div className="space-y-3">
        {filteredNotifications.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <Bell className="w-12 h-12 text-zinc-200 mx-auto mb-4" />
              <p className="text-zinc-500">No notifications</p>
            </CardContent>
          </Card>
        ) : (
          filteredNotifications.map(notif => {
            const config = NOTIFICATION_CONFIG[notif.type] || NOTIFICATION_CONFIG.default;
            const IconComponent = config.icon;
            const isActioned = notif.status === 'actioned';
            
            return (
              <Card 
                key={notif.id}
                className={`cursor-pointer transition-all hover:shadow-md ${
                  !notif.is_read ? 'border-l-4 border-l-blue-500 bg-blue-50/30' : ''
                } ${isActioned ? 'opacity-60' : ''}`}
                onClick={() => handleNotificationClick(notif)}
                data-testid={`notification-${notif.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    {/* Icon */}
                    <div className={`p-2 rounded-lg ${config.color} bg-opacity-10`}>
                      <IconComponent className={`w-5 h-5 ${config.color.replace('bg-', 'text-')}`} />
                    </div>
                    
                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-zinc-900">{notif.title}</p>
                            <Badge variant="outline" className="text-xs">
                              {config.label}
                            </Badge>
                            {config.actionable && !isActioned && (
                              <Badge className="bg-amber-100 text-amber-700 text-xs">
                                Action Required
                              </Badge>
                            )}
                            {isActioned && (
                              <Badge className={`text-xs ${
                                notif.action_taken === 'approve' 
                                  ? 'bg-emerald-100 text-emerald-700' 
                                  : 'bg-red-100 text-red-700'
                              }`}>
                                {notif.action_taken === 'approve' ? 'Approved' : 'Rejected'}
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-zinc-600 mt-1">{notif.message}</p>
                        </div>
                        {!notif.is_read && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0 mt-2" />
                        )}
                      </div>
                      
                      <div className="flex items-center justify-between mt-3">
                        <span className="text-xs text-zinc-400">{timeAgo(notif.created_at)}</span>
                        {config.onwardLink && (
                          <span className="text-xs text-blue-600 flex items-center gap-1">
                            View Details <ChevronRight className="w-3 h-3" />
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      {/* Action Dialog for Actionable Notifications */}
      <Dialog open={actionDialog} onOpenChange={setActionDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              Action Required
            </DialogTitle>
          </DialogHeader>
          
          {selectedNotification && (
            <div className="space-y-4">
              <Card>
                <CardContent className="p-4">
                  <h4 className="font-medium text-zinc-900">{selectedNotification.title}</h4>
                  <p className="text-sm text-zinc-600 mt-1">{selectedNotification.message}</p>
                  
                  {/* Show additional details if available */}
                  {selectedNotification.details && (
                    <div className="mt-4 p-3 bg-zinc-50 rounded-lg">
                      <pre className="text-xs text-zinc-600 whitespace-pre-wrap">
                        {JSON.stringify(selectedNotification.details, null, 2)}
                      </pre>
                    </div>
                  )}
                </CardContent>
              </Card>
              
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-700">
                  Rejection Reason (optional)
                </label>
                <Textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Enter reason if rejecting..."
                  rows={2}
                />
              </div>
              
              <DialogFooter className="gap-2">
                <Button 
                  variant="outline" 
                  onClick={() => setActionDialog(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => handleAction('reject')}
                  disabled={actionLoading}
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4 mr-1" />}
                  Reject
                </Button>
                <Button
                  className="bg-emerald-600 hover:bg-emerald-700"
                  onClick={() => handleAction('approve')}
                  disabled={actionLoading}
                >
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-1" />}
                  Approve
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Notifications;
