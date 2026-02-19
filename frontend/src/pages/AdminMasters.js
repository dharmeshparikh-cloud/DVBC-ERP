import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { 
  Plus, Pencil, Trash2, Settings, Users, Calendar, 
  ChevronDown, ChevronUp, Check, X, Database, Percent,
  FileText, FolderTree, Layers, Building2, TrendingUp,
  Briefcase, DollarSign, Shield
} from 'lucide-react';
import { toast } from 'sonner';

// Department icon mapping
const DEPT_ICONS = {
  TrendingUp: TrendingUp,
  Users: Users,
  Briefcase: Briefcase,
  DollarSign: DollarSign,
  Shield: Shield,
  Building2: Building2,
};

// Default colors for departments
const DEPT_COLORS = [
  { name: 'Orange', value: '#F97316' },
  { name: 'Green', value: '#10B981' },
  { name: 'Purple', value: '#8B5CF6' },
  { name: 'Blue', value: '#3B82F6' },
  { name: 'Red', value: '#EF4444' },
  { name: 'Pink', value: '#EC4899' },
  { name: 'Yellow', value: '#EAB308' },
  { name: 'Teal', value: '#14B8A6' },
];

const AdminMasters = () => {
  const { user } = useContext(AuthContext);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('departments');
  
  // Data states
  const [tenureTypes, setTenureTypes] = useState([]);
  const [consultantRoles, setConsultantRoles] = useState([]);
  const [meetingTypes, setMeetingTypes] = useState([]);
  const [departments, setDepartments] = useState([]);
  
  // SOW Categories and Scopes
  const [sowCategories, setSowCategories] = useState([]);
  const [sowScopes, setSowScopes] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  
  // Edit states
  const [editingTenure, setEditingTenure] = useState(null);
  const [editingRole, setEditingRole] = useState(null);
  const [editingCategory, setEditingCategory] = useState(null);
  const [editingScope, setEditingScope] = useState(null);
  const [editingDept, setEditingDept] = useState(null);
  
  // New item forms
  const [showNewTenure, setShowNewTenure] = useState(false);
  const [showNewRole, setShowNewRole] = useState(false);
  const [showNewCategory, setShowNewCategory] = useState(false);
  const [showNewScope, setShowNewScope] = useState(false);
  const [showNewDept, setShowNewDept] = useState(false);
  const [newTenure, setNewTenure] = useState({
    name: '', code: '', allocation_percentage: 0, 
    meetings_per_month: 0, description: ''
  });
  const [newRole, setNewRole] = useState({
    name: '', code: '', min_rate_per_meeting: 10000, 
    max_rate_per_meeting: 50000, default_rate: 12500, seniority_level: 1
  });
  const [newCategory, setNewCategory] = useState({
    name: '', code: '', description: '', order: 0
  });
  const [newScope, setNewScope] = useState({
    name: '', description: '', category_id: ''
  });
  const [newDept, setNewDept] = useState({
    name: '', code: '', description: '', pages: '', icon: 'Building2', color: '#6B7280'
  });

  useEffect(() => {
    fetchAllMasters();
    fetchDepartments();
  }, []);

  useEffect(() => {
    if (activeTab === 'scope-builder') {
      fetchSowData();
    }
  }, [activeTab]);

  const fetchDepartments = async () => {
    try {
      const res = await axios.get(`${API}/permission-config/departments?include_inactive=true`);
      setDepartments(res.data.departments || []);
    } catch (error) {
      console.error('Failed to fetch departments:', error);
    }
  };

  const fetchSowData = async () => {
    try {
      const [categoriesRes, scopesRes] = await Promise.all([
        axios.get(`${API}/sow-masters/categories?include_inactive=true`),
        axios.get(`${API}/sow-masters/scopes?include_inactive=true`)
      ]);
      setSowCategories(categoriesRes.data);
      setSowScopes(scopesRes.data);
    } catch (error) {
      toast.error('Failed to fetch SOW data');
    }
  };

  const fetchAllMasters = async () => {
    try {
      setLoading(true);
      const [tenureRes, rolesRes, meetingsRes] = await Promise.all([
        axios.get(`${API}/masters/tenure-types?include_inactive=true`),
        axios.get(`${API}/masters/consultant-roles?include_inactive=true`),
        axios.get(`${API}/masters/meeting-types?include_inactive=true`)
      ]);
      setTenureTypes(tenureRes.data);
      setConsultantRoles(rolesRes.data);
      setMeetingTypes(meetingsRes.data);
    } catch (error) {
      toast.error('Failed to fetch master data');
    } finally {
      setLoading(false);
    }
  };

  const handleSeedDefaults = async () => {
    try {
      const response = await axios.post(`${API}/masters/seed-defaults`);
      toast.success(`Seeded: ${response.data.created.tenure_types} tenure types, ${response.data.created.consultant_roles} roles, ${response.data.created.meeting_types} meeting types`);
      fetchAllMasters();
    } catch (error) {
      toast.error('Failed to seed defaults');
    }
  };

  // Tenure Type CRUD
  const handleCreateTenure = async () => {
    try {
      if (!newTenure.name || !newTenure.code) {
        toast.error('Name and Code are required');
        return;
      }
      await axios.post(`${API}/masters/tenure-types`, newTenure);
      toast.success('Tenure type created');
      setShowNewTenure(false);
      setNewTenure({ name: '', code: '', allocation_percentage: 0, meetings_per_month: 0, description: '' });
      fetchAllMasters();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create tenure type');
    }
  };

  const handleUpdateTenure = async (id, data) => {
    try {
      await axios.put(`${API}/masters/tenure-types/${id}`, data);
      toast.success('Tenure type updated');
      setEditingTenure(null);
      fetchAllMasters();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update tenure type');
    }
  };

  const handleDeleteTenure = async (id) => {
    if (!window.confirm('Are you sure you want to deactivate this tenure type?')) return;
    try {
      await axios.delete(`${API}/masters/tenure-types/${id}`);
      toast.success('Tenure type deactivated');
      fetchAllMasters();
    } catch (error) {
      toast.error('Failed to deactivate tenure type');
    }
  };

  // Consultant Role CRUD
  const handleCreateRole = async () => {
    try {
      if (!newRole.name || !newRole.code) {
        toast.error('Name and Code are required');
        return;
      }
      await axios.post(`${API}/masters/consultant-roles`, newRole);
      toast.success('Consultant role created');
      setShowNewRole(false);
      setNewRole({ name: '', code: '', min_rate_per_meeting: 10000, max_rate_per_meeting: 50000, default_rate: 12500, seniority_level: 1 });
      fetchAllMasters();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create role');
    }
  };

  const handleUpdateRole = async (id, data) => {
    try {
      await axios.put(`${API}/masters/consultant-roles/${id}`, data);
      toast.success('Consultant role updated');
      setEditingRole(null);
      fetchAllMasters();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleDeleteRole = async (id) => {
    if (!window.confirm('Are you sure you want to deactivate this role?')) return;
    try {
      await axios.delete(`${API}/masters/consultant-roles/${id}`);
      toast.success('Consultant role deactivated');
      fetchAllMasters();
    } catch (error) {
      toast.error('Failed to deactivate role');
    }
  };

  // ============ SOW CATEGORY CRUD ============
  const handleCreateCategory = async () => {
    try {
      if (!newCategory.name || !newCategory.code) {
        toast.error('Name and Code are required');
        return;
      }
      await axios.post(`${API}/sow-masters/categories`, newCategory);
      toast.success('Category created successfully');
      setShowNewCategory(false);
      setNewCategory({ name: '', code: '', description: '', order: sowCategories.length });
      fetchSowData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create category');
    }
  };

  const handleUpdateCategory = async (id, data) => {
    try {
      await axios.put(`${API}/sow-masters/categories/${id}`, data);
      toast.success('Category updated');
      setEditingCategory(null);
      fetchSowData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update category');
    }
  };

  const handleDeleteCategory = async (id) => {
    const scopesInCategory = sowScopes.filter(s => s.category_id === id);
    if (scopesInCategory.length > 0) {
      toast.error(`Cannot delete category with ${scopesInCategory.length} scopes. Remove scopes first.`);
      return;
    }
    if (!window.confirm('Are you sure you want to deactivate this category?')) return;
    try {
      await axios.delete(`${API}/sow-masters/categories/${id}`);
      toast.success('Category deactivated');
      fetchSowData();
    } catch (error) {
      toast.error('Failed to deactivate category');
    }
  };

  // ============ SOW SCOPE CRUD ============
  const handleCreateScope = async () => {
    try {
      if (!newScope.name || !newScope.category_id) {
        toast.error('Name and Category are required');
        return;
      }
      const category = sowCategories.find(c => c.id === newScope.category_id);
      await axios.post(`${API}/sow-masters/scopes`, {
        ...newScope,
        category_code: category?.code || ''
      });
      toast.success('Scope created successfully');
      setShowNewScope(false);
      setNewScope({ name: '', description: '', category_id: '' });
      fetchSowData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create scope');
    }
  };

  const handleUpdateScope = async (id, data) => {
    try {
      await axios.put(`${API}/sow-masters/scopes/${id}`, data);
      toast.success('Scope updated');
      setEditingScope(null);
      fetchSowData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update scope');
    }
  };

  const handleDeleteScope = async (id) => {
    if (!window.confirm('Are you sure you want to deactivate this scope?')) return;
    try {
      await axios.delete(`${API}/sow-masters/scopes/${id}`);
      toast.success('Scope deactivated');
      fetchSowData();
    } catch (error) {
      toast.error('Failed to deactivate scope');
    }
  };

  const handleSeedSowDefaults = async () => {
    try {
      const response = await axios.post(`${API}/sow-masters/seed-defaults`);
      toast.success(`Seeded: ${response.data.created.categories} categories, ${response.data.created.scopes} scopes`);
      fetchSowData();
    } catch (error) {
      toast.error('Failed to seed SOW defaults');
    }
  };

  // Get scopes for selected category
  const filteredScopes = selectedCategory 
    ? sowScopes.filter(s => s.category_id === selectedCategory)
    : sowScopes;

  // Format currency
  const formatINR = (amount) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
  };

  if (user?.role !== 'admin') {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Card className="p-8 text-center">
          <CardContent>
            <Settings className="w-12 h-12 text-zinc-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-zinc-950 mb-2">Access Restricted</h2>
            <p className="text-zinc-500">Only administrators can access the Masters module.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto" data-testid="admin-masters-page">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
            Admin Masters
          </h1>
          <p className="text-zinc-500">Manage tenure types, allocation rules, consultant roles, and SOW scope templates</p>
        </div>
        <div className="flex gap-2">
          {activeTab === 'scope-builder' ? (
            <Button 
              onClick={handleSeedSowDefaults}
              variant="outline"
              className="border-zinc-300"
              data-testid="seed-sow-defaults-btn"
            >
              <Database className="w-4 h-4 mr-2" />
              Seed SOW Defaults
            </Button>
          ) : (
            <Button 
              onClick={handleSeedDefaults}
              variant="outline"
              className="border-zinc-300"
              data-testid="seed-defaults-btn"
            >
              <Database className="w-4 h-4 mr-2" />
              Seed Defaults
            </Button>
          )}
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4 bg-zinc-100 p-1 rounded-lg">
          <TabsTrigger 
            value="tenure-types" 
            className="data-[state=active]:bg-white data-[state=active]:shadow-sm rounded-md text-xs sm:text-sm"
            data-testid="tenure-types-tab"
          >
            <Percent className="w-4 h-4 mr-1 sm:mr-2" />
            <span className="hidden sm:inline">Tenure Types</span>
            <span className="sm:hidden">Tenure</span>
          </TabsTrigger>
          <TabsTrigger 
            value="consultant-roles"
            className="data-[state=active]:bg-white data-[state=active]:shadow-sm rounded-md text-xs sm:text-sm"
            data-testid="consultant-roles-tab"
          >
            <Users className="w-4 h-4 mr-1 sm:mr-2" />
            <span className="hidden sm:inline">Consultant Roles</span>
            <span className="sm:hidden">Roles</span>
          </TabsTrigger>
          <TabsTrigger 
            value="meeting-types"
            className="data-[state=active]:bg-white data-[state=active]:shadow-sm rounded-md text-xs sm:text-sm"
            data-testid="meeting-types-tab"
          >
            <Calendar className="w-4 h-4 mr-1 sm:mr-2" />
            <span className="hidden sm:inline">Meeting Types</span>
            <span className="sm:hidden">Meetings</span>
          </TabsTrigger>
          <TabsTrigger 
            value="scope-builder"
            className="data-[state=active]:bg-white data-[state=active]:shadow-sm rounded-md text-xs sm:text-sm"
            data-testid="scope-builder-tab"
          >
            <Layers className="w-4 h-4 mr-1 sm:mr-2" />
            <span className="hidden sm:inline">SOW Scope Builder</span>
            <span className="sm:hidden">Scopes</span>
          </TabsTrigger>
        </TabsList>

        {/* TENURE TYPES TAB */}
        <TabsContent value="tenure-types" className="space-y-4">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardHeader className="flex flex-row items-center justify-between border-b border-zinc-100 pb-4">
              <div>
                <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
                  Tenure Types & Allocation Percentages
                </CardTitle>
                <p className="text-xs text-zinc-500 mt-1">
                  Define allocation percentages for top-down pricing calculations
                </p>
              </div>
              <Button 
                size="sm" 
                onClick={() => setShowNewTenure(!showNewTenure)}
                className="bg-zinc-950 text-white"
                data-testid="add-tenure-btn"
              >
                <Plus className="w-4 h-4 mr-1" />
                Add Tenure Type
              </Button>
            </CardHeader>
            <CardContent className="pt-4">
              {/* New Tenure Form */}
              {showNewTenure && (
                <div className="p-4 bg-blue-50 rounded-lg mb-4 space-y-4" data-testid="new-tenure-form">
                  <div className="grid grid-cols-5 gap-4">
                    <div className="space-y-1">
                      <Label className="text-xs">Name *</Label>
                      <Input
                        value={newTenure.name}
                        onChange={(e) => setNewTenure({...newTenure, name: e.target.value})}
                        placeholder="e.g., Full-time"
                        className="h-9"
                        data-testid="new-tenure-name"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Code *</Label>
                      <Input
                        value={newTenure.code}
                        onChange={(e) => setNewTenure({...newTenure, code: e.target.value.toLowerCase().replace(/\s+/g, '_')})}
                        placeholder="e.g., full_time"
                        className="h-9"
                        data-testid="new-tenure-code"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Allocation %</Label>
                      <Input
                        type="number"
                        min="0"
                        max="100"
                        step="0.1"
                        value={newTenure.allocation_percentage}
                        onChange={(e) => setNewTenure({...newTenure, allocation_percentage: parseFloat(e.target.value) || 0})}
                        className="h-9"
                        data-testid="new-tenure-allocation"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Meetings/Month</Label>
                      <Input
                        type="number"
                        min="0"
                        step="0.1"
                        value={newTenure.meetings_per_month}
                        onChange={(e) => setNewTenure({...newTenure, meetings_per_month: parseFloat(e.target.value) || 0})}
                        className="h-9"
                        data-testid="new-tenure-meetings"
                      />
                    </div>
                    <div className="space-y-1 flex items-end gap-2">
                      <Button size="sm" onClick={handleCreateTenure} className="h-9" data-testid="save-tenure-btn">
                        <Check className="w-4 h-4" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setShowNewTenure(false)} className="h-9">
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Description</Label>
                    <Input
                      value={newTenure.description}
                      onChange={(e) => setNewTenure({...newTenure, description: e.target.value})}
                      placeholder="Brief description..."
                      className="h-9"
                    />
                  </div>
                </div>
              )}

              {/* Tenure Types Table */}
              <div className="rounded-lg border border-zinc-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-zinc-50">
                    <tr className="text-xs font-medium text-zinc-500 uppercase">
                      <th className="px-4 py-3 text-left">Name</th>
                      <th className="px-4 py-3 text-left">Code</th>
                      <th className="px-4 py-3 text-center">Allocation %</th>
                      <th className="px-4 py-3 text-center">Meetings/Month</th>
                      <th className="px-4 py-3 text-left">Description</th>
                      <th className="px-4 py-3 text-center">Status</th>
                      <th className="px-4 py-3 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {loading ? (
                      <tr><td colSpan={7} className="px-4 py-8 text-center text-zinc-400">Loading...</td></tr>
                    ) : tenureTypes.length === 0 ? (
                      <tr><td colSpan={7} className="px-4 py-8 text-center text-zinc-400">No tenure types found. Click "Seed Defaults" to add default types.</td></tr>
                    ) : (
                      tenureTypes.map((tenure) => (
                        <tr 
                          key={tenure.id} 
                          className={`hover:bg-zinc-50 ${!tenure.is_active ? 'opacity-50 bg-zinc-100' : ''}`}
                          data-testid={`tenure-row-${tenure.code}`}
                        >
                          {editingTenure === tenure.id ? (
                            <EditTenureRow 
                              tenure={tenure} 
                              onSave={(data) => handleUpdateTenure(tenure.id, data)}
                              onCancel={() => setEditingTenure(null)}
                            />
                          ) : (
                            <>
                              <td className="px-4 py-3 text-sm font-medium text-zinc-900">
                                {tenure.name}
                                {tenure.is_default && (
                                  <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">Default</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-sm text-zinc-600 font-mono">{tenure.code}</td>
                              <td className="px-4 py-3 text-sm text-center">
                                <span className="font-semibold text-emerald-600">{tenure.allocation_percentage}%</span>
                              </td>
                              <td className="px-4 py-3 text-sm text-center text-zinc-600">{tenure.meetings_per_month || '-'}</td>
                              <td className="px-4 py-3 text-sm text-zinc-500 max-w-xs truncate">{tenure.description || '-'}</td>
                              <td className="px-4 py-3 text-center">
                                <span className={`px-2 py-1 text-xs rounded ${tenure.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                  {tenure.is_active ? 'Active' : 'Inactive'}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-center">
                                <div className="flex items-center justify-center gap-1">
                                  <Button 
                                    size="sm" 
                                    variant="ghost" 
                                    onClick={() => setEditingTenure(tenure.id)}
                                    className="h-8 w-8 p-0 text-zinc-500 hover:text-blue-600"
                                    data-testid={`edit-tenure-${tenure.code}`}
                                  >
                                    <Pencil className="w-4 h-4" />
                                  </Button>
                                  {tenure.is_active && (
                                    <Button 
                                      size="sm" 
                                      variant="ghost" 
                                      onClick={() => handleDeleteTenure(tenure.id)}
                                      className="h-8 w-8 p-0 text-zinc-500 hover:text-red-600"
                                    >
                                      <Trash2 className="w-4 h-4" />
                                    </Button>
                                  )}
                                </div>
                              </td>
                            </>
                          )}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              
              {/* Info box about allocation */}
              <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <h4 className="text-sm font-medium text-amber-800 mb-2">How Allocation Works</h4>
                <p className="text-xs text-amber-700">
                  When creating a Pricing Plan, the salesperson enters the <strong>Total Client Investment</strong>. 
                  The system then distributes this amount among team members based on the allocation percentages defined here. 
                  For example, a Full-time resource with 70% allocation gets a larger share than a Weekly resource with 20% allocation.
                  The <strong>Rate per Meeting</strong> is calculated automatically as: Breakup Amount ÷ Total Meetings.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* CONSULTANT ROLES TAB */}
        <TabsContent value="consultant-roles" className="space-y-4">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardHeader className="flex flex-row items-center justify-between border-b border-zinc-100 pb-4">
              <div>
                <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
                  Consultant Roles & Rate Ranges
                </CardTitle>
                <p className="text-xs text-zinc-500 mt-1">
                  Define consultant roles with minimum, maximum, and default rates
                </p>
              </div>
              <Button 
                size="sm" 
                onClick={() => setShowNewRole(!showNewRole)}
                className="bg-zinc-950 text-white"
                data-testid="add-role-btn"
              >
                <Plus className="w-4 h-4 mr-1" />
                Add Role
              </Button>
            </CardHeader>
            <CardContent className="pt-4">
              {/* New Role Form */}
              {showNewRole && (
                <div className="p-4 bg-blue-50 rounded-lg mb-4 space-y-4" data-testid="new-role-form">
                  <div className="grid grid-cols-6 gap-4">
                    <div className="space-y-1">
                      <Label className="text-xs">Name *</Label>
                      <Input
                        value={newRole.name}
                        onChange={(e) => setNewRole({...newRole, name: e.target.value})}
                        placeholder="e.g., Senior Consultant"
                        className="h-9"
                        data-testid="new-role-name"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Code *</Label>
                      <Input
                        value={newRole.code}
                        onChange={(e) => setNewRole({...newRole, code: e.target.value.toLowerCase().replace(/\s+/g, '_')})}
                        placeholder="e.g., senior_consultant"
                        className="h-9"
                        data-testid="new-role-code"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Min Rate</Label>
                      <Input
                        type="number"
                        min="0"
                        value={newRole.min_rate_per_meeting}
                        onChange={(e) => setNewRole({...newRole, min_rate_per_meeting: parseFloat(e.target.value) || 0})}
                        className="h-9"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Max Rate</Label>
                      <Input
                        type="number"
                        min="0"
                        value={newRole.max_rate_per_meeting}
                        onChange={(e) => setNewRole({...newRole, max_rate_per_meeting: parseFloat(e.target.value) || 0})}
                        className="h-9"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Default Rate</Label>
                      <Input
                        type="number"
                        min="0"
                        value={newRole.default_rate}
                        onChange={(e) => setNewRole({...newRole, default_rate: parseFloat(e.target.value) || 0})}
                        className="h-9"
                      />
                    </div>
                    <div className="space-y-1 flex items-end gap-2">
                      <Button size="sm" onClick={handleCreateRole} className="h-9" data-testid="save-role-btn">
                        <Check className="w-4 h-4" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setShowNewRole(false)} className="h-9">
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {/* Consultant Roles Table */}
              <div className="rounded-lg border border-zinc-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-zinc-50">
                    <tr className="text-xs font-medium text-zinc-500 uppercase">
                      <th className="px-4 py-3 text-left">Role Name</th>
                      <th className="px-4 py-3 text-left">Code</th>
                      <th className="px-4 py-3 text-center">Seniority</th>
                      <th className="px-4 py-3 text-right">Min Rate</th>
                      <th className="px-4 py-3 text-right">Max Rate</th>
                      <th className="px-4 py-3 text-right">Default Rate</th>
                      <th className="px-4 py-3 text-center">Status</th>
                      <th className="px-4 py-3 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {loading ? (
                      <tr><td colSpan={8} className="px-4 py-8 text-center text-zinc-400">Loading...</td></tr>
                    ) : consultantRoles.length === 0 ? (
                      <tr><td colSpan={8} className="px-4 py-8 text-center text-zinc-400">No roles found.</td></tr>
                    ) : (
                      consultantRoles.map((role) => (
                        <tr 
                          key={role.id} 
                          className={`hover:bg-zinc-50 ${!role.is_active ? 'opacity-50 bg-zinc-100' : ''}`}
                          data-testid={`role-row-${role.code}`}
                        >
                          <td className="px-4 py-3 text-sm font-medium text-zinc-900">{role.name}</td>
                          <td className="px-4 py-3 text-sm text-zinc-600 font-mono">{role.code}</td>
                          <td className="px-4 py-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              {[1,2,3,4,5].map(level => (
                                <div 
                                  key={level}
                                  className={`w-2 h-4 rounded-sm ${level <= role.seniority_level ? 'bg-blue-500' : 'bg-zinc-200'}`}
                                />
                              ))}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-right text-zinc-600">{formatINR(role.min_rate_per_meeting)}</td>
                          <td className="px-4 py-3 text-sm text-right text-zinc-600">{formatINR(role.max_rate_per_meeting)}</td>
                          <td className="px-4 py-3 text-sm text-right font-semibold text-emerald-600">{formatINR(role.default_rate)}</td>
                          <td className="px-4 py-3 text-center">
                            <span className={`px-2 py-1 text-xs rounded ${role.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                              {role.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              <Button 
                                size="sm" 
                                variant="ghost" 
                                onClick={() => setEditingRole(role.id)}
                                className="h-8 w-8 p-0 text-zinc-500 hover:text-blue-600"
                              >
                                <Pencil className="w-4 h-4" />
                              </Button>
                              {role.is_active && (
                                <Button 
                                  size="sm" 
                                  variant="ghost" 
                                  onClick={() => handleDeleteRole(role.id)}
                                  className="h-8 w-8 p-0 text-zinc-500 hover:text-red-600"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* MEETING TYPES TAB */}
        <TabsContent value="meeting-types" className="space-y-4">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardHeader className="flex flex-row items-center justify-between border-b border-zinc-100 pb-4">
              <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950">
                Meeting Types
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="rounded-lg border border-zinc-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-zinc-50">
                    <tr className="text-xs font-medium text-zinc-500 uppercase">
                      <th className="px-4 py-3 text-left">Name</th>
                      <th className="px-4 py-3 text-left">Code</th>
                      <th className="px-4 py-3 text-center">Default Duration</th>
                      <th className="px-4 py-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {loading ? (
                      <tr><td colSpan={4} className="px-4 py-8 text-center text-zinc-400">Loading...</td></tr>
                    ) : meetingTypes.length === 0 ? (
                      <tr><td colSpan={4} className="px-4 py-8 text-center text-zinc-400">No meeting types found.</td></tr>
                    ) : (
                      meetingTypes.map((mt) => (
                        <tr 
                          key={mt.id} 
                          className={`hover:bg-zinc-50 ${!mt.is_active ? 'opacity-50 bg-zinc-100' : ''}`}
                        >
                          <td className="px-4 py-3 text-sm font-medium text-zinc-900">{mt.name}</td>
                          <td className="px-4 py-3 text-sm text-zinc-600 font-mono">{mt.code}</td>
                          <td className="px-4 py-3 text-sm text-center text-zinc-600">{mt.default_duration_minutes} min</td>
                          <td className="px-4 py-3 text-center">
                            <span className={`px-2 py-1 text-xs rounded ${mt.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                              {mt.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* SOW SCOPE BUILDER TAB */}
        <TabsContent value="scope-builder" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Categories Panel */}
            <Card className="border-zinc-200 shadow-none rounded-sm lg:col-span-1">
              <CardHeader className="flex flex-row items-center justify-between border-b border-zinc-100 pb-4">
                <div>
                  <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950 flex items-center gap-2">
                    <FolderTree className="w-4 h-4" />
                    Categories
                  </CardTitle>
                  <p className="text-xs text-zinc-500 mt-1">
                    Create categories first, then add scopes
                  </p>
                </div>
                <Button 
                  size="sm" 
                  onClick={() => setShowNewCategory(!showNewCategory)}
                  className="bg-zinc-950 text-white"
                  data-testid="add-category-btn"
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </CardHeader>
              <CardContent className="pt-4">
                {/* New Category Form */}
                {showNewCategory && (
                  <div className="p-4 bg-blue-50 rounded-lg mb-4 space-y-3" data-testid="new-category-form">
                    <div className="space-y-1">
                      <Label className="text-xs">Name *</Label>
                      <Input
                        value={newCategory.name}
                        onChange={(e) => setNewCategory({...newCategory, name: e.target.value})}
                        placeholder="e.g., Financial Consulting"
                        className="h-9 text-sm"
                        data-testid="category-name-input"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Code *</Label>
                      <Input
                        value={newCategory.code}
                        onChange={(e) => setNewCategory({...newCategory, code: e.target.value.toLowerCase().replace(/\s+/g, '_')})}
                        placeholder="e.g., financial"
                        className="h-9 text-sm font-mono"
                        data-testid="category-code-input"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Description</Label>
                      <Input
                        value={newCategory.description}
                        onChange={(e) => setNewCategory({...newCategory, description: e.target.value})}
                        placeholder="Brief description..."
                        className="h-9 text-sm"
                      />
                    </div>
                    <div className="flex gap-2 pt-2">
                      <Button size="sm" variant="outline" onClick={() => setShowNewCategory(false)} className="flex-1">Cancel</Button>
                      <Button size="sm" onClick={handleCreateCategory} className="flex-1 bg-blue-600 text-white" data-testid="save-category-btn">Save</Button>
                    </div>
                  </div>
                )}

                {/* Categories List */}
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {sowCategories.length === 0 ? (
                    <div className="text-center py-8 text-zinc-400 text-sm">
                      <FolderTree className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      No categories yet. Create one to get started.
                    </div>
                  ) : (
                    sowCategories.map((cat) => (
                      <div 
                        key={cat.id}
                        className={`p-3 rounded-lg border cursor-pointer transition-all ${
                          selectedCategory === cat.id 
                            ? 'border-blue-500 bg-blue-50' 
                            : 'border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50'
                        } ${!cat.is_active ? 'opacity-50' : ''}`}
                        onClick={() => setSelectedCategory(selectedCategory === cat.id ? null : cat.id)}
                        data-testid={`category-${cat.code}`}
                      >
                        {editingCategory === cat.id ? (
                          <EditCategoryInline 
                            category={cat}
                            onSave={(data) => handleUpdateCategory(cat.id, data)}
                            onCancel={() => setEditingCategory(null)}
                          />
                        ) : (
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="font-medium text-sm text-zinc-900">{cat.name}</div>
                              <div className="text-xs text-zinc-500 font-mono">{cat.code}</div>
                              {cat.description && (
                                <div className="text-xs text-zinc-400 mt-1">{cat.description}</div>
                              )}
                              <div className="text-xs text-zinc-400 mt-1">
                                {sowScopes.filter(s => s.category_id === cat.id).length} scopes
                              </div>
                            </div>
                            <div className="flex gap-1">
                              <Button 
                                size="sm" 
                                variant="ghost" 
                                onClick={(e) => { e.stopPropagation(); setEditingCategory(cat.id); }}
                                className="h-7 w-7 p-0 text-zinc-400 hover:text-blue-600"
                              >
                                <Pencil className="w-3 h-3" />
                              </Button>
                              {cat.is_active && (
                                <Button 
                                  size="sm" 
                                  variant="ghost" 
                                  onClick={(e) => { e.stopPropagation(); handleDeleteCategory(cat.id); }}
                                  className="h-7 w-7 p-0 text-zinc-400 hover:text-red-600"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </Button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Scopes Panel */}
            <Card className="border-zinc-200 shadow-none rounded-sm lg:col-span-2">
              <CardHeader className="flex flex-row items-center justify-between border-b border-zinc-100 pb-4">
                <div>
                  <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-950 flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    Scope Templates
                    {selectedCategory && (
                      <span className="text-xs font-normal text-blue-600 ml-2">
                        (Filtered: {sowCategories.find(c => c.id === selectedCategory)?.name})
                      </span>
                    )}
                  </CardTitle>
                  <p className="text-xs text-zinc-500 mt-1">
                    {selectedCategory ? 'Showing scopes for selected category' : 'Showing all scopes'}
                  </p>
                </div>
                <div className="flex gap-2">
                  {selectedCategory && (
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => setSelectedCategory(null)}
                      className="text-xs"
                    >
                      Show All
                    </Button>
                  )}
                  <Button 
                    size="sm" 
                    onClick={() => {
                      setShowNewScope(!showNewScope);
                      if (selectedCategory && !showNewScope) {
                        setNewScope({ ...newScope, category_id: selectedCategory });
                      }
                    }}
                    className="bg-zinc-950 text-white"
                    disabled={sowCategories.length === 0}
                    data-testid="add-scope-btn"
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Add Scope
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="pt-4">
                {/* New Scope Form */}
                {showNewScope && (
                  <div className="p-4 bg-green-50 rounded-lg mb-4 space-y-3" data-testid="new-scope-form">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <Label className="text-xs">Category *</Label>
                        <select
                          value={newScope.category_id}
                          onChange={(e) => setNewScope({...newScope, category_id: e.target.value})}
                          className="w-full h-9 px-3 rounded-sm border border-zinc-200 bg-white text-sm"
                          data-testid="scope-category-select"
                        >
                          <option value="">Select category...</option>
                          {sowCategories.filter(c => c.is_active).map(cat => (
                            <option key={cat.id} value={cat.id}>{cat.name}</option>
                          ))}
                        </select>
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Scope Name *</Label>
                        <Input
                          value={newScope.name}
                          onChange={(e) => setNewScope({...newScope, name: e.target.value})}
                          placeholder="e.g., Financial Analysis"
                          className="h-9 text-sm"
                          data-testid="scope-name-input"
                        />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Description</Label>
                      <Input
                        value={newScope.description}
                        onChange={(e) => setNewScope({...newScope, description: e.target.value})}
                        placeholder="Brief description of this scope..."
                        className="h-9 text-sm"
                      />
                    </div>
                    <div className="flex gap-2 pt-2">
                      <Button size="sm" variant="outline" onClick={() => setShowNewScope(false)} className="flex-1">Cancel</Button>
                      <Button size="sm" onClick={handleCreateScope} className="flex-1 bg-green-600 text-white" data-testid="save-scope-btn">Save Scope</Button>
                    </div>
                  </div>
                )}

                {/* Scopes Table */}
                <div className="rounded-lg border border-zinc-200 overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-zinc-50">
                      <tr className="text-xs font-medium text-zinc-500 uppercase">
                        <th className="px-4 py-3 text-left">Scope Name</th>
                        <th className="px-4 py-3 text-left">Category</th>
                        <th className="px-4 py-3 text-left">Description</th>
                        <th className="px-4 py-3 text-center">Type</th>
                        <th className="px-4 py-3 text-center">Status</th>
                        <th className="px-4 py-3 text-center w-24">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                      {filteredScopes.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-4 py-8 text-center text-zinc-400">
                            {sowCategories.length === 0 
                              ? 'Create a category first, then add scopes' 
                              : 'No scopes found. Add one to get started.'}
                          </td>
                        </tr>
                      ) : (
                        filteredScopes.map((scope) => {
                          const category = sowCategories.find(c => c.id === scope.category_id);
                          return editingScope === scope.id ? (
                            <EditScopeRow 
                              key={scope.id}
                              scope={scope}
                              categories={sowCategories}
                              onSave={(data) => handleUpdateScope(scope.id, data)}
                              onCancel={() => setEditingScope(null)}
                            />
                          ) : (
                            <tr 
                              key={scope.id} 
                              className={`hover:bg-zinc-50 ${!scope.is_active ? 'opacity-50 bg-zinc-100' : ''}`}
                            >
                              <td className="px-4 py-3 text-sm font-medium text-zinc-900">{scope.name}</td>
                              <td className="px-4 py-3 text-sm">
                                <span className="px-2 py-1 bg-zinc-100 rounded text-xs text-zinc-600">
                                  {category?.name || scope.category_code}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-sm text-zinc-500 max-w-xs truncate">
                                {scope.description || '-'}
                              </td>
                              <td className="px-4 py-3 text-center">
                                <span className={`px-2 py-1 text-xs rounded ${
                                  scope.is_custom ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                                }`}>
                                  {scope.is_custom ? 'Custom' : 'Default'}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-center">
                                <span className={`px-2 py-1 text-xs rounded ${scope.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                  {scope.is_active ? 'Active' : 'Inactive'}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-center">
                                <div className="flex items-center justify-center gap-1">
                                  <Button 
                                    size="sm" 
                                    variant="ghost" 
                                    onClick={() => setEditingScope(scope.id)}
                                    className="h-8 w-8 p-0 text-zinc-500 hover:text-blue-600"
                                  >
                                    <Pencil className="w-4 h-4" />
                                  </Button>
                                  {scope.is_active && (
                                    <Button 
                                      size="sm" 
                                      variant="ghost" 
                                      onClick={() => handleDeleteScope(scope.id)}
                                      className="h-8 w-8 p-0 text-zinc-500 hover:text-red-600"
                                    >
                                      <Trash2 className="w-4 h-4" />
                                    </Button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

// Inline edit component for Tenure Types
const EditTenureRow = ({ tenure, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    name: tenure.name,
    allocation_percentage: tenure.allocation_percentage,
    meetings_per_month: tenure.meetings_per_month || 0,
    description: tenure.description || '',
    is_active: tenure.is_active,
    is_default: tenure.is_default
  });

  return (
    <>
      <td className="px-4 py-2">
        <Input 
          value={formData.name} 
          onChange={(e) => setFormData({...formData, name: e.target.value})}
          className="h-8 text-sm"
        />
      </td>
      <td className="px-4 py-2 text-sm text-zinc-600 font-mono">{tenure.code}</td>
      <td className="px-4 py-2">
        <Input 
          type="number"
          min="0"
          max="100"
          step="0.1"
          value={formData.allocation_percentage}
          onChange={(e) => setFormData({...formData, allocation_percentage: parseFloat(e.target.value) || 0})}
          className="h-8 text-sm text-center w-20 mx-auto"
        />
      </td>
      <td className="px-4 py-2">
        <Input 
          type="number"
          min="0"
          step="0.1"
          value={formData.meetings_per_month}
          onChange={(e) => setFormData({...formData, meetings_per_month: parseFloat(e.target.value) || 0})}
          className="h-8 text-sm text-center w-20 mx-auto"
        />
      </td>
      <td className="px-4 py-2">
        <Input 
          value={formData.description}
          onChange={(e) => setFormData({...formData, description: e.target.value})}
          className="h-8 text-sm"
        />
      </td>
      <td className="px-4 py-2 text-center">
        <label className="flex items-center justify-center gap-2 text-xs">
          <input 
            type="checkbox"
            checked={formData.is_active}
            onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
          />
          Active
        </label>
      </td>
      <td className="px-4 py-2 text-center">
        <div className="flex items-center justify-center gap-1">
          <Button size="sm" variant="ghost" onClick={() => onSave(formData)} className="h-7 w-7 p-0 text-green-600">
            <Check className="w-4 h-4" />
          </Button>
          <Button size="sm" variant="ghost" onClick={onCancel} className="h-7 w-7 p-0 text-red-600">
            <X className="w-4 h-4" />
          </Button>
        </div>
      </td>
    </>
  );
};

// Inline edit component for SOW Categories
const EditCategoryInline = ({ category, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    name: category.name,
    description: category.description || '',
    is_active: category.is_active
  });

  return (
    <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
      <Input 
        value={formData.name} 
        onChange={(e) => setFormData({...formData, name: e.target.value})}
        className="h-8 text-sm"
        placeholder="Category name"
      />
      <Input 
        value={formData.description}
        onChange={(e) => setFormData({...formData, description: e.target.value})}
        className="h-8 text-sm"
        placeholder="Description"
      />
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-1 text-xs">
          <input 
            type="checkbox"
            checked={formData.is_active}
            onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
          />
          Active
        </label>
        <div className="flex-1" />
        <Button size="sm" variant="ghost" onClick={onCancel} className="h-7 px-2 text-xs">Cancel</Button>
        <Button size="sm" onClick={() => onSave(formData)} className="h-7 px-2 text-xs bg-blue-600 text-white">Save</Button>
      </div>
    </div>
  );
};

// Inline edit component for SOW Scopes (table row)
const EditScopeRow = ({ scope, categories, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    name: scope.name,
    description: scope.description || '',
    is_active: scope.is_active
  });

  return (
    <tr className="bg-yellow-50">
      <td className="px-4 py-2">
        <Input 
          value={formData.name} 
          onChange={(e) => setFormData({...formData, name: e.target.value})}
          className="h-8 text-sm"
        />
      </td>
      <td className="px-4 py-2 text-sm">
        <span className="px-2 py-1 bg-zinc-100 rounded text-xs text-zinc-600">
          {categories.find(c => c.id === scope.category_id)?.name || scope.category_code}
        </span>
      </td>
      <td className="px-4 py-2">
        <Input 
          value={formData.description}
          onChange={(e) => setFormData({...formData, description: e.target.value})}
          className="h-8 text-sm"
          placeholder="Description"
        />
      </td>
      <td className="px-4 py-2 text-center">
        <span className={`px-2 py-1 text-xs rounded ${
          scope.is_custom ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
        }`}>
          {scope.is_custom ? 'Custom' : 'Default'}
        </span>
      </td>
      <td className="px-4 py-2 text-center">
        <label className="flex items-center justify-center gap-1 text-xs">
          <input 
            type="checkbox"
            checked={formData.is_active}
            onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
          />
          Active
        </label>
      </td>
      <td className="px-4 py-2 text-center">
        <div className="flex items-center justify-center gap-1">
          <Button size="sm" variant="ghost" onClick={() => onSave(formData)} className="h-7 w-7 p-0 text-green-600">
            <Check className="w-4 h-4" />
          </Button>
          <Button size="sm" variant="ghost" onClick={onCancel} className="h-7 w-7 p-0 text-red-600">
            <X className="w-4 h-4" />
          </Button>
        </div>
      </td>
    </tr>
  );
};

export default AdminMasters;
