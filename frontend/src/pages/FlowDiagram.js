import React, { useState, useCallback, useMemo } from 'react';
import ReactFlow, { 
  Controls, 
  Background, 
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { 
  Users, Briefcase, DollarSign, AlertTriangle, CheckCircle, XCircle,
  Target, FileText, Calendar, Clock, TrendingUp, UserPlus, UserMinus, 
  Award, BookOpen, CreditCard, Receipt, PieChart, Eye, EyeOff, Info,
  Maximize2, ZoomIn, ZoomOut
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

// Custom Node Components
const ModuleNode = ({ data }) => {
  const getBgGradient = () => {
    switch(data.module) {
      case 'hr': return 'from-emerald-500 to-emerald-600';
      case 'sales': return 'from-orange-500 to-orange-600';
      case 'consulting': return 'from-blue-500 to-blue-600';
      case 'finance': return 'from-purple-500 to-purple-600';
      default: return 'from-zinc-500 to-zinc-600';
    }
  };

  const Icon = data.icon;

  return (
    <div className={`bg-gradient-to-r ${getBgGradient()} rounded-xl shadow-lg p-4 min-w-[180px] text-white`}>
      <Handle type="target" position={Position.Top} className="w-3 h-3 !bg-white" />
      <div className="flex items-center gap-3">
        {Icon && <Icon className="w-8 h-8" />}
        <div>
          <div className="font-bold text-lg">{data.label}</div>
          <div className="text-xs opacity-80">{data.subtitle}</div>
        </div>
      </div>
      {data.stats && (
        <div className="mt-2 pt-2 border-t border-white/20 text-sm">
          {data.stats}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 !bg-white" />
    </div>
  );
};

const ProcessNode = ({ data }) => {
  const getStatusStyle = () => {
    switch(data.status) {
      case 'exists': return {
        border: 'border-green-400',
        bg: 'bg-green-50 dark:bg-green-900/30',
        dot: 'bg-green-500'
      };
      case 'partial': return {
        border: 'border-amber-400',
        bg: 'bg-amber-50 dark:bg-amber-900/30',
        dot: 'bg-amber-500'
      };
      case 'missing': return {
        border: 'border-red-400',
        bg: 'bg-red-50 dark:bg-red-900/30',
        dot: 'bg-red-500'
      };
      default: return {
        border: 'border-zinc-300',
        bg: 'bg-zinc-50 dark:bg-zinc-800',
        dot: 'bg-zinc-400'
      };
    }
  };

  const style = getStatusStyle();
  const Icon = data.icon;

  return (
    <div className={`relative ${style.bg} ${style.border} border-2 rounded-lg p-3 min-w-[130px] max-w-[160px] shadow-md 
      hover:shadow-lg transition-all cursor-pointer group`}>
      <Handle type="target" position={Position.Left} className="w-2 h-2 !bg-zinc-400" />
      <div className={`absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full ${style.dot} border-2 border-white shadow`} />
      <div className="flex items-center gap-2 mb-1">
        {Icon && <Icon className="w-4 h-4 text-zinc-600 dark:text-zinc-300" />}
        <span className="font-semibold text-sm text-zinc-800 dark:text-zinc-100">{data.label}</span>
      </div>
      <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-tight">{data.description}</p>
      <Handle type="source" position={Position.Right} className="w-2 h-2 !bg-zinc-400" />
    </div>
  );
};

const LinkageNode = ({ data }) => {
  const getStyle = () => {
    switch(data.status) {
      case 'exists': return 'bg-green-100 border-green-400 text-green-800';
      case 'partial': return 'bg-amber-100 border-amber-400 text-amber-800';
      case 'missing': return 'bg-red-100 border-red-400 text-red-800';
      default: return 'bg-zinc-100 border-zinc-400 text-zinc-800';
    }
  };

  const StatusIcon = data.status === 'exists' ? CheckCircle : 
                     data.status === 'partial' ? AlertTriangle : XCircle;

  return (
    <div className={`${getStyle()} border-2 border-dashed rounded-full px-4 py-2 shadow-sm 
      flex items-center gap-2 text-sm font-medium`}>
      <Handle type="target" position={Position.Top} className="w-2 h-2 opacity-0" />
      <StatusIcon className="w-4 h-4" />
      <span>{data.label}</span>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 opacity-0" />
    </div>
  );
};

const nodeTypes = {
  moduleNode: ModuleNode,
  processNode: ProcessNode,
  linkageNode: LinkageNode,
};

const FlowDiagram = () => {
  const { theme } = useTheme();
  const [showMissing, setShowMissing] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);

  // Initial nodes
  const initialNodes = useMemo(() => [
    // HR Module Header
    { id: 'hr-header', type: 'moduleNode', position: { x: 50, y: 0 }, 
      data: { label: 'HR Module', subtitle: 'GET PEOPLE', module: 'hr', icon: Users, stats: '4/8 Complete' }
    },
    // HR Process Nodes
    { id: 'hr-1', type: 'processNode', position: { x: 50, y: 100 }, 
      data: { label: 'Recruitment', status: 'missing', icon: UserPlus, description: 'Job posting, Applications' }
    },
    { id: 'hr-2', type: 'processNode', position: { x: 220, y: 100 }, 
      data: { label: 'Onboarding', status: 'missing', icon: BookOpen, description: 'Documents, Training' }
    },
    { id: 'hr-3', type: 'processNode', position: { x: 390, y: 100 }, 
      data: { label: 'Employee Master', status: 'exists', icon: Users, description: 'Profile, Department' }
    },
    { id: 'hr-4', type: 'processNode', position: { x: 560, y: 100 }, 
      data: { label: 'Attendance', status: 'exists', icon: Clock, description: 'Check-in/out, WFH' }
    },
    { id: 'hr-5', type: 'processNode', position: { x: 730, y: 100 }, 
      data: { label: 'Leave Mgmt', status: 'exists', icon: Calendar, description: 'Apply, Approve, Balance' }
    },
    { id: 'hr-6', type: 'processNode', position: { x: 900, y: 100 }, 
      data: { label: 'Payroll', status: 'exists', icon: CreditCard, description: 'Salary, Deductions' }
    },
    { id: 'hr-7', type: 'processNode', position: { x: 1070, y: 100 }, 
      data: { label: 'Skill Matrix', status: 'missing', icon: Award, description: 'Competencies, Certs' }
    },
    { id: 'hr-8', type: 'processNode', position: { x: 1240, y: 100 }, 
      data: { label: 'Exit Process', status: 'missing', icon: UserMinus, description: 'Resignation, F&F' }
    },

    // Linkage: HR to Sales
    { id: 'link-hr-sales', type: 'linkageNode', position: { x: 550, y: 220 },
      data: { label: 'Bench Availability Check', status: 'missing' }
    },

    // Sales Module Header
    { id: 'sales-header', type: 'moduleNode', position: { x: 50, y: 320 }, 
      data: { label: 'Sales Module', subtitle: 'WORK PEOPLE ON', module: 'sales', icon: Target, stats: '9/11 Complete' }
    },
    // Sales Process Nodes
    { id: 'sales-1', type: 'processNode', position: { x: 50, y: 420 }, 
      data: { label: 'Lead Capture', status: 'exists', icon: UserPlus, description: 'Source, Contact, Company' }
    },
    { id: 'sales-2', type: 'processNode', position: { x: 200, y: 420 }, 
      data: { label: 'Meetings', status: 'exists', icon: Calendar, description: 'Schedule, Attendees' }
    },
    { id: 'sales-3', type: 'processNode', position: { x: 350, y: 420 }, 
      data: { label: 'MOM', status: 'exists', icon: FileText, description: 'Minutes, Action items' }
    },
    { id: 'sales-4', type: 'processNode', position: { x: 500, y: 420 }, 
      data: { label: 'Qualification', status: 'exists', icon: Target, description: 'Hot/Warm/Cold scoring' }
    },
    { id: 'sales-5', type: 'processNode', position: { x: 650, y: 420 }, 
      data: { label: 'Pricing Plan', status: 'exists', icon: DollarSign, description: 'Services, Rates' }
    },
    { id: 'sales-6', type: 'processNode', position: { x: 800, y: 420 }, 
      data: { label: 'SOW', status: 'exists', icon: FileText, description: 'Scope, Deliverables' }
    },
    { id: 'sales-7', type: 'processNode', position: { x: 950, y: 420 }, 
      data: { label: 'Proforma', status: 'exists', icon: Receipt, description: 'Invoice preview' }
    },
    { id: 'sales-8', type: 'processNode', position: { x: 1100, y: 420 }, 
      data: { label: 'Agreement', status: 'exists', icon: FileText, description: 'Contract, Signatures' }
    },
    { id: 'sales-9', type: 'processNode', position: { x: 1250, y: 420 }, 
      data: { label: 'Kickoff', status: 'exists', icon: TrendingUp, description: 'Handoff to Consulting' }
    },
    { id: 'sales-10', type: 'processNode', position: { x: 650, y: 520 }, 
      data: { label: 'Forecasting', status: 'missing', icon: PieChart, description: 'Pipeline prediction' }
    },
    { id: 'sales-11', type: 'processNode', position: { x: 800, y: 520 }, 
      data: { label: 'Commission', status: 'missing', icon: DollarSign, description: 'Sales incentive calc' }
    },

    // Linkage: Sales to Consulting
    { id: 'link-sales-consulting', type: 'linkageNode', position: { x: 550, y: 620 },
      data: { label: 'Context Transfer & Kickoff', status: 'partial' }
    },

    // Consulting Module Header
    { id: 'consulting-header', type: 'moduleNode', position: { x: 50, y: 720 }, 
      data: { label: 'Consulting Module', subtitle: 'ENCASH PEOPLE TO', module: 'consulting', icon: Briefcase, stats: '4/10 Complete' }
    },
    // Consulting Process Nodes
    { id: 'cons-1', type: 'processNode', position: { x: 50, y: 820 }, 
      data: { label: 'Project Setup', status: 'exists', icon: Briefcase, description: 'From kickoff approval' }
    },
    { id: 'cons-2', type: 'processNode', position: { x: 200, y: 820 }, 
      data: { label: 'Team Allocation', status: 'exists', icon: Users, description: 'Assign consultants' }
    },
    { id: 'cons-3', type: 'processNode', position: { x: 350, y: 820 }, 
      data: { label: 'Timesheets', status: 'missing', icon: Clock, description: 'Effort logging, Approval' }
    },
    { id: 'cons-4', type: 'processNode', position: { x: 500, y: 820 }, 
      data: { label: 'Milestones', status: 'missing', icon: Target, description: 'Deliverables, Deadlines' }
    },
    { id: 'cons-5', type: 'processNode', position: { x: 650, y: 820 }, 
      data: { label: 'SOW Changes', status: 'exists', icon: FileText, description: 'Scope modifications' }
    },
    { id: 'cons-6', type: 'processNode', position: { x: 800, y: 820 }, 
      data: { label: 'Delivery', status: 'partial', icon: CheckCircle, description: 'Sign-off, Acceptance' }
    },
    { id: 'cons-7', type: 'processNode', position: { x: 950, y: 820 }, 
      data: { label: 'Project P&L', status: 'missing', icon: PieChart, description: 'Revenue vs Cost' }
    },
    { id: 'cons-8', type: 'processNode', position: { x: 1100, y: 820 }, 
      data: { label: 'Invoicing', status: 'missing', icon: Receipt, description: 'Generate from milestones' }
    },
    { id: 'cons-9', type: 'processNode', position: { x: 1250, y: 820 }, 
      data: { label: 'Payment Track', status: 'exists', icon: CreditCard, description: 'Reminders, Collection' }
    },
    { id: 'cons-10', type: 'processNode', position: { x: 950, y: 920 }, 
      data: { label: 'Client NPS', status: 'missing', icon: Award, description: 'Satisfaction score' }
    },

    // Linkage: Consulting to Finance
    { id: 'link-consulting-finance', type: 'linkageNode', position: { x: 550, y: 1020 },
      data: { label: 'Invoice & Utilization Update', status: 'missing' }
    },

    // Finance Module (Future)
    { id: 'finance-header', type: 'moduleNode', position: { x: 550, y: 1120 }, 
      data: { label: 'Finance Module', subtitle: 'TRACK MONEY', module: 'finance', icon: DollarSign, stats: 'Not Started' }
    },
  ], []);

  // Initial edges
  const initialEdges = useMemo(() => [
    // HR flow connections
    { id: 'e-hr-1-2', source: 'hr-1', target: 'hr-2', animated: false, style: { stroke: '#10b981' } },
    { id: 'e-hr-2-3', source: 'hr-2', target: 'hr-3', animated: false, style: { stroke: '#10b981' } },
    { id: 'e-hr-3-4', source: 'hr-3', target: 'hr-4', animated: true, style: { stroke: '#10b981' } },
    { id: 'e-hr-4-5', source: 'hr-4', target: 'hr-5', animated: true, style: { stroke: '#10b981' } },
    { id: 'e-hr-5-6', source: 'hr-5', target: 'hr-6', animated: true, style: { stroke: '#10b981' } },
    { id: 'e-hr-6-7', source: 'hr-6', target: 'hr-7', animated: false, style: { stroke: '#ef4444' } },
    { id: 'e-hr-7-8', source: 'hr-7', target: 'hr-8', animated: false, style: { stroke: '#ef4444' } },
    
    // HR Header to first process
    { id: 'e-hr-header', source: 'hr-header', target: 'hr-1', type: 'smoothstep', style: { stroke: '#10b981', strokeDasharray: '5,5' } },

    // HR to Sales linkage
    { id: 'e-hr-sales-link', source: 'hr-6', target: 'link-hr-sales', type: 'smoothstep', 
      style: { stroke: '#ef4444', strokeDasharray: '5,5' }, animated: true,
      markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' }
    },
    { id: 'e-link-sales', source: 'link-hr-sales', target: 'sales-header', type: 'smoothstep',
      style: { stroke: '#ef4444', strokeDasharray: '5,5' }, animated: true,
      markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' }
    },

    // Sales Header to first process
    { id: 'e-sales-header', source: 'sales-header', target: 'sales-1', type: 'smoothstep', style: { stroke: '#f97316', strokeDasharray: '5,5' } },

    // Sales flow connections
    { id: 'e-s-1-2', source: 'sales-1', target: 'sales-2', animated: true, style: { stroke: '#f97316' } },
    { id: 'e-s-2-3', source: 'sales-2', target: 'sales-3', animated: true, style: { stroke: '#f97316' } },
    { id: 'e-s-3-4', source: 'sales-3', target: 'sales-4', animated: true, style: { stroke: '#f97316' } },
    { id: 'e-s-4-5', source: 'sales-4', target: 'sales-5', animated: true, style: { stroke: '#f97316' } },
    { id: 'e-s-5-6', source: 'sales-5', target: 'sales-6', animated: true, style: { stroke: '#f97316' } },
    { id: 'e-s-6-7', source: 'sales-6', target: 'sales-7', animated: true, style: { stroke: '#f97316' } },
    { id: 'e-s-7-8', source: 'sales-7', target: 'sales-8', animated: true, style: { stroke: '#f97316' } },
    { id: 'e-s-8-9', source: 'sales-8', target: 'sales-9', animated: true, style: { stroke: '#f97316' } },
    // Missing features branch
    { id: 'e-s-5-10', source: 'sales-5', target: 'sales-10', type: 'smoothstep', style: { stroke: '#ef4444', strokeDasharray: '5,5' } },
    { id: 'e-s-10-11', source: 'sales-10', target: 'sales-11', style: { stroke: '#ef4444', strokeDasharray: '5,5' } },

    // Sales to Consulting linkage
    { id: 'e-sales-cons-link', source: 'sales-9', target: 'link-sales-consulting', type: 'smoothstep',
      style: { stroke: '#f59e0b', strokeDasharray: '5,5' }, animated: true,
      markerEnd: { type: MarkerType.ArrowClosed, color: '#f59e0b' }
    },
    { id: 'e-link-cons', source: 'link-sales-consulting', target: 'consulting-header', type: 'smoothstep',
      style: { stroke: '#f59e0b', strokeDasharray: '5,5' }, animated: true,
      markerEnd: { type: MarkerType.ArrowClosed, color: '#f59e0b' }
    },

    // Consulting Header to first process
    { id: 'e-cons-header', source: 'consulting-header', target: 'cons-1', type: 'smoothstep', style: { stroke: '#3b82f6', strokeDasharray: '5,5' } },

    // Consulting flow connections
    { id: 'e-c-1-2', source: 'cons-1', target: 'cons-2', animated: true, style: { stroke: '#3b82f6' } },
    { id: 'e-c-2-3', source: 'cons-2', target: 'cons-3', style: { stroke: '#ef4444', strokeDasharray: '5,5' } },
    { id: 'e-c-3-4', source: 'cons-3', target: 'cons-4', style: { stroke: '#ef4444', strokeDasharray: '5,5' } },
    { id: 'e-c-4-5', source: 'cons-4', target: 'cons-5', animated: true, style: { stroke: '#3b82f6' } },
    { id: 'e-c-5-6', source: 'cons-5', target: 'cons-6', animated: true, style: { stroke: '#f59e0b' } },
    { id: 'e-c-6-7', source: 'cons-6', target: 'cons-7', style: { stroke: '#ef4444', strokeDasharray: '5,5' } },
    { id: 'e-c-7-8', source: 'cons-7', target: 'cons-8', style: { stroke: '#ef4444', strokeDasharray: '5,5' } },
    { id: 'e-c-8-9', source: 'cons-8', target: 'cons-9', animated: true, style: { stroke: '#3b82f6' } },
    { id: 'e-c-6-10', source: 'cons-6', target: 'cons-10', type: 'smoothstep', style: { stroke: '#ef4444', strokeDasharray: '5,5' } },

    // Consulting to Finance linkage
    { id: 'e-cons-fin-link', source: 'cons-9', target: 'link-consulting-finance', type: 'smoothstep',
      style: { stroke: '#ef4444', strokeDasharray: '5,5' }, animated: true,
      markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' }
    },
    { id: 'e-link-fin', source: 'link-consulting-finance', target: 'finance-header', type: 'smoothstep',
      style: { stroke: '#ef4444', strokeDasharray: '5,5' }, animated: true,
      markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' }
    },
  ], []);

  // Filter nodes based on showMissing state
  const filteredNodes = useMemo(() => {
    if (showMissing) return initialNodes;
    return initialNodes.filter(node => 
      node.type === 'moduleNode' || 
      node.type === 'linkageNode' ||
      (node.data.status && node.data.status !== 'missing')
    );
  }, [showMissing, initialNodes]);

  const [nodes, setNodes, onNodesChange] = useNodesState(filteredNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes when filter changes
  React.useEffect(() => {
    setNodes(filteredNodes);
  }, [filteredNodes, setNodes]);

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
  }, []);

  // Stats calculation
  const stats = useMemo(() => {
    const processNodes = initialNodes.filter(n => n.type === 'processNode');
    return {
      total: processNodes.length,
      exists: processNodes.filter(n => n.data.status === 'exists').length,
      partial: processNodes.filter(n => n.data.status === 'partial').length,
      missing: processNodes.filter(n => n.data.status === 'missing').length,
    };
  }, [initialNodes]);

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="border-b bg-card px-6 py-4 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Business Flow Analysis</h1>
          <p className="text-muted-foreground text-sm">Interactive end-to-end process visualization</p>
        </div>
        <div className="flex items-center gap-6">
          {/* Stats badges */}
          <div className="flex items-center gap-3 text-sm">
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
              <CheckCircle className="w-4 h-4" />
              <span className="font-medium">{stats.exists} Complete</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
              <AlertTriangle className="w-4 h-4" />
              <span className="font-medium">{stats.partial} Partial</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400">
              <XCircle className="w-4 h-4" />
              <span className="font-medium">{stats.missing} Missing</span>
            </div>
          </div>

          {/* Toggle */}
          <Button
            variant={showMissing ? "default" : "outline"}
            size="sm"
            onClick={() => setShowMissing(!showMissing)}
            className="gap-2"
          >
            {showMissing ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            {showMissing ? 'Showing All' : 'Hiding Missing'}
          </Button>
        </div>
      </div>

      {/* Flow Diagram */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.3}
          maxZoom={1.5}
          defaultViewport={{ x: 0, y: 0, zoom: 0.6 }}
          className="bg-zinc-50 dark:bg-zinc-900"
        >
          <Background 
            color={theme === 'dark' ? '#374151' : '#d4d4d8'} 
            gap={20} 
            size={1}
          />
          <Controls 
            className="bg-card border shadow-lg rounded-lg"
            showInteractive={false}
          />
          <MiniMap 
            nodeColor={(node) => {
              if (node.type === 'moduleNode') {
                switch(node.data.module) {
                  case 'hr': return '#10b981';
                  case 'sales': return '#f97316';
                  case 'consulting': return '#3b82f6';
                  case 'finance': return '#8b5cf6';
                  default: return '#71717a';
                }
              }
              if (node.data.status === 'exists') return '#22c55e';
              if (node.data.status === 'partial') return '#f59e0b';
              if (node.data.status === 'missing') return '#ef4444';
              return '#71717a';
            }}
            className="bg-card border shadow-lg rounded-lg"
            maskColor={theme === 'dark' ? 'rgba(0,0,0,0.7)' : 'rgba(255,255,255,0.7)'}
          />
        </ReactFlow>

        {/* Legend */}
        <div className="absolute bottom-4 left-4 bg-card border rounded-lg shadow-lg p-4 text-sm">
          <h4 className="font-semibold mb-3 text-foreground">Legend</h4>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-8 h-1 bg-green-500 rounded" />
              <span className="text-muted-foreground">Implemented Flow</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-1 bg-green-500 rounded animate-pulse" />
              <span className="text-muted-foreground">Active/Working</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-1 bg-red-500 rounded" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #ef4444 0, #ef4444 4px, transparent 4px, transparent 8px)' }} />
              <span className="text-muted-foreground">Missing/Gap</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-1 bg-amber-500 rounded" style={{ backgroundImage: 'repeating-linear-gradient(90deg, #f59e0b 0, #f59e0b 4px, transparent 4px, transparent 8px)' }} />
              <span className="text-muted-foreground">Partial Implementation</span>
            </div>
          </div>
        </div>

        {/* Selected Node Detail */}
        {selectedNode && selectedNode.type === 'processNode' && (
          <div className="absolute top-4 right-4 w-72 bg-card border rounded-lg shadow-lg overflow-hidden">
            <div className={`p-3 ${
              selectedNode.data.status === 'exists' ? 'bg-green-500' :
              selectedNode.data.status === 'partial' ? 'bg-amber-500' : 'bg-red-500'
            } text-white`}>
              <div className="flex items-center justify-between">
                <span className="font-semibold">{selectedNode.data.label}</span>
                <Badge variant="secondary" className="bg-white/20 text-white">
                  {selectedNode.data.status}
                </Badge>
              </div>
            </div>
            <div className="p-4">
              <p className="text-sm text-muted-foreground mb-3">{selectedNode.data.description}</p>
              <div className="text-xs text-muted-foreground">
                <Info className="w-3 h-3 inline mr-1" />
                Click and drag nodes to rearrange. Use scroll to zoom.
              </div>
            </div>
            <div className="border-t p-3">
              <Button 
                variant="ghost" 
                size="sm" 
                className="w-full"
                onClick={() => setSelectedNode(null)}
              >
                Close
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Stats Bar */}
      <div className="border-t bg-card px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-emerald-500" />
            <span className="text-muted-foreground">HR Module</span>
            <span className="font-medium text-foreground">4/8</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-orange-500" />
            <span className="text-muted-foreground">Sales Module</span>
            <span className="font-medium text-foreground">9/11</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-blue-500" />
            <span className="text-muted-foreground">Consulting Module</span>
            <span className="font-medium text-foreground">4/10</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded bg-purple-500" />
            <span className="text-muted-foreground">Finance Module</span>
            <span className="font-medium text-foreground">0/0</span>
          </div>
        </div>
        <div className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{stats.total}</span> total processes • 
          <span className="font-medium text-green-600 dark:text-green-400 ml-1">{Math.round((stats.exists / stats.total) * 100)}%</span> complete
        </div>
      </div>
    </div>
  );
};

export default FlowDiagram;
