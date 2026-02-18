import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Switch } from '../components/ui/switch';
import { Textarea } from '../components/ui/textarea';
import { 
  Shield, Users, Settings, CheckCircle, XCircle, Clock,
  ChevronRight, Save, AlertCircle, User, Building2, Briefcase,
  Lock, Unlock
} from 'lucide-react';
import { toast } from 'sonner';

const PERMISSION_LABELS = {
  can_view_own_data: 'View Own Data',
  can_edit_own_profile: 'Edit Own Profile',
  can_submit_requests: 'Submit Requests',
  can_view_team_data: 'View Team Data',
  can_approve_requests: 'Approve Requests',
  can_manage_team: 'Manage Team',
  can_access_reports: 'Access Reports',
  can_access_financials: 'Access Financial Data',
  can_create_projects: 'Create Projects',
  can_assign_tasks: 'Assign Tasks',
};

const RoleManagement = () => {
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('requests');
  const [stats, setStats] = useState(null);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [levelPermissions, setLevelPermissions] = useState({});
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [approvalDialog, setApprovalDialog] = useState(false);
  const [approvalComments, setApprovalComments] = useState('');
  const [permissionsDialog, setPermissionsDialog] = useState(false);
  const [editingLevel, setEditingLevel] = useState(null);
  const [editingPermissions, setEditingPermissions] = useState({});

  const isAdmin = user?.role === 'admin';
  const isHR = ['hr_manager', 'hr_executive'].includes(user?.role);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const [statsRes, requestsRes, permissionsRes] = await Promise.all([
        fetch(`${API}/role-management/stats`, { headers }),
        fetch(`${API}/role-management/role-requests/pending`, { headers }),
        fetch(`${API}/role-management/level-permissions`, { headers })
      ]);

      if (statsRes.ok) setStats(await statsRes.json());
      if (requestsRes.ok) setPendingRequests(await requestsRes.json());
      if (permissionsRes.ok) setLevelPermissions(await permissionsRes.json());
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveRequest = async (approved) => {
    if (!selectedRequest) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/role-management/role-requests/${selectedRequest.id}/approve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          approved,
          comments: approvalComments
        })
      });

      if (response.ok) {
        toast.success(`Request ${approved ? 'approved' : 'rejected'} successfully`);
        setApprovalDialog(false);
        setSelectedRequest(null);
        setApprovalComments('');
        fetchData();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to process request');
      }
    } catch (error) {
      toast.error('Error processing request');
    }
  };

  const handleUpdatePermissions = async () => {
    if (!editingLevel) return;

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/role-management/level-permissions`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          level: editingLevel,
          permissions: editingPermissions
        })
      });

      if (response.ok) {
        toast.success('Permissions updated successfully');
        setPermissionsDialog(false);
        setEditingLevel(null);
        fetchData();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to update permissions');
      }
    } catch (error) {
      toast.error('Error updating permissions');
    }
  };

  const openPermissionsEditor = (level) => {
    setEditingLevel(level);
    setEditingPermissions({ ...levelPermissions[level] });
    setPermissionsDialog(true);
  };

  const getLevelColor = (level) => {
    switch (level) {
      case 'leader': return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400';
      case 'manager': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
      default: return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="role-management-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="w-6 h-6 text-orange-500" />
            Role & Permission Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage employee levels, roles, and permission configurations
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                  <Clock className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.requests?.pending || 0}</p>
                  <p className="text-sm text-muted-foreground">Pending Requests</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.requests?.approved || 0}</p>
                  <p className="text-sm text-muted-foreground">Approved</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <Users className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {(stats.employees_by_level?.executive || 0) + 
                     (stats.employees_by_level?.manager || 0) + 
                     (stats.employees_by_level?.leader || 0)}
                  </p>
                  <p className="text-sm text-muted-foreground">With Levels</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                  <Briefcase className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.roles?.custom || 0}</p>
                  <p className="text-sm text-muted-foreground">Custom Roles</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="requests" className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Pending Requests
            {pendingRequests.length > 0 && (
              <Badge variant="destructive" className="ml-1">{pendingRequests.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="levels" className="flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Level Permissions
          </TabsTrigger>
        </TabsList>

        {/* Pending Requests Tab */}
        <TabsContent value="requests" className="mt-4">
          {pendingRequests.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium">All Caught Up!</h3>
                <p className="text-muted-foreground mt-2">
                  No pending role requests at the moment.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {pendingRequests.map((request) => (
                <Card key={request.id} className="hover:border-orange-200 transition-colors">
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="outline" className="capitalize">
                            {request.request_type === 'create_role' ? 'New Role' : 'Role Assignment'}
                          </Badge>
                          <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                            Pending
                          </Badge>
                        </div>
                        
                        {request.request_type === 'create_role' ? (
                          <div>
                            <h3 className="font-medium text-lg">{request.role_name}</h3>
                            <p className="text-sm text-muted-foreground">{request.role_description}</p>
                            <p className="text-xs text-muted-foreground mt-2">
                              Role ID: <code className="bg-muted px-1 rounded">{request.role_id}</code>
                            </p>
                          </div>
                        ) : (
                          <div>
                            <h3 className="font-medium text-lg">
                              Assign {request.new_role_name} to {request.employee_name}
                            </h3>
                            <div className="flex items-center gap-4 mt-2 text-sm">
                              <span className="flex items-center gap-1">
                                <User className="w-4 h-4" />
                                {request.employee_code}
                              </span>
                              <span className="flex items-center gap-1">
                                <Briefcase className="w-4 h-4" />
                                {request.current_role || 'No Role'} → {request.new_role_name}
                              </span>
                              <Badge className={getLevelColor(request.level)}>
                                Level: {request.level}
                              </Badge>
                            </div>
                          </div>
                        )}

                        {request.reason && (
                          <p className="text-sm bg-muted p-2 rounded mt-2">
                            <strong>Reason:</strong> {request.reason}
                          </p>
                        )}

                        <p className="text-xs text-muted-foreground mt-3">
                          Submitted by {request.submitted_by_name} on{' '}
                          {new Date(request.submitted_at).toLocaleDateString()}
                        </p>
                      </div>

                      <div className="flex gap-2 ml-4">
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-red-600 hover:bg-red-50"
                          onClick={() => {
                            setSelectedRequest(request);
                            setApprovalDialog(true);
                          }}
                          data-testid={`reject-request-${request.id}`}
                        >
                          <XCircle className="w-4 h-4 mr-1" />
                          Reject
                        </Button>
                        <Button
                          size="sm"
                          className="bg-green-600 hover:bg-green-700"
                          onClick={() => {
                            setSelectedRequest(request);
                            setApprovalDialog(true);
                          }}
                          data-testid={`approve-request-${request.id}`}
                        >
                          <CheckCircle className="w-4 h-4 mr-1" />
                          Approve
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Level Permissions Tab */}
        <TabsContent value="levels" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {['executive', 'manager', 'leader'].map((level) => (
              <Card key={level} className="hover:border-orange-200 transition-colors">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg capitalize flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${
                        level === 'leader' ? 'bg-purple-500' :
                        level === 'manager' ? 'bg-blue-500' : 'bg-gray-400'
                      }`} />
                      {level}
                    </CardTitle>
                    {isAdmin && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openPermissionsEditor(level)}
                        data-testid={`edit-${level}-permissions`}
                      >
                        <Settings className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                  <CardDescription>
                    {level === 'executive' && 'Entry level - basic permissions'}
                    {level === 'manager' && 'Mid level - team management'}
                    {level === 'leader' && 'Senior level - strategic access'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(levelPermissions[level] || {}).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">
                          {PERMISSION_LABELS[key] || key}
                        </span>
                        {value ? (
                          <Unlock className="w-4 h-4 text-green-500" />
                        ) : (
                          <Lock className="w-4 h-4 text-gray-400" />
                        )}
                      </div>
                    ))}
                  </div>
                  
                  {stats?.employees_by_level && (
                    <div className="mt-4 pt-4 border-t">
                      <p className="text-sm text-muted-foreground">
                        <Users className="w-4 h-4 inline mr-1" />
                        {stats.employees_by_level[level] || 0} employees at this level
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Approval Dialog */}
      <Dialog open={approvalDialog} onOpenChange={setApprovalDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Review Request</DialogTitle>
            <DialogDescription>
              {selectedRequest?.request_type === 'create_role' 
                ? `Review request to create role: ${selectedRequest?.role_name}`
                : `Review request to assign ${selectedRequest?.new_role_name} to ${selectedRequest?.employee_name}`
              }
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Comments (optional)</Label>
              <Textarea
                placeholder="Add any comments for the requester..."
                value={approvalComments}
                onChange={(e) => setApprovalComments(e.target.value)}
                data-testid="approval-comments"
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setApprovalDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => handleApproveRequest(false)}
              data-testid="confirm-reject"
            >
              <XCircle className="w-4 h-4 mr-1" />
              Reject
            </Button>
            <Button
              className="bg-green-600 hover:bg-green-700"
              onClick={() => handleApproveRequest(true)}
              data-testid="confirm-approve"
            >
              <CheckCircle className="w-4 h-4 mr-1" />
              Approve
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Permissions Dialog */}
      <Dialog open={permissionsDialog} onOpenChange={setPermissionsDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="capitalize">
              Edit {editingLevel} Level Permissions
            </DialogTitle>
            <DialogDescription>
              Configure what employees at this level can do
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4 max-h-[400px] overflow-y-auto">
            {Object.entries(editingPermissions).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <Label htmlFor={key} className="cursor-pointer">
                  {PERMISSION_LABELS[key] || key}
                </Label>
                <Switch
                  id={key}
                  checked={value}
                  onCheckedChange={(checked) => 
                    setEditingPermissions(prev => ({ ...prev, [key]: checked }))
                  }
                  data-testid={`perm-switch-${key}`}
                />
              </div>
            ))}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setPermissionsDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdatePermissions} data-testid="save-permissions">
              <Save className="w-4 h-4 mr-1" />
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default RoleManagement;
