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
  CheckCircle, AlertCircle, Clock as ClockIcon, XCircle,
  Users, UserPlus, Calendar, GanttChart, Save, Paperclip
} from 'lucide-react';
import { toast } from 'sonner';
import { format, addWeeks, startOfWeek } from 'date-fns';

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

const BACKEND_SUPPORT_ROLES = [
  { value: 'developer', label: 'Developer' },
  { value: 'designer', label: 'Designer' },
  { value: 'qa', label: 'QA Engineer' },
  { value: 'analyst', label: 'Business Analyst' },
  { value: 'support', label: 'Support Staff' }
];

const SOWBuilder = () => {
  const { pricingPlanId } = useParams();
  const [searchParams] = useSearchParams();
  const leadId = searchParams.get('lead_id');
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);
  const fileInputRefs = useRef({});
  
  const [pricingPlan, setPricingPlan] = useState(null);
  const [lead, setLead] = useState(null);
  const [sow, setSow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [consultants, setConsultants] = useState([]);
  const [backendStaff, setBackendStaff] = useState([]);
  
  // View mode: 'list', 'roadmap', 'gantt'
  const [viewMode, setViewMode] = useState('list');
  
  // Inline editing state
  const [editingRows, setEditingRows] = useState({});
  const [newRows, setNewRows] = useState([]);
  const [savingRows, setSavingRows] = useState({});
  
  // Dialogs
  const [versionDialogOpen, setVersionDialogOpen] = useState(false);
  const [versions, setVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectingItem, setRejectingItem] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [supportDialogOpen, setSupportDialogOpen] = useState(false);
  const [supportItem, setSupportItem] = useState(null);
  const [docsDialogOpen, setDocsDialogOpen] = useState(false);
  const [docsItem, setDocsItem] = useState(null);
  const [userPermissions, setUserPermissions] = useState({});

  // Role-based access control
  // Sales Team (create/edit SOW): admin, executive, account_manager
  // Consulting Team (view, update progress): consultant, lean_consultant, lead_consultant, senior_consultant, principal_consultant, subject_matter_expert
  // PM/Audit (approve, authorize): admin, project_manager, manager
  
  const salesRoles = ['admin', 'executive', 'account_manager'];
  const consultingRoles = ['consultant', 'lean_consultant', 'lead_consultant', 'senior_consultant', 'principal_consultant', 'subject_matter_expert'];
  const pmRoles = ['admin', 'project_manager', 'manager'];
  
  const isSalesTeam = salesRoles.includes(user?.role);
  const isConsultingTeam = consultingRoles.includes(user?.role);
  const isPMTeam = pmRoles.includes(user?.role);
  const isManager = user?.role === 'admin' || user?.role === 'manager' || user?.role === 'project_manager';
  
  // Can create/edit SOW items
  const canCreateSOW = isSalesTeam && (!sow?.is_frozen || user?.role === 'admin');
  const canEditSOW = isSalesTeam && (!sow?.is_frozen || user?.role === 'admin');
  const canEdit = canEditSOW;
  
  // Can update status (consulting team and PM)
  const canUpdateStatus = isConsultingTeam || isPMTeam;
  
  // Can approve/authorize (PM team only)
  const canApprove = isPMTeam;

  useEffect(() => {
    fetchData();
    fetchConsultants();
    fetchBackendStaff();
    fetchUserPermissions();
  }, [pricingPlanId]);

  const fetchUserPermissions = async () => {
    try {
      const res = await axios.get(`${API}/users/me/permissions`);
      setUserPermissions(res.data.sow || {});
    } catch (error) {
      console.error('Error fetching permissions:', error);
    }
  };

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

  const fetchConsultants = async () => {
    try {
      const res = await axios.get(`${API}/consultants`);
      setConsultants(res.data || []);
    } catch (error) {
      console.error('Error fetching consultants:', error);
    }
  };

  const fetchBackendStaff = async () => {
    try {
      const res = await axios.get(`${API}/users`);
      setBackendStaff(res.data || []);
    } catch (error) {
      console.error('Error fetching backend staff:', error);
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

  // Inline editing functions
  const createEmptyRow = () => ({
    id: `new-${Date.now()}`,
    isNew: true,
    category: 'sales',
    title: '',
    description: '',
    timeline_weeks: '',
    start_week: '',
    status: 'draft',
    assigned_consultant_id: '',
    assigned_consultant_name: '',
    has_backend_support: false,
    backend_support_id: '',
    backend_support_name: '',
    backend_support_role: '',
    documents: []
  });

  const addNewRow = () => {
    setNewRows([...newRows, createEmptyRow()]);
  };

  const updateNewRow = (rowId, field, value) => {
    setNewRows(newRows.map(row => 
      row.id === rowId ? { ...row, [field]: value } : row
    ));
  };

  const updateExistingRow = (itemId, field, value) => {
    setEditingRows({
      ...editingRows,
      [itemId]: {
        ...editingRows[itemId],
        [field]: value
      }
    });
  };

  const startEditing = (item) => {
    setEditingRows({
      ...editingRows,
      [item.id]: { ...item }
    });
  };

  const cancelEditing = (itemId) => {
    const newEditingRows = { ...editingRows };
    delete newEditingRows[itemId];
    setEditingRows(newEditingRows);
  };

  const removeNewRow = (rowId) => {
    setNewRows(newRows.filter(row => row.id !== rowId));
  };

  const saveNewRow = async (row) => {
    if (!row.title.trim()) {
      toast.error('Title is required');
      return;
    }
    
    setSavingRows({ ...savingRows, [row.id]: true });
    
    try {
      const itemData = {
        category: row.category,
        title: row.title,
        description: row.description || '',
        timeline_weeks: row.timeline_weeks ? parseInt(row.timeline_weeks) : null,
        start_week: row.start_week ? parseInt(row.start_week) : null,
        status: row.status || 'draft',
        assigned_consultant_id: row.assigned_consultant_id || null,
        assigned_consultant_name: row.assigned_consultant_name || null,
        has_backend_support: row.has_backend_support || false,
        backend_support_id: row.backend_support_id || null,
        backend_support_name: row.backend_support_name || null,
        backend_support_role: row.backend_support_role || null
      };
      
      await axios.post(`${API}/sow/${sow.id}/items`, itemData);
      toast.success('Item added');
      removeNewRow(row.id);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save item');
    } finally {
      setSavingRows({ ...savingRows, [row.id]: false });
    }
  };

  const saveExistingRow = async (itemId) => {
    const row = editingRows[itemId];
    if (!row.title?.trim()) {
      toast.error('Title is required');
      return;
    }
    
    setSavingRows({ ...savingRows, [itemId]: true });
    
    try {
      const itemData = {
        category: row.category,
        title: row.title,
        description: row.description || '',
        timeline_weeks: row.timeline_weeks ? parseInt(row.timeline_weeks) : null,
        start_week: row.start_week ? parseInt(row.start_week) : null,
        status: row.status || 'draft',
        assigned_consultant_id: row.assigned_consultant_id || null,
        assigned_consultant_name: row.assigned_consultant_name || null,
        has_backend_support: row.has_backend_support || false,
        backend_support_id: row.backend_support_id || null,
        backend_support_name: row.backend_support_name || null,
        backend_support_role: row.backend_support_role || null,
        notes: row.notes || null
      };
      
      await axios.patch(`${API}/sow/${sow.id}/items/${itemId}`, itemData);
      toast.success('Item updated');
      cancelEditing(itemId);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update item');
    } finally {
      setSavingRows({ ...savingRows, [itemId]: false });
    }
  };

  const deleteItem = async (itemId) => {
    if (!window.confirm('Are you sure you want to delete this item?')) return;
    
    try {
      await axios.delete(`${API}/sow/${sow.id}/items/${itemId}`);
      toast.success('Item deleted');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete item');
    }
  };

  const handleStatusChange = async (itemId, newStatus) => {
    try {
      // If marking as completed, this will trigger email notification on backend
      await axios.patch(`${API}/sow/${sow.id}/items/${itemId}/status`, {
        status: newStatus,
        notify_on_complete: newStatus === 'completed' // Signal backend to send emails
      });
      
      if (newStatus === 'completed') {
        toast.success('Item marked as completed. Notifications sent to manager and client.');
      } else {
        toast.success(`Status updated to ${newStatus.replace('_', ' ')}`);
      }
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

  // Document handling - per item
  const handleFileUpload = async (file, itemId) => {
    if (!file || !itemId) return;
    
    const reader = new FileReader();
    reader.onload = async (e) => {
      const base64Data = e.target.result.split(',')[1];
      
      try {
        await axios.post(`${API}/sow/${sow.id}/items/${itemId}/documents`, {
          filename: file.name,
          file_data: base64Data,
          description: ''
        });
        
        toast.success('Document uploaded to SOW item');
        fetchData();
      } catch (error) {
        toast.error('Failed to upload document');
      }
    };
    reader.readAsDataURL(file);
  };

  const handleDownload = async (itemId, documentId) => {
    try {
      const res = await axios.get(`${API}/sow/${sow.id}/items/${itemId}/documents/${documentId}`);
      const link = document.createElement('a');
      link.href = `data:application/octet-stream;base64,${res.data.file_data}`;
      link.download = res.data.filename || res.data.original_filename;
      link.click();
    } catch (error) {
      toast.error('Failed to download document');
    }
  };

  const openDocsDialog = (item) => {
    setDocsItem(item);
    setDocsDialogOpen(true);
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

  const openSupportDialog = (item) => {
    setSupportItem(item);
    setSupportDialogOpen(true);
  };

  const saveBackendSupport = async () => {
    if (!supportItem) return;
    
    try {
      const itemData = {
        ...supportItem,
        has_backend_support: true
      };
      
      await axios.patch(`${API}/sow/${sow.id}/items/${supportItem.id}`, itemData);
      toast.success('Backend support assigned');
      setSupportDialogOpen(false);
      setSupportItem(null);
      fetchData();
    } catch (error) {
      toast.error('Failed to assign backend support');
    }
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

  // Calculate roadmap data
  const getRoadmapData = () => {
    if (!sow?.items) return { months: [], itemsByMonth: {} };
    
    const items = sow.items.filter(i => i.timeline_weeks && i.start_week);
    const months = [];
    const itemsByMonth = {};
    
    items.forEach(item => {
      const monthIndex = Math.floor((item.start_week - 1) / 4);
      const monthLabel = `Month ${monthIndex + 1}`;
      
      if (!itemsByMonth[monthLabel]) {
        itemsByMonth[monthLabel] = [];
        months.push(monthLabel);
      }
      itemsByMonth[monthLabel].push(item);
    });
    
    const unscheduled = sow.items.filter(i => !i.start_week);
    if (unscheduled.length > 0) {
      itemsByMonth['Unscheduled'] = unscheduled;
      months.push('Unscheduled');
    }
    
    return { months: [...new Set(months)].sort(), itemsByMonth };
  };

  // Gantt chart data
  const getGanttData = () => {
    if (!sow?.items) return [];
    
    return sow.items.map(item => ({
      ...item,
      startWeek: item.start_week || 1,
      endWeek: (item.start_week || 1) + (item.timeline_weeks || 1) - 1
    }));
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96"><div className="text-zinc-500">Loading...</div></div>;
  }

  // Render inline editable row
  const renderEditableRow = (item, isNew = false) => {
    const data = isNew ? item : (editingRows[item.id] || item);
    const isEditing = isNew || editingRows[item.id];
    const isSaving = savingRows[item.id];
    const docCount = item.documents?.length || 0;
    
    const updateField = (field, value) => {
      if (isNew) {
        updateNewRow(item.id, field, value);
      } else {
        updateExistingRow(item.id, field, value);
      }
    };

    const handleConsultantChange = (consultantId) => {
      const consultant = consultants.find(c => c.id === consultantId);
      if (isNew) {
        updateNewRow(item.id, 'assigned_consultant_id', consultantId);
        updateNewRow(item.id, 'assigned_consultant_name', consultant?.full_name || '');
      } else {
        updateExistingRow(item.id, 'assigned_consultant_id', consultantId);
        updateExistingRow(item.id, 'assigned_consultant_name', consultant?.full_name || '');
      }
    };

    return (
      <tr key={item.id} className={`border-b border-zinc-100 ${isEditing ? 'bg-blue-50' : 'hover:bg-zinc-50'}`} data-testid={`sow-row-${item.id}`}>
        <td className="px-2 py-2 w-10 text-zinc-400 text-sm">
          {isNew ? 'NEW' : (sow?.items?.findIndex(i => i.id === item.id) + 1)}
        </td>
        <td className="px-2 py-2 w-28">
          {isEditing ? (
            <select
              value={data.category}
              onChange={(e) => updateField('category', e.target.value)}
              className="w-full h-8 px-2 text-xs rounded border border-zinc-300 bg-white"
            >
              {SOW_CATEGORIES.map(cat => (
                <option key={cat.value} value={cat.value}>{cat.label}</option>
              ))}
            </select>
          ) : (
            <span className="text-xs px-2 py-1 bg-zinc-100 text-zinc-700 rounded-sm capitalize">
              {item.category?.replace('_', ' ')}
            </span>
          )}
        </td>
        <td className="px-2 py-2 min-w-[180px]">
          {isEditing ? (
            <Input
              value={data.title}
              onChange={(e) => updateField('title', e.target.value)}
              placeholder="Enter title..."
              className="h-8 text-sm"
            />
          ) : (
            <div>
              <div className="font-medium text-zinc-900 text-sm">{item.title}</div>
              {item.description && <div className="text-xs text-zinc-500 truncate">{item.description}</div>}
            </div>
          )}
        </td>
        <td className="px-2 py-2 w-14">
          {isEditing ? (
            <Input
              type="number"
              min="1"
              value={data.start_week || ''}
              onChange={(e) => updateField('start_week', e.target.value)}
              placeholder="Wk"
              className="h-8 text-sm w-14"
            />
          ) : (
            <span className="text-sm text-zinc-600">{item.start_week ? `W${item.start_week}` : '-'}</span>
          )}
        </td>
        <td className="px-2 py-2 w-14">
          {isEditing ? (
            <Input
              type="number"
              min="1"
              value={data.timeline_weeks || ''}
              onChange={(e) => updateField('timeline_weeks', e.target.value)}
              placeholder="Wks"
              className="h-8 text-sm w-14"
            />
          ) : (
            <span className="text-sm text-zinc-600">{item.timeline_weeks ? `${item.timeline_weeks}w` : '-'}</span>
          )}
        </td>
        <td className="px-2 py-2 w-28">
          {isEditing ? (
            <select
              value={data.assigned_consultant_id || ''}
              onChange={(e) => handleConsultantChange(e.target.value)}
              className="w-full h-8 px-2 text-xs rounded border border-zinc-300 bg-white"
            >
              <option value="">Select...</option>
              {consultants.map(c => (
                <option key={c.id} value={c.id}>{c.full_name}</option>
              ))}
            </select>
          ) : (
            <span className="text-xs text-zinc-600">
              {item.assigned_consultant_name || '-'}
            </span>
          )}
        </td>
        <td className="px-2 py-2 w-24">
          {!isNew && (
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
              disabled={!canUpdateStatus && !canApprove}
              className={`h-8 px-2 text-xs rounded border w-full ${
                item.status === 'approved' ? 'border-emerald-300 text-emerald-700 bg-emerald-50' :
                item.status === 'rejected' ? 'border-red-300 text-red-700 bg-red-50' :
                item.status === 'pending_review' ? 'border-yellow-300 text-yellow-700 bg-yellow-50' :
                item.status === 'completed' ? 'border-green-300 text-green-700 bg-green-50' :
                item.status === 'in_progress' ? 'border-blue-300 text-blue-700 bg-blue-50' :
                'border-zinc-200 text-zinc-700 bg-white'
              }`}
            >
              {SOW_ITEM_STATUSES.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          )}
        </td>
        {/* Documents Column - per item */}
        <td className="px-2 py-2 w-20">
          {!isNew && (
            <div className="flex items-center gap-1">
              <Button
                onClick={() => openDocsDialog(item)}
                variant="ghost"
                size="sm"
                className={`h-7 px-2 text-xs ${docCount > 0 ? 'text-blue-600 bg-blue-50' : 'text-zinc-500'}`}
                title={`${docCount} document(s)`}
              >
                <Paperclip className="w-3 h-3 mr-1" />
                {docCount}
              </Button>
            </div>
          )}
        </td>
        {/* Support Column */}
        <td className="px-2 py-2 w-16">
          {!isNew && (
            <div className="flex items-center gap-1">
              {item.has_backend_support ? (
                <span className="text-xs text-blue-600 font-medium px-1.5 py-0.5 bg-blue-50 rounded" title={`${item.backend_support_name} (${item.backend_support_role})`}>
                  {item.backend_support_role?.charAt(0).toUpperCase() || 'S'}
                </span>
              ) : (
                <Button
                  onClick={() => openSupportDialog(item)}
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 text-zinc-400 hover:text-zinc-600"
                  title="Add Backend Support"
                >
                  <UserPlus className="w-3 h-3" />
                </Button>
              )}
            </div>
          )}
        </td>
        <td className="px-2 py-2 w-24">
          <div className="flex items-center gap-1">
            {isEditing ? (
              <>
                <Button
                  onClick={() => isNew ? saveNewRow(item) : saveExistingRow(item.id)}
                  disabled={isSaving}
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                >
                  <Save className="w-3 h-3 mr-1" />
                  {isSaving ? '...' : 'Save'}
                </Button>
                <Button
                  onClick={() => isNew ? removeNewRow(item.id) : cancelEditing(item.id)}
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 text-zinc-500"
                >
                  <X className="w-4 h-4" />
                </Button>
              </>
            ) : (
              <>
                {/* Sales team can edit */}
                {canEditSOW && (
                  <Button onClick={() => startEditing(item)} variant="ghost" size="sm" className="h-7 w-7 p-0 text-zinc-600">
                    <Edit2 className="w-3 h-3" />
                  </Button>
                )}
                {canEditSOW && (
                  <Button onClick={() => deleteItem(item.id)} variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-500">
                    <Trash2 className="w-3 h-3" />
                  </Button>
                )}
                {/* PM team can approve/reject pending items */}
                {canApprove && item.status === 'pending_review' && (
                  <>
                    <Button
                      onClick={() => handleStatusChange(item.id, 'approved')}
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-emerald-600"
                      title="Approve"
                    >
                      <Check className="w-4 h-4" />
                    </Button>
                    <Button
                      onClick={() => { setRejectingItem(item); setRejectDialogOpen(true); }}
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-red-600"
                      title="Reject"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </>
                )}
              </>
            )}
          </div>
        </td>
      </tr>
    );
  };

  // Roadmap View
  const renderRoadmapView = () => {
    const { months, itemsByMonth } = getRoadmapData();
    
    return (
      <div className="space-y-6">
        {months.length === 0 ? (
          <div className="text-center py-12 text-zinc-400">
            No items with timeline data. Add start week and duration to items to see the roadmap.
          </div>
        ) : (
          months.map(month => (
            <Card key={month} className="border-zinc-200 shadow-none rounded-sm">
              <CardHeader className="pb-2 bg-zinc-50">
                <CardTitle className="text-sm font-medium uppercase tracking-wide text-zinc-700 flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  {month}
                  <span className="text-xs font-normal text-zinc-500">({itemsByMonth[month]?.length || 0} items)</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y divide-zinc-100">
                  {itemsByMonth[month]?.map((item, idx) => (
                    <div key={item.id} className="px-4 py-3 flex items-center justify-between hover:bg-zinc-50">
                      <div className="flex items-center gap-3">
                        <span className="text-xs px-2 py-1 bg-zinc-100 text-zinc-600 rounded-sm capitalize">
                          {item.category?.replace('_', ' ')}
                        </span>
                        <div>
                          <div className="font-medium text-sm text-zinc-900">{item.title}</div>
                          <div className="text-xs text-zinc-500">
                            {item.timeline_weeks}w • {item.assigned_consultant_name || 'Unassigned'}
                            {item.documents?.length > 0 && <span className="ml-2 text-blue-500">📎 {item.documents.length}</span>}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-1 rounded-sm ${
                          item.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                          item.status === 'completed' ? 'bg-green-100 text-green-700' :
                          item.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                          'bg-zinc-100 text-zinc-600'
                        }`}>
                          {item.status?.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    );
  };

  // Gantt View
  const renderGanttView = () => {
    const items = getGanttData();
    const maxWeek = Math.max(...items.map(i => i.endWeek), 12);
    const weeks = Array.from({ length: maxWeek }, (_, i) => i + 1);
    
    return (
      <div className="overflow-x-auto">
        <div className="min-w-[1200px]">
          {/* Header */}
          <div className="flex border-b border-zinc-200 bg-zinc-50">
            <div className="w-64 px-4 py-2 font-medium text-xs uppercase tracking-wide text-zinc-500 border-r border-zinc-200">
              Task
            </div>
            <div className="flex-1 flex">
              {weeks.map(week => (
                <div key={week} className="flex-1 px-1 py-2 text-center text-xs text-zinc-500 border-r border-zinc-100">
                  W{week}
                </div>
              ))}
            </div>
          </div>
          
          {/* Rows */}
          {items.map((item, idx) => (
            <div key={item.id} className="flex border-b border-zinc-100 hover:bg-zinc-50">
              <div className="w-64 px-4 py-3 border-r border-zinc-200">
                <div className="font-medium text-sm text-zinc-900 truncate">{item.title}</div>
                <div className="text-xs text-zinc-500">
                  {item.assigned_consultant_name || 'Unassigned'}
                  {item.documents?.length > 0 && <span className="ml-2 text-blue-500">📎 {item.documents.length}</span>}
                </div>
              </div>
              <div className="flex-1 flex relative py-2">
                {weeks.map(week => (
                  <div key={week} className="flex-1 border-r border-zinc-50" />
                ))}
                {/* Gantt Bar */}
                <div
                  className={`absolute h-6 rounded-sm top-1/2 -translate-y-1/2 ${
                    item.status === 'completed' ? 'bg-green-500' :
                    item.status === 'in_progress' ? 'bg-blue-500' :
                    item.status === 'approved' ? 'bg-emerald-500' :
                    'bg-zinc-400'
                  }`}
                  style={{
                    left: `${((item.startWeek - 1) / maxWeek) * 100}%`,
                    width: `${((item.endWeek - item.startWeek + 1) / maxWeek) * 100}%`,
                    minWidth: '20px'
                  }}
                  title={`${item.title}: Week ${item.startWeek} - ${item.endWeek}`}
                />
              </div>
            </div>
          ))}
          
          {items.length === 0 && (
            <div className="text-center py-12 text-zinc-400">
              No items with timeline data. Add start week and duration to items to see the Gantt chart.
            </div>
          )}
        </div>
      </div>
    );
  };

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
                {sow.is_frozen && (
                  <span className="flex items-center gap-1 text-xs text-orange-600 bg-orange-50 px-2 py-1 rounded-sm">
                    <Lock className="w-3 h-3" /> Frozen
                  </span>
                )}
                <Button onClick={fetchVersionHistory} variant="outline" className="rounded-sm">
                  <History className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  History
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Stats */}
      {sow && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
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
        </div>
      )}

      {/* View Toggle & Action Buttons */}
      {sow && (
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="flex bg-zinc-100 rounded-sm p-1">
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-1.5 text-sm rounded-sm transition-colors ${
                  viewMode === 'list' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                List
              </button>
              <button
                onClick={() => setViewMode('roadmap')}
                className={`px-3 py-1.5 text-sm rounded-sm transition-colors ${
                  viewMode === 'roadmap' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                <Calendar className="w-4 h-4 inline mr-1" />
                Roadmap
              </button>
              <button
                onClick={() => setViewMode('gantt')}
                className={`px-3 py-1.5 text-sm rounded-sm transition-colors ${
                  viewMode === 'gantt' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                <GanttChart className="w-4 h-4 inline mr-1" />
                Gantt
              </button>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Sales team can submit for approval */}
            {isSalesTeam && !isPMTeam && sow.overall_status === 'draft' && sow.items?.length > 0 && (
              <Button onClick={handleSubmitForApproval} className="bg-yellow-500 text-white hover:bg-yellow-600 rounded-sm shadow-none">
                <Send className="w-4 h-4 mr-2" />
                Submit for Approval
              </Button>
            )}
            {/* PM team can approve all pending items */}
            {canApprove && pendingCount > 0 && (
              <Button onClick={handleApproveAll} className="bg-emerald-600 text-white hover:bg-emerald-700 rounded-sm shadow-none">
                <CheckCircle className="w-4 h-4 mr-2" />
                Approve All ({pendingCount})
              </Button>
            )}
          </div>
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
            <Button onClick={handleCreateSOW} className="bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
              <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Create SOW
            </Button>
          </CardContent>
        </Card>
      )}

      {/* SOW Content based on view mode */}
      {sow && viewMode === 'list' && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-zinc-50 text-xs font-medium uppercase tracking-wide text-zinc-500">
                    <th className="px-2 py-3 text-left w-10">#</th>
                    <th className="px-2 py-3 text-left w-28">Category</th>
                    <th className="px-2 py-3 text-left min-w-[180px]">Title</th>
                    <th className="px-2 py-3 text-left w-14">Start</th>
                    <th className="px-2 py-3 text-left w-14">Dur.</th>
                    <th className="px-2 py-3 text-left w-28">Consultant</th>
                    <th className="px-2 py-3 text-left w-24">Status</th>
                    <th className="px-2 py-3 text-left w-20">Docs</th>
                    <th className="px-2 py-3 text-left w-16">Support</th>
                    <th className="px-2 py-3 text-left w-24">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sow.items?.map((item, idx) => renderEditableRow(item, false))}
                  {newRows.map(row => renderEditableRow(row, true))}
                </tbody>
              </table>
            </div>
            
            {/* Add Row Button - Sales team only */}
            {canCreateSOW && (
              <div className="p-4 border-t border-zinc-100">
                <Button
                  onClick={addNewRow}
                  variant="outline"
                  className="w-full border-dashed border-zinc-300 text-zinc-600 hover:text-zinc-900 hover:border-zinc-400 rounded-sm"
                  data-testid="add-row-btn"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add New Row
                </Button>
              </div>
            )}
            
            {sow.items?.length === 0 && newRows.length === 0 && (
              <div className="text-center py-12 text-zinc-400">
                {canCreateSOW 
                  ? "No SOW items yet. Click \"Add New Row\" to start adding items."
                  : "No SOW items yet. Sales team will add items."
                }
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {sow && viewMode === 'roadmap' && renderRoadmapView()}
      {sow && viewMode === 'gantt' && (
        <Card className="border-zinc-200 shadow-none rounded-sm">
          <CardContent className="p-4">
            {renderGanttView()}
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

      {/* Documents Dialog - Per Item */}
      <Dialog open={docsDialogOpen} onOpenChange={setDocsDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Documents
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {docsItem?.title}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {/* Existing Documents */}
            {docsItem?.documents?.length > 0 ? (
              <div className="space-y-2">
                <Label className="text-xs uppercase text-zinc-500">Attached Files</Label>
                {docsItem.documents.map(doc => (
                  <div key={doc.id} className="flex items-center justify-between p-2 bg-zinc-50 rounded-sm border border-zinc-200">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-zinc-400" />
                      <span className="text-sm text-zinc-700">{doc.original_filename || doc.filename}</span>
                    </div>
                    <Button
                      onClick={() => handleDownload(docsItem.id, doc.id)}
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2"
                    >
                      <Download className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-zinc-400 text-center py-4">
                No documents attached to this item
              </div>
            )}
            
            {/* Upload New Document */}
            <div className="pt-4 border-t border-zinc-200">
              <Label className="text-xs uppercase text-zinc-500 mb-2 block">Upload New Document</Label>
              <input
                type="file"
                id="doc-upload"
                className="hidden"
                onChange={(e) => {
                  handleFileUpload(e.target.files[0], docsItem?.id);
                  e.target.value = '';
                }}
              />
              <Button
                onClick={() => document.getElementById('doc-upload').click()}
                variant="outline"
                className="w-full rounded-sm"
              >
                <Upload className="w-4 h-4 mr-2" />
                Choose File
              </Button>
              <p className="text-xs text-zinc-400 mt-2">
                When SOW item is marked as Completed, documents will be emailed to manager and client.
              </p>
            </div>
          </div>
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

      {/* Backend Support Dialog */}
      <Dialog open={supportDialogOpen} onOpenChange={setSupportDialogOpen}>
        <DialogContent className="border-zinc-200 rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold uppercase text-zinc-950">
              Assign Backend Support
            </DialogTitle>
            <DialogDescription className="text-zinc-500">
              {supportItem?.title}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Support Role</Label>
              <select
                value={supportItem?.backend_support_role || ''}
                onChange={(e) => setSupportItem({ ...supportItem, backend_support_role: e.target.value })}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent"
              >
                <option value="">Select role...</option>
                {BACKEND_SUPPORT_ROLES.map(role => (
                  <option key={role.value} value={role.value}>{role.label}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Support Staff</Label>
              <select
                value={supportItem?.backend_support_id || ''}
                onChange={(e) => {
                  const staff = backendStaff.find(s => s.id === e.target.value);
                  setSupportItem({
                    ...supportItem,
                    backend_support_id: e.target.value,
                    backend_support_name: staff?.full_name || ''
                  });
                }}
                className="w-full h-10 px-3 rounded-sm border border-zinc-200 bg-transparent"
              >
                <option value="">Select staff member...</option>
                {backendStaff.map(staff => (
                  <option key={staff.id} value={staff.id}>{staff.full_name}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-3">
              <Button onClick={() => setSupportDialogOpen(false)} variant="outline" className="flex-1 rounded-sm">
                Cancel
              </Button>
              <Button onClick={saveBackendSupport} className="flex-1 bg-zinc-950 text-white hover:bg-zinc-800 rounded-sm shadow-none">
                Assign Support
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
                        version.change_type === 'document_added' || version.change_type === 'item_document_added' ? 'bg-blue-100 text-blue-700' :
                        version.change_type === 'bulk_items_added' ? 'bg-purple-100 text-purple-700' :
                        'bg-zinc-100 text-zinc-700'
                      }`}>
                        {version.change_type.replace(/_/g, ' ')}
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
                      {selectedVersion.change_type?.replace(/_/g, ' ')}
                    </span>
                  </div>
                  
                  {selectedVersion.changes && Object.keys(selectedVersion.changes).length > 0 && (
                    <div className="bg-zinc-50 p-3 rounded-sm border border-zinc-200">
                      <div className="text-xs font-medium uppercase tracking-wide text-zinc-500 mb-2">Changes Made</div>
                      <div className="space-y-1">
                        {Object.entries(selectedVersion.changes).map(([key, value]) => (
                          <div key={key} className="text-sm">
                            <span className="text-zinc-500">{key.replace(/_/g, ' ')}:</span>{' '}
                            <span className="text-zinc-900 font-medium">
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div>
                    <div className="text-xs font-medium uppercase tracking-wide text-zinc-500 mb-2">
                      SOW Items at this Version ({(selectedVersion.items || selectedVersion.snapshot)?.length || 0})
                    </div>
                    <div className="space-y-2 max-h-[40vh] overflow-y-auto">
                      {(selectedVersion.items || selectedVersion.snapshot)?.map((item, idx) => (
                        <div key={item.id || idx} className="p-2 bg-white border border-zinc-200 rounded-sm">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-xs px-2 py-0.5 bg-zinc-100 text-zinc-600 rounded-sm capitalize">
                                {item.category?.replace('_', ' ')}
                              </span>
                              <span className="font-medium text-sm text-zinc-900">{item.title}</span>
                              {item.documents?.length > 0 && (
                                <span className="text-xs text-blue-500">📎 {item.documents.length}</span>
                              )}
                            </div>
                            <span className={`text-xs px-2 py-0.5 rounded-sm ${
                              item.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                              item.status === 'rejected' ? 'bg-red-100 text-red-700' :
                              item.status === 'completed' ? 'bg-green-100 text-green-700' :
                              item.status === 'pending_review' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-zinc-100 text-zinc-600'
                            }`}>
                              {item.status?.replace('_', ' ') || 'draft'}
                            </span>
                          </div>
                        </div>
                      ))}
                      {(!(selectedVersion.items || selectedVersion.snapshot) || (selectedVersion.items || selectedVersion.snapshot).length === 0) && (
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
