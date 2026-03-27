/**
 * SOWBuilder - Unified Scope of Work Builder
 * 
 * Sales creates SOW with: Category | Scope | Deliverables (comma-separated in single line)
 * Links to: Quotation → Agreement → Kickoff → Project SOW
 */

import React, { useState, useEffect, useContext } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Badge } from '../../components/ui/badge';
import { 
  ArrowLeft, Plus, Trash2, Sparkles, Save, Library, 
  Check, Loader2, FileText, Lock, ArrowRight, PlusCircle
} from 'lucide-react';
import { toast } from 'sonner';
import FunnelStepperHeader from '../../components/FunnelStepperHeader';

const API = process.env.REACT_APP_BACKEND_URL;

const SOWBuilderNew = () => {
  const { pricingPlanId } = useParams();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('lead_id');
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const queryClient = useQueryClient();

  // State
  const [scopes, setScopes] = useState([]);
  const [saving, setSaving] = useState(false);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryCode, setNewCategoryCode] = useState('');
  const [newCategoryColor, setNewCategoryColor] = useState('#3B82F6');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [suggestingId, setSuggestingId] = useState(null);

  // Fetch pricing plan and lead data
  const { data: planData } = useQuery({
    queryKey: ['pricing-plan', pricingPlanId],
    queryFn: async () => {
      const plansRes = await axios.get(`${API}/api/pricing-plans`);
      const plan = (plansRes?.data || []).find(p => p.id === pricingPlanId);
      let lead = null;
      if (plan?.lead_id) {
        const leadsRes = await axios.get(`${API}/api/leads`);
        const leadsArray = leadsRes?.data?.items || leadsRes?.data || [];
        lead = leadsArray.find(l => l.id === plan.lead_id);
      }
      return { plan, lead };
    },
    enabled: !!pricingPlanId
  });

  const plan = planData?.plan;
  const lead = planData?.lead;

  // Fetch existing SOW
  const { data: sowData, isLoading: loadingSOW } = useQuery({
    queryKey: ['enhanced-sow-simple', pricingPlanId],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/enhanced-sow/by-pricing-plan-simple/${pricingPlanId}`);
      return res.data;
    },
    enabled: !!pricingPlanId
  });

  // Fetch categories
  const { data: categories = [], refetch: refetchCategories } = useQuery({
    queryKey: ['sow-categories'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/sow-masters/categories`);
      return res.data || [];
    }
  });

  // Fetch scope library (grouped by category)
  const { data: scopeLibrary = [] } = useQuery({
    queryKey: ['sow-scope-library'],
    queryFn: async () => {
      const res = await axios.get(`${API}/api/sow-masters/scopes/grouped`);
      return res.data || [];
    }
  });

  // Load existing scopes when SOW data arrives
  useEffect(() => {
    if (sowData?.sow?.scopes) {
      setScopes(sowData.sow.scopes.map(s => ({
        id: s.id,
        category_code: s.category_code,
        category_name: s.category_name,
        name: s.name,
        deliverables: s.deliverables_text || s.deliverables?.join(', ') || ''
      })));
    }
  }, [sowData]);

  const existingSOW = sowData?.sow;
  const isLocked = existingSOW?.is_locked;

  // Create SOW mutation
  const createMutation = useMutation({
    mutationFn: async (scopeData) => {
      const res = await axios.post(`${API}/api/enhanced-sow/simple-create`, {
        pricing_plan_id: pricingPlanId,
        lead_id: leadId || plan?.lead_id,
        scopes: scopeData
      });
      return res.data;
    },
    onSuccess: () => {
      toast.success('SOW created successfully');
      queryClient.invalidateQueries(['enhanced-sow-simple', pricingPlanId]);
      // Navigate back to funnel after successful save
      if (leadId) {
        navigate(`/leads/${leadId}/funnel`);
      } else {
        navigate(-1);
      }
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to create SOW');
    }
  });

  // Update SOW mutation
  const updateMutation = useMutation({
    mutationFn: async (scopeData) => {
      const res = await axios.put(`${API}/api/enhanced-sow/${existingSOW.id}/simple-update`, {
        scopes: scopeData
      });
      return res.data;
    },
    onSuccess: () => {
      toast.success('SOW updated successfully');
      queryClient.invalidateQueries(['enhanced-sow-simple', pricingPlanId]);
      // Navigate back to funnel after successful save
      if (leadId) {
        navigate(`/leads/${leadId}/funnel`);
      } else {
        navigate(-1);
      }
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to update SOW');
    }
  });

  // AI Suggest deliverables mutation
  const suggestMutation = useMutation({
    mutationFn: async ({ scopeName, categoryCode }) => {
      const res = await axios.post(`${API}/api/sow-masters/ai-suggest-deliverables`, {
        scope_name: scopeName,
        category_code: categoryCode
      });
      return res.data;
    }
  });

  // Create category mutation
  const createCategoryMutation = useMutation({
    mutationFn: async (categoryData) => {
      const res = await axios.post(`${API}/api/sow-masters/categories`, categoryData);
      return res.data;
    },
    onSuccess: () => {
      toast.success('Category created successfully');
      refetchCategories();
      setCategoryDialogOpen(false);
      setNewCategoryName('');
      setNewCategoryCode('');
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to create category');
    }
  });

  // Add empty scope row
  const addScope = () => {
    setScopes([...scopes, {
      id: `new-${Date.now()}`,
      category_code: '',
      category_name: '',
      name: '',
      deliverables: ''
    }]);
  };

  // Remove scope row
  const removeScope = (id) => {
    setScopes(scopes.filter(s => s.id !== id));
  };

  // Update scope field
  const updateScope = (id, field, value) => {
    setScopes(scopes.map(s => {
      if (s.id !== id) return s;
      
      const updated = { ...s, [field]: value };
      
      // If category changed, update category_name
      if (field === 'category_code') {
        const cat = categories.find(c => c.code === value);
        updated.category_name = cat?.name || value;
      }
      
      return updated;
    }));
  };

  // AI suggest deliverables for a scope
  const handleSuggestDeliverables = async (scopeId) => {
    const scope = scopes.find(s => s.id === scopeId);
    if (!scope?.name) {
      toast.error('Enter scope name first');
      return;
    }

    setSuggestingId(scopeId);
    try {
      const result = await suggestMutation.mutateAsync({
        scopeName: scope.name,
        categoryCode: scope.category_code
      });
      
      const deliverables = result.deliverables?.join(', ') || '';
      updateScope(scopeId, 'deliverables', deliverables);
      
      if (result.source === 'ai') {
        toast.success('AI suggested deliverables');
      } else if (result.source === 'library') {
        toast.success('Found deliverables from library');
      }
    } catch (err) {
      toast.error('Failed to suggest deliverables');
    } finally {
      setSuggestingId(null);
    }
  };

  // Add scope from library
  const addFromLibrary = (template) => {
    const existingIds = new Set(scopes.map(s => s.name?.toLowerCase()));
    if (existingIds.has(template.name?.toLowerCase())) {
      toast.error('This scope is already added');
      return;
    }

    setScopes([...scopes, {
      id: `lib-${Date.now()}`,
      category_code: template.category_code,
      category_name: template.category_name || template.category_code,
      name: template.name,
      deliverables: template.deliverables?.join(', ') || ''
    }]);
    
    toast.success(`Added "${template.name}"`);
  };

  // Save SOW
  const handleSave = async () => {
    // Validate
    const validScopes = scopes.filter(s => s.category_code && s.name);
    if (validScopes.length === 0) {
      toast.error('Add at least one scope with category and name');
      return;
    }

    setSaving(true);
    try {
      if (existingSOW) {
        await updateMutation.mutateAsync(validScopes);
      } else {
        await createMutation.mutateAsync(validScopes);
      }
    } finally {
      setSaving(false);
    }
  };

  // Handle create category
  const handleCreateCategory = () => {
    if (!newCategoryName.trim()) {
      toast.error('Category name is required');
      return;
    }
    const code = newCategoryCode || newCategoryName.toLowerCase().replace(/\s+/g, '_');
    createCategoryMutation.mutate({
      name: newCategoryName,
      code: code,
      color: newCategoryColor,
      description: ''
    });
  };

  // Navigate to quotation
  const goToQuotation = () => {
    navigate(`/sales-funnel/proforma-invoices?pricing_plan_id=${pricingPlanId}&leadId=${leadId || plan?.lead_id}`);
  };

  // Filter library by category
  const filteredLibrary = selectedCategory === 'all' 
    ? scopeLibrary 
    : scopeLibrary.filter(g => g.category?.code === selectedCategory);

  if (loadingSOW) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-xl font-semibold">Scope of Work</h1>
            <p className="text-sm text-zinc-500">
              {lead?.company || plan?.client_name || 'New SOW'}
              {existingSOW?.sow_number && ` • ${existingSOW.sow_number}`}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {isLocked && (
            <Badge variant="secondary" className="gap-1">
              <Lock className="w-3 h-3" /> Locked
            </Badge>
          )}
          <Button variant="outline" size="sm" onClick={() => setLibraryOpen(true)}>
            <Library className="w-4 h-4 mr-1" />
            Pick from Library
          </Button>
          <Button 
            size="sm" 
            onClick={handleSave} 
            disabled={saving || isLocked}
          >
            {saving ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Save className="w-4 h-4 mr-1" />}
            Save
          </Button>
        </div>
      </div>

      {/* Funnel Progress */}
      {(leadId || plan?.lead_id) && <FunnelStepperHeader leadId={leadId || plan?.lead_id} currentStepId="scope_of_work" />}

      {/* SOW Table */}
      <Card>
        <CardHeader className="py-3 border-b">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Scope Items ({scopes.length})
            </CardTitle>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={addScope}
              disabled={isLocked}
            >
              <Plus className="w-4 h-4 mr-1" />
              Add Scope
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-2 px-4 py-2 bg-zinc-50 border-b text-xs font-medium text-zinc-600">
            <div className="col-span-1">#</div>
            <div className="col-span-2">Category</div>
            <div className="col-span-3">Scope</div>
            <div className="col-span-5">Deliverables</div>
            <div className="col-span-1"></div>
          </div>

          {/* Table Rows */}
          {scopes.length === 0 ? (
            <div className="text-center py-12 text-zinc-400">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No scopes added yet</p>
              <p className="text-xs mt-1">Click "Add Scope" or "Pick from Library" to start</p>
            </div>
          ) : (
            <div className="divide-y">
              {scopes.map((scope, idx) => (
                <div 
                  key={scope.id} 
                  className="grid grid-cols-12 gap-2 px-4 py-2 items-center hover:bg-zinc-50"
                >
                  {/* Row Number */}
                  <div className="col-span-1 text-sm text-zinc-400">{idx + 1}</div>
                  
                  {/* Category Dropdown */}
                  <div className="col-span-2">
                    <Select
                      value={scope.category_code}
                      onValueChange={(v) => {
                        if (v === '__add_new__') {
                          setCategoryDialogOpen(true);
                        } else {
                          updateScope(scope.id, 'category_code', v);
                        }
                      }}
                      disabled={isLocked}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="Select..." />
                      </SelectTrigger>
                      <SelectContent>
                        {categories.map(cat => (
                          <SelectItem key={cat.code} value={cat.code}>
                            <span className="flex items-center gap-2">
                              <span 
                                className="w-2 h-2 rounded-full" 
                                style={{ backgroundColor: cat.color }}
                              />
                              {cat.name}
                            </span>
                          </SelectItem>
                        ))}
                        <SelectItem value="__add_new__" className="text-blue-600 border-t mt-1 pt-1">
                          <span className="flex items-center gap-2">
                            <PlusCircle className="w-3 h-3" />
                            Add New Category
                          </span>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {/* Scope Name */}
                  <div className="col-span-3">
                    <Input
                      value={scope.name}
                      onChange={(e) => updateScope(scope.id, 'name', e.target.value)}
                      placeholder="Scope name..."
                      className="h-8 text-sm"
                      disabled={isLocked}
                    />
                  </div>
                  
                  {/* Deliverables with AI Suggest */}
                  <div className="col-span-5 flex items-center gap-1">
                    <Input
                      value={scope.deliverables}
                      onChange={(e) => updateScope(scope.id, 'deliverables', e.target.value)}
                      placeholder="e.g. Report, Training Manual, Dashboard"
                      className="h-8 text-sm flex-1"
                      disabled={isLocked}
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 text-purple-600 hover:text-purple-700 hover:bg-purple-50"
                      onClick={() => handleSuggestDeliverables(scope.id)}
                      disabled={isLocked || suggestingId === scope.id}
                      title="AI Suggest Deliverables"
                    >
                      {suggestingId === scope.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Sparkles className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                  
                  {/* Delete Button */}
                  <div className="col-span-1 flex justify-end">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 text-red-500 hover:text-red-600 hover:bg-red-50"
                      onClick={() => removeScope(scope.id)}
                      disabled={isLocked}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      {existingSOW && (
        <div className="flex justify-end">
          <Button onClick={goToQuotation}>
            Continue to Quotation
            <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      )}

      {/* Library Dialog */}
      <Dialog open={libraryOpen} onOpenChange={setLibraryOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Scope Library</DialogTitle>
          </DialogHeader>
          
          {/* Category Filter */}
          <div className="flex items-center gap-2 pb-2 border-b">
            <span className="text-sm text-zinc-500">Filter:</span>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger className="w-40 h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map(cat => (
                  <SelectItem key={cat.code} value={cat.code}>{cat.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {/* Library List */}
          <div className="flex-1 overflow-y-auto space-y-4 py-2">
            {filteredLibrary.map(group => (
              <div key={group.category?.code} className="space-y-1">
                <h3 className="text-sm font-medium flex items-center gap-2 px-2 py-1 bg-zinc-50 rounded">
                  <span 
                    className="w-2 h-2 rounded-full" 
                    style={{ backgroundColor: group.category?.color }}
                  />
                  {group.category?.name} ({group.scopes?.length || 0})
                </h3>
                <div className="space-y-1 pl-4">
                  {group.scopes?.map(template => {
                    const isAdded = scopes.some(s => 
                      s.name?.toLowerCase() === template.name?.toLowerCase()
                    );
                    return (
                      <div 
                        key={template.id}
                        className="flex items-center justify-between p-2 hover:bg-zinc-50 rounded"
                      >
                        <div className="flex-1">
                          <p className="text-sm font-medium">{template.name}</p>
                          {template.deliverables?.length > 0 && (
                            <p className="text-xs text-zinc-500">
                              {template.deliverables.join(', ')}
                            </p>
                          )}
                        </div>
                        <Button
                          variant={isAdded ? "secondary" : "outline"}
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => addFromLibrary({
                            ...template,
                            category_code: group.category?.code,
                            category_name: group.category?.name
                          })}
                          disabled={isAdded}
                        >
                          {isAdded ? (
                            <>
                              <Check className="w-3 h-3 mr-1" />
                              Added
                            </>
                          ) : (
                            <>
                              <Plus className="w-3 h-3 mr-1" />
                              Add
                            </>
                          )}
                        </Button>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Add Category Dialog */}
      <Dialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add New Category</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium">Category Name *</label>
              <Input
                value={newCategoryName}
                onChange={(e) => setNewCategoryName(e.target.value)}
                placeholder="e.g., Quality, Maintenance"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Category Code (optional)</label>
              <Input
                value={newCategoryCode}
                onChange={(e) => setNewCategoryCode(e.target.value)}
                placeholder="Auto-generated if empty"
                className="mt-1"
              />
              <p className="text-xs text-zinc-500 mt-1">Used internally, e.g., "quality_assurance"</p>
            </div>
            <div>
              <label className="text-sm font-medium">Color</label>
              <div className="flex items-center gap-2 mt-1">
                <input
                  type="color"
                  value={newCategoryColor}
                  onChange={(e) => setNewCategoryColor(e.target.value)}
                  className="w-10 h-10 rounded cursor-pointer"
                />
                <span className="text-sm text-zinc-500">{newCategoryColor}</span>
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setCategoryDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateCategory} disabled={createCategoryMutation.isPending}>
              {createCategoryMutation.isPending ? (
                <Loader2 className="w-4 h-4 mr-1 animate-spin" />
              ) : (
                <Plus className="w-4 h-4 mr-1" />
              )}
              Create Category
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SOWBuilderNew;
