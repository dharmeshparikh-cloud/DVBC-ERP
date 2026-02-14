import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { 
  Users, Shield, Plus, Edit2, Trash2, Search, Check, X, 
  ChevronDown, ChevronUp, Settings, UserPlus, Key, Save
} from 'lucide-react';
import { toast } from 'sonner';

const UserManagement = () => {
  const { user } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRole, setSelectedRole] = useState('');
  
  // Dialogs
  const [createUserDialog, setCreateUserDialog] = useState(false);
  const [editRoleDialog, setEditRoleDialog] = useState(false);
  const [createRoleDialog, setCreateRoleDialog] = useState(false);
  const [permissionsDialog, setPermissionsDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedRoleData, setSelectedRoleData] = useState(null);
  
  // Form data
  const [newUserData, setNewUserData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'consultant',
    department: ''
  });
  
  const [newRoleData, setNewRoleData] = useState({
    id: '',
    name: '',
    description: ''
  });
  
  const [permissionModules, setPermissionModules] = useState(null);
  const [editingPermissions, setEditingPermissions] = useState({});
  
  const isAdmin = user?.role === 'admin';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [usersRes, rolesRes] = await Promise.all([
        axios.get(`${API}/users-with-roles`),
        axios.get(`${API}/roles`)
      ]);
      setUsers(usersRes.data || []);
      setRoles(rolesRes.data || []);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const fetchPermissionModules = async () => {
    if (permissionModules) return permissionModules;
    try {
      const res = await axios.get(`${API}/permission-modules`);
      setPermissionModules(res.data);
      return res.data;
    } catch (error) {
      toast.error('Failed to load permission modules');
      return null;
    }
  };

  const handleCreateUser = async () => {
    if (!newUserData.email || !newUserData.password || !newUserData.full_name) {
      toast.error('Please fill in all required fields');
      return;
    }
    
    try {
      await axios.post(`${API}/auth/register`, newUserData);
      toast.success('User created successfully');
      setCreateUserDialog(false);
      setNewUserData({ email: '', password: '', full_name: '', role: 'consultant', department: '' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleUpdateUserRole = async (userId, newRole) => {
    try {
      await axios.patch(`${API}/users/${userId}/role?role=${newRole}`);
      toast.success('User role updated');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleCreateRole = async () => {
    if (!newRoleData.id || !newRoleData.name) {
      toast.error('Role ID and Name are required');
      return;
    }
    
    // Convert name to snake_case ID if not provided properly
    const roleId = newRoleData.id.toLowerCase().replace(/\s+/g, '_');
    
    try {
      await axios.post(`${API}/roles`, {
        id: roleId,
        name: newRoleData.name,
        description: newRoleData.description
      });
      toast.success('Role created successfully');
      setCreateRoleDialog(false);
      setNewRoleData({ id: '', name: '', description: '' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create role');
    }
  };

  const handleDeleteRole = async (roleId) => {
    if (!window.confirm(`Are you sure you want to delete role "${roleId}"?`)) return;
    
    try {
      await axios.delete(`${API}/roles/${roleId}`);
      toast.success('Role deleted');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete role');
    }
  };

  const openPermissionsDialog = async (role) => {
    setSelectedRoleData(role);
    await fetchPermissionModules();
    
    // Get current permissions for this role
    try {
      const res = await axios.get(`${API}/roles/${role.id}`);
      setEditingPermissions(res.data.permissions || {});
      setPermissionsDialog(true);
    } catch (error) {
      toast.error('Failed to load role permissions');
    }
  };

  const handlePermissionChange = (module, action, value) => {
    setEditingPermissions(prev => ({
      ...prev,
      [module]: {
        ...prev[module],
        [action]: value
      }
    }));
  };

  const savePermissions = async () => {
    try {
      await axios.patch(`${API}/roles/${selectedRoleData.id}`, {
        permissions: editingPermissions
      });
      toast.success('Permissions saved successfully');
      setPermissionsDialog(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save permissions');
    }
  };

  const filteredUsers = users.filter(u => {
    const matchesSearch = !searchTerm || 
      u.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.email?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = !selectedRole || u.role === selectedRole;
    return matchesSearch && matchesRole;
  });

  const getRoleBadgeColor = (role) => {
    const colors = {
      admin: 'bg-red-100 text-red-700 border-red-200',
      manager: 'bg-blue-100 text-blue-700 border-blue-200',
      executive: 'bg-emerald-100 text-emerald-700 border-emerald-200',
      consultant: 'bg-purple-100 text-purple-700 border-purple-200',
      principal_consultant: 'bg-amber-100 text-amber-700 border-amber-200',
      project_manager: 'bg-cyan-100 text-cyan-700 border-cyan-200',
      lean_consultant: 'bg-indigo-100 text-indigo-700 border-indigo-200',
      lead_consultant: 'bg-violet-100 text-violet-700 border-violet-200',
      senior_consultant: 'bg-fuchsia-100 text-fuchsia-700 border-fuchsia-200',
      hr_executive: 'bg-pink-100 text-pink-700 border-pink-200',
      hr_manager: 'bg-rose-100 text-rose-700 border-rose-200',
      account_manager: 'bg-orange-100 text-orange-700 border-orange-200',
      subject_matter_expert: 'bg-teal-100 text-teal-700 border-teal-200'
    };
    return colors[role] || 'bg-zinc-100 text-zinc-700 border-zinc-200';
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96"><div className="text-zinc-500">Loading...</div></div>;
  }

  return (
    <div data-testid="user-management-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
          User Management
        </h1>
        <p className="text-zinc-500">Manage users, roles, and permissions</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-zinc-200 mb-6">
        <button
          onClick={() => setActiveTab('users')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'users' 
              ? 'border-zinc-950 text-zinc-950' 
              : 'border-transparent text-zinc-500 hover:text-zinc-950'
          }`}
          data-testid="tab-users"
        >
          <Users className="w-4 h-4 inline mr-2" />
          Users ({users.length})
        </button>
        <button
          onClick={() => setActiveTab('roles')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'roles' 
              ? 'border-zinc-950 text-zinc-950' 
              : 'border-transparent text-zinc-500 hover:text-zinc-950'
          }`}
          data-testid="tab-roles"
        >
          <Shield className="w-4 h-4 inline mr-2" />
          Roles ({roles.length})
        </button>
      </div>

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div>
          {/* Search and Filters */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="relative w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                <Input
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search users..."
                  className="pl-10 rounded-sm"
                />
              </div>
              <select
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value)}
                className="h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
              >
                <option value="">All Roles</option>
                {roles.map(role => (
                  <option key={role.id} value={role.id}>{role.name}</option>
                ))}
              </select>
            </div>
            {isAdmin && (
              <Button 
                onClick={() => setCreateUserDialog(true)}
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                <UserPlus className="w-4 h-4 mr-2" />
                Add User
              </Button>
            )}
          </div>

          {/* Users Table */}
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="p-0">
              <table className="w-full">
                <thead>
                  <tr className="bg-zinc-50 text-xs font-medium uppercase tracking-wide text-zinc-500">
                    <th className="px-4 py-3 text-left">User</th>
                    <th className="px-4 py-3 text-left">Email</th>
                    <th className="px-4 py-3 text-left">Department</th>
                    <th className="px-4 py-3 text-left">Role</th>
                    <th className="px-4 py-3 text-left">Status</th>
                    {isAdmin && <th className="px-4 py-3 text-left">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map(u => (
                    <tr key={u.id} className="border-b border-zinc-100 hover:bg-zinc-50" data-testid={`user-row-${u.id}`}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-zinc-200 flex items-center justify-center text-xs font-medium text-zinc-600">
                            {u.full_name?.charAt(0)?.toUpperCase()}
                          </div>
                          <span className="font-medium text-zinc-900">{u.full_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-zinc-600">{u.email}</td>
                      <td className="px-4 py-3 text-sm text-zinc-600">{u.department || '-'}</td>
                      <td className="px-4 py-3">
                        {isAdmin ? (
                          <select
                            value={u.role}
                            onChange={(e) => handleUpdateUserRole(u.id, e.target.value)}
                            className={`h-8 px-2 text-xs rounded border ${getRoleBadgeColor(u.role)}`}
                            data-testid={`role-select-${u.id}`}
                          >
                            {roles.map(role => (
                              <option key={role.id} value={role.id}>{role.name}</option>
                            ))}
                          </select>
                        ) : (
                          <span className={`px-2 py-1 text-xs font-medium rounded border ${getRoleBadgeColor(u.role)}`}>
                            {u.role?.replace('_', ' ')}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs rounded ${
                          u.is_active !== false ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
                        }`}>
                          {u.is_active !== false ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      {isAdmin && (
                        <td className="px-4 py-3">
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <Edit2 className="w-4 h-4 text-zinc-500" />
                          </Button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredUsers.length === 0 && (
                <div className="text-center py-12 text-zinc-400">
                  No users found
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Roles Tab */}
      {activeTab === 'roles' && (
        <div>
          <div className="flex items-center justify-between mb-6">
            <p className="text-sm text-zinc-500">
              Configure roles and their permissions. System roles cannot be deleted.
            </p>
            {isAdmin && (
              <Button 
                onClick={() => setCreateRoleDialog(true)}
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create Role
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {roles.map(role => (
              <Card key={role.id} className="border-zinc-200 shadow-none rounded-sm" data-testid={`role-card-${role.id}`}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-semibold text-zinc-950">
                      {role.name}
                    </CardTitle>
                    {role.is_system_role && (
                      <span className="text-xs px-2 py-1 bg-zinc-100 text-zinc-600 rounded">System</span>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-zinc-500 mb-4">{role.description || 'No description'}</p>
                  
                  {/* Users count with this role */}
                  <div className="text-xs text-zinc-400 mb-4">
                    <Users className="w-3 h-3 inline mr-1" />
                    {users.filter(u => u.role === role.id).length} user(s)
                  </div>

                  <div className="flex items-center gap-2">
                    {isAdmin && (
                      <>
                        <Button
                          onClick={() => openPermissionsDialog(role)}
                          variant="outline"
                          size="sm"
                          className="flex-1 rounded-sm"
                        >
                          <Key className="w-3 h-3 mr-1" />
                          Permissions
                        </Button>
                        {role.can_delete && (
                          <Button
                            onClick={() => handleDeleteRole(role.id)}
                            variant="ghost"
                            size="sm"
                            className="text-red-500 hover:text-red-700 rounded-sm"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Create User Dialog */}
      <Dialog open={createUserDialog} onOpenChange={setCreateUserDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Add New User
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Full Name *</Label>
              <Input
                value={newUserData.full_name}
                onChange={(e) => setNewUserData({ ...newUserData, full_name: e.target.value })}
                placeholder="John Doe"
                className="rounded-sm"
              />
            </div>
            <div className="space-y-2">
              <Label>Email *</Label>
              <Input
                type="email"
                value={newUserData.email}
                onChange={(e) => setNewUserData({ ...newUserData, email: e.target.value })}
                placeholder="john@company.com"
                className="rounded-sm"
              />
            </div>
            <div className="space-y-2">
              <Label>Password *</Label>
              <Input
                type="password"
                value={newUserData.password}
                onChange={(e) => setNewUserData({ ...newUserData, password: e.target.value })}
                placeholder="••••••••"
                className="rounded-sm"
              />
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <select
                value={newUserData.role}
                onChange={(e) => setNewUserData({ ...newUserData, role: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
              >
                {roles.map(role => (
                  <option key={role.id} value={role.id}>{role.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Department</Label>
              <Input
                value={newUserData.department}
                onChange={(e) => setNewUserData({ ...newUserData, department: e.target.value })}
                placeholder="Consulting"
                className="rounded-sm"
              />
            </div>
            <div className="flex gap-3 pt-4">
              <Button onClick={() => setCreateUserDialog(false)} variant="outline" className="flex-1 rounded-sm">
                Cancel
              </Button>
              <Button onClick={handleCreateUser} className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                Create User
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Create Role Dialog */}
      <Dialog open={createRoleDialog} onOpenChange={setCreateRoleDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Create New Role
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Role ID *</Label>
              <Input
                value={newRoleData.id}
                onChange={(e) => setNewRoleData({ ...newRoleData, id: e.target.value.toLowerCase().replace(/\s+/g, '_') })}
                placeholder="custom_role"
                className="rounded-sm"
              />
              <p className="text-xs text-zinc-400">Lowercase, use underscores for spaces</p>
            </div>
            <div className="space-y-2">
              <Label>Role Name *</Label>
              <Input
                value={newRoleData.name}
                onChange={(e) => setNewRoleData({ ...newRoleData, name: e.target.value })}
                placeholder="Custom Role"
                className="rounded-sm"
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <textarea
                value={newRoleData.description}
                onChange={(e) => setNewRoleData({ ...newRoleData, description: e.target.value })}
                rows={3}
                placeholder="Describe what this role does..."
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950 text-sm"
              />
            </div>
            <div className="flex gap-3 pt-4">
              <Button onClick={() => setCreateRoleDialog(false)} variant="outline" className="flex-1 rounded-sm">
                Cancel
              </Button>
              <Button onClick={handleCreateRole} className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                Create Role
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Permissions Dialog */}
      <Dialog open={permissionsDialog} onOpenChange={setPermissionsDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Permissions: {selectedRoleData?.name}
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Configure module access and actions for this role
            </DialogDescription>
          </DialogHeader>
          
          {permissionModules && (
            <div className="space-y-4 mt-4">
              {permissionModules.modules.map(module => {
                const modulePerms = editingPermissions[module.id] || {};
                const actions = permissionModules.actions[module.id] || permissionModules.actions.common;
                
                return (
                  <div key={module.id} className="p-4 border border-zinc-200 rounded-sm">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h4 className="font-medium text-zinc-950">{module.name}</h4>
                        <p className="text-xs text-zinc-500">{module.description}</p>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {actions.map(action => (
                        <button
                          key={action}
                          onClick={() => handlePermissionChange(module.id, action, !modulePerms[action])}
                          className={`flex items-center gap-1 px-3 py-1.5 text-xs rounded-sm border transition-colors ${
                            modulePerms[action] 
                              ? 'bg-emerald-50 border-emerald-300 text-emerald-700'
                              : 'bg-zinc-50 border-zinc-200 text-zinc-500 hover:border-zinc-400'
                          }`}
                        >
                          {modulePerms[action] ? (
                            <Check className="w-3 h-3" />
                          ) : (
                            <X className="w-3 h-3" />
                          )}
                          <span className="capitalize">{action.replace('_', ' ')}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
              
              <div className="flex justify-end gap-3 pt-4 border-t border-zinc-200">
                <Button onClick={() => setPermissionsDialog(false)} variant="outline" className="rounded-sm">
                  Cancel
                </Button>
                <Button onClick={savePermissions} className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                  <Save className="w-4 h-4 mr-2" />
                  Save Permissions
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default UserManagement;
