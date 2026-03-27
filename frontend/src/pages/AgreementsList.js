/**
 * AgreementsList.js - Agreements Management Page
 * 
 * Features:
 * - Table view: Agreement No, Client Name, Start Date, End Date, Version, Actions
 * - Actions: View, Edit, Download (PDF/DOCX)
 * - Version dropdown with history
 * - RBAC: Admin + Sales only
 * - Auto-sync indicator
 */

import React, { useState, useContext } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { API, AuthContext } from '../App';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '../components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
  Search,
  Eye,
  Edit,
  Download,
  MoreVertical,
  RefreshCw,
  History,
  FileText,
  FileDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from 'lucide-react';

const AgreementsList = () => {
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [editDialog, setEditDialog] = useState({ open: false, agreement: null });
  const [versionDialog, setVersionDialog] = useState({ open: false, agreementId: null });
  const [editForm, setEditForm] = useState({
    start_date: '',
    end_date: '',
    total_value: '',
    duration_months: '',
    notes: ''
  });

  // Fetch agreements list
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['agreements-management', page, search],
    queryFn: async () => {
      const params = new URLSearchParams({ page, page_size: 25 });
      if (search) params.append('search', search);
      const res = await axios.get(`${API}/agreements/management/list?${params}`);
      return res.data;
    },
  });

  // Fetch version history
  const { data: versionData, isLoading: loadingVersions } = useQuery({
    queryKey: ['agreement-versions', versionDialog.agreementId],
    queryFn: async () => {
      if (!versionDialog.agreementId) return null;
      const res = await axios.get(`${API}/agreements/${versionDialog.agreementId}/versions`);
      return res.data;
    },
    enabled: !!versionDialog.agreementId,
  });

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: async (agreementId) => {
      const res = await axios.post(`${API}/agreements/${agreementId}/sync`);
      return res.data;
    },
    onSuccess: (data) => {
      if (data.synced) {
        toast.success(data.message);
        queryClient.invalidateQueries(['agreements-management']);
      } else {
        toast.info(data.message);
      }
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Sync failed');
    },
  });

  // Edit mutation
  const editMutation = useMutation({
    mutationFn: async ({ agreementId, data }) => {
      const res = await axios.put(`${API}/agreements/${agreementId}/edit`, data);
      return res.data;
    },
    onSuccess: (data) => {
      if (data.updated) {
        toast.success(data.message);
        setEditDialog({ open: false, agreement: null });
        queryClient.invalidateQueries(['agreements-management']);
      } else {
        toast.info(data.message);
      }
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Update failed');
    },
  });

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    refetch();
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      const dt = new Date(dateStr);
      const day = String(dt.getDate()).padStart(2, '0');
      const month = String(dt.getMonth() + 1).padStart(2, '0');
      const year = dt.getFullYear();
      return `${day}-${month}-${year}`;
    } catch {
      return dateStr;
    }
  };

  const openEditDialog = (agreement) => {
    setEditForm({
      start_date: agreement.start_date || '',
      end_date: agreement.end_date || '',
      total_value: agreement.total_value || '',
      duration_months: agreement.duration_months || '',
      notes: ''
    });
    setEditDialog({ open: true, agreement });
  };

  const handleEditSubmit = () => {
    const data = {};
    if (editForm.start_date) data.start_date = editForm.start_date;
    if (editForm.end_date) data.end_date = editForm.end_date;
    if (editForm.total_value) data.total_value = parseFloat(editForm.total_value);
    if (editForm.duration_months) data.duration_months = parseInt(editForm.duration_months);
    if (editForm.notes) data.notes = editForm.notes;
    
    editMutation.mutate({ agreementId: editDialog.agreement.id, data });
  };

  const handleDownload = async (agreementId, format) => {
    try {
      // Navigate to agreement view for download
      window.open(`/agreements/${agreementId}?download=${format}`, '_blank');
    } catch (err) {
      toast.error('Download failed');
    }
  };

  const agreements = data?.data || [];
  const total = data?.total || 0;
  const totalPages = data?.total_pages || 1;

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="agreements-list-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Agreements</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Manage all generated agreements</p>
        </div>
        <Badge variant="outline" className="text-xs">
          {total} Agreement{total !== 1 ? 's' : ''}
        </Badge>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <Input
            placeholder="Search by Agreement No or Client..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            data-testid="agreements-search-input"
          />
        </div>
        <Button type="submit" variant="outline" data-testid="agreements-search-btn">
          Search
        </Button>
      </form>

      {/* Table */}
      <div className="border rounded-lg overflow-hidden dark:border-zinc-800">
        <Table>
          <TableHeader>
            <TableRow className="bg-zinc-50 dark:bg-zinc-900">
              <TableHead className="font-semibold">Agreement No</TableHead>
              <TableHead className="font-semibold">Client Name</TableHead>
              <TableHead className="font-semibold">Start Date</TableHead>
              <TableHead className="font-semibold">End Date</TableHead>
              <TableHead className="font-semibold text-center">Version</TableHead>
              <TableHead className="font-semibold text-center">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto text-zinc-400" />
                </TableCell>
              </TableRow>
            ) : agreements.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-zinc-500">
                  No agreements found
                </TableCell>
              </TableRow>
            ) : (
              agreements.map((agr) => (
                <TableRow key={agr.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/50">
                  <TableCell className="font-mono text-sm" data-testid={`agreement-row-${agr.id}`}>
                    {agr.agreement_number}
                  </TableCell>
                  <TableCell className="font-medium">{agr.client_name || '-'}</TableCell>
                  <TableCell>{formatDate(agr.start_date)}</TableCell>
                  <TableCell>{formatDate(agr.end_date)}</TableCell>
                  <TableCell className="text-center">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-7 px-2">
                          <Badge variant="secondary" className="cursor-pointer">
                            v{agr.version || 1}
                          </Badge>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="center">
                        <DropdownMenuItem onClick={() => setVersionDialog({ open: true, agreementId: agr.id })}>
                          <History className="w-4 h-4 mr-2" />
                          View Version History
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                  <TableCell className="text-center">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" data-testid={`agreement-actions-${agr.id}`}>
                          <MoreVertical className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => navigate(`/agreements/${agr.id}?leadId=${agr.lead_id}`)}>
                          <Eye className="w-4 h-4 mr-2" />
                          View
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => openEditDialog(agr)}>
                          <Edit className="w-4 h-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => handleDownload(agr.id, 'pdf')}>
                          <FileText className="w-4 h-4 mr-2" />
                          Download PDF
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDownload(agr.id, 'docx')}>
                          <FileDown className="w-4 h-4 mr-2" />
                          Download DOCX
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem 
                          onClick={() => syncMutation.mutate(agr.id)}
                          disabled={syncMutation.isPending}
                        >
                          <RefreshCw className={`w-4 h-4 mr-2 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
                          Sync from Funnel
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-zinc-500">
            Page {page} of {totalPages} ({total} total)
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              <ChevronLeft className="w-4 h-4 mr-1" /> Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
            >
              Next <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={editDialog.open} onOpenChange={(open) => setEditDialog({ open, agreement: editDialog.agreement })}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Agreement</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <p className="text-sm text-zinc-500">
              Editing: <strong>{editDialog.agreement?.agreement_number}</strong>
              <br />
              <span className="text-xs">Changes will create a new version (v{(editDialog.agreement?.version || 1) + 1})</span>
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="start_date">Start Date</Label>
                <Input
                  id="start_date"
                  type="date"
                  value={editForm.start_date}
                  onChange={(e) => setEditForm({ ...editForm, start_date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end_date">End Date</Label>
                <Input
                  id="end_date"
                  type="date"
                  value={editForm.end_date}
                  onChange={(e) => setEditForm({ ...editForm, end_date: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="total_value">Total Value (INR)</Label>
                <Input
                  id="total_value"
                  type="number"
                  value={editForm.total_value}
                  onChange={(e) => setEditForm({ ...editForm, total_value: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="duration_months">Duration (Months)</Label>
                <Input
                  id="duration_months"
                  type="number"
                  value={editForm.duration_months}
                  onChange={(e) => setEditForm({ ...editForm, duration_months: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Edit Reason / Notes</Label>
              <Input
                id="notes"
                placeholder="Reason for edit..."
                value={editForm.notes}
                onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialog({ open: false, agreement: null })}>
              Cancel
            </Button>
            <Button onClick={handleEditSubmit} disabled={editMutation.isPending}>
              {editMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Version History Dialog */}
      <Dialog open={versionDialog.open} onOpenChange={(open) => setVersionDialog({ open, agreementId: open ? versionDialog.agreementId : null })}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Version History</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            {loadingVersions ? (
              <div className="text-center py-4">
                <Loader2 className="w-6 h-6 animate-spin mx-auto" />
              </div>
            ) : versionData ? (
              <div className="space-y-3">
                <p className="text-sm text-zinc-500 mb-4">
                  Agreement: <strong>{versionData.agreement_number}</strong>
                </p>
                {versionData.versions?.map((v, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg border ${v.is_current ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800' : 'bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800'}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant={v.is_current ? 'default' : 'secondary'}>v{v.version}</Badge>
                        {v.is_current && <span className="text-xs text-green-600 dark:text-green-400">Current</span>}
                      </div>
                      <span className="text-xs text-zinc-500">{formatDate(v.created_at)}</span>
                    </div>
                    {v.changes && (
                      <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
                        Changes: {v.changes}
                      </p>
                    )}
                    {v.archived_by && (
                      <p className="text-xs text-zinc-500 mt-1">By: {v.archived_by}</p>
                    )}
                    {v.edit_reason && (
                      <p className="text-xs text-zinc-500 mt-1">Reason: {v.edit_reason}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-zinc-500">No version history available</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setVersionDialog({ open: false, agreementId: null })}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AgreementsList;
