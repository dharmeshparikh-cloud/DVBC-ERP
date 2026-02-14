import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Card, CardContent } from '../components/ui/card';
import { Users as UsersIcon, Building2, User, ChevronDown, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';

const DEPT_COLORS = {
  Engineering: 'border-l-blue-500', Sales: 'border-l-emerald-500', HR: 'border-l-purple-500',
  Marketing: 'border-l-orange-500', Operations: 'border-l-yellow-500', Finance: 'border-l-red-500',
  Consulting: 'border-l-teal-500', Management: 'border-l-zinc-700'
};

function TreeNode(props) {
  const { node, level } = props;
  const [expanded, setExpanded] = useState(level < 2);
  const hasChildren = node.children && node.children.length > 0;
  const borderColor = DEPT_COLORS[node.department] || 'border-l-zinc-300';
  const indent = level * 32;

  return (
    <div data-testid={'org-node-' + node.id}>
      <div className="flex items-start gap-2" style={{ paddingLeft: indent + 'px' }}>
        <div className={'flex-1 border border-zinc-200 rounded-sm bg-white hover:shadow-sm transition-shadow border-l-4 mb-1.5 ' + borderColor}>
          <div className="p-3 flex items-center gap-3">
            {hasChildren ? (
              <button onClick={function() { setExpanded(!expanded); }}
                className="w-6 h-6 flex items-center justify-center rounded-sm bg-zinc-100 hover:bg-zinc-200 flex-shrink-0"
                data-testid={'org-toggle-' + node.id}>
                {expanded ? <ChevronDown className="w-3.5 h-3.5 text-zinc-600" /> : <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />}
              </button>
            ) : (
              <div className="w-6" />
            )}
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
              <span className="text-xs px-1.5 py-0.5 bg-zinc-100 text-zinc-600 rounded-sm flex-shrink-0">
                {node.children.length}
              </span>
            )}
          </div>
        </div>
      </div>
      {expanded && hasChildren && node.children.map(function(child) {
        return <TreeNode key={child.id} node={child} level={level + 1} />;
      })}
    </div>
  );
}

function OrgChart() {
  var _useState1 = useState([]);
  var hierarchy = _useState1[0];
  var setHierarchy = _useState1[1];
  var _useState2 = useState(true);
  var loading = _useState2[0];
  var setLoading = _useState2[1];
  var _useState3 = useState({ total: 0, departments: 0, managers: 0 });
  var stats = _useState3[0];
  var setStats = _useState3[1];

  useEffect(function() {
    fetchOrgChart();
  }, []);

  function countNodes(nodes) {
    var count = 0;
    for (var i = 0; i < nodes.length; i++) {
      count += 1;
      if (nodes[i].children) count += countNodes(nodes[i].children);
    }
    return count;
  }

  function countManagers(nodes) {
    var count = 0;
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].children && nodes[i].children.length > 0) count += 1;
      if (nodes[i].children) count += countManagers(nodes[i].children);
    }
    return count;
  }

  function getDepts(nodes, deptsSet) {
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].department) deptsSet.add(nodes[i].department);
      if (nodes[i].children) getDepts(nodes[i].children, deptsSet);
    }
    return deptsSet;
  }

  function fetchOrgChart() {
    axios.get(API + '/employees/org-chart/hierarchy')
      .then(function(res) {
        setHierarchy(res.data);
        var deptsSet = new Set();
        getDepts(res.data, deptsSet);
        setStats({
          total: countNodes(res.data),
          departments: deptsSet.size,
          managers: countManagers(res.data)
        });
      })
      .catch(function() {
        toast.error('Failed to load org chart');
      })
      .finally(function() {
        setLoading(false);
      });
  }

  return (
    <div data-testid="org-chart-page">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">Organization Chart</h1>
        <p className="text-zinc-500">Visual hierarchy based on reporting structure</p>
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
        <div className="flex items-center justify-center h-64">
          <div className="text-zinc-500">Loading org chart...</div>
        </div>
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
            {hierarchy.map(function(node) {
              return <TreeNode key={node.id} node={node} level={0} />;
            })}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default OrgChart;
