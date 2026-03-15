import React, { useContext } from 'react';
import { Link } from 'react-router-dom';
import { AuthContext } from '../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { 
  Settings as SettingsIcon, 
  FileText, 
  Mail, 
  Calendar, 
  MapPin, 
  Shield, 
  Users,
  Building2,
  Clock,
  Palette,
  Bell,
  Lock,
  ChevronRight
} from 'lucide-react';
import { isAdmin as checkIsAdmin, isHR as checkIsHR } from '../utils/roles';

const Settings = () => {
  const { user } = useContext(AuthContext);
  const isAdmin = checkIsAdmin(user);
  const isHR = checkIsHR(user);

  const settingsGroups = [
    {
      title: 'General',
      description: 'Basic application settings',
      items: [
        {
          name: 'Office Locations',
          description: 'Manage office locations and addresses',
          href: '/office-locations',
          icon: MapPin,
          show: isAdmin,
        },
        {
          name: 'Letterhead Settings',
          description: 'Configure document letterheads and branding',
          href: '/letterhead-settings',
          icon: FileText,
          show: isAdmin,
        },
      ],
    },
    {
      title: 'HR Settings',
      description: 'Human resources configuration',
      items: [
        {
          name: 'Attendance & Leave',
          description: 'Configure attendance rules and leave policies',
          href: '/attendance-leave-settings',
          icon: Clock,
          show: isHR,
        },
        {
          name: 'Leave Policies',
          description: 'Manage leave types and allocation rules',
          href: '/leave-policy-settings',
          icon: Calendar,
          show: isHR,
        },
      ],
    },
    {
      title: 'Communication',
      description: 'Email and notification settings',
      items: [
        {
          name: 'Email Settings',
          description: 'Configure email templates and SMTP settings',
          href: '/email-settings',
          icon: Mail,
          show: isAdmin,
        },
      ],
    },
    {
      title: 'Security',
      description: 'Access control and permissions',
      items: [
        {
          name: 'Roles & Permissions',
          description: 'Manage user roles and access control',
          href: '/rbac',
          icon: Shield,
          show: isAdmin,
        },
        {
          name: 'User Management',
          description: 'Manage user accounts and access',
          href: '/admin/users',
          icon: Users,
          show: isAdmin,
        },
      ],
    },
  ];

  return (
    <div className="space-y-8" data-testid="settings-page">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 mb-2">Settings</h1>
        <p className="text-zinc-500">Manage your application settings and preferences</p>
      </div>

      <div className="space-y-8">
        {settingsGroups.map((group) => {
          const visibleItems = group.items.filter(item => item.show);
          if (visibleItems.length === 0) return null;

          return (
            <div key={group.title}>
              <h2 className="text-lg font-semibold text-zinc-900 mb-1">{group.title}</h2>
              <p className="text-sm text-zinc-500 mb-4">{group.description}</p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {visibleItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      title={item.name}
                      className="group"
                    >
                      <Card className="h-full border-zinc-200 hover:border-zinc-400 hover:shadow-md transition-all cursor-pointer">
                        <CardContent className="p-5">
                          <div className="flex items-start gap-4">
                            <div className="w-10 h-10 rounded-lg bg-zinc-100 flex items-center justify-center flex-shrink-0 group-hover:bg-emerald-50 transition-colors">
                              <Icon className="w-5 h-5 text-zinc-600 group-hover:text-emerald-600 transition-colors" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between">
                                <h3 className="font-medium text-zinc-900 group-hover:text-emerald-600 transition-colors">
                                  {item.name}
                                </h3>
                                <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:text-emerald-600 transition-colors" />
                              </div>
                              <p className="text-sm text-zinc-500 mt-1 line-clamp-2">
                                {item.description}
                              </p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* No settings available message for non-admin users */}
      {!isAdmin && !isHR && (
        <Card className="border-zinc-200">
          <CardContent className="p-8 text-center">
            <SettingsIcon className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-zinc-900 mb-2">No Settings Available</h3>
            <p className="text-zinc-500">
              Contact your administrator if you need access to specific settings.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Settings;
