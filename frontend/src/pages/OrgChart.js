import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { ChevronDown, ChevronRight, Users as UsersIcon, Building2, User } from 'lucide-react';

const DEPT_COLORS = {
  'Engineering': 'border-l-blue-500', 'Sales': 'border-l-emerald-500', 'HR': 'border-l-purple-500',
  'Marketing': 'border-l-orange-500', 'Operations': 'border-l-yellow-500', 'Finance': 'border-l-red-500',
  'Consulting': 'border-l-teal-500', 'Management': 'border-l-zinc-700'
};

const OrgNode = ({ node, level = 0 }) => {
  const [expanded, setExpanded] = useState(level < 2);
  const hasChildren = node.children && node.children.length > 0;
  const borderColor = DEPT_COLORS[node.department] || 'border-l-zinc-300';

  return (
    <div className="relative" data-testid={`org-node-${node.id}`}>
      <div className={`flex items-start gap-3 ${level > 0 ? 'ml-8' : ''}`}>
        {/* Connector line */}
        {level > 0 && (
          <div className="absolute -left-0 top-0 bottom-0" style={{ marginLeft: `${(level - 1) * 32 + 16}px` }}>
            <div className="w-6 h-5 border-l-2 border-b-2 border-zinc-200 rounded-bl-lg" />
          </div>
        )}
        {/* Node card */}
        <div className={`flex-1 border border-zinc-200 rounded-sm bg-white hover:shadow-sm transition-shadow border-l-4 ${borderColor} mb-2`}>
          <div className="p-3 flex items-center gap-3">
            {hasChildren && (
              <button onClick={() => setExpanded(!expanded)}
                className="w-6 h-6 flex items-center justify-center rounded-sm bg-zinc-100 hover:bg-zinc-200 transition-colors flex-shrink-0"
                data-testid={`org-toggle-${node.id}`}>
                {expanded ? <ChevronDown className="w-3.5 h-3.5 text-zinc-600" /> : <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />}
              </button>
            )}
            {!hasChildren && <div className="w-6" />}
            <div className="w-9 h-9 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0">
              <User className="w-4 h-4 text-zinc-500" strokeWidth={1.5} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm text-zinc-950 truncate">{node.name}</div>
              <div className="text-xs text-zinc-500 truncate">{node.designation || 'No designation'}</div>
            </div>
            <div className="text-right flex-shrink-0">
              <div className="text-xs text-zinc-500">{node.department || '-'}</div>
              <div className="text-xs text-zinc-400">{node.employee_id}</div>
            </div>
            {hasChildren && (
              <span className="text-[10px] px-1.5 py-0.5 bg-zinc-100 text-zinc-600 rounded-sm flex-shrink-0">
                {node.children.length}
              </span>
            )}
          </div>
        </div>
      </div>
      {/* Children */}
      {expanded && hasChildren && (
        <div className="relative" style={{ paddingLeft: `${level > 0 ? 0 : 0}px` }}>
          {node.children.map((child) => (
            <OrgNode key={child.id} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

const OrgChart = () => {
  const [hierarchy, setHierarchy] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, departments: 0, managers: 0 });

  useEffect(() => {
    fetchOrgChart();
  }, []);

  const fetchOrgChart = async () => {
    try {
      const [orgRes, empRes] = await Promise.all([
        axios.get(`${API}/employees/org-chart/hierarchy`),
        axios.get(`${API}/employees/stats/summary`).catch(() => ({ data: {} }))
      ]);
      setHierarchy(orgRes.data);
      const countNodes = (nodes) => nodes.reduce((sum, n) => sum + 1 + (n.children ? countNodes(n.children) : 0), 0);
      const countManagers = (nodes) => nodes.reduce((sum, n) => sum + (n.children?.length > 0 ? 1 : 0) + (n.children ? countManagers(n.children) : 0), 0);
      const getDepts = (nodes, set = new Set()) => { nodes.forEach(n => { if (n.department) set.add(n.department); if (n.children) getDepts(n.children, set); }); return set; };
      setStats({
        total: countNodes(orgRes.data),
        departments: getDepts(orgRes.data).size,
        managers: countManagers(orgRes.data)
      });
    } catch (error) {
      console.error('Failed to fetch org chart:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="org-chart-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">Organization Chart</h1>
        <p className="text-zinc-500">Visual hierarchy of the organization based on reporting structure</p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <UsersIcon className="w-8 h-8 text-zinc-300" />
            <div>
              <div className="text-xs uppercase tracking-wide text-zinc-500">Total Employees</div>
              <div className="text-2xl font-semibold text-zinc-950" data-testid="org-total">{stats.total}</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <Building2 className="w-8 h-8 text-zinc-300" />
            <div>
              <div className="text-xs uppercase tracking-wide text-zinc-500">Departments</div>
              <div className="text-2xl font-semibold text-zinc-950">{stats.departments}</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <User className="w-8 h-8 text-zinc-300" />
            <div>
              <div className="text-xs uppercase tracking-wide text-zinc-500">Managers</div>
              <div className="text-2xl font-semibold text-zinc-950">{stats.managers}</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64"><div className="text-zinc-500">Loading org chart...</div></div>
      ) : hierarchy.length === 0 ? (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center h-64">
            <UsersIcon className="w-12 h-12 text-zinc-300 mb-4" />
            <p className="text-zinc-500">No employee hierarchy found</p>
            <p className="text-xs text-zinc-400 mt-1">Assign reporting managers in Employees to build the chart</p>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-6">
            {hierarchy.map(node => <OrgNode key={node.id} node={node} level={0} />)}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default OrgChart;
