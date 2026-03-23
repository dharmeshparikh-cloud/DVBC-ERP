import React, { useState, useContext } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { toast } from 'sonner';
import { AuthContext, API } from '../../App';
import { useTheme } from '../../contexts/ThemeContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Switch } from '../../components/ui/switch';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '../../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../../components/ui/select';
import {
  Calendar, Plane, Receipt, Clock, DollarSign, FileText, Settings,
  Plus, Edit2, Trash2, Save, X, ChevronRight, Building2, Users,
  User, Briefcase, AlertCircle, CheckCircle, Eye, Search, Filter,
  Loader2, Copy, ToggleLeft, Info, IndianRupee, Calculator
} from 'lucide-react';
import { isAdmin as checkIsAdmin, isHR as checkIsHR } from '../../utils/roles';

const POLICY_TYPE_ICONS = {
  leave: Calendar,
  travel: Plane,
  expense: Receipt,
  attendance: Clock,
  payroll: DollarSign,
  general: FileText
};

const POLICY_TYPE_COLORS = {
  leave: 'bg-blue-100 text-blue-700 border-blue-200',
  travel: 'bg-purple-100 text-purple-700 border-purple-200',
  expense: 'bg-amber-100 text-amber-700 border-amber-200',
  attendance: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  payroll: 'bg-rose-100 text-rose-700 border-rose-200',
  general: 'bg-zinc-100 text-zinc-700 border-zinc-200'
};

const SCOPE_ICONS = {
  company: Building2,
  department: Users,
  role: Briefcase,
  employee: User
};

const BusinessRules = () => {
  const { user } = useContext(AuthContext);
  const { theme } = useTheme();
  const queryClient = useQueryClient();
  const isDark = theme === 'dark';
  
  const isAdmin = checkIsAdmin(user);
  const isHR = checkIsHR(user);
  const canEdit = isAdmin || isHR;
  
  // State
  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [editingRule, setEditingRule] = useState(null);
  const [showPolicyDialog, setShowPolicyDialog] = useState(false);
  const [showRuleDialog, setShowRuleDialog] = useState(false);
  
  // Fetch all policies
  const { data: policies = [], isLoading: loading, refetch } = useQuery({
    queryKey: ['business-policies'],
    queryFn: async () => {
      const res = await axios.get(`${API}/business-rules`);
      return res.data || [];
    },
    staleTime: 3 * 60 * 1000
  });
  
  // Fetch policy types
  const { data: policyTypes } = useQuery({
    queryKey: ['policy-types'],
    queryFn: async () => {
      const res = await axios.get(`${API}/business-rules/types`);
      return res.data;
    },
    staleTime: 30 * 60 * 1000
  });
  
  // Update rule mutation
  const updateRuleMutation = useMutation({
    mutationFn: async ({ policyId, ruleId, ruleData }) => {
      return axios.put(`${API}/business-rules/${policyId}/rule/${ruleId}`, ruleData);
    },
    onSuccess: () => {
      toast.success('Rule updated successfully');
      queryClient.invalidateQueries(['business-policies']);
      setShowRuleDialog(false);
      setEditingRule(null);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to update rule')
  });
  
  // Update policy mutation
  const updatePolicyMutation = useMutation({
    mutationFn: async ({ policyId, policyData }) => {
      return axios.put(`${API}/business-rules/${policyId}`, policyData);
    },
    onSuccess: () => {
      toast.success('Policy updated successfully');
      queryClient.invalidateQueries(['business-policies']);
      setShowPolicyDialog(false);
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to update policy')
  });
  
  // Filter policies
  const filteredPolicies = policies.filter(p => {
    if (activeTab !== 'all' && p.policy_type !== activeTab) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return p.name?.toLowerCase().includes(query) || 
             p.description?.toLowerCase().includes(query) ||
             p.rules?.some(r => r.rule_name?.toLowerCase().includes(query));
    }
    return true;
  });
  
  // Group policies by type
  const policiesByType = policies.reduce((acc, p) => {
    if (!acc[p.policy_type]) acc[p.policy_type] = [];
    acc[p.policy_type].push(p);
    return acc;
  }, {});
  
  const handleEditRule = (policy, rule) => {
    setSelectedPolicy(policy);
    setEditingRule({ ...rule });
    setShowRuleDialog(true);
  };
  
  const handleSaveRule = () => {
    if (!selectedPolicy || !editingRule) return;
    updateRuleMutation.mutate({
      policyId: selectedPolicy.id,
      ruleId: editingRule.rule_id,
      ruleData: editingRule
    });
  };
  
  const handleToggleRule = async (policy, rule) => {
    if (!canEdit) {
      toast.error('You do not have permission to modify rules');
      return;
    }
    
    try {
      await axios.put(`${API}/business-rules/${policy.id}/rule/${rule.rule_id}`, {
        ...rule,
        is_enabled: !rule.is_enabled
      });
      toast.success(`Rule ${rule.is_enabled ? 'disabled' : 'enabled'}`);
      queryClient.invalidateQueries(['business-policies']);
    } catch (err) {
      toast.error('Failed to toggle rule');
    }
  };
  
  const getRuleTypeColor = (type) => {
    const colors = {
      limit: 'bg-red-100 text-red-700',
      threshold: 'bg-blue-100 text-blue-700',
      condition: 'bg-purple-100 text-purple-700',
      formula: 'bg-emerald-100 text-emerald-700',
      approval: 'bg-amber-100 text-amber-700'
    };
    return colors[type] || 'bg-zinc-100 text-zinc-700';
  };
  
  const formatRuleValue = (rule) => {
    if (rule.numeric_value !== undefined && rule.numeric_value !== null) {
      const formatted = new Intl.NumberFormat('en-IN').format(rule.numeric_value);
      return `${formatted} ${rule.unit || ''}`;
    }
    if (rule.value) return rule.value;
    return '-';
  };
  
  const renderRuleCard = (policy, rule, index) => {
    const Icon = rule.is_enabled ? CheckCircle : AlertCircle;
    
    return (
      <div
        key={rule.rule_id || index}
        className={`p-4 rounded-lg border transition-all ${
          rule.is_enabled 
            ? isDark ? 'bg-zinc-800 border-zinc-700' : 'bg-white border-zinc-200'
            : isDark ? 'bg-zinc-900/50 border-zinc-800' : 'bg-zinc-50 border-zinc-200 opacity-60'
        }`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Badge className={`text-xs ${getRuleTypeColor(rule.rule_type)}`}>
                {rule.rule_type?.toUpperCase()}
              </Badge>
              <span className="text-xs text-zinc-500">{rule.rule_id}</span>
              {rule.category && (
                <span className={`text-xs px-2 py-0.5 rounded ${isDark ? 'bg-zinc-700' : 'bg-zinc-100'}`}>
                  {rule.category}
                </span>
              )}
            </div>
            <h4 className="font-medium">{rule.rule_name}</h4>
            <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
              {rule.description}
            </p>
            
            {/* Rule Value Display */}
            <div className={`mt-3 p-2 rounded ${isDark ? 'bg-zinc-900' : 'bg-zinc-50'}`}>
              <div className="flex items-center gap-4 text-sm">
                <div>
                  <span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>Value: </span>
                  <span className="font-mono font-medium">{formatRuleValue(rule)}</span>
                </div>
                {rule.conditions && (
                  <div className="text-xs">
                    <span className={isDark ? 'text-zinc-500' : 'text-zinc-400'}>Conditions: </span>
                    <span className="font-mono">{JSON.stringify(rule.conditions).slice(0, 50)}...</span>
                  </div>
                )}
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {canEdit && (
              <>
                <Switch
                  checked={rule.is_enabled}
                  onCheckedChange={() => handleToggleRule(policy, rule)}
                  data-testid={`toggle-${rule.rule_id}`}
                />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleEditRule(policy, rule)}
                  data-testid={`edit-${rule.rule_id}`}
                >
                  <Edit2 className="w-4 h-4" />
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  };
  
  const renderPolicyCard = (policy) => {
    const TypeIcon = POLICY_TYPE_ICONS[policy.policy_type] || FileText;
    const ScopeIcon = SCOPE_ICONS[policy.scope] || Building2;
    const enabledRules = policy.rules?.filter(r => r.is_enabled)?.length || 0;
    const totalRules = policy.rules?.length || 0;
    
    return (
      <Card 
        key={policy.id} 
        className={`${isDark ? 'bg-zinc-800 border-zinc-700' : ''} hover:shadow-lg transition-shadow cursor-pointer`}
        onClick={() => setSelectedPolicy(selectedPolicy?.id === policy.id ? null : policy)}
        data-testid={`policy-${policy.policy_type}`}
      >
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${POLICY_TYPE_COLORS[policy.policy_type]?.split(' ')[0]} ${isDark ? 'opacity-80' : ''}`}>
                <TypeIcon className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  {policy.name}
                  {policy.is_active ? (
                    <Badge className="bg-emerald-100 text-emerald-700">Active</Badge>
                  ) : (
                    <Badge className="bg-zinc-100 text-zinc-500">Inactive</Badge>
                  )}
                </CardTitle>
                <CardDescription className="flex items-center gap-2 mt-1">
                  <ScopeIcon className="w-3 h-3" />
                  {policy.scope === 'company' ? 'All Employees' : policy.scope_value || policy.scope}
                </CardDescription>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium">{enabledRules}/{totalRules} rules</p>
              <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>
                Effective: {new Date(policy.effective_from).toLocaleDateString()}
              </p>
            </div>
          </div>
        </CardHeader>
        
        {selectedPolicy?.id === policy.id && (
          <CardContent className="pt-4 border-t border-zinc-200 dark:border-zinc-700">
            <p className={`text-sm mb-4 ${isDark ? 'text-zinc-400' : 'text-zinc-600'}`}>
              {policy.description}
            </p>
            
            {/* Rules List */}
            <div className="space-y-3">
              <h4 className="font-medium flex items-center gap-2">
                <Settings className="w-4 h-4" />
                Policy Rules ({totalRules})
              </h4>
              {policy.rules?.map((rule, idx) => renderRuleCard(policy, rule, idx))}
            </div>
            
            {/* Payroll Integration Info */}
            {policy.payroll_integration && Object.keys(policy.payroll_integration).length > 0 && (
              <div className={`mt-4 p-3 rounded-lg ${isDark ? 'bg-emerald-900/20 border border-emerald-800' : 'bg-emerald-50 border border-emerald-200'}`}>
                <h5 className="font-medium text-emerald-700 dark:text-emerald-400 flex items-center gap-2 mb-2">
                  <IndianRupee className="w-4 h-4" />
                  Payroll Integration
                </h5>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(policy.payroll_integration).map(([key, value]) => (
                    <div key={key}>
                      <span className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
                        {key.replace(/_/g, ' ')}: 
                      </span>
                      <span className="font-medium ml-1">
                        {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* CTC Linkage Info */}
            {policy.ctc_linkage && Object.keys(policy.ctc_linkage).length > 0 && (
              <div className={`mt-4 p-3 rounded-lg ${isDark ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
                <h5 className="font-medium text-blue-700 dark:text-blue-400 flex items-center gap-2 mb-2">
                  <Calculator className="w-4 h-4" />
                  CTC Component Linkage
                </h5>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(policy.ctc_linkage).map(([key, value]) => (
                    <div key={key}>
                      <span className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
                        {key.replace(/_/g, ' ')}: 
                      </span>
                      <span className="font-medium ml-1">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        )}
      </Card>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div data-testid="business-rules-page" className={`space-y-6 ${isDark ? 'text-zinc-100' : 'text-zinc-900'}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FileText className="w-6 h-6 text-emerald-600" />
            Business Rules & Policies
          </h1>
          <p className={`text-sm mt-1 ${isDark ? 'text-zinc-400' : 'text-zinc-500'}`}>
            {canEdit ? 'View and manage all company policies and rules' : 'View company policies and rules'}
          </p>
        </div>
        
        {/* Search */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <Input
              type="text"
              placeholder="Search rules..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={`pl-10 w-64 ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}
              data-testid="search-rules"
            />
          </div>
        </div>
      </div>
      
      {/* Permission Notice */}
      {!canEdit && (
        <div className={`p-4 rounded-lg flex items-center gap-3 ${isDark ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
          <Info className="w-5 h-5 text-blue-500" />
          <p className={`text-sm ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>
            You have view-only access to company policies. Contact HR for any policy-related queries.
          </p>
        </div>
      )}
      
      {/* Policy Type Tabs */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setActiveTab('all')}
          className={`px-4 py-2 rounded-lg font-medium text-sm flex items-center gap-2 transition-colors ${
            activeTab === 'all'
              ? 'bg-emerald-600 text-white'
              : isDark ? 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
          }`}
          data-testid="tab-all"
        >
          All Policies
          <Badge className={activeTab === 'all' ? 'bg-white/20 text-white' : ''}>{policies.length}</Badge>
        </button>
        
        {policyTypes?.policy_types?.map(pt => {
          const Icon = POLICY_TYPE_ICONS[pt.id] || FileText;
          const count = policiesByType[pt.id]?.length || 0;
          
          return (
            <button
              key={pt.id}
              onClick={() => setActiveTab(pt.id)}
              className={`px-4 py-2 rounded-lg font-medium text-sm flex items-center gap-2 transition-colors ${
                activeTab === pt.id
                  ? `${POLICY_TYPE_COLORS[pt.id]?.split(' ').slice(0, 2).join(' ')} border`
                  : isDark ? 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
              }`}
              data-testid={`tab-${pt.id}`}
            >
              <Icon className="w-4 h-4" />
              {pt.name}
              {count > 0 && (
                <Badge className={activeTab === pt.id ? 'bg-white/30' : ''}>{count}</Badge>
              )}
            </button>
          );
        })}
      </div>
      
      {/* Stats Summary */}
      <div className="grid grid-cols-6 gap-4">
        {policyTypes?.policy_types?.map(pt => {
          const Icon = POLICY_TYPE_ICONS[pt.id] || FileText;
          const policyList = policiesByType[pt.id] || [];
          const totalRules = policyList.reduce((sum, p) => sum + (p.rules?.length || 0), 0);
          
          return (
            <div
              key={pt.id}
              className={`p-4 rounded-lg border cursor-pointer transition-all ${
                activeTab === pt.id ? 'ring-2 ring-emerald-500' : ''
              } ${isDark ? 'bg-zinc-800 border-zinc-700 hover:bg-zinc-700' : 'bg-white border-zinc-200 hover:bg-zinc-50'}`}
              onClick={() => setActiveTab(pt.id)}
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`w-4 h-4 ${POLICY_TYPE_COLORS[pt.id]?.split(' ')[1]}`} />
                <span className="text-xs font-medium">{pt.name.replace(' Policies', '').replace(' Rules', '')}</span>
              </div>
              <p className="text-2xl font-bold">{totalRules}</p>
              <p className={`text-xs ${isDark ? 'text-zinc-500' : 'text-zinc-400'}`}>rules</p>
            </div>
          );
        })}
      </div>
      
      {/* Policies Grid */}
      <div className="space-y-4">
        {filteredPolicies.length === 0 ? (
          <div className={`text-center py-12 rounded-lg ${isDark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
            <FileText className="w-12 h-12 mx-auto mb-4 text-zinc-400" />
            <p className={isDark ? 'text-zinc-400' : 'text-zinc-500'}>
              {searchQuery ? `No policies found matching "${searchQuery}"` : 'No policies found'}
            </p>
          </div>
        ) : (
          filteredPolicies.map(policy => renderPolicyCard(policy))
        )}
      </div>
      
      {/* Edit Rule Dialog */}
      <Dialog open={showRuleDialog} onOpenChange={setShowRuleDialog}>
        <DialogContent className={`max-w-lg ${isDark ? 'bg-zinc-800 border-zinc-700' : ''}`}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit2 className="w-5 h-5" />
              Edit Rule: {editingRule?.rule_name}
            </DialogTitle>
            <DialogDescription>
              Modify the rule configuration. Changes will take effect immediately.
            </DialogDescription>
          </DialogHeader>
          
          {editingRule && (
            <div className="space-y-4 py-4">
              <div>
                <Label>Rule Name</Label>
                <Input
                  value={editingRule.rule_name || ''}
                  onChange={(e) => setEditingRule({...editingRule, rule_name: e.target.value})}
                  className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                />
              </div>
              
              <div>
                <Label>Description</Label>
                <Input
                  value={editingRule.description || ''}
                  onChange={(e) => setEditingRule({...editingRule, description: e.target.value})}
                  className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Numeric Value</Label>
                  <Input
                    type="number"
                    value={editingRule.numeric_value || ''}
                    onChange={(e) => setEditingRule({...editingRule, numeric_value: parseFloat(e.target.value) || null})}
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
                <div>
                  <Label>Unit</Label>
                  <Input
                    value={editingRule.unit || ''}
                    onChange={(e) => setEditingRule({...editingRule, unit: e.target.value})}
                    className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                  />
                </div>
              </div>
              
              <div>
                <Label>String Value</Label>
                <Input
                  value={editingRule.value || ''}
                  onChange={(e) => setEditingRule({...editingRule, value: e.target.value})}
                  className={isDark ? 'bg-zinc-900 border-zinc-700' : ''}
                />
              </div>
              
              <div className="flex items-center gap-2">
                <Switch
                  checked={editingRule.is_enabled}
                  onCheckedChange={(checked) => setEditingRule({...editingRule, is_enabled: checked})}
                />
                <Label>Rule Enabled</Label>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRuleDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveRule}
              disabled={updateRuleMutation.isPending}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              {updateRuleMutation.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default BusinessRules;
