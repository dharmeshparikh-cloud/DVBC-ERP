import React, { useState, useContext } from 'react';
import { AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Switch } from '../components/ui/switch';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  Shield, Users, Settings, Building2, Plus, Edit2, Trash2,
  CheckCircle, XCircle, ChevronRight, Save, AlertCircle,
  Lock, Eye, RefreshCw, Layers, UserCog, Crown
} from 'lucide-react';
import { toast } from 'sonner';
import { useFetch, useMutate } from '../hooks/useApi';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const RBACAdmin = () => {
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('roles');
  
  // Dialog states
  const [roleDialog, setRoleDialog] = useState(false);
  const [deptDialog, setDeptDialog] = useState(false);
  const [groupDialog, setGroupDialog] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [editingDept, setEditingDept] = useState(null);
  const [editingGroup, setEditingGroup] = useState(null);
  
  // Form states
  const [roleForm, setRoleForm] = useState({
    code: '',
    name: '',
    description: '',
    level: 50,
    department: '',
    can_approve: false,
    can_manage_users: false,
    inherits_from: [],
    permissions: []
  });
  
  const [deptForm, setDeptForm] = useState({
    code: '',
    name: '',
    color: '#6B7280'
  });

  const isAdmin = user?.role === 'admin';

  // Query: Fetch roles using centralized hook
  const { data: rolesData, isLoading: rolesLoading } = useFetch('/api/rbac/roles');

  // Query: Fetch departments using centralized hook
  const { data: deptsData } = useFetch('/api/rbac/departments');

  // Query: Fetch role groups using centralized hook
  const { data: groupsData } = useFetch('/api/rbac/role-groups');

  // Query: Fetch my permissions using centralized hook
  const { data: myPermissions } = useFetch('/api/rbac/my-permissions');

  const roles = rolesData?.roles || [];
  const departments = deptsData?.departments || [];
  const roleGroups = groupsData?.groups || [];
  const loading = rolesLoading;

  // Mutation: Refresh cache
  const refreshCacheMutation = useMutate('/api/rbac/refresh-cache', {
    method: 'post',
    onSuccess: () => {
      toast.success('RBAC cache refreshed successfully');
      queryClient.invalidateQueries({ queryKey: ['/api/rbac/roles'] });
      queryClient.invalidateQueries({ queryKey: ['/api/rbac/departments'] });
      queryClient.invalidateQueries({ queryKey: ['/api/rbac/role-groups'] });
    }
  });

  const refreshCache = () => {
    refreshCacheMutation.mutate({});
  };

  // Mutation: Save role - Using useMutation for dynamic endpoints
  const saveRoleMutation = useMutation({
    mutationFn: async () => {
      const isUpdate = !!editingRole;
      const url = isUpdate ? `${API}/api/rbac/roles/${editingRole.code}` : `${API}/api/rbac/roles`;
      return isUpdate 
        ? axios.put(url, roleForm)
        : axios.post(url, roleForm);
    },
    onSuccess: () => {
      toast.success(`Role ${editingRole ? 'updated' : 'created'} successfully`);
      setRoleDialog(false);
      queryClient.invalidateQueries({ queryKey: ['/api/rbac/roles'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to save role');
    }
  });

  // Mutation: Delete role
  const deleteRoleMutation = useMutation({
    mutationFn: async (roleCode) => {
      return axios.delete(`${API}/api/rbac/roles/${roleCode}`);
    },
    onSuccess: () => {
      toast.success('Role deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['/api/rbac/roles'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to delete role');
    }
  });

  // Mutation: Save department
  const saveDeptMutation = useMutation({
    mutationFn: async () => {
      const isUpdate = !!editingDept;
      const url = isUpdate ? `${API}/api/rbac/departments/${editingDept.code}` : `${API}/api/rbac/departments`;
      return isUpdate
        ? axios.put(url, deptForm)
        : axios.post(url, deptForm);
    },
    onSuccess: () => {
      toast.success(`Department ${editingDept ? 'updated' : 'created'} successfully`);
      setDeptDialog(false);
      queryClient.invalidateQueries({ queryKey: ['/api/rbac/departments'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to save department');
    }
  });

  // Mutation: Delete department
  const deleteDeptMutation = useMutation({
    mutationFn: async (deptCode) => {
      return axios.delete(`${API}/api/rbac/departments/${deptCode}`);
    },
    onSuccess: () => {
      toast.success('Department deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['/api/rbac/departments'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to delete department');
    }
  });

  // Role CRUD
  const openRoleDialog = (role = null) => {
    if (role) {
      setEditingRole(role);
      setRoleForm({
        code: role.code,
        name: role.name,
        description: role.description || '',
        level: role.level || 50,
        department: role.department || '',
        can_approve: role.can_approve || false,
        can_manage_users: role.can_manage_users || false,
        inherits_from: role.inherits_from || [],
        permissions: role.permissions || []
      });
    } else {
      setEditingRole(null);
      setRoleForm({
        code: '',
        name: '',
        description: '',
        level: 50,
        department: '',
        can_approve: false,
        can_manage_users: false,
        inherits_from: [],
        permissions: []
      });
    }
    setRoleDialog(true);
  };

  const saveRole = () => {
    saveRoleMutation.mutate();
  };

  const deleteRole = (roleCode) => {
    if (!confirm(`Are you sure you want to delete the role "${roleCode}"?`)) return;
    deleteRoleMutation.mutate(roleCode);
  };

  // Department CRUD
  const openDeptDialog = (dept = null) => {
    if (dept) {
      setEditingDept(dept);
      setDeptForm({
        code: dept.code,
        name: dept.name,
        color: dept.color || '#6B7280'
      });
    } else {
      setEditingDept(null);
      setDeptForm({ code: '', name: '', color: '#6B7280' });
    }
    setDeptDialog(true);
  };

  const saveDept = async () => {
    try {
      const isUpdate = !!editingDept;
      const url = isUpdate ? `${API}/rbac/departments/${editingDept.code}` : `${API}/rbac/departments`;
      const method = isUpdate ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: getAuthHeaders(),
        body: JSON.stringify(deptForm)
      });

      if (response.ok) {
        toast.success(`Department ${isUpdate ? 'updated' : 'created'} successfully`);
        setDeptDialog(false);
        fetchAllData();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to save department');
      }
    } catch (error) {
      toast.error('Failed to save department');
    }
  };

  // Role Group editing
  const openGroupDialog = (group) => {
    setEditingGroup(group);
    setGroupDialog(true);
  };

  const toggleRoleInGroup = async (roleCode) => {
    if (!editingGroup) return;
    
    const currentRoles = editingGroup.roles || [];
    const newRoles = currentRoles.includes(roleCode)
      ? currentRoles.filter(r => r !== roleCode)
      : [...currentRoles, roleCode];
    
    try {
      const response = await fetch(`${API}/rbac/role-groups/${editingGroup.code}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ roles: newRoles })
      });

      if (response.ok) {
        toast.success('Role group updated');
        setEditingGroup({ ...editingGroup, roles: newRoles });
        fetchAllData();
      }
    } catch (error) {
      toast.error('Failed to update group');
    }
  };

  const getLevelColor = (level) => {
    if (level >= 90) return 'bg-purple-100 text-purple-800 border-purple-300';
    if (level >= 70) return 'bg-blue-100 text-blue-800 border-blue-300';
    if (level >= 50) return 'bg-green-100 text-green-800 border-green-300';
    return 'bg-zinc-100 text-zinc-800 border-zinc-300';
  };

  const getDeptColor = (deptCode) => {
    const dept = departments.find(d => d.code === deptCode);
    return dept?.color || '#6B7280';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (!isAdmin && user?.role !== 'hr_manager') {
    return (
      <div className="p-6">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-6 flex items-center gap-3">
            <Lock className="w-6 h-6 text-red-500" />
            <div>
              <h3 className="font-semibold text-red-900">Access Denied</h3>
              <p className="text-red-700">You do not have permission to access RBAC Administration.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="rbac-admin-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 flex items-center gap-2">
            <Shield className="w-7 h-7" />
            RBAC Administration
          </h1>
          <p className="text-zinc-500 mt-1">Manage roles, permissions, and departments</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={refreshCache} data-testid="refresh-cache-btn">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh Cache
          </Button>
        </div>
      </div>

      {/* My Permissions Card */}
      {myPermissions && (
        <Card className="bg-zinc-50 border-zinc-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <Crown className="w-5 h-5 text-amber-500" />
                <span className="font-medium">Your Role:</span>
                <Badge variant="outline" className="font-mono">{myPermissions.role}</Badge>
              </div>
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-500" />
                <span className="font-medium">Level:</span>
                <Badge className={getLevelColor(myPermissions.level)}>{myPermissions.level}</Badge>
              </div>
              <div className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-green-500" />
                <span className="font-medium">Department:</span>
                <span>{myPermissions.department}</span>
              </div>
              {myPermissions.can_approve && (
                <Badge className="bg-green-100 text-green-800">Can Approve</Badge>
              )}
              {myPermissions.can_manage_users && (
                <Badge className="bg-blue-100 text-blue-800">Can Manage Users</Badge>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-zinc-100">
          <TabsTrigger value="roles" className="flex items-center gap-2">
            <UserCog className="w-4 h-4" />
            Roles ({roles.length})
          </TabsTrigger>
          <TabsTrigger value="departments" className="flex items-center gap-2">
            <Building2 className="w-4 h-4" />
            Departments ({departments.length})
          </TabsTrigger>
          <TabsTrigger value="groups" className="flex items-center gap-2">
            <Users className="w-4 h-4" />
            Role Groups ({roleGroups.length})
          </TabsTrigger>
        </TabsList>

        {/* Roles Tab */}
        <TabsContent value="roles" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <div>
                <CardTitle>System Roles</CardTitle>
                <CardDescription>Manage all roles and their permissions</CardDescription>
              </div>
              {isAdmin && (
                <Button onClick={() => openRoleDialog()} data-testid="create-role-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Create Role
                </Button>
              )}
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {roles.map(role => (
                  <div 
                    key={role.code} 
                    className="flex items-center justify-between p-4 bg-zinc-50 rounded-lg border border-zinc-200 hover:bg-zinc-100 transition-colors"
                    data-testid={`role-item-${role.code}`}
                  >
                    <div className="flex items-center gap-4">
                      <div 
                        className="w-2 h-12 rounded-full" 
                        style={{ backgroundColor: getDeptColor(role.department) }}
                      />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-zinc-900">{role.name}</span>
                          <Badge variant="outline" className="font-mono text-xs">{role.code}</Badge>
                        </div>
                        <p className="text-sm text-zinc-500">{role.description || 'No description'}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge className={getLevelColor(role.level)}>Level {role.level}</Badge>
                          <Badge variant="outline">{role.department}</Badge>
                          {role.can_approve && (
                            <Badge className="bg-green-100 text-green-700">Approver</Badge>
                          )}
                          {role.permissions?.includes('*') && (
                            <Badge className="bg-purple-100 text-purple-700">Full Access</Badge>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => openRoleDialog(role)}
                        data-testid={`edit-role-${role.code}`}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        View
                      </Button>
                      {isAdmin && role.code !== 'admin' && role.code !== 'client' && (
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="text-red-600 hover:text-red-700"
                          onClick={() => deleteRole(role.code)}
                          data-testid={`delete-role-${role.code}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Departments Tab */}
        <TabsContent value="departments" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <div>
                <CardTitle>Departments</CardTitle>
                <CardDescription>Organizational departments for role grouping</CardDescription>
              </div>
              {isAdmin && (
                <Button onClick={() => openDeptDialog()} data-testid="create-dept-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Create Department
                </Button>
              )}
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {departments.map(dept => (
                  <div 
                    key={dept.code}
                    className="p-4 border rounded-lg bg-white hover:shadow-md transition-shadow"
                    data-testid={`dept-item-${dept.code}`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <div 
                        className="w-4 h-4 rounded-full" 
                        style={{ backgroundColor: dept.color }}
                      />
                      <span className="font-semibold">{dept.name}</span>
                    </div>
                    <Badge variant="outline" className="font-mono text-xs mb-3">{dept.code}</Badge>
                    <div className="text-sm text-zinc-500">
                      {roles.filter(r => r.department === dept.code).length} roles
                    </div>
                    {isAdmin && (
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="mt-3"
                        onClick={() => openDeptDialog(dept)}
                      >
                        <Edit2 className="w-3 h-3 mr-1" />
                        Edit
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Role Groups Tab */}
        <TabsContent value="groups" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Role Groups</CardTitle>
              <CardDescription>
                Pre-defined groups of roles for access control (used throughout the system)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {roleGroups.map(group => (
                  <div 
                    key={group.code}
                    className="p-4 border rounded-lg bg-zinc-50"
                    data-testid={`group-item-${group.code}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="font-semibold">{group.name || group.code}</span>
                        <Badge variant="outline" className="ml-2 font-mono text-xs">{group.code}</Badge>
                      </div>
                      {isAdmin && (
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => openGroupDialog(group)}
                        >
                          <Edit2 className="w-3 h-3 mr-1" />
                          Edit Roles
                        </Button>
                      )}
                    </div>
                    <p className="text-sm text-zinc-500 mb-2">{group.description || 'No description'}</p>
                    <div className="flex flex-wrap gap-1">
                      {(group.roles || []).map(roleCode => (
                        <Badge key={roleCode} variant="secondary" className="text-xs">
                          {roleCode}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Role Dialog */}
      <Dialog open={roleDialog} onOpenChange={setRoleDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingRole ? 'Edit Role' : 'Create New Role'}</DialogTitle>
            <DialogDescription>
              {editingRole 
                ? 'Modify role properties and permissions'
                : 'Define a new role with specific permissions'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Role Code</Label>
                <Input 
                  value={roleForm.code}
                  onChange={(e) => setRoleForm({...roleForm, code: e.target.value.toLowerCase().replace(/[^a-z_]/g, '')})}
                  placeholder="e.g. sales_lead"
                  disabled={!!editingRole}
                  data-testid="role-code-input"
                />
                <p className="text-xs text-zinc-500">Lowercase letters and underscores only</p>
              </div>
              <div className="space-y-2">
                <Label>Display Name</Label>
                <Input 
                  value={roleForm.name}
                  onChange={(e) => setRoleForm({...roleForm, name: e.target.value})}
                  placeholder="e.g. Sales Lead"
                  data-testid="role-name-input"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea 
                value={roleForm.description}
                onChange={(e) => setRoleForm({...roleForm, description: e.target.value})}
                placeholder="Describe the role's responsibilities..."
                rows={2}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Department</Label>
                <Select 
                  value={roleForm.department} 
                  onValueChange={(v) => setRoleForm({...roleForm, department: v})}
                >
                  <SelectTrigger data-testid="role-dept-select">
                    <SelectValue placeholder="Select department" />
                  </SelectTrigger>
                  <SelectContent>
                    {departments.map(d => (
                      <SelectItem key={d.code} value={d.code}>{d.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Hierarchy Level (1-100)</Label>
                <Input 
                  type="number"
                  min={1}
                  max={100}
                  value={roleForm.level}
                  onChange={(e) => setRoleForm({...roleForm, level: parseInt(e.target.value) || 50})}
                  data-testid="role-level-input"
                />
                <p className="text-xs text-zinc-500">Higher = more access</p>
              </div>
            </div>

            <div className="flex items-center gap-6 py-2">
              <div className="flex items-center gap-2">
                <Switch 
                  checked={roleForm.can_approve}
                  onCheckedChange={(v) => setRoleForm({...roleForm, can_approve: v})}
                  data-testid="role-can-approve-switch"
                />
                <Label>Can Approve Requests</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch 
                  checked={roleForm.can_manage_users}
                  onCheckedChange={(v) => setRoleForm({...roleForm, can_manage_users: v})}
                  data-testid="role-can-manage-switch"
                />
                <Label>Can Manage Users</Label>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Inherits From (Optional)</Label>
              <div className="flex flex-wrap gap-2">
                {roles.filter(r => r.code !== roleForm.code).map(r => (
                  <Badge 
                    key={r.code}
                    variant={roleForm.inherits_from.includes(r.code) ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => {
                      const newInherits = roleForm.inherits_from.includes(r.code)
                        ? roleForm.inherits_from.filter(x => x !== r.code)
                        : [...roleForm.inherits_from, r.code];
                      setRoleForm({...roleForm, inherits_from: newInherits});
                    }}
                  >
                    {r.code}
                  </Badge>
                ))}
              </div>
              <p className="text-xs text-zinc-500">Click to toggle inheritance</p>
            </div>

            <div className="space-y-2">
              <Label>Permissions</Label>
              <Textarea 
                value={roleForm.permissions.join(', ')}
                onChange={(e) => setRoleForm({
                  ...roleForm, 
                  permissions: e.target.value.split(',').map(p => p.trim()).filter(Boolean)
                })}
                placeholder="e.g. leads.own, meetings.create, projects.view"
                rows={3}
              />
              <p className="text-xs text-zinc-500">
                Comma-separated. Use wildcards like "hr.*" for all HR permissions. Use "*" for full access.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setRoleDialog(false)}>Cancel</Button>
            <Button onClick={saveRole} disabled={!roleForm.code || !roleForm.name} data-testid="save-role-btn">
              <Save className="w-4 h-4 mr-2" />
              {editingRole ? 'Update Role' : 'Create Role'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Department Dialog */}
      <Dialog open={deptDialog} onOpenChange={setDeptDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingDept ? 'Edit Department' : 'Create New Department'}</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Department Code</Label>
              <Input 
                value={deptForm.code}
                onChange={(e) => setDeptForm({...deptForm, code: e.target.value})}
                placeholder="e.g. Marketing"
                disabled={!!editingDept}
              />
            </div>
            <div className="space-y-2">
              <Label>Display Name</Label>
              <Input 
                value={deptForm.name}
                onChange={(e) => setDeptForm({...deptForm, name: e.target.value})}
                placeholder="e.g. Marketing & Communications"
              />
            </div>
            <div className="space-y-2">
              <Label>Color</Label>
              <div className="flex items-center gap-3">
                <input 
                  type="color"
                  value={deptForm.color}
                  onChange={(e) => setDeptForm({...deptForm, color: e.target.value})}
                  className="w-10 h-10 rounded cursor-pointer"
                />
                <Input 
                  value={deptForm.color}
                  onChange={(e) => setDeptForm({...deptForm, color: e.target.value})}
                  className="w-28 font-mono"
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDeptDialog(false)}>Cancel</Button>
            <Button onClick={saveDept} disabled={!deptForm.code || !deptForm.name}>
              <Save className="w-4 h-4 mr-2" />
              {editingDept ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Role Group Dialog */}
      <Dialog open={groupDialog} onOpenChange={setGroupDialog}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Edit Role Group: {editingGroup?.code}</DialogTitle>
            <DialogDescription>
              Click on roles to add or remove them from this group
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <p className="text-sm text-zinc-500 mb-3">{editingGroup?.description}</p>
            <div className="flex flex-wrap gap-2">
              {roles.map(role => (
                <Badge 
                  key={role.code}
                  variant={editingGroup?.roles?.includes(role.code) ? 'default' : 'outline'}
                  className="cursor-pointer text-sm py-1 px-3"
                  onClick={() => toggleRoleInGroup(role.code)}
                >
                  {editingGroup?.roles?.includes(role.code) && (
                    <CheckCircle className="w-3 h-3 mr-1" />
                  )}
                  {role.code}
                </Badge>
              ))}
            </div>
          </div>

          <DialogFooter>
            <Button onClick={() => setGroupDialog(false)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default RBACAdmin;
