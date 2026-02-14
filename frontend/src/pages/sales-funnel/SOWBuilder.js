import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { API, AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { 
  ArrowLeft, Plus, Lock, History, Check, X, 
  FileText, Clock, Trash2, Edit2, Eye, ChevronDown, ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const SOW_CATEGORIES = [
  { value: 'sales', label: 'Sales' },
  { value: 'hr', label: 'HR' },
  { value: 'operations', label: 'Operations' },
  { value: 'training', label: 'Training' },
  { value: 'analytics', label: 'Analytics' },
  { value: 'digital_marketing', label: 'Digital Marketing' }
];

const SOWBuilder = () => {
  const { pricingPlanId } = useParams();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('lead_id');
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  
  const [pricingPlan, setPricingPlan] = useState(null);
  const [lead, setLead] = useState(null);
  const [sow, setSow] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [versionDialogOpen, setVersionDialogOpen] = useState(false);
  const [versions, setVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [expandedCategories, setExpandedCategories] = useState({});
  
  const [formData, setFormData] = useState({
    category: 'sales',
    sub_category: '',
    title: '',
    description: '',
    deliverables: [''],
    timeline_weeks: ''
  });

  useEffect(() => {
    fetchData();
  }, [pricingPlanId]);

  const fetchData = async () => {
    try {
      // Get pricing plan
      const plansRes = await axios.get(`${API}/pricing-plans`);
      const plan = plansRes.data.find(p => p.id === pricingPlanId);
      if (plan) {
        setPricingPlan(plan);
        
        // Get lead info
        if (plan.lead_id) {
          const leadsRes = await axios.get(`${API}/leads`);
          const leadData = leadsRes.data.find(l => l.id === plan.lead_id);
          setLead(leadData);
        }
      }
      
      // Get SOW for this pricing plan
      try {
        const sowRes = await axios.get(`${API}/sow/by-pricing-plan/${pricingPlanId}`);
        setSow(sowRes.data);
        
        // Initialize expanded categories
        const expanded = {};
        SOW_CATEGORIES.forEach(cat => {
          expanded[cat.value] = true;
        });
        setExpandedCategories(expanded);
      } catch (err) {
        // SOW doesn't exist yet - that's okay
        setSow(null);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSOW = async () => {
    try {
      await axios.post(`${API}/sow`, {
        pricing_plan_id: pricingPlanId,
        lead_id: leadId || pricingPlan?.lead_id,
        items: []
      });
      toast.success('SOW created successfully');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create SOW');
    }
  };

  const handleSubmitItem = async (e) => {
    e.preventDefault();
    
    if (!formData.title.trim()) {
      toast.error('Title is required');
      return;
    }
    
    try {
      const itemData = {
        category: formData.category,
        sub_category: formData.sub_category || null,
        title: formData.title,
        description: formData.description,
        deliverables: formData.deliverables.filter(d => d.trim()),
        timeline_weeks: formData.timeline_weeks ? parseInt(formData.timeline_weeks) : null,
        order: editingItem ? editingItem.order : (sow?.items?.length || 0)
      };
      
      if (editingItem) {
        await axios.patch(`${API}/sow/${sow.id}/items/${editingItem.id}`, itemData);
        toast.success('SOW item updated');
      } else {
        await axios.post(`${API}/sow/${sow.id}/items`, itemData);
        toast.success('SOW item added');
      }
      
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save SOW item');
    }
  };

  const fetchVersionHistory = async () => {
    try {
      const res = await axios.get(`${API}/sow/${sow.id}/versions`);
      setVersions(res.data.versions || []);
      setVersionDialogOpen(true);
    } catch (error) {
      toast.error('Failed to fetch version history');
    }
  };

  const viewVersion = async (versionNum) => {
    try {
      const res = await axios.get(`${API}/sow/${sow.id}/version/${versionNum}`);
      setSelectedVersion(res.data);
    } catch (error) {
      toast.error('Failed to fetch version');
    }
  };

  const openEditDialog = (item) => {
    setEditingItem(item);
    setFormData({
      category: item.category || 'sales',
      sub_category: item.sub_category || '',
      title: item.title || '',
      description: item.description || '',
      deliverables: item.deliverables?.length > 0 ? item.deliverables : [''],
      timeline_weeks: item.timeline_weeks?.toString() || ''
    });
    setDialogOpen(true);
  };

  const resetForm = () => {
    setEditingItem(null);
    setFormData({
      category: 'sales',
      sub_category: '',
      title: '',
      description: '',
      deliverables: [''],
      timeline_weeks: ''
    });
  };

  const addDeliverable = () => {
    setFormData({
      ...formData,
      deliverables: [...formData.deliverables, '']
    });
  };

  const updateDeliverable = (index, value) => {
    const newDeliverables = [...formData.deliverables];
    newDeliverables[index] = value;
    setFormData({ ...formData, deliverables: newDeliverables });
  };

  const removeDeliverable = (index) => {
    if (formData.deliverables.length > 1) {
      setFormData({
        ...formData,
        deliverables: formData.deliverables.filter((_, i) => i !== index)
      });
    }
  };

  const toggleCategory = (category) => {
    setExpandedCategories({
      ...expandedCategories,
      [category]: !expandedCategories[category]
    });
  };

  const getItemsByCategory = (category) => {
    return sow?.items?.filter(item => item.category === category) || [];
  };

  const canEdit = !sow?.is_frozen || user?.role === 'admin';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  return (
    <div data-testid="sow-builder-page">
      {/* Header */}
      <div className="mb-6">
        <Button
          onClick={() => navigate('/sales-funnel/pricing-plans')}
          variant="ghost"
          className="mb-4 hover:bg-zinc-100 rounded-sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Back to Pricing Plans
        </Button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight uppercase text-zinc-950 mb-2">
              Scope of Work
            </h1>
            <p className="text-zinc-500">
              {lead ? `${lead.first_name} ${lead.last_name} - ${lead.company}` : 'Loading...'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {sow && (
              <>
                <Button
                  onClick={fetchVersionHistory}
                  variant="outline"
                  className="rounded-sm"
                  data-testid="view-history-btn"
                >
                  <History className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Version History
                </Button>
                {canEdit && (
                  <Button
                    onClick={() => { resetForm(); setDialogOpen(true); }}
                    className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
                    data-testid="add-item-btn"
                  >
                    <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                    Add Item
                  </Button>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Freeze Alert */}
      {sow?.is_frozen && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-sm flex items-center gap-3">
          <Lock className="w-5 h-5 text-amber-600" />
          <div>
            <div className="font-medium text-amber-800">SOW is Frozen</div>
            <div className="text-sm text-amber-600">
              {user?.role === 'admin' ? 'As Admin, you can still edit.' : 'Contact Admin to make changes.'}
            </div>
          </div>
        </div>
      )}

      {/* Version Info */}
      {sow && (
        <div className="mb-6 flex items-center gap-4 text-sm text-zinc-500">
          <span>Version: <strong className="text-zinc-700">{sow.current_version}</strong></span>
          <span>|</span>
          <span>Items: <strong className="text-zinc-700">{sow.items?.length || 0}</strong></span>
          {sow.is_frozen && (
            <>
              <span>|</span>
              <span className="flex items-center gap-1">
                <Lock className="w-3 h-3" /> Frozen
              </span>
            </>
          )}
        </div>
      )}

      {/* No SOW Yet */}
      {!sow && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FileText className="w-16 h-16 text-zinc-300 mb-4" strokeWidth={1} />
            <h3 className="text-lg font-medium text-zinc-700 mb-2">No SOW Created</h3>
            <p className="text-zinc-500 mb-6 text-center max-w-md">
              Create a Scope of Work to define deliverables, timelines, and categories for this project.
            </p>
            <Button
              onClick={handleCreateSOW}
              className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
              data-testid="create-sow-btn"
            >
              <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Create SOW
            </Button>
          </CardContent>
        </Card>
      )}

      {/* SOW Categories */}
      {sow && (
        <div className="space-y-4">
          {SOW_CATEGORIES.map(category => {
            const items = getItemsByCategory(category.value);
            const isExpanded = expandedCategories[category.value];
            
            return (
              <Card key={category.value} className="border-zinc-200 shadow-none rounded-sm overflow-hidden">
                <div
                  className="flex items-center justify-between px-4 py-3 bg-zinc-50 cursor-pointer hover:bg-zinc-100 transition-colors"
                  onClick={() => toggleCategory(category.value)}
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5 text-zinc-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-zinc-400" />
                    )}
                    <h3 className="font-semibold text-zinc-950">{category.label}</h3>
                    <span className="text-xs px-2 py-1 bg-zinc-200 text-zinc-600 rounded-sm">
                      {items.length} items
                    </span>
                  </div>
                  {canEdit && (
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        resetForm();
                        setFormData(prev => ({ ...prev, category: category.value }));
                        setDialogOpen(true);
                      }}
                      variant="ghost"
                      size="sm"
                      className="text-zinc-600 hover:text-zinc-900"
                    >
                      <Plus className="w-4 h-4 mr-1" /> Add
                    </Button>
                  )}
                </div>
                
                {isExpanded && (
                  <CardContent className="p-4">
                    {items.length === 0 ? (
                      <div className="text-center py-6 text-zinc-400">
                        No items in this category
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {items.map((item, idx) => (
                          <div
                            key={item.id}
                            className="p-4 border border-zinc-100 rounded-sm hover:border-zinc-200 transition-colors"
                            data-testid={`sow-item-${item.id}`}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-xs font-medium text-zinc-400">{idx + 1}.</span>
                                  <h4 className="font-medium text-zinc-950">{item.title}</h4>
                                  {item.timeline_weeks && (
                                    <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-sm flex items-center gap-1">
                                      <Clock className="w-3 h-3" />
                                      {item.timeline_weeks}w
                                    </span>
                                  )}
                                </div>
                                {item.description && (
                                  <p className="text-sm text-zinc-600 mb-2">{item.description}</p>
                                )}
                                {item.deliverables?.length > 0 && (
                                  <div className="mt-2">
                                    <div className="text-xs uppercase tracking-wide text-zinc-400 mb-1">Deliverables</div>
                                    <ul className="text-sm text-zinc-600 list-disc list-inside space-y-1">
                                      {item.deliverables.map((d, i) => (
                                        <li key={i}>{d}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                              {canEdit && (
                                <Button
                                  onClick={() => openEditDialog(item)}
                                  variant="ghost"
                                  size="sm"
                                  className="text-zinc-500 hover:text-zinc-700"
                                >
                                  <Edit2 className="w-4 h-4" />
                                </Button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {/* Proceed to Quotation */}
      {sow && sow.items?.length > 0 && (
        <div className="mt-8 flex justify-end">
          <Button
            onClick={() => navigate(`/sales-funnel/quotations?pricing_plan_id=${pricingPlanId}`)}
            className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
          >
            Proceed to Quotation
            <ChevronRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      )}

      {/* Add/Edit Item Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              {editingItem ? 'Edit SOW Item' : 'Add SOW Item'}
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              Define scope, deliverables, and timeline
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmitItem} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Category *</Label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent"
                >
                  {SOW_CATEGORIES.map(cat => (
                    <option key={cat.value} value={cat.value}>{cat.label}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label>Sub-Category</Label>
                <Input
                  value={formData.sub_category}
                  onChange={(e) => setFormData({ ...formData, sub_category: e.target.value })}
                  placeholder="Optional"
                  className="rounded-sm"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Title *</Label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Scope item title"
                required
                className="rounded-sm"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Description</Label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
                placeholder="Detailed description..."
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-zinc-950"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Deliverables</Label>
              {formData.deliverables.map((d, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input
                    value={d}
                    onChange={(e) => updateDeliverable(idx, e.target.value)}
                    placeholder={`Deliverable ${idx + 1}`}
                    className="rounded-sm"
                  />
                  {formData.deliverables.length > 1 && (
                    <Button
                      type="button"
                      onClick={() => removeDeliverable(idx)}
                      variant="ghost"
                      size="sm"
                      className="text-red-500 px-2"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
              <Button
                type="button"
                onClick={addDeliverable}
                variant="outline"
                size="sm"
                className="rounded-sm"
              >
                <Plus className="w-4 h-4 mr-1" /> Add Deliverable
              </Button>
            </div>
            
            <div className="space-y-2">
              <Label>Timeline (weeks)</Label>
              <Input
                type="number"
                min="1"
                value={formData.timeline_weeks}
                onChange={(e) => setFormData({ ...formData, timeline_weeks: e.target.value })}
                placeholder="e.g., 4"
                className="rounded-sm"
              />
            </div>
            
            <Button
              type="submit"
              className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none"
            >
              {editingItem ? 'Update Item' : 'Add Item'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Version History Dialog */}
      <Dialog open={versionDialogOpen} onOpenChange={setVersionDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Version History
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              View all changes made to this SOW
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {versions.length === 0 ? (
              <p className="text-zinc-500 text-center py-8">No version history available</p>
            ) : (
              <div className="space-y-3">
                {versions.map((version, idx) => (
                  <div
                    key={version.version}
                    className={`p-4 border rounded-sm cursor-pointer transition-colors ${
                      selectedVersion?.version === version.version
                        ? 'border-zinc-950 bg-zinc-50'
                        : 'border-zinc-200 hover:border-zinc-300'
                    }`}
                    onClick={() => viewVersion(version.version)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-zinc-950">Version {version.version}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-sm ${
                          version.change_type === 'created' ? 'bg-emerald-100 text-emerald-700' :
                          version.change_type === 'item_added' ? 'bg-blue-100 text-blue-700' :
                          'bg-amber-100 text-amber-700'
                        }`}>
                          {version.change_type.replace('_', ' ')}
                        </span>
                        {idx === 0 && (
                          <span className="text-xs px-2 py-0.5 bg-zinc-900 text-white rounded-sm">Current</span>
                        )}
                      </div>
                      <span className="text-xs text-zinc-500">
                        {format(new Date(version.changed_at), 'MMM d, yyyy HH:mm')}
                      </span>
                    </div>
                    <div className="text-sm text-zinc-600">
                      By: {version.changed_by_name || 'Unknown'}
                    </div>
                    {version.changes && Object.keys(version.changes).length > 0 && (
                      <div className="mt-2 text-xs text-zinc-500">
                        Changes: {JSON.stringify(version.changes).substring(0, 100)}...
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {selectedVersion && (
              <div className="mt-6 p-4 bg-zinc-50 rounded-sm">
                <h4 className="font-semibold mb-3">Version {selectedVersion.version} Snapshot</h4>
                <div className="space-y-2">
                  {selectedVersion.items?.map((item, idx) => (
                    <div key={idx} className="text-sm p-2 bg-white rounded border border-zinc-200">
                      <span className="font-medium">{item.title}</span>
                      <span className="text-zinc-500 ml-2">({item.category})</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SOWBuilder;
