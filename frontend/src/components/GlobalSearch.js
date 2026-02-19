import React, { useState, useEffect, useContext, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext, API } from '../App';
import { Dialog, DialogContent } from './ui/dialog';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import {
  Search, LayoutDashboard, Users, Briefcase, FileText, Settings,
  UserCog, DollarSign, Calendar, Clock, Receipt, BarChart3,
  Building2, GitBranch, Wallet, Shield, FileSignature, Star,
  ChevronRight, Command, ArrowRight, User, Hash
} from 'lucide-react';

// All ERP pages/features for search
const ERP_PAGES = [
  // Dashboard
  { name: 'Dashboard', path: '/', icon: LayoutDashboard, category: 'Main', keywords: ['home', 'overview', 'main'] },
  
  // HR Module
  { name: 'Employees', path: '/employees', icon: Users, category: 'HR', keywords: ['staff', 'team', 'people', 'directory'] },
  { name: 'Onboarding', path: '/onboarding', icon: UserCog, category: 'HR', keywords: ['new hire', 'joining', 'recruit'] },
  { name: 'Document Center', path: '/document-center', icon: FileSignature, category: 'HR', keywords: ['letters', 'offer', 'appointment', 'documents'] },
  { name: 'Org Chart', path: '/org-chart', icon: GitBranch, category: 'HR', keywords: ['organization', 'hierarchy', 'structure'] },
  { name: 'Leave Management', path: '/leave-management', icon: Calendar, category: 'HR', keywords: ['vacation', 'time off', 'holiday'] },
  { name: 'Attendance', path: '/attendance', icon: Clock, category: 'HR', keywords: ['check in', 'time', 'present'] },
  { name: 'CTC Designer', path: '/ctc-designer', icon: DollarSign, category: 'HR', keywords: ['salary', 'compensation', 'pay'] },
  { name: 'Payroll', path: '/payroll', icon: Wallet, category: 'HR', keywords: ['salary', 'payment', 'wages'] },
  { name: 'Password Management', path: '/password-management', icon: Shield, category: 'HR', keywords: ['reset', 'access', 'security'] },
  
  // Sales Module
  { name: 'Sales Dashboard', path: '/sales-funnel', icon: BarChart3, category: 'Sales', keywords: ['leads', 'pipeline', 'revenue'] },
  { name: 'Leads', path: '/sales-funnel/leads', icon: Users, category: 'Sales', keywords: ['prospects', 'clients', 'customers'] },
  { name: 'Proposals', path: '/sales-funnel/pricing', icon: FileText, category: 'Sales', keywords: ['quotes', 'pricing', 'offers'] },
  { name: 'SOW List', path: '/sales-funnel/sow-list', icon: FileText, category: 'Sales', keywords: ['scope', 'work', 'contracts'] },
  
  // Consulting Module
  { name: 'Consulting Dashboard', path: '/consulting', icon: Briefcase, category: 'Consulting', keywords: ['projects', 'delivery'] },
  { name: 'Project Timeline', path: '/project-timeline', icon: Calendar, category: 'Consulting', keywords: ['schedule', 'milestones', 'gantt'] },
  { name: 'Project Roadmap', path: '/project-roadmap', icon: GitBranch, category: 'Consulting', keywords: ['plan', 'phases'] },
  
  // Finance Module
  { name: 'Expenses', path: '/expenses', icon: Receipt, category: 'Finance', keywords: ['bills', 'costs', 'spending'] },
  { name: 'Travel Reimbursement', path: '/travel-reimbursement', icon: Receipt, category: 'Finance', keywords: ['travel', 'claims'] },
  
  // Admin Module
  { name: 'Permission Manager', path: '/permission-manager', icon: Shield, category: 'Admin', keywords: ['roles', 'access', 'rights'] },
  { name: 'Employee Permissions', path: '/employee-permissions', icon: User, category: 'Admin', keywords: ['access', 'permissions', 'employee access'] },
  { name: 'Dept Access Manager', path: '/department-access', icon: Building2, category: 'Admin', keywords: ['department', 'permissions'] },
  { name: 'Role Management', path: '/role-management', icon: Shield, category: 'Admin', keywords: ['roles', 'create role'] },
  { name: 'Admin Masters', path: '/admin-masters', icon: Settings, category: 'Admin', keywords: ['settings', 'configuration'] },
  { name: 'Approvals Center', path: '/approvals-center', icon: FileText, category: 'Admin', keywords: ['pending', 'approve', 'reject'] },
  
  // Reports
  { name: 'Reports', path: '/reports', icon: BarChart3, category: 'Reports', keywords: ['analytics', 'insights', 'data'] },
  { name: 'Employee Scorecard', path: '/employee-scorecard', icon: Star, category: 'Reports', keywords: ['performance', 'kpi'] },
];

// Quick actions
const QUICK_ACTIONS = [
  { name: 'Add New Employee', path: '/onboarding', icon: UserCog, category: 'Action' },
  { name: 'Generate Document', path: '/document-center', icon: FileSignature, category: 'Action' },
  { name: 'Create Lead', path: '/sales-funnel/leads', icon: Users, category: 'Action' },
  { name: 'Submit Expense', path: '/expenses', icon: Receipt, category: 'Action' },
];

const GlobalSearch = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);

  // Fetch employees for search
  useEffect(() => {
    const fetchEmployees = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API}/employees`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setEmployees(data);
        }
      } catch (error) {
        console.error('Failed to fetch employees:', error);
      }
    };
    if (isOpen) {
      fetchEmployees();
    }
  }, [isOpen]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
    if (!isOpen) {
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Search logic
  useEffect(() => {
    if (!query.trim()) {
      // Show quick actions when no query
      setResults([
        { type: 'section', label: 'Quick Actions' },
        ...QUICK_ACTIONS.map(a => ({ ...a, type: 'action' })),
        { type: 'section', label: 'Recent Pages' },
        ...ERP_PAGES.slice(0, 5).map(p => ({ ...p, type: 'page' }))
      ]);
      return;
    }

    const searchQuery = query.toLowerCase();
    const matchedResults = [];

    // Search pages
    const matchedPages = ERP_PAGES.filter(page => 
      page.name.toLowerCase().includes(searchQuery) ||
      page.category.toLowerCase().includes(searchQuery) ||
      page.keywords.some(k => k.includes(searchQuery))
    );

    // Search employees
    const matchedEmployees = employees.filter(emp =>
      `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(searchQuery) ||
      emp.employee_id?.toLowerCase().includes(searchQuery) ||
      emp.email?.toLowerCase().includes(searchQuery) ||
      emp.department?.toLowerCase().includes(searchQuery)
    ).slice(0, 5);

    // Build results
    if (matchedPages.length > 0) {
      matchedResults.push({ type: 'section', label: 'Pages & Features' });
      matchedResults.push(...matchedPages.slice(0, 6).map(p => ({ ...p, type: 'page' })));
    }

    if (matchedEmployees.length > 0) {
      matchedResults.push({ type: 'section', label: 'Employees' });
      matchedResults.push(...matchedEmployees.map(emp => ({
        type: 'employee',
        name: `${emp.first_name} ${emp.last_name}`,
        employee_id: emp.employee_id,
        department: emp.department,
        path: `/employees?search=${emp.employee_id}`,
        icon: User
      })));
    }

    setResults(matchedResults);
    setSelectedIndex(0);
  }, [query, employees]);

  // Keyboard navigation
  const handleKeyDown = useCallback((e) => {
    const selectableResults = results.filter(r => r.type !== 'section');
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, selectableResults.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const selected = selectableResults[selectedIndex];
      if (selected?.path) {
        navigate(selected.path);
        onClose();
      }
    } else if (e.key === 'Escape') {
      onClose();
    }
  }, [results, selectedIndex, navigate, onClose]);

  const handleSelect = (item) => {
    if (item.path) {
      navigate(item.path);
      onClose();
    }
  };

  const getCategoryColor = (category) => {
    const colors = {
      'Main': 'bg-zinc-100 text-zinc-700',
      'HR': 'bg-emerald-100 text-emerald-700',
      'Sales': 'bg-blue-100 text-blue-700',
      'Consulting': 'bg-purple-100 text-purple-700',
      'Finance': 'bg-amber-100 text-amber-700',
      'Admin': 'bg-red-100 text-red-700',
      'Reports': 'bg-indigo-100 text-indigo-700',
      'Action': 'bg-orange-100 text-orange-700',
    };
    return colors[category] || 'bg-zinc-100 text-zinc-700';
  };

  let selectableIndex = -1;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl p-0 gap-0 overflow-hidden" onKeyDown={handleKeyDown}>
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b">
          <Search className="w-5 h-5 text-zinc-400" />
          <Input
            ref={inputRef}
            placeholder="Search pages, features, employees..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="border-0 focus-visible:ring-0 text-base px-0"
            data-testid="global-search-input"
          />
          <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-1 text-xs font-mono bg-zinc-100 dark:bg-zinc-800 rounded">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[400px] overflow-y-auto">
          {results.length === 0 ? (
            <div className="p-8 text-center text-zinc-500">
              <Search className="w-10 h-10 mx-auto mb-3 text-zinc-300" />
              <p>No results found for "{query}"</p>
            </div>
          ) : (
            <div className="py-2">
              {results.map((item, index) => {
                if (item.type === 'section') {
                  return (
                    <div key={index} className="px-4 py-2 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                      {item.label}
                    </div>
                  );
                }

                selectableIndex++;
                const isSelected = selectableIndex === selectedIndex;
                const Icon = item.icon;

                return (
                  <button
                    key={index}
                    onClick={() => handleSelect(item)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                      isSelected 
                        ? 'bg-orange-50 dark:bg-orange-900/20' 
                        : 'hover:bg-zinc-50 dark:hover:bg-zinc-800'
                    }`}
                    data-testid={`search-result-${item.name?.toLowerCase().replace(/\s+/g, '-')}`}
                  >
                    <div className={`p-2 rounded-lg ${isSelected ? 'bg-orange-100' : 'bg-zinc-100 dark:bg-zinc-800'}`}>
                      <Icon className={`w-4 h-4 ${isSelected ? 'text-orange-600' : 'text-zinc-500'}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`font-medium truncate ${isSelected ? 'text-orange-700' : ''}`}>
                        {item.name}
                      </p>
                      {item.type === 'employee' && (
                        <p className="text-xs text-zinc-500 truncate">
                          <span className="font-mono">{item.employee_id}</span>
                          {item.department && ` • ${item.department}`}
                        </p>
                      )}
                    </div>
                    {item.category && (
                      <Badge variant="secondary" className={`text-xs ${getCategoryColor(item.category)}`}>
                        {item.category}
                      </Badge>
                    )}
                    <ArrowRight className={`w-4 h-4 ${isSelected ? 'text-orange-500' : 'text-zinc-300'}`} />
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2 border-t bg-zinc-50 dark:bg-zinc-900 text-xs text-zinc-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-white dark:bg-zinc-800 rounded border text-[10px]">↑</kbd>
              <kbd className="px-1.5 py-0.5 bg-white dark:bg-zinc-800 rounded border text-[10px]">↓</kbd>
              <span className="ml-1">Navigate</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-white dark:bg-zinc-800 rounded border text-[10px]">Enter</kbd>
              <span className="ml-1">Select</span>
            </span>
          </div>
          <span className="flex items-center gap-1">
            <Command className="w-3 h-3" />
            <span>+K to open</span>
          </span>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default GlobalSearch;
