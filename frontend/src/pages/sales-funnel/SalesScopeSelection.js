import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { API, AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Checkbox } from '../../components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { 
  ArrowLeft, ArrowRight, Plus, Check, X, CheckCircle, 
  FileText, FolderOpen, Search, Loader2, Send
} from 'lucide-react';
import { toast } from 'sonner';

const SalesScopeSelection = () => {
  const { pricingPlanId } = useParams();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('lead_id');
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [pricingPlan, setPricingPlan] = useState(null);
  const [lead, setLead] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  
  // Grouped scopes from master
  const [groupedScopes, setGroupedScopes] = useState([]);
  const [selectedScopes, setSelectedScopes] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  
  // Custom scope dialog
  const [customScopeDialog, setCustomScopeDialog] = useState(false);
  const [customScopes, setCustomScopes] = useState([]);
  const [newCustomScope, setNewCustomScope] = useState({ name: '', category_id: '', description: '' });
  
  // Existing SOW check
  const [existingSOW, setExistingSOW] = useState(null);

  useEffect(() => {
    fetchData();
  }, [pricingPlanId]);

  const fetchData = async () => {
    try {
      // Fetch pricing plan
      const plansRes = await axios.get(`${API}/pricing-plans`);
      const plan = plansRes.data.find(p => p.id === pricingPlanId);
      if (plan) {
        setPricingPlan(plan);
        if (plan.lead_id) {
          const leadsRes = await axios.get(`${API}/leads`);
          const leadData = leadsRes.data.find(l => l.id === plan.lead_id);
          setLead(leadData);
        }
      }
      
      // Fetch grouped scopes from master
      const scopesRes = await axios.get(`${API}/sow-masters/scopes/grouped`);
      setGroupedScopes(scopesRes.data || []);
      
      // Check if enhanced SOW already exists
      try {
        const sowRes = await axios.get(`${API}/enhanced-sow/by-pricing-plan/${pricingPlanId}`);
        setExistingSOW(sowRes.data);
      } catch (err) {
        setExistingSOW(null);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const toggleScope = (scopeId) => {
    const newSelected = new Set(selectedScopes);
    if (newSelected.has(scopeId)) {
      newSelected.delete(scopeId);
    } else {
      newSelected.add(scopeId);
    }
    setSelectedScopes(newSelected);
  };

  const toggleCategory = (categoryScopes) => {
    const scopeIds = categoryScopes.map(s => s.id);
    const allSelected = scopeIds.every(id => selectedScopes.has(id));
    
    const newSelected = new Set(selectedScopes);
    if (allSelected) {
      scopeIds.forEach(id => newSelected.delete(id));
    } else {
      scopeIds.forEach(id => newSelected.add(id));
    }
    setSelectedScopes(newSelected);
  };

  const addCustomScope = () => {
    if (!newCustomScope.name.trim() || !newCustomScope.category_id) {
      toast.error('Please fill in scope name and select a category');
      return;
    }
    
    setCustomScopes([...customScopes, { ...newCustomScope, id: `custom-${Date.now()}` }]);
    setNewCustomScope({ name: '', category_id: '', description: '' });
    setCustomScopeDialog(false);
    toast.success('Custom scope added');
  };

  const removeCustomScope = (customId) => {
    setCustomScopes(customScopes.filter(s => s.id !== customId));
  };

  const handleSubmit = async () => {
    const totalSelected = selectedScopes.size + customScopes.length;
    if (totalSelected === 0) {
      toast.error('Please select at least one scope');
      return;
    }
    
    setSubmitting(true);
    try {
      const payload = {
        scope_template_ids: Array.from(selectedScopes),
        custom_scopes: customScopes.map(s => ({
          name: s.name,
          category_id: s.category_id,
          description: s.description
        }))
      };
      
      await axios.post(
        `${API}/enhanced-sow/${pricingPlanId}/sales-selection`,
        payload,
        {
          params: {
            current_user_id: user?.id,
            current_user_name: user?.full_name || user?.email,
            current_user_role: user?.role
          }
        }
      );
      
      toast.success('Scope of Work created successfully!');
      // Navigate to Proforma Invoice page after scope selection
      navigate(`/sales-funnel/proforma-invoice?pricing_plan_id=${pricingPlanId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create SOW');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredGroupedScopes = groupedScopes.map(group => ({
    ...group,
    scopes: group.scopes.filter(scope => 
      scope.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      scope.description?.toLowerCase().includes(searchQuery.toLowerCase())
    )
  })).filter(group => group.scopes.length > 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  // If SOW already exists, show message and redirect to quotation
  if (existingSOW) {
    return (
      <div data-testid="sales-scope-selection-page">
        <Button onClick={() => navigate('/sales-funnel/pricing-plans')} variant="ghost" className="mb-4 hover:bg-zinc-100 rounded-sm">
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Pricing Plans
        </Button>
        
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <CheckCircle className="w-16 h-16 text-emerald-500 mb-4" strokeWidth={1} />
            <h3 className="text-lg font-medium text-zinc-700 mb-2">SOW Already Created</h3>
            <p className="text-zinc-500 mb-6 text-center max-w-md">
              A Scope of Work has already been created for this pricing plan with {existingSOW.scopes?.length || 0} scopes.
            </p>
            <div className="flex gap-3">
              <Button 
                onClick={() => navigate(`/sales-funnel/quotations?pricing_plan_id=${pricingPlanId}`)}
                className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              >
                Proceed to Quotation
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div data-testid="sales-scope-selection-page">
      {/* Header */}
      <div className="mb-6">
        <Button onClick={() => navigate('/sales-funnel/pricing-plans')} variant="ghost" className="mb-4 hover:bg-zinc-100 rounded-sm">
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Pricing Plans
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              Select Scope of Work
            </h1>
            <p className="text-zinc-500">
              {lead ? `${lead.first_name} ${lead.last_name} - ${lead.company}` : 'Loading...'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-sm text-zinc-500">Selected Scopes</div>
              <div className="text-2xl font-semibold text-zinc-950">
                {selectedScopes.size + customScopes.length}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Search and Add Custom Scope */}
      <div className="flex items-center justify-between mb-6 gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search scopes..."
            className="pl-10 rounded-sm border-zinc-200"
            data-testid="scope-search-input"
          />
        </div>
        <Button
          onClick={() => setCustomScopeDialog(true)}
          variant="outline"
          className="rounded-sm"
          data-testid="add-custom-scope-btn"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Custom Scope
        </Button>
      </div>

      {/* Custom Scopes Section */}
      {customScopes.length > 0 && (
        <Card className="border-blue-200 bg-blue-50/50 shadow-none rounded-sm mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-blue-700 flex items-center gap-2">
              <Plus className="w-4 h-4" />
              Custom Scopes ({customScopes.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-blue-200">
              {customScopes.map(scope => {
                const category = groupedScopes.find(g => g.category.id === scope.category_id)?.category;
                return (
                  <div 
                    key={scope.id} 
                    className="flex items-center justify-between px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-blue-600" />
                      <div>
                        <div className="font-medium text-zinc-900">{scope.name}</div>
                        <div className="text-xs text-zinc-500">
                          {category?.name || 'Unknown Category'}
                          {scope.description && ` • ${scope.description}`}
                        </div>
                      </div>
                    </div>
                    <Button
                      onClick={() => removeCustomScope(scope.id)}
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Scope Table - Categories with 2 scopes per row */}
      <div className="space-y-4">
        {filteredGroupedScopes.map(group => {
          const categoryScopes = group.scopes;
          const selectedInCategory = categoryScopes.filter(s => selectedScopes.has(s.id)).length;
          const allSelected = selectedInCategory === categoryScopes.length && categoryScopes.length > 0;
          
          // Create pairs of scopes (2 per row)
          const scopePairs = [];
          for (let i = 0; i < categoryScopes.length; i += 2) {
            scopePairs.push(categoryScopes.slice(i, i + 2));
          }
          
          return (
            <Card 
              key={group.category.id} 
              className="border-zinc-200 shadow-none rounded-sm"
              data-testid={`category-${group.category.code}`}
            >
              <CardHeader 
                className="pb-2 cursor-pointer hover:bg-zinc-50 transition-colors border-b border-zinc-100"
                onClick={() => toggleCategory(categoryScopes)}
              >
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-700 flex items-center gap-2">
                    <div 
                      className="w-3 h-3 rounded-sm"
                      style={{ backgroundColor: group.category.color }}
                    />
                    <FolderOpen className="w-4 h-4" />
                    {group.category.name}
                    <span className="text-xs font-normal text-zinc-500">
                      ({selectedInCategory}/{categoryScopes.length} selected)
                    </span>
                  </CardTitle>
                  <Checkbox
                    checked={allSelected}
                    className="border-zinc-300"
                    data-testid={`category-checkbox-${group.category.code}`}
                  />
                </div>
              </CardHeader>
              <CardContent className="p-4">
                {/* Table View - 2 scopes per row */}
                <div className="space-y-2">
                  {scopePairs.map((pair, pairIndex) => (
                    <div key={pairIndex} className="grid grid-cols-2 gap-3">
                      {pair.map(scope => {
                        const isSelected = selectedScopes.has(scope.id);
                        return (
                          <div
                            key={scope.id}
                            onClick={() => toggleScope(scope.id)}
                            className={`px-4 py-3 cursor-pointer transition-all flex items-center gap-3 rounded-sm border ${
                              isSelected 
                                ? 'bg-emerald-50 border-emerald-200' 
                                : 'bg-white border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300'
                            }`}
                            data-testid={`scope-item-${scope.id}`}
                          >
                            <Checkbox
                              checked={isSelected}
                              className={isSelected ? 'border-emerald-500 data-[state=checked]:bg-emerald-500' : 'border-zinc-300'}
                            />
                            <span className={`text-sm font-medium flex-1 truncate ${isSelected ? 'text-emerald-900' : 'text-zinc-900'}`}>
                              {scope.name}
                            </span>
                            {isSelected && (
                              <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                            )}
                          </div>
                        );
                      })}
                      {/* Fill empty space if odd number of scopes */}
                      {pair.length === 1 && <div className="hidden md:block"></div>}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {filteredGroupedScopes.length === 0 && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Search className="w-12 h-12 text-zinc-300 mb-4" />
            <p className="text-zinc-500">No scopes found matching your search</p>
          </CardContent>
        </Card>
      )}

      {/* Submit Button */}
      <div className="mt-8 flex justify-end gap-3">
        <Button
          onClick={() => navigate('/sales-funnel/pricing-plans')}
          variant="outline"
          className="rounded-sm"
        >
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={submitting || (selectedScopes.size + customScopes.length === 0)}
          className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
          data-testid="submit-scopes-btn"
        >
          {submitting ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Creating SOW...
            </>
          ) : (
            <>
              <Send className="w-4 h-4 mr-2" />
              Create SOW & Proceed to Quotation ({selectedScopes.size + customScopes.length} scopes)
            </>
          )}
        </Button>
      </div>

      {/* Custom Scope Dialog */}
      <Dialog open={customScopeDialog} onOpenChange={setCustomScopeDialog}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Add Custom Scope
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Add a custom scope that will be saved to master for future use.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Category *</Label>
              <select
                value={newCustomScope.category_id}
                onChange={(e) => setNewCustomScope({ ...newCustomScope, category_id: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent"
                data-testid="custom-scope-category"
              >
                <option value="">Select category...</option>
                {groupedScopes.map(group => (
                  <option key={group.category.id} value={group.category.id}>
                    {group.category.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Scope Name *</Label>
              <Input
                value={newCustomScope.name}
                onChange={(e) => setNewCustomScope({ ...newCustomScope, name: e.target.value })}
                placeholder="Enter scope name..."
                className="rounded-sm"
                data-testid="custom-scope-name"
              />
            </div>
            <div className="space-y-2">
              <Label>Description (Optional)</Label>
              <textarea
                value={newCustomScope.description}
                onChange={(e) => setNewCustomScope({ ...newCustomScope, description: e.target.value })}
                placeholder="Brief description..."
                rows={2}
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-400"
                data-testid="custom-scope-description"
              />
            </div>
            <div className="flex gap-3 pt-2">
              <Button 
                onClick={() => setCustomScopeDialog(false)} 
                variant="outline" 
                className="flex-1 rounded-sm"
              >
                Cancel
              </Button>
              <Button 
                onClick={addCustomScope}
                className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                data-testid="save-custom-scope-btn"
              >
                Add Scope
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SalesScopeSelection;
