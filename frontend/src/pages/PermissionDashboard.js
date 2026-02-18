import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import {
  Users, Shield, UserCheck, Crown, Briefcase, Search,
  ChevronDown, ChevronUp, Check, X, Edit2, Save, RefreshCw
} from 'lucide-react';

const PermissionDashboard = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  
  const [stats, setStats] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [levelPermissions, setLevelPermissions] = useState({});
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterLevel, setFilterLevel] = useState('all');
  const [editingLevel, setEditingLevel] = useState(null);
  const [editedPermissions, setEditedPermissions] = useState({});
  const [expandedEmployee, setExpandedEmployee] = useState(null);
  const [updatingEmployee, setUpdatingEmployee] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, permissionsRes, employeesRes] = await Promise.all([
        axios.get(`${API}/role-management/stats`),
        axios.get(`${API}/role-management/level-permissions`),
        axios.get(`${API}/employees`)
      ]);
      
      setStats(statsRes.data);
      setLevelPermissions(permissionsRes.data);
      setEmployees(employeesRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load permission data');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateEmployeeLevel = async (employeeId, newLevel) => {
    setUpdatingEmployee(employeeId);
    try {
      await axios.patch(`${API}/employees/${employeeId}`, { level: newLevel });
      toast.success('Employee level updated');
      fetchData();
    } catch (error) {
      console.error('Failed to update level:', error);
      toast.error('Failed to update employee level');
    } finally {
      setUpdatingEmployee(null);
    }
  };

  const handleEditLevelPermissions = (level) => {
    setEditingLevel(level);
    setEditedPermissions({ ...levelPermissions[level] });
  };

  const handleSaveLevelPermissions = async () => {
    try {
      await axios.put(`${API}/role-management/level-permissions`, {
        level: editingLevel,
        permissions: editedPermissions
      });
      toast.success(`${editingLevel} permissions updated`);
      setEditingLevel(null);
      fetchData();
    } catch (error) {
      console.error('Failed to update permissions:', error);
      toast.error('Failed to update permissions');
    }
  };

  const filteredEmployees = employees.filter(emp => {
    const matchesSearch = 
      `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.employee_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.email?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesLevel = filterLevel === 'all' || emp.level === filterLevel;
    return matchesSearch && matchesLevel;
  });

  const levelIcons = {
    executive: Briefcase,
    manager: UserCheck,
    leader: Crown
  };

  const levelColors = {
    executive: 'bg-blue-500',
    manager: 'bg-amber-500',
    leader: 'bg-purple-500'
  };

  const permissionLabels = {
    can_view_own_data: 'View Own Data',
    can_edit_own_profile: 'Edit Own Profile',
    can_submit_requests: 'Submit Requests',
    can_view_team_data: 'View Team Data',
    can_approve_requests: 'Approve Requests',
    can_manage_team: 'Manage Team',
    can_access_reports: 'Access Reports',
    can_access_financials: 'Access Financials',
    can_create_projects: 'Create Projects',
    can_assign_tasks: 'Assign Tasks'
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="permission-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            Permission Dashboard
          </h1>
          <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            Manage employee levels and permissions across your organization
          </p>
        </div>
        <Button onClick={fetchData} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" /> Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {['executive', 'manager', 'leader'].map(level => {
          const Icon = levelIcons[level];
          const count = stats?.employees_by_level?.[level] || 0;
          return (
            <Card key={level} className={isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white'}>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${levelColors[level]}`}>
                    <Icon className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                      {count}
                    </p>
                    <p className={`text-xs capitalize ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                      {level}s
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
        <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white'}>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500">
                <Users className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className={`text-2xl font-bold ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                  {stats?.employees_by_level?.unassigned || 0}
                </p>
                <p className={`text-xs ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                  Unassigned
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Level Permissions Section */}
      <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white'}>
        <CardHeader className="pb-3">
          <CardTitle className={`text-lg flex items-center gap-2 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
            <Shield className="w-5 h-5" /> Level Permission Matrix
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className={isDark ? 'border-b border-zinc-800' : 'border-b border-zinc-200'}>
                  <th className={`text-left py-3 px-4 text-sm font-medium ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                    Permission
                  </th>
                  {['executive', 'manager', 'leader'].map(level => (
                    <th key={level} className={`text-center py-3 px-4 text-sm font-medium capitalize ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
                      <div className="flex items-center justify-center gap-2">
                        {level}
                        {editingLevel !== level && (
                          <button
                            onClick={() => handleEditLevelPermissions(level)}
                            className="p-1 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded"
                          >
                            <Edit2 className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(permissionLabels).map(([key, label]) => (
                  <tr key={key} className={isDark ? 'border-b border-zinc-800' : 'border-b border-zinc-100'}>
                    <td className={`py-3 px-4 text-sm ${isDark ? 'text-zinc-300' : 'text-zinc-700'}`}>
                      {label}
                    </td>
                    {['executive', 'manager', 'leader'].map(level => {
                      const isEditing = editingLevel === level;
                      const hasPermission = isEditing 
                        ? editedPermissions[key] 
                        : levelPermissions[level]?.[key];
                      
                      return (
                        <td key={level} className="py-3 px-4 text-center">
                          {isEditing ? (
                            <button
                              onClick={() => setEditedPermissions(prev => ({
                                ...prev,
                                [key]: !prev[key]
                              }))}
                              className={`p-1.5 rounded-full transition-colors ${
                                hasPermission 
                                  ? 'bg-green-500 text-white' 
                                  : isDark ? 'bg-zinc-700 text-zinc-400' : 'bg-zinc-200 text-zinc-400'
                              }`}
                            >
                              {hasPermission ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
                            </button>
                          ) : (
                            <span className={`inline-flex p-1.5 rounded-full ${
                              hasPermission 
                                ? 'bg-green-500/20 text-green-500' 
                                : isDark ? 'bg-zinc-800 text-zinc-600' : 'bg-zinc-100 text-zinc-400'
                            }`}>
                              {hasPermission ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {editingLevel && (
            <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-800">
              <Button variant="outline" size="sm" onClick={() => setEditingLevel(null)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleSaveLevelPermissions}>
                <Save className="w-4 h-4 mr-2" /> Save {editingLevel} Permissions
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Employee List */}
      <Card className={isDark ? 'bg-zinc-900 border-zinc-800' : 'bg-white'}>
        <CardHeader className="pb-3">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <CardTitle className={`text-lg flex items-center gap-2 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
              <Users className="w-5 h-5" /> Employee Permission Levels
            </CardTitle>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                <Input
                  placeholder="Search employees..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 w-64"
                />
              </div>
              <select
                value={filterLevel}
                onChange={(e) => setFilterLevel(e.target.value)}
                className={`px-3 py-2 rounded-md border text-sm ${
                  isDark 
                    ? 'bg-zinc-800 border-zinc-700 text-zinc-100' 
                    : 'bg-white border-zinc-300 text-zinc-900'
                }`}
              >
                <option value="all">All Levels</option>
                <option value="executive">Executive</option>
                <option value="manager">Manager</option>
                <option value="leader">Leader</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {filteredEmployees.length === 0 ? (
              <p className={`text-center py-8 ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                No employees found
              </p>
            ) : (
              filteredEmployees.map(emp => {
                const Icon = levelIcons[emp.level] || Users;
                const isExpanded = expandedEmployee === emp.id;
                
                return (
                  <div
                    key={emp.id}
                    className={`rounded-lg border ${
                      isDark ? 'border-zinc-800 bg-zinc-800/50' : 'border-zinc-200 bg-zinc-50'
                    }`}
                  >
                    <div
                      className="flex items-center justify-between p-4 cursor-pointer"
                      onClick={() => setExpandedEmployee(isExpanded ? null : emp.id)}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-lg ${levelColors[emp.level] || 'bg-zinc-500'}`}>
                          <Icon className="w-4 h-4 text-white" />
                        </div>
                        <div>
                          <p className={`font-medium ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
                            {emp.first_name} {emp.last_name}
                          </p>
                          <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                            {emp.employee_id} • {emp.designation || 'N/A'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium capitalize ${
                          emp.level === 'leader' ? 'bg-purple-500/20 text-purple-500' :
                          emp.level === 'manager' ? 'bg-amber-500/20 text-amber-500' :
                          emp.level === 'executive' ? 'bg-blue-500/20 text-blue-500' :
                          'bg-red-500/20 text-red-500'
                        }`}>
                          {emp.level || 'Unassigned'}
                        </span>
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </div>
                    </div>
                    
                    {isExpanded && (
                      <div className={`px-4 pb-4 pt-2 border-t ${isDark ? 'border-zinc-700' : 'border-zinc-200'}`}>
                        <div className="flex flex-wrap gap-2 mb-4">
                          <p className={`text-sm ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
                            Change level to:
                          </p>
                          {['executive', 'manager', 'leader'].map(level => (
                            <Button
                              key={level}
                              size="sm"
                              variant={emp.level === level ? 'default' : 'outline'}
                              disabled={updatingEmployee === emp.id}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (emp.level !== level) {
                                  handleUpdateEmployeeLevel(emp.id, level);
                                }
                              }}
                              className="capitalize"
                            >
                              {updatingEmployee === emp.id ? (
                                <RefreshCw className="w-3 h-3 animate-spin" />
                              ) : (
                                level
                              )}
                            </Button>
                          ))}
                        </div>
                        
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                          {Object.entries(permissionLabels).map(([key, label]) => {
                            const hasPermission = levelPermissions[emp.level]?.[key];
                            return (
                              <div
                                key={key}
                                className={`flex items-center gap-2 text-xs px-2 py-1.5 rounded ${
                                  hasPermission
                                    ? 'bg-green-500/10 text-green-600'
                                    : isDark ? 'bg-zinc-800 text-zinc-500' : 'bg-zinc-100 text-zinc-400'
                                }`}
                              >
                                {hasPermission ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                                <span className="truncate">{label}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PermissionDashboard;
