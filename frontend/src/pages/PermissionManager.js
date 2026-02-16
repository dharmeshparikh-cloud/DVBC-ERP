import React, { useState, useEffect, useContext } from 'react';
import { AuthContext, API } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from '../components/ui/dialog';
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger
} from '../components/ui/accordion';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import {
  Shield, Users, Settings, Lock, Unlock, Save, RotateCcw,
  CheckCircle, XCircle, ChevronRight, Plus, Trash2, Copy,
  Building2, FileText, DollarSign, Calendar, BarChart3,
  Briefcase, UserCog, ClipboardList, Receipt, AlertTriangle
} from 'lucide-react';

// Module definitions with their features
const MODULE_DEFINITIONS = {
  sales: {
    name: 'Sales',
    icon: DollarSign,
    color: 'text-orange-600 bg-orange-50',
    features: {
      leads: { name: 'Leads Management', actions: ['create', 'read', 'update', 'delete', 'assign', 'import', 'export'] },
      pricing_plans: { name: 'Pricing Plans', actions: ['create', 'read', 'update', 'delete', 'clone'] },
      sow: { name: 'SOW Builder', actions: ['create', 'read', 'update', 'delete', 'freeze', 'send_to_client'] },
      quotations: { name: 'Quotations', actions: ['create', 'read', 'update', 'delete', 'send', 'download'] },
      agreements: { name: 'Agreements', actions: ['create', 'read', 'update', 'delete', 'approve', 'sign'] },
      meetings: { name: 'Sales Meetings', actions: ['create', 'read', 'update', 'delete', 'generate_mom'] },
      kickoff: { name: 'Kickoff Requests', actions: ['create', 'read', 'approve', 'reject'] }
    }
  },
  consulting: {
    name: 'Consulting',
    icon: Briefcase,
    color: 'text-blue-600 bg-blue-50',
    features: {
      projects: { name: 'Projects', actions: ['create', 'read', 'update', 'delete', 'assign_team'] },
      tasks: { name: 'Tasks', actions: ['create', 'read', 'update', 'delete', 'assign'] },
      timesheets: { name: 'Timesheets', actions: ['create', 'read', 'update', 'approve'] },
      deliverables: { name: 'Deliverables', actions: ['create', 'read', 'update', 'delete', 'upload'] },
      sow_changes: { name: 'SOW Change Requests', actions: ['create', 'read', 'approve', 'reject'] }
    }
  },
  hr: {
    name: 'HR',
    icon: Users,
    color: 'text-green-600 bg-green-50',
    features: {
      employees: { name: 'Employees', actions: ['create', 'read', 'update', 'delete', 'view_salary'] },
      attendance: { name: 'Attendance', actions: ['read', 'update', 'approve', 'export'] },
      leaves: { name: 'Leave Management', actions: ['create', 'read', 'approve', 'reject', 'cancel'] },
      payroll: { name: 'Payroll', actions: ['read', 'process', 'approve', 'export'] },
      expenses: { name: 'Expenses', actions: ['create', 'read', 'approve', 'reject', 'reimburse'] }
    }
  },
  finance: {
    name: 'Finance',
    icon: Receipt,
    color: 'text-purple-600 bg-purple-50',
    features: {
      invoices: { name: 'Invoices', actions: ['create', 'read', 'update', 'delete', 'send'] },
      payments: { name: 'Payments', actions: ['read', 'record', 'reconcile'] },
      reports: { name: 'Financial Reports', actions: ['view', 'export', 'download'] }
    }
  },
  admin: {
    name: 'Administration',
    icon: Settings,
    color: 'text-zinc-600 bg-zinc-50',
    features: {
      users: { name: 'User Management', actions: ['create', 'read', 'update', 'delete', 'manage_roles'] },
      roles: { name: 'Role Management', actions: ['create', 'read', 'update', 'delete'] },
      permissions: { name: 'Permission Management', actions: ['read', 'update'] },
      masters: { name: 'Master Data', actions: ['create', 'read', 'update', 'delete'] },
      audit_logs: { name: 'Audit Logs', actions: ['read', 'export'] }
    }
  }
};

const ACTION_LABELS = {
  create: 'Create',
  read: 'View',
  update: 'Edit',
  delete: 'Delete',
  assign: 'Assign',
  approve: 'Approve',
  reject: 'Reject',
  import: 'Import',
  export: 'Export',
  clone: 'Clone',
  freeze: 'Freeze',
  send: 'Send',
  send_to_client: 'Send to Client',
  download: 'Download',
  sign: 'Sign',
  generate_mom: 'Generate MOM',
  assign_team: 'Assign Team',
  upload: 'Upload',
  view_salary: 'View Salary',
  process: 'Process',
  reimburse: 'Reimburse',
  record: 'Record',
  reconcile: 'Reconcile',
  view: 'View',
  manage_roles: 'Manage Roles',
  cancel: 'Cancel'
};

const PermissionManager = () => {
  const { user } = useContext(AuthContext);
  const [roles, setRoles] = useState([]);
  const [selectedRole, setSelectedRole] = useState('');
  const [permissions, setPermissions] = useState({});
  const [originalPermissions, setOriginalPermissions] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showCreateRole, setShowCreateRole] = useState(false);
  const [newRole, setNewRole] = useState({ id: '', name: '', description: '' });
  const [activeTab, setActiveTab] = useState('permissions');

  useEffect(() => {
    fetchRoles();
  }, []);

  useEffect(() => {
    if (selectedRole) {
      fetchPermissions(selectedRole);
    }
  }, [selectedRole]);

  const fetchRoles = async () => {
    try {
      const response = await fetch(`${API}/roles`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setRoles(data);
        if (data.length > 0 && !selectedRole) {
          setSelectedRole(data[0].id);
        }
      }
    } catch (error) {
      console.error('Failed to fetch roles:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchPermissions = async (role) => {
    try {
      const response = await fetch(`${API}/role-permissions/${role}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (response.ok) {
        const data = await response.json();
        setPermissions(data);
        setOriginalPermissions(JSON.parse(JSON.stringify(data)));
      } else {
        // Initialize with empty permissions if none exist
        const emptyPerms = {};
        Object.keys(MODULE_DEFINITIONS).forEach(moduleKey => {
          emptyPerms[moduleKey] = { enabled: false, features: {} };
          Object.keys(MODULE_DEFINITIONS[moduleKey].features).forEach(featureKey => {
            emptyPerms[moduleKey].features[featureKey] = {};
            MODULE_DEFINITIONS[moduleKey].features[featureKey].actions.forEach(action => {
              emptyPerms[moduleKey].features[featureKey][action] = false;
            });
          });
        });
        setPermissions(emptyPerms);
        setOriginalPermissions(JSON.parse(JSON.stringify(emptyPerms)));
      }
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
    }
  };

  const handleModuleToggle = (moduleKey, enabled) => {
    setPermissions(prev => {
      const updated = { ...prev };
      if (!updated[moduleKey]) {
        updated[moduleKey] = { enabled: false, features: {} };
      }
      updated[moduleKey].enabled = enabled;
      
      // If disabling, turn off all features
      if (!enabled && updated[moduleKey].features) {
        Object.keys(updated[moduleKey].features).forEach(featureKey => {
          Object.keys(updated[moduleKey].features[featureKey]).forEach(action => {
            updated[moduleKey].features[featureKey][action] = false;
          });
        });
      }
      
      return updated;
    });
  };

  const handleFeatureToggle = (moduleKey, featureKey, action, enabled) => {
    setPermissions(prev => {
      const updated = { ...prev };
      if (!updated[moduleKey]) {
        updated[moduleKey] = { enabled: true, features: {} };
      }
      if (!updated[moduleKey].features) {
        updated[moduleKey].features = {};
      }
      if (!updated[moduleKey].features[featureKey]) {
        updated[moduleKey].features[featureKey] = {};
      }
      updated[moduleKey].features[featureKey][action] = enabled;
      
      // If enabling any feature, enable the module
      if (enabled) {
        updated[moduleKey].enabled = true;
      }
      
      return updated;
    });
  };

  const handleSelectAllFeature = (moduleKey, featureKey, selectAll) => {
    const actions = MODULE_DEFINITIONS[moduleKey].features[featureKey].actions;
    actions.forEach(action => {
      handleFeatureToggle(moduleKey, featureKey, action, selectAll);
    });
  };

  const handleSelectAllModule = (moduleKey, selectAll) => {
    handleModuleToggle(moduleKey, selectAll);
    if (selectAll) {
      Object.keys(MODULE_DEFINITIONS[moduleKey].features).forEach(featureKey => {
        handleSelectAllFeature(moduleKey, featureKey, true);
      });
    }
  };

  const savePermissions = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API}/role-permissions/${selectedRole}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(permissions)
      });
      
      if (response.ok) {
        toast.success('Permissions saved successfully!');
        setOriginalPermissions(JSON.parse(JSON.stringify(permissions)));
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to save permissions');
      }
    } catch (error) {
      toast.error('Failed to save permissions');
    } finally {
      setSaving(false);
    }
  };

  const resetPermissions = () => {
    setPermissions(JSON.parse(JSON.stringify(originalPermissions)));
    toast.info('Permissions reset to last saved state');
  };

  const createRole = async () => {
    if (!newRole.id || !newRole.name) {
      toast.error('Role ID and Name are required');
      return;
    }
    
    try {
      const response = await fetch(`${API}/roles`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          id: newRole.id.toLowerCase().replace(/\s+/g, '_'),
          name: newRole.name,
          description: newRole.description
        })
      });
      
      if (response.ok) {
        toast.success('Role created successfully!');
        setShowCreateRole(false);
        setNewRole({ id: '', name: '', description: '' });
        fetchRoles();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to create role');
      }
    } catch (error) {
      toast.error('Failed to create role');
    }
  };

  const getPermissionCount = (moduleKey) => {
    const modulePerms = permissions[moduleKey]?.features || {};
    let enabled = 0;
    let total = 0;
    
    Object.keys(MODULE_DEFINITIONS[moduleKey].features).forEach(featureKey => {
      const actions = MODULE_DEFINITIONS[moduleKey].features[featureKey].actions;
      total += actions.length;
      actions.forEach(action => {
        if (modulePerms[featureKey]?.[action]) enabled++;
      });
    });
    
    return { enabled, total };
  };

  const isModuleEnabled = (moduleKey) => {
    return permissions[moduleKey]?.enabled ?? false;
  };

  const isFeatureEnabled = (moduleKey, featureKey, action) => {
    return permissions[moduleKey]?.features?.[featureKey]?.[action] ?? false;
  };

  const hasChanges = JSON.stringify(permissions) !== JSON.stringify(originalPermissions);

  const selectedRoleData = roles.find(r => r.id === selectedRole);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="permission-manager">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 flex items-center gap-2">
            <Shield className="w-6 h-6 text-orange-500" />
            Permission Manager
          </h1>
          <p className="text-sm text-zinc-500 mt-1">Configure module and feature access for each role</p>
        </div>
        <div className="flex items-center gap-3">
          {hasChanges && (
            <Badge className="bg-amber-100 text-amber-700 animate-pulse">
              Unsaved Changes
            </Badge>
          )}
          <Button
            variant="outline"
            onClick={resetPermissions}
            disabled={!hasChanges}
            className="text-zinc-600"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset
          </Button>
          <Button
            onClick={savePermissions}
            disabled={!hasChanges || saving}
            className="bg-orange-600 hover:bg-orange-700"
          >
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      {/* Role Selector */}
      <Card className="border-zinc-200">
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Label className="text-sm font-medium text-zinc-700">Select Role:</Label>
              <Select value={selectedRole} onValueChange={setSelectedRole}>
                <SelectTrigger className="w-64">
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {roles.map(role => (
                    <SelectItem key={role.id} value={role.id}>
                      <div className="flex items-center gap-2">
                        <UserCog className="w-4 h-4 text-zinc-400" />
                        {role.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedRoleData && (
                <Badge variant="secondary" className="text-xs">
                  {selectedRoleData.is_system_role ? 'System Role' : 'Custom Role'}
                </Badge>
              )}
            </div>
            <Button
              variant="outline"
              onClick={() => setShowCreateRole(true)}
              className="text-orange-600 border-orange-200 hover:bg-orange-50"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create New Role
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-zinc-100 p-1">
          <TabsTrigger value="permissions" className="data-[state=active]:bg-white">
            <Shield className="w-4 h-4 mr-2" />
            Module Permissions
          </TabsTrigger>
          <TabsTrigger value="overview" className="data-[state=active]:bg-white">
            <BarChart3 className="w-4 h-4 mr-2" />
            Overview
          </TabsTrigger>
        </TabsList>

        {/* Permissions Tab */}
        <TabsContent value="permissions" className="space-y-4">
          <Accordion type="multiple" className="space-y-3">
            {Object.entries(MODULE_DEFINITIONS).map(([moduleKey, module]) => {
              const { enabled, total } = getPermissionCount(moduleKey);
              const ModuleIcon = module.icon;
              const moduleEnabled = isModuleEnabled(moduleKey);
              
              return (
                <AccordionItem
                  key={moduleKey}
                  value={moduleKey}
                  className="border border-zinc-200 rounded-lg overflow-hidden"
                >
                  <AccordionTrigger className="px-4 py-3 hover:no-underline hover:bg-zinc-50">
                    <div className="flex items-center justify-between w-full pr-4">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${module.color}`}>
                          <ModuleIcon className="w-5 h-5" />
                        </div>
                        <div className="text-left">
                          <p className="font-medium text-zinc-900">{module.name}</p>
                          <p className="text-xs text-zinc-500">
                            {enabled} of {total} permissions enabled
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSelectAllModule(moduleKey, true)}
                          className="text-xs text-green-600 hover:text-green-700 hover:bg-green-50"
                        >
                          Enable All
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSelectAllModule(moduleKey, false)}
                          className="text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          Disable All
                        </Button>
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-zinc-500">Module Access</span>
                          <Switch
                            checked={moduleEnabled}
                            onCheckedChange={(checked) => handleModuleToggle(moduleKey, checked)}
                          />
                        </div>
                      </div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4">
                    <div className="space-y-4 pt-2">
                      {Object.entries(module.features).map(([featureKey, feature]) => {
                        const allEnabled = feature.actions.every(
                          action => isFeatureEnabled(moduleKey, featureKey, action)
                        );
                        const someEnabled = feature.actions.some(
                          action => isFeatureEnabled(moduleKey, featureKey, action)
                        );
                        
                        return (
                          <div
                            key={featureKey}
                            className={`p-4 rounded-lg border ${
                              moduleEnabled ? 'bg-white border-zinc-200' : 'bg-zinc-50 border-zinc-100 opacity-50'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-3">
                              <div className="flex items-center gap-2">
                                {allEnabled ? (
                                  <CheckCircle className="w-4 h-4 text-green-500" />
                                ) : someEnabled ? (
                                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                                ) : (
                                  <XCircle className="w-4 h-4 text-zinc-300" />
                                )}
                                <span className="font-medium text-sm text-zinc-800">{feature.name}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleSelectAllFeature(moduleKey, featureKey, !allEnabled)}
                                  disabled={!moduleEnabled}
                                  className="text-xs"
                                >
                                  {allEnabled ? 'Deselect All' : 'Select All'}
                                </Button>
                              </div>
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {feature.actions.map(action => (
                                <label
                                  key={action}
                                  className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm cursor-pointer transition-colors ${
                                    isFeatureEnabled(moduleKey, featureKey, action)
                                      ? 'bg-green-100 text-green-700 border border-green-200'
                                      : 'bg-zinc-100 text-zinc-500 border border-zinc-200 hover:bg-zinc-200'
                                  } ${!moduleEnabled ? 'cursor-not-allowed' : ''}`}
                                >
                                  <input
                                    type="checkbox"
                                    checked={isFeatureEnabled(moduleKey, featureKey, action)}
                                    onChange={(e) => handleFeatureToggle(moduleKey, featureKey, action, e.target.checked)}
                                    disabled={!moduleEnabled}
                                    className="hidden"
                                  />
                                  {isFeatureEnabled(moduleKey, featureKey, action) ? (
                                    <Unlock className="w-3 h-3" />
                                  ) : (
                                    <Lock className="w-3 h-3" />
                                  )}
                                  {ACTION_LABELS[action] || action}
                                </label>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              );
            })}
          </Accordion>
        </TabsContent>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <Card className="border-zinc-200">
            <CardHeader>
              <CardTitle className="text-base">Permission Summary for {selectedRoleData?.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-5 gap-4">
                {Object.entries(MODULE_DEFINITIONS).map(([moduleKey, module]) => {
                  const { enabled, total } = getPermissionCount(moduleKey);
                  const percentage = total > 0 ? Math.round((enabled / total) * 100) : 0;
                  const ModuleIcon = module.icon;
                  
                  return (
                    <div
                      key={moduleKey}
                      className="p-4 rounded-lg border border-zinc-200 text-center"
                    >
                      <div className={`w-12 h-12 mx-auto rounded-full ${module.color} flex items-center justify-center mb-3`}>
                        <ModuleIcon className="w-6 h-6" />
                      </div>
                      <p className="font-medium text-sm text-zinc-900">{module.name}</p>
                      <p className="text-2xl font-bold text-zinc-900 mt-2">{percentage}%</p>
                      <p className="text-xs text-zinc-500">{enabled}/{total} enabled</p>
                      <div className="mt-2 h-2 bg-zinc-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-500 transition-all duration-300"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create Role Dialog */}
      <Dialog open={showCreateRole} onOpenChange={setShowCreateRole}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Role</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Role ID</Label>
              <Input
                value={newRole.id}
                onChange={(e) => setNewRole({...newRole, id: e.target.value})}
                placeholder="e.g., sales_lead"
              />
              <p className="text-xs text-zinc-500">Lowercase, no spaces (use underscores)</p>
            </div>
            <div className="space-y-2">
              <Label>Display Name</Label>
              <Input
                value={newRole.name}
                onChange={(e) => setNewRole({...newRole, name: e.target.value})}
                placeholder="e.g., Sales Lead"
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={newRole.description}
                onChange={(e) => setNewRole({...newRole, description: e.target.value})}
                placeholder="Role description..."
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateRole(false)}>Cancel</Button>
            <Button onClick={createRole} className="bg-orange-600 hover:bg-orange-700">
              Create Role
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PermissionManager;
