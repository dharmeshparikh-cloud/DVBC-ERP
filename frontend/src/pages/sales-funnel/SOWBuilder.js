import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { API, AuthContext } from '../../App';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { 
  ArrowLeft, Plus, Lock, History, Check, X, Send,
  FileText, Clock, Trash2, Edit2, Eye, Upload, Download,
  CheckCircle, AlertCircle, Clock as ClockIcon, XCircle
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

const SOW_ITEM_STATUSES = [
  { value: 'draft', label: 'Draft', color: 'bg-zinc-100 text-zinc-700', icon: FileText },
  { value: 'pending_review', label: 'Pending Review', color: 'bg-yellow-100 text-yellow-700', icon: ClockIcon },
  { value: 'approved', label: 'Approved', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  { value: 'rejected', label: 'Rejected', color: 'bg-red-100 text-red-700', icon: XCircle },
  { value: 'in_progress', label: 'In Progress', color: 'bg-blue-100 text-blue-700', icon: Clock },
  { value: 'completed', label: 'Completed', color: 'bg-green-100 text-green-700', icon: Check }
];

const SOWBuilder = () => {
  const { pricingPlanId } = useParams();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('lead_id');
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const fileInputRef = useRef(null);
  const itemFileInputRef = useRef(null);
  
  const [pricingPlan, setPricingPlan] = useState(null);
  const [lead, setLead] = useState(null);
  const [sow, setSow] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [versionDialogOpen, setVersionDialogOpen] = useState(false);
  const [versions, setVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [uploadingItem, setUploadingItem] = useState(null);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectingItem, setRejectingItem] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  
  const [formData, setFormData] = useState({
    category: 'sales',
    sub_category: '',
    title: '',
    description: '',
    deliverables: [''],
    timeline_weeks: '',
    notes: ''
  });

  const isManager = user?.role === 'admin' || user?.role === 'manager';
  const canEdit = !sow?.is_frozen || user?.role === 'admin';

  useEffect(() => {
    fetchData();
  }, [pricingPlanId]);

  const fetchData = async () => {
    try {
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
      
      try {
        const sowRes = await axios.get(`${API}/sow/by-pricing-plan/${pricingPlanId}`);
        setSow(sowRes.data);
      } catch (err) {
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
        order: editingItem ? editingItem.order : (sow?.items?.length || 0),
        notes: formData.notes || null
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

  const handleStatusChange = async (itemId, newStatus) => {
    try {
      await axios.patch(`${API}/sow/${sow.id}/items/${itemId}/status`, {
        status: newStatus
      });
      toast.success(`Status updated to ${newStatus.replace('_', ' ')}`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update status');
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }
    
    try {
      await axios.patch(`${API}/sow/${sow.id}/items/${rejectingItem.id}/status`, {
        status: 'rejected',
        rejection_reason: rejectReason
      });
      toast.success('Item rejected');
      setRejectDialogOpen(false);
      setRejectingItem(null);
      setRejectReason('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject');
    }
  };

  const handleSubmitForApproval = async () => {
    try {
      await axios.post(`${API}/sow/${sow.id}/submit-for-approval`);
      toast.success('SOW submitted for manager approval');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit');
    }
  };

  const handleApproveAll = async () => {
    try {
      await axios.post(`${API}/sow/${sow.id}/approve-all`);
      toast.success('All pending items approved');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve');
    }
  };

  const handleFileUpload = async (file, itemId = null) => {
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async (e) => {
      const base64Data = e.target.result.split(',')[1];
      
      try {
        const endpoint = itemId 
          ? `${API}/sow/${sow.id}/items/${itemId}/documents`
          : `${API}/sow/${sow.id}/documents`;
          
        await axios.post(endpoint, {
          filename: file.name,
          file_data: base64Data,
          description: ''
        });
        
        toast.success('Document uploaded');
        fetchData();
      } catch (error) {
        toast.error('Failed to upload document');
      }
    };
    reader.readAsDataURL(file);
  };

  const handleDownload = async (documentId) => {
    try {
      const res = await axios.get(`${API}/sow/${sow.id}/documents/${documentId}`);
      const link = document.createElement('a');
      link.href = `data:application/octet-stream;base64,${res.data.file_data}`;
      link.download = res.data.filename;
      link.click();
    } catch (error) {
      toast.error('Failed to download document');
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
      timeline_weeks: item.timeline_weeks?.toString() || '',
      notes: item.notes || ''
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
      timeline_weeks: '',
      notes: ''
    });
  };

  const addDeliverable = () => {
    setFormData({ ...formData, deliverables: [...formData.deliverables, ''] });
  };

  const updateDeliverable = (index, value) => {
    const newDeliverables = [...formData.deliverables];
    newDeliverables[index] = value;
    setFormData({ ...formData, deliverables: newDeliverables });
  };

  const removeDeliverable = (index) => {
    if (formData.deliverables.length > 1) {
      setFormData({ ...formData, deliverables: formData.deliverables.filter((_, i) => i !== index) });
    }
  };

  const getStatusBadge = (status) => {
    const statusObj = SOW_ITEM_STATUSES.find(s => s.value === status) || SOW_ITEM_STATUSES[0];
    const Icon = statusObj.icon;
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-sm ${statusObj.color}`}>
        <Icon className="w-3 h-3" />
        {statusObj.label}
      </span>
    );
  };

  const getOverallStatusBadge = () => {
    const status = sow?.overall_status || 'draft';
    const colors = {
      draft: 'bg-zinc-100 text-zinc-700',
      pending_approval: 'bg-yellow-100 text-yellow-700',
      partially_approved: 'bg-orange-100 text-orange-700',
      approved: 'bg-emerald-100 text-emerald-700',
      complete: 'bg-green-100 text-green-700'
    };
    return (
      <span className={`px-3 py-1 text-sm font-medium rounded-sm capitalize ${colors[status] || colors.draft}`}>
        {status.replace('_', ' ')}
      </span>
    );
  };

  const pendingCount = sow?.items?.filter(i => i.status === 'pending_review').length || 0;
  const approvedCount = sow?.items?.filter(i => i.status === 'approved').length || 0;
  const completedCount = sow?.items?.filter(i => i.status === 'completed').length || 0;

  if (loading) {
    return <div className="flex items-center justify-center h-96"><div className="text-zinc-500">Loading...</div></div>;
  }

  return (
    <div data-testid="sow-builder-page">
      {/* Header */}
      <div className="mb-6">
        <Button onClick={() => navigate('/sales-funnel/pricing-plans')} variant="ghost" className="mb-4 hover:bg-zinc-100 rounded-sm">
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
                {getOverallStatusBadge()}
                <Button onClick={fetchVersionHistory} variant="outline" className="rounded-sm">
                  <History className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  History
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

      {/* Stats and Actions */}
      {sow && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="py-3 px-4">
              <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Items</div>
              <div className="text-2xl font-semibold text-zinc-950">{sow.items?.length || 0}</div>
            </CardContent>
          </Card>
          <Card className="border-yellow-200 bg-yellow-50 shadow-none rounded-sm">
            <CardContent className="py-3 px-4">
              <div className="text-xs text-yellow-600 uppercase tracking-wide">Pending</div>
              <div className="text-2xl font-semibold text-yellow-700">{pendingCount}</div>
            </CardContent>
          </Card>
          <Card className="border-emerald-200 bg-emerald-50 shadow-none rounded-sm">
            <CardContent className="py-3 px-4">
              <div className="text-xs text-emerald-600 uppercase tracking-wide">Approved</div>
              <div className="text-2xl font-semibold text-emerald-700">{approvedCount}</div>
            </CardContent>
          </Card>
          <Card className="border-green-200 bg-green-50 shadow-none rounded-sm">
            <CardContent className="py-3 px-4">
              <div className="text-xs text-green-600 uppercase tracking-wide">Completed</div>
              <div className="text-2xl font-semibold text-green-700">{completedCount}</div>
            </CardContent>
          </Card>
          <Card className="border-zinc-200 shadow-none rounded-sm">
            <CardContent className="py-3 px-4">
              <div className="text-xs text-zinc-500 uppercase tracking-wide">Documents</div>
              <div className="text-2xl font-semibold text-zinc-950">{sow.documents?.length || 0}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Action Buttons */}
      {sow && (
        <div className="flex items-center gap-3 mb-6">
          {!isManager && sow.overall_status === 'draft' && sow.items?.length > 0 && (
            <Button onClick={handleSubmitForApproval} className="bg-yellow-500 text-white hover:bg-yellow-600 rounded-sm shadow-none">
              <Send className="w-4 h-4 mr-2" />
              Submit for Approval
            </Button>
          )}
          {isManager && pendingCount > 0 && (
            <Button onClick={handleApproveAll} className="bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm shadow-none">
              <CheckCircle className="w-4 h-4 mr-2" />
              Approve All ({pendingCount})
            </Button>
          )}
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files[0])}
          />
          <Button onClick={() => fileInputRef.current?.click()} variant="outline" className="rounded-sm">
            <Upload className="w-4 h-4 mr-2" />
            Upload Document
          </Button>
        </div>
      )}

      {/* SOW Documents */}
      {sow?.documents?.length > 0 && (
        <Card className="border-zinc-200 shadow-none rounded-sm mb-6">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-500">
              Attached Documents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {sow.documents.map(doc => (
                <div key={doc.id} className="flex items-center gap-2 px-3 py-2 bg-zinc-50 rounded-sm border border-zinc-200">
                  <FileText className="w-4 h-4 text-zinc-400" />
                  <span className="text-sm">{doc.original_filename}</span>
                  <Button onClick={() => handleDownload(doc.id)} variant="ghost" size="sm" className="h-6 w-6 p-0">
                    <Download className="w-3 h-3" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
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
            <Button onClick={handleCreateSOW} className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
              <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Create SOW
            </Button>
          </CardContent>
        </Card>
      )}

      {/* SOW Items List View */}
      {sow && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-0">
            {sow.items?.length === 0 ? (
              <div className="text-center py-12 text-zinc-400">
                No SOW items yet. Click "Add Item" to start.
              </div>
            ) : (
              <div className="divide-y divide-zinc-200">
                {/* Table Header */}
                <div className="hidden md:grid grid-cols-12 gap-4 px-4 py-3 bg-zinc-50 text-xs font-medium uppercase tracking-wide text-zinc-500">
                  <div className="col-span-1">#</div>
                  <div className="col-span-2">Category</div>
                  <div className="col-span-3">Title</div>
                  <div className="col-span-1">Timeline</div>
                  <div className="col-span-2">Status</div>
                  <div className="col-span-1">Docs</div>
                  <div className="col-span-2">Actions</div>
                </div>
                
                {sow.items.map((item, idx) => (
                  <div key={item.id} className="grid grid-cols-1 md:grid-cols-12 gap-4 px-4 py-4 hover:bg-zinc-50 transition-colors items-center" data-testid={`sow-item-${item.id}`}>
                    <div className="col-span-1 text-zinc-400 font-mono">{idx + 1}</div>
                    <div className="col-span-2">
                      <span className="text-xs px-2 py-1 bg-zinc-100 text-zinc-700 rounded-sm capitalize">
                        {item.category?.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="col-span-3">
                      <div className="font-medium text-zinc-950">{item.title}</div>
                      {item.description && (
                        <div className="text-xs text-zinc-500 truncate mt-1">{item.description}</div>
                      )}
                    </div>
                    <div className="col-span-1">
                      {item.timeline_weeks ? (
                        <span className="text-sm text-zinc-600">{item.timeline_weeks}w</span>
                      ) : (
                        <span className="text-zinc-400">-</span>
                      )}
                    </div>
                    <div className="col-span-2">
                      {/* Inline Status Dropdown */}
                      <select
                        value={item.status || 'draft'}
                        onChange={(e) => {
                          const newStatus = e.target.value;
                          if (newStatus === 'rejected') {
                            setRejectingItem(item);
                            setRejectDialogOpen(true);
                          } else {
                            handleStatusChange(item.id, newStatus);
                          }
                        }}
                        disabled={!canEdit && !isManager}
                        className={`h-8 px-2 text-xs rounded-sm border bg-transparent w-full ${
                          item.status === 'approved' ? 'border-emerald-300 text-emerald-700' :
                          item.status === 'rejected' ? 'border-red-300 text-red-700' :
                          item.status === 'pending_review' ? 'border-yellow-300 text-yellow-700' :
                          item.status === 'completed' ? 'border-green-300 text-green-700' :
                          item.status === 'in_progress' ? 'border-blue-300 text-blue-700' :
                          'border-zinc-200 text-zinc-700'
                        }`}
                      >
                        {SOW_ITEM_STATUSES.map(s => (
                          <option key={s.value} value={s.value}>{s.label}</option>
                        ))}
                      </select>
                      {item.rejection_reason && (
                        <div className="text-xs text-red-500 mt-1 truncate" title={item.rejection_reason}>
                          Reason: {item.rejection_reason}
                        </div>
                      )}
                    </div>
                    <div className="col-span-1">
                      <div className="flex items-center gap-1">
                        <span className="text-sm text-zinc-600">{item.documents?.length || 0}</span>
                        <input
                          type="file"
                          ref={itemFileInputRef}
                          className="hidden"
                          onChange={(e) => {
                            handleFileUpload(e.target.files[0], uploadingItem);
                            setUploadingItem(null);
                          }}
                        />
                        <Button
                          onClick={() => {
                            setUploadingItem(item.id);
                            setTimeout(() => itemFileInputRef.current?.click(), 0);
                          }}
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                        >
                          <Upload className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                    <div className="col-span-2 flex items-center gap-1">
                      {canEdit && (
                        <Button onClick={() => openEditDialog(item)} variant="ghost" size="sm" className="text-zinc-600">
                          <Edit2 className="w-4 h-4" />
                        </Button>
                      )}
                      {isManager && item.status === 'pending_review' && (
                        <>
                          <Button
                            onClick={() => handleStatusChange(item.id, 'approved')}
                            variant="ghost"
                            size="sm"
                            className="text-emerald-600 hover:text-emerald-700"
                          >
                            <Check className="w-4 h-4" />
                          </Button>
                          <Button
                            onClick={() => { setRejectingItem(item); setRejectDialogOpen(true); }}
                            variant="ghost"
                            size="sm"
                            className="text-red-600 hover:text-red-700"
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Proceed Button */}
      {sow && sow.overall_status === 'approved' && (
        <div className="mt-8 flex justify-end">
          <Button onClick={() => navigate(`/sales-funnel/quotations?pricing_plan_id=${pricingPlanId}`)} className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
            Proceed to Quotation
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
                    <Button type="button" onClick={() => removeDeliverable(idx)} variant="ghost" size="sm" className="text-red-500 px-2">
                      <X className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
              <Button type="button" onClick={addDeliverable} variant="outline" size="sm" className="rounded-sm">
                <Plus className="w-4 h-4 mr-1" /> Add Deliverable
              </Button>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
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
              <div className="space-y-2">
                <Label>Notes</Label>
                <Input
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Internal notes"
                  className="rounded-sm"
                />
              </div>
            </div>
            
            <Button type="submit" className="w-full bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
              {editingItem ? 'Update Item' : 'Add Item'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Reject Item
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {rejectingItem?.title}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Rejection Reason *</Label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                rows={3}
                placeholder="Please provide a reason for rejection..."
                className="w-full px-3 py-2 rounded-sm border border-zinc-200 bg-transparent focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>
            <div className="flex gap-3">
              <Button onClick={() => { setRejectDialogOpen(false); setRejectReason(''); }} variant="outline" className="flex-1 rounded-sm">
                Cancel
              </Button>
              <Button onClick={handleReject} className="flex-1 bg-red-600 text-white hover:bg-red-700 rounded-sm shadow-none">
                Reject
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Version History Dialog */}
      <Dialog open={versionDialogOpen} onOpenChange={(open) => { setVersionDialogOpen(open); if (!open) setSelectedVersion(null); }}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Version History
            </DialogTitle>
          </DialogHeader>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Version List */}
            <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-2">
              <div className="text-xs font-medium uppercase tracking-wide text-zinc-500 mb-2">Select Version</div>
              {versions.map((version, idx) => (
                <div
                  key={version.version}
                  className={`p-3 border rounded-sm cursor-pointer transition-colors ${
                    selectedVersion?.version === version.version ? 'border-zinc-950 bg-zinc-100' : 'border-zinc-200 hover:border-zinc-400'
                  }`}
                  onClick={() => viewVersion(version.version)}
                  data-testid={`version-${version.version}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-zinc-950">v{version.version}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-sm ${
                        version.change_type === 'created' ? 'bg-emerald-100 text-emerald-700' :
                        version.change_type === 'status_changed' ? 'bg-yellow-100 text-yellow-700' :
                        version.change_type === 'document_added' ? 'bg-blue-100 text-blue-700' :
                        'bg-zinc-100 text-zinc-700'
                      }`}>
                        {version.change_type.replace('_', ' ')}
                      </span>
                    </div>
                    <span className="text-xs text-zinc-500">
                      {format(new Date(version.changed_at), 'MMM d, yyyy HH:mm')}
                    </span>
                  </div>
                  <div className="text-xs text-zinc-500">
                    By: {version.changed_by_name || 'Unknown'}
                  </div>
                </div>
              ))}
            </div>
            
            {/* Version Details */}
            <div className="border-l border-zinc-200 pl-4">
              <div className="text-xs font-medium uppercase tracking-wide text-zinc-500 mb-2">Version Details</div>
              {selectedVersion ? (
                <div className="space-y-3" data-testid="version-details">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg font-semibold text-zinc-950">Version {selectedVersion.version}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-sm ${
                      selectedVersion.change_type === 'created' ? 'bg-emerald-100 text-emerald-700' :
                      selectedVersion.change_type === 'status_changed' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-zinc-100 text-zinc-700'
                    }`}>
                      {selectedVersion.change_type?.replace('_', ' ')}
                    </span>
                  </div>
                  
                  {/* Changes Made */}
                  {selectedVersion.changes && Object.keys(selectedVersion.changes).length > 0 && (
                    <div className="bg-zinc-50 p-3 rounded-sm border border-zinc-200">
                      <div className="text-xs font-medium uppercase tracking-wide text-zinc-500 mb-2">Changes Made</div>
                      <div className="space-y-1">
                        {Object.entries(selectedVersion.changes).map(([key, value]) => (
                          <div key={key} className="text-sm">
                            <span className="text-zinc-500">{key.replace('_', ' ')}:</span>{' '}
                            <span className="text-zinc-900 font-medium">
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Snapshot Items */}
                  <div>
                    <div className="text-xs font-medium uppercase tracking-wide text-zinc-500 mb-2">
                      SOW Items at this Version ({selectedVersion.snapshot?.length || 0})
                    </div>
                    <div className="space-y-2 max-h-[40vh] overflow-y-auto">
                      {selectedVersion.snapshot?.map((item, idx) => (
                        <div key={item.id || idx} className="p-2 bg-white border border-zinc-200 rounded-sm">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-xs px-2 py-0.5 bg-zinc-100 text-zinc-600 rounded-sm capitalize">
                                {item.category?.replace('_', ' ')}
                              </span>
                              <span className="font-medium text-sm text-zinc-900">{item.title}</span>
                            </div>
                            <span className={`text-xs px-2 py-0.5 rounded-sm ${
                              item.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                              item.status === 'rejected' ? 'bg-red-100 text-red-700' :
                              item.status === 'pending_review' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-zinc-100 text-zinc-600'
                            }`}>
                              {item.status?.replace('_', ' ') || 'draft'}
                            </span>
                          </div>
                          {item.description && (
                            <p className="text-xs text-zinc-500 mt-1 line-clamp-2">{item.description}</p>
                          )}
                        </div>
                      ))}
                      {(!selectedVersion.snapshot || selectedVersion.snapshot.length === 0) && (
                        <div className="text-sm text-zinc-400 py-4 text-center">No items in this version</div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-48 text-zinc-400 text-sm">
                  <div className="text-center">
                    <Eye className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>Click on a version to view details</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SOWBuilder;
