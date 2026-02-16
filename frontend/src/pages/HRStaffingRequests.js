import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { 
  Briefcase, Calendar, Users, Clock, Building2,
  AlertCircle, CheckCircle, Eye, ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';

const HRStaffingRequests = () => {
  const { user } = useContext(AuthContext);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);

  useEffect(() => {
    if (user?.role !== 'hr_manager') {
      toast.error('Access denied. This page is for HR Managers only.');
      return;
    }
    fetchStaffingRequests();
  }, [user]);

  const fetchStaffingRequests = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/notifications`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const notifications = await response.json();
        // Filter for staffing notifications
        const staffingNotifications = notifications.filter(
          n => n.type === 'project_staffing_required'
        );
        setRequests(staffingNotifications);
      }
    } catch (error) {
      console.error('Failed to fetch staffing requests:', error);
      toast.error('Failed to load staffing requests');
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`${API}/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      setRequests(prev => prev.map(r => 
        r.id === notificationId ? { ...r, is_read: true } : r
      ));
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const handleViewDetails = (request) => {
    setSelectedRequest(request);
    setShowDetailDialog(true);
    if (!request.is_read) {
      markAsRead(request.id);
    }
  };

  const getPriorityColor = (priority) => {
    if (priority === 'high') return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
    if (priority === 'medium') return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
    return 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-400';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  if (user?.role !== 'hr_manager') {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Access Denied</h2>
          <p className="text-zinc-500 mt-2">This page is only accessible to HR Managers</p>
        </div>
      </div>
    );
  }

  const unreadCount = requests.filter(r => !r.is_read).length;

  return (
    <div className="space-y-6" data-testid="hr-staffing-requests">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Staffing Requests</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Project staffing requirements from kickoff approvals
          </p>
        </div>
        {unreadCount > 0 && (
          <Badge className="bg-red-100 text-red-700">
            {unreadCount} New
          </Badge>
        )}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Total Requests</p>
                <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  {requests.length}
                </p>
              </div>
              <Briefcase className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">High Priority</p>
                <p className="text-3xl font-bold text-red-600 mt-1">
                  {requests.filter(r => r.priority === 'high').length}
                </p>
              </div>
              <AlertCircle className="w-8 h-8 text-red-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-200 dark:border-zinc-800">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Resources Needed</p>
                <p className="text-3xl font-bold text-emerald-600 mt-1">
                  {requests.reduce((sum, r) => sum + (r.metadata?.resources_needed || 0), 0)}
                </p>
              </div>
              <Users className="w-8 h-8 text-emerald-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Requests List */}
      <Card className="border-zinc-200 dark:border-zinc-800">
        <CardHeader>
          <CardTitle className="text-base">Staffing Requests</CardTitle>
        </CardHeader>
        <CardContent>
          {requests.length > 0 ? (
            <div className="space-y-4">
              {requests.map((request) => {
                const metadata = request.metadata || {};
                
                return (
                  <div
                    key={request.id}
                    className={`flex items-center gap-4 p-4 rounded-lg border transition-colors cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800/50 ${
                      !request.is_read 
                        ? 'bg-emerald-50/50 border-emerald-200 dark:bg-emerald-900/10 dark:border-emerald-800' 
                        : 'bg-white border-zinc-200 dark:bg-zinc-900 dark:border-zinc-800'
                    }`}
                    onClick={() => handleViewDetails(request)}
                    data-testid={`staffing-request-${request.id}`}
                  >
                    {/* Icon */}
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                      request.priority === 'high' 
                        ? 'bg-red-100 dark:bg-red-900/30' 
                        : 'bg-emerald-100 dark:bg-emerald-900/30'
                    }`}>
                      <Briefcase className={`w-6 h-6 ${
                        request.priority === 'high' 
                          ? 'text-red-600 dark:text-red-400' 
                          : 'text-emerald-600 dark:text-emerald-400'
                      }`} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-zinc-900 dark:text-zinc-100">
                          {metadata.project_name || request.title}
                        </h3>
                        {!request.is_read && (
                          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                        )}
                      </div>
                      <p className="text-sm text-zinc-500 dark:text-zinc-400">
                        {metadata.client_name}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-zinc-500">
                        <span className="flex items-center gap-1">
                          <Users className="w-3 h-3" />
                          {metadata.resources_needed || 0} resources
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          Start: {metadata.start_date || 'TBD'}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {metadata.project_tenure_months || 12} months
                        </span>
                      </div>
                    </div>

                    {/* Priority Badge */}
                    <Badge className={getPriorityColor(request.priority)}>
                      {request.priority || 'normal'}
                    </Badge>

                    {/* Action */}
                    <Button variant="ghost" size="sm">
                      <Eye className="w-4 h-4 mr-1" />
                      View
                    </Button>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12 text-zinc-500">
              <CheckCircle className="w-12 h-12 mx-auto mb-4 text-emerald-300" />
              <p className="text-lg font-medium">No Staffing Requests</p>
              <p className="text-sm mt-1">
                New staffing requirements will appear here when projects are kicked off
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Staffing Request Details</DialogTitle>
          </DialogHeader>
          
          {selectedRequest && (
            <div className="space-y-6">
              {/* Project Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-zinc-500">Project Name</p>
                  <p className="font-medium text-zinc-900 dark:text-zinc-100">
                    {selectedRequest.metadata?.project_name || 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-zinc-500">Client</p>
                  <p className="font-medium text-zinc-900 dark:text-zinc-100">
                    {selectedRequest.metadata?.client_name || 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-zinc-500">Start Date</p>
                  <p className="font-medium text-zinc-900 dark:text-zinc-100">
                    {selectedRequest.metadata?.start_date || 'TBD'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-zinc-500">Duration</p>
                  <p className="font-medium text-zinc-900 dark:text-zinc-100">
                    {selectedRequest.metadata?.project_tenure_months || 12} months
                  </p>
                </div>
              </div>

              {/* Team Requirements */}
              <div>
                <h4 className="font-medium text-zinc-900 dark:text-zinc-100 mb-3">
                  Team Requirements ({selectedRequest.metadata?.resources_needed || 0} resources)
                </h4>
                {selectedRequest.metadata?.team_deployment?.length > 0 ? (
                  <div className="space-y-2">
                    {selectedRequest.metadata.team_deployment.map((member, idx) => (
                      <div 
                        key={idx}
                        className="flex items-center justify-between p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                            <Users className="w-4 h-4 text-emerald-600" />
                          </div>
                          <div>
                            <p className="font-medium">{member.role}</p>
                            <p className="text-xs text-zinc-500">
                              {member.frequency} • {member.mode}
                            </p>
                          </div>
                        </div>
                        <Badge variant="outline">
                          {member.committed_meetings || 0} meetings
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-zinc-500 text-sm">No specific team requirements defined</p>
                )}
              </div>

              {/* Info Banner */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                  <div>
                    <p className="font-medium text-blue-800 dark:text-blue-300">Action Required</p>
                    <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
                      Review consultant availability and coordinate with the Project Manager for team assignment.
                      Check the Team Workload page to identify available resources.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default HRStaffingRequests;
