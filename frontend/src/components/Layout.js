import React, { useContext } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { AuthContext } from '../App';
import { Button } from './ui/button';
import { LayoutDashboard, Users, Briefcase, Calendar, LogOut } from 'lucide-react';

const Layout = () => {
  const { user, logout } = useContext(AuthContext);
  const location = useLocation();

  const navigation = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Leads', href: '/leads', icon: Users },
    { name: 'Projects', href: '/projects', icon: Briefcase },
    { name: 'Meetings', href: '/meetings', icon: Calendar },
  ];

  const isActive = (href) => {
    if (href === '/') return location.pathname === '/';
    return location.pathname.startsWith(href);
  };

  return (
    <div className="flex min-h-screen bg-white">
      <aside className="w-64 border-r border-zinc-200 bg-white" data-testid="sidebar">
        <div className="flex flex-col h-full">
          <div className="p-6 border-b border-zinc-200">
            <h1 className="text-xl font-semibold tracking-tight uppercase text-zinc-950">
              Workflow Manager
            </h1>
          </div>

          <nav className="flex-1 p-4 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  data-testid={`nav-${item.name.toLowerCase()}`}
                  className={`flex items-center gap-3 px-3 py-2 rounded-sm text-sm transition-colors ${
                    active
                      ? 'bg-zinc-100 text-zinc-950 font-medium'
                      : 'text-zinc-600 hover:text-zinc-950 hover:bg-zinc-50'
                  }`}
                >
                  <Icon className="w-4 h-4" strokeWidth={1.5} />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          <div className="p-4 border-t border-zinc-200">
            <div className="mb-3">
              <div className="text-xs font-medium uppercase tracking-wide text-zinc-500 mb-1">
                User
              </div>
              <div className="text-sm text-zinc-950">{user?.full_name}</div>
              <div className="text-xs text-zinc-500 data-text">{user?.role}</div>
            </div>
            <Button
              onClick={logout}
              data-testid="logout-button"
              variant="ghost"
              className="w-full justify-start text-zinc-600 hover:text-zinc-950 hover:bg-zinc-100 rounded-sm"
            >
              <LogOut className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Sign Out
            </Button>
          </div>
        </div>
      </aside>

      <main className="flex-1">
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
