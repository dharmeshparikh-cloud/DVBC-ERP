import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { 
  Users, Briefcase, DollarSign, ArrowRight, ArrowDown, AlertTriangle,
  CheckCircle, XCircle, Link2, Unlink, Building2, Target, FileText,
  Calendar, Clock, TrendingUp, UserPlus, UserMinus, Award, BookOpen,
  CreditCard, Receipt, PieChart, Settings, Bell, ChevronRight
} from 'lucide-react';

const FlowDiagram = () => {
  const [activeModule, setActiveModule] = useState(null);
  const [showMissing, setShowMissing] = useState(true);

  // HR Module Flow
  const hrFlow = [
    { id: 'recruitment', name: 'Recruitment', status: 'missing', icon: UserPlus, 
      desc: 'Job posting, Applications, Interviews' },
    { id: 'onboarding', name: 'Onboarding', status: 'missing', icon: BookOpen,
      desc: 'Documents, IT setup, Training' },
    { id: 'employee', name: 'Employee Master', status: 'exists', icon: Users,
      desc: 'Profile, Department, Designation' },
    { id: 'attendance', name: 'Attendance', status: 'exists', icon: Clock,
      desc: 'Check-in/out, WFH tracking' },
    { id: 'leave', name: 'Leave Mgmt', status: 'exists', icon: Calendar,
      desc: 'Apply, Approve, Balance' },
    { id: 'payroll', name: 'Payroll', status: 'exists', icon: CreditCard,
      desc: 'Salary, Deductions, Disbursement' },
    { id: 'skills', name: 'Skill Matrix', status: 'missing', icon: Award,
      desc: 'Competencies, Certifications' },
    { id: 'exit', name: 'Exit Process', status: 'missing', icon: UserMinus,
      desc: 'Resignation, Clearance, F&F' },
  ];

  // Sales Module Flow
  const salesFlow = [
    { id: 'lead', name: 'Lead Capture', status: 'exists', icon: UserPlus,
      desc: 'Source, Contact, Company' },
    { id: 'meeting', name: 'Meetings', status: 'exists', icon: Calendar,
      desc: 'Schedule, Attendees, Location' },
    { id: 'mom', name: 'MOM', status: 'exists', icon: FileText,
      desc: 'Minutes, Action items' },
    { id: 'qualify', name: 'Qualification', status: 'exists', icon: Target,
      desc: 'Hot/Warm/Cold scoring' },
    { id: 'pricing', name: 'Pricing Plan', status: 'exists', icon: DollarSign,
      desc: 'Services, Rates, Duration' },
    { id: 'sow', name: 'SOW', status: 'exists', icon: FileText,
      desc: 'Scope, Deliverables, Terms' },
    { id: 'proforma', name: 'Proforma', status: 'exists', icon: Receipt,
      desc: 'Invoice preview' },
    { id: 'agreement', name: 'Agreement', status: 'exists', icon: FileText,
      desc: 'Contract, Signatures' },
    { id: 'kickoff', name: 'Kickoff', status: 'exists', icon: TrendingUp,
      desc: 'Handoff to Consulting' },
    { id: 'forecast', name: 'Forecasting', status: 'missing', icon: PieChart,
      desc: 'Pipeline value prediction' },
    { id: 'commission', name: 'Commission', status: 'missing', icon: DollarSign,
      desc: 'Sales incentive calc' },
  ];

  // Consulting Module Flow
  const consultingFlow = [
    { id: 'project', name: 'Project Setup', status: 'exists', icon: Briefcase,
      desc: 'From kickoff approval' },
    { id: 'team', name: 'Team Allocation', status: 'exists', icon: Users,
      desc: 'Assign consultants' },
    { id: 'timesheet', name: 'Timesheets', status: 'missing', icon: Clock,
      desc: 'Effort logging, Approval' },
    { id: 'milestone', name: 'Milestones', status: 'missing', icon: Target,
      desc: 'Deliverables, Deadlines' },
    { id: 'sowchange', name: 'SOW Changes', status: 'exists', icon: FileText,
      desc: 'Scope modifications' },
    { id: 'delivery', name: 'Delivery', status: 'partial', icon: CheckCircle,
      desc: 'Sign-off, Acceptance' },
    { id: 'pnl', name: 'Project P&L', status: 'missing', icon: PieChart,
      desc: 'Revenue vs Cost' },
    { id: 'invoice', name: 'Invoicing', status: 'missing', icon: Receipt,
      desc: 'Generate from milestones' },
    { id: 'payment', name: 'Payment Track', status: 'exists', icon: CreditCard,
      desc: 'Reminders, Collection' },
    { id: 'nps', name: 'Client NPS', status: 'missing', icon: Award,
      desc: 'Satisfaction score' },
  ];

  // Cross-module linkages
  const linkages = [
    { from: 'HR', to: 'Sales', name: 'Bench → Capacity', status: 'missing',
      desc: 'Check available salespeople before lead assignment' },
    { from: 'HR', to: 'Consulting', name: 'Skills → Staffing', status: 'missing',
      desc: 'Match consultant skills to project needs' },
    { from: 'Sales', to: 'HR', name: 'Deal → Hiring', status: 'missing',
      desc: 'Trigger hiring for large deals' },
    { from: 'Sales', to: 'Consulting', name: 'Context Transfer', status: 'partial',
      desc: 'Pass SOW, expectations, client history' },
    { from: 'Consulting', to: 'HR', name: 'Utilization Update', status: 'missing',
      desc: 'Update employee utilization %' },
    { from: 'Consulting', to: 'Finance', name: 'Work → Invoice', status: 'missing',
      desc: 'Auto-generate invoices from delivered milestones' },
    { from: 'Finance', to: 'HR', name: 'Revenue → Payroll', status: 'missing',
      desc: 'Performance bonus, Commission payout' },
    { from: 'All', to: 'All', name: 'Unified Notifications', status: 'missing',
      desc: 'Single notification system across modules' },
  ];

  // Duplicates
  const duplicates = [
    { area: 'User Data', modules: ['HR Employees', 'Users Table'], 
      issue: 'Separate tables, potential sync issues' },
    { area: 'Approval Workflow', modules: ['Leave', 'SOW Change', 'Kickoff'], 
      issue: 'Different approval logic in each module' },
    { area: 'Client Data', modules: ['Leads', 'Clients', 'Agreements'], 
      issue: 'Client info scattered across collections' },
    { area: 'Notifications', modules: ['Email', 'In-app', 'Reminders'], 
      issue: 'No unified notification center' },
  ];

  const getStatusColor = (status) => {
    switch(status) {
      case 'exists': return 'bg-green-500';
      case 'partial': return 'bg-amber-500';
      case 'missing': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusBg = (status) => {
    switch(status) {
      case 'exists': return 'bg-green-50 border-green-200';
      case 'partial': return 'bg-amber-50 border-amber-200';
      case 'missing': return 'bg-red-50 border-red-200';
      default: return 'bg-gray-50 border-gray-200';
    }
  };

  const FlowStep = ({ step, index, total }) => {
    if (!showMissing && step.status === 'missing') return null;
    const Icon = step.icon;
    return (
      <div className="flex items-center">
        <div className={`relative p-3 rounded-lg border-2 ${getStatusBg(step.status)} 
          hover:shadow-md transition-shadow cursor-pointer min-w-[140px]`}>
          <div className={`absolute -top-2 -right-2 w-4 h-4 rounded-full ${getStatusColor(step.status)}`} />
          <div className="flex items-center gap-2 mb-1">
            <Icon className="w-4 h-4 text-zinc-600" />
            <span className="font-medium text-sm text-zinc-800">{step.name}</span>
          </div>
          <p className="text-xs text-zinc-500">{step.desc}</p>
        </div>
        {index < total - 1 && (
          <ArrowRight className="w-5 h-5 mx-1 text-zinc-300 flex-shrink-0" />
        )}
      </div>
    );
  };

  return (
    <div className="p-6 space-y-8 bg-zinc-50 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-zinc-900">ERP Flow Analysis</h1>
          <p className="text-zinc-500">End-to-end business process mapping</p>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input 
              type="checkbox" 
              checked={showMissing} 
              onChange={(e) => setShowMissing(e.target.checked)}
              className="w-4 h-4 rounded"
            />
            <span className="text-sm text-zinc-600">Show Missing Items</span>
          </label>
          <div className="flex items-center gap-3 text-sm">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span>Exists</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-amber-500" />
              <span>Partial</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span>Missing</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Flow Diagram */}
      <div className="grid grid-cols-1 gap-6">
        
        {/* HR Module */}
        <Card className="border-2 border-emerald-200 bg-gradient-to-r from-emerald-50 to-white">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-3">
              <div className="p-2 bg-emerald-500 rounded-lg">
                <Users className="w-6 h-6 text-white" />
              </div>
              <div>
                <span className="text-emerald-700">HR Module</span>
                <p className="text-sm font-normal text-emerald-600">GET PEOPLE</p>
              </div>
              <Badge className="ml-auto bg-emerald-100 text-emerald-700">
                {hrFlow.filter(s => s.status === 'exists').length}/{hrFlow.length} Complete
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-2 overflow-x-auto pb-2">
              {hrFlow.map((step, i) => (
                <FlowStep key={step.id} step={step} index={i} total={hrFlow.length} />
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Connection: HR to Sales */}
        <div className="flex items-center justify-center gap-4 py-2">
          <div className="flex-1 h-px bg-gradient-to-r from-emerald-300 to-orange-300" />
          <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow border">
            <Unlink className="w-4 h-4 text-red-500" />
            <span className="text-sm text-zinc-600">Bench Availability Check</span>
            <Badge variant="destructive" className="text-xs">Missing</Badge>
          </div>
          <div className="flex-1 h-px bg-gradient-to-r from-orange-300 to-emerald-300" />
        </div>

        {/* Sales Module */}
        <Card className="border-2 border-orange-200 bg-gradient-to-r from-orange-50 to-white">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-3">
              <div className="p-2 bg-orange-500 rounded-lg">
                <Target className="w-6 h-6 text-white" />
              </div>
              <div>
                <span className="text-orange-700">Sales Module</span>
                <p className="text-sm font-normal text-orange-600">WORK PEOPLE ON</p>
              </div>
              <Badge className="ml-auto bg-orange-100 text-orange-700">
                {salesFlow.filter(s => s.status === 'exists').length}/{salesFlow.length} Complete
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-2 overflow-x-auto pb-2">
              {salesFlow.map((step, i) => (
                <FlowStep key={step.id} step={step} index={i} total={salesFlow.length} />
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Connection: Sales to Consulting */}
        <div className="flex items-center justify-center gap-4 py-2">
          <div className="flex-1 h-px bg-gradient-to-r from-orange-300 to-blue-300" />
          <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow border">
            <Link2 className="w-4 h-4 text-amber-500" />
            <span className="text-sm text-zinc-600">Kickoff Handoff</span>
            <Badge className="text-xs bg-amber-100 text-amber-700">Partial</Badge>
          </div>
          <div className="flex-1 h-px bg-gradient-to-r from-blue-300 to-orange-300" />
        </div>

        {/* Consulting Module */}
        <Card className="border-2 border-blue-200 bg-gradient-to-r from-blue-50 to-white">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-3">
              <div className="p-2 bg-blue-500 rounded-lg">
                <Briefcase className="w-6 h-6 text-white" />
              </div>
              <div>
                <span className="text-blue-700">Consulting Module</span>
                <p className="text-sm font-normal text-blue-600">ENCASH PEOPLE TO</p>
              </div>
              <Badge className="ml-auto bg-blue-100 text-blue-700">
                {consultingFlow.filter(s => s.status === 'exists').length}/{consultingFlow.length} Complete
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-2 overflow-x-auto pb-2">
              {consultingFlow.map((step, i) => (
                <FlowStep key={step.id} step={step} index={i} total={consultingFlow.length} />
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Connection: Consulting to Finance/HR */}
        <div className="flex items-center justify-center gap-4 py-2">
          <div className="flex-1 h-px bg-gradient-to-r from-blue-300 to-purple-300" />
          <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow border">
            <Unlink className="w-4 h-4 text-red-500" />
            <span className="text-sm text-zinc-600">Invoice Generation & Utilization Update</span>
            <Badge variant="destructive" className="text-xs">Missing</Badge>
          </div>
          <div className="flex-1 h-px bg-gradient-to-r from-purple-300 to-emerald-300" />
        </div>
      </div>

      {/* Cross-Module Linkages */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link2 className="w-5 h-5" />
            Cross-Module Linkages
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            {linkages.map((link, i) => (
              <div 
                key={i}
                className={`p-4 rounded-lg border-2 ${
                  link.status === 'missing' ? 'border-red-200 bg-red-50' :
                  link.status === 'partial' ? 'border-amber-200 bg-amber-50' :
                  'border-green-200 bg-green-50'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{link.from}</Badge>
                    <ArrowRight className="w-4 h-4 text-zinc-400" />
                    <Badge variant="outline">{link.to}</Badge>
                  </div>
                  {link.status === 'missing' ? (
                    <XCircle className="w-5 h-5 text-red-500" />
                  ) : link.status === 'partial' ? (
                    <AlertTriangle className="w-5 h-5 text-amber-500" />
                  ) : (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  )}
                </div>
                <p className="font-medium text-zinc-800">{link.name}</p>
                <p className="text-sm text-zinc-500">{link.desc}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Duplicates */}
      <Card className="border-amber-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-amber-700">
            <AlertTriangle className="w-5 h-5" />
            Potential Duplicates & Data Silos
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            {duplicates.map((dup, i) => (
              <div key={i} className="p-4 rounded-lg bg-amber-50 border border-amber-200">
                <p className="font-medium text-amber-800 mb-2">{dup.area}</p>
                <div className="flex flex-wrap gap-2 mb-2">
                  {dup.modules.map((mod, j) => (
                    <Badge key={j} variant="outline" className="bg-white">{mod}</Badge>
                  ))}
                </div>
                <p className="text-sm text-amber-600">{dup.issue}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-green-500 to-emerald-600 text-white">
          <CardContent className="pt-6">
            <p className="text-green-100 text-sm">Implemented</p>
            <p className="text-4xl font-bold">
              {[...hrFlow, ...salesFlow, ...consultingFlow].filter(s => s.status === 'exists').length}
            </p>
            <p className="text-green-200 text-sm">features working</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-amber-500 to-orange-600 text-white">
          <CardContent className="pt-6">
            <p className="text-amber-100 text-sm">Partial</p>
            <p className="text-4xl font-bold">
              {[...hrFlow, ...salesFlow, ...consultingFlow].filter(s => s.status === 'partial').length}
            </p>
            <p className="text-amber-200 text-sm">need completion</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-red-500 to-rose-600 text-white">
          <CardContent className="pt-6">
            <p className="text-red-100 text-sm">Missing</p>
            <p className="text-4xl font-bold">
              {[...hrFlow, ...salesFlow, ...consultingFlow].filter(s => s.status === 'missing').length}
            </p>
            <p className="text-red-200 text-sm">to be built</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-500 to-indigo-600 text-white">
          <CardContent className="pt-6">
            <p className="text-purple-100 text-sm">Linkages</p>
            <p className="text-4xl font-bold">
              {linkages.filter(l => l.status === 'missing').length}/{linkages.length}
            </p>
            <p className="text-purple-200 text-sm">disconnected</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default FlowDiagram;
