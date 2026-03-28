import React, { useState, useContext } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AuthContext } from '../App';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Shield, Users, Building2, Info } from 'lucide-react';
import { isAdmin as checkIsAdmin } from '../utils/roles';

// Import existing page components as tab content
import RBACAdmin from './RBACAdmin';
import EmployeeAccessPermissions from './EmployeeAccessPermissions';
import DepartmentAccessManager from './DepartmentAccessManager';

const TAB_GUIDES = {
  roles: {
    title: 'Roles & Groups',
    icon: Shield,
    description: 'Create and manage system roles. Each role belongs to a department and has a level. Role Groups (like "Sales Roles", "Consulting Roles") control which sidebar sections users with those roles can see. Adding a role to a group instantly updates access for everyone with that role.',
    color: 'border-violet-200 bg-violet-50 text-violet-800',
  },
  people: {
    title: 'People Access',
    icon: Users,
    description: 'Manage individual employee access. Grant or revoke portal access, reset passwords, and set module-level permissions for specific employees. Use this for one-off overrides when someone needs access beyond their default role.',
    color: 'border-sky-200 bg-sky-50 text-sky-800',
  },
  departments: {
    title: 'Department View',
    icon: Building2,
    description: 'View and manage which departments each employee belongs to. An employee in the Sales department automatically sees the Sales sidebar. Use "Dept" to assign additional departments and "Special" for temporary cross-department access.',
    color: 'border-amber-200 bg-amber-50 text-amber-800',
  },
};

const AccessAndRoles = () => {
  const { user } = useContext(AuthContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const isAdmin = checkIsAdmin(user);

  const getInitialTab = () => {
    const tab = searchParams.get('tab');
    if (['roles', 'people', 'departments'].includes(tab)) return tab;
    return 'roles';
  };

  const [activeTab, setActiveTab] = useState(getInitialTab());

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const guide = TAB_GUIDES[activeTab];

  return (
    <div className="min-h-screen bg-zinc-50" data-testid="access-roles-page">
      {/* Header */}
      <div className="border-b bg-white px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-zinc-900 flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-zinc-900">Access & Roles</h1>
            <p className="text-sm text-zinc-500">Manage roles, permissions, and department access from one place</p>
          </div>
        </div>
      </div>

      <div className="p-6">
        {/* On-page guide */}
        <Card className={`mb-5 border ${guide.color}`} data-testid="tab-guide">
          <CardContent className="p-4 flex items-start gap-3">
            <Info className="w-5 h-5 mt-0.5 shrink-0 opacity-70" />
            <div>
              <p className="text-sm font-medium mb-0.5">{guide.title}</p>
              <p className="text-xs leading-relaxed opacity-80">{guide.description}</p>
            </div>
          </CardContent>
        </Card>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={handleTabChange}>
          <TabsList className="bg-white border mb-6 h-11">
            <TabsTrigger value="roles" className="gap-2 data-[state=active]:bg-zinc-900 data-[state=active]:text-white" data-testid="tab-roles">
              <Shield className="w-4 h-4" />
              Roles & Groups
              <Badge className="ml-1 h-5 px-1.5 text-[10px] bg-violet-100 text-violet-700 hover:bg-violet-100">RBAC</Badge>
            </TabsTrigger>
            <TabsTrigger value="people" className="gap-2 data-[state=active]:bg-zinc-900 data-[state=active]:text-white" data-testid="tab-people">
              <Users className="w-4 h-4" />
              People Access
            </TabsTrigger>
            <TabsTrigger value="departments" className="gap-2 data-[state=active]:bg-zinc-900 data-[state=active]:text-white" data-testid="tab-departments">
              <Building2 className="w-4 h-4" />
              Department View
            </TabsTrigger>
          </TabsList>

          <TabsContent value="roles" className="mt-0">
            <RBACAdmin />
          </TabsContent>

          <TabsContent value="people" className="mt-0">
            <EmployeeAccessPermissions />
          </TabsContent>

          <TabsContent value="departments" className="mt-0">
            <DepartmentAccessManager />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default AccessAndRoles;
